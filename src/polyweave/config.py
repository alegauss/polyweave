"""What a project declares, and how a value is resolved.

`docs/specs/project-config.md` is the contract. `polyweave.toml` at the project root,
and the plugin ships a default for all of it — **a default that cannot be overridden is
a defect**, and so is a value that can only be set by editing the plugin.

Resolution is explicit argument, then `polyweave.toml`, then the default, evaluated on
every call. The file is therefore read on every `load` rather than held from startup, so
correcting it does not need a session restart. It is a few hundred bytes of TOML; the
read is cheaper than the round trip it saves.

The evidence is §PW5: Cottony's art tools resolve their own repository root from their
own file path and import a palette module that lives beside them, so nothing in them
runs from another repository.
"""

from __future__ import annotations

import difflib
import os
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from .errors import PolyweaveError

FILENAME = "polyweave.toml"

#: `${NAME}`, an environment variable named in the file and resolved per call — which is
#: how a machine-specific path stays out of a file a colleague also reads.
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

#: Tables whose keys a project names itself, so an unknown key in them is not a typo.
#: `render.samples` is keyed by the rung names `render.rungs` declares.
_OPEN_TABLES = ("render.samples",)

#: Only a binary may sit outside the tree. Everything else resolves under
#: `project.root`, because a path elsewhere is state a colleague cannot reproduce.
_BINARIES = ("paths.blender", "paths.godot")

#: Settings that name a file inside the tree although they do not live under `[paths]`.
_INSIDE = ("service.schema",)

#: Every key, with the value used where the project declares none. The shape is the
#: schema: a key absent from here is refused rather than ignored.
DEFAULTS: dict[str, Any] = {
    "project": {
        "name": "",  # the root directory's name, filled in on load
        "root": ".",
    },
    "paths": {
        "blender": "blender",  # found on PATH unless the project says where
        "godot": "godot",
        "meshes": "assets/3d",
        "renders": "docs/renders",
        "specs": "docs/accept",
        "work": ".polyweave",
        # The ledger of what was paid for. Inside the tree and committed with it: a
        # purchase and its record are one artefact (§PW17).
        "purchases": "polyweave.purchases.json",
    },
    "render": {
        "rungs": ["sphere", "preview", "final"],
        "preview_size": 256,
        "final_size": 1024,
        "samples": {"sphere": 32, "preview": 64, "final": 512},
        "seed": 0,
        "max_parallel": 4,
    },
    "tolerance": {
        "alpha_floor": 0.02,
        "render_noise": 0.004,
        "silhouette_iou": 0.97,
        "delta_e": 2.0,
    },
    "cache": {"max_bytes": 8_000_000_000},
    "service": {
        "base": "",  # naming no service is how a project that buys nothing says so
        "key_env": "",
        # What the service was proved to accept, learned by probing (§PW19).
        "schema": "polyweave.service.toml",
    },
    "budget": {
        # No budget is no spend, never an unlimited one: the absence of a ceiling is
        # not read as permission.
        "credits": 0,
        "expires": "",
    },
    "capture": {
        "locale": "",
        "resolution": [1920, 1080],
        # The two that differed between two machines in §PW25, and the reason the list
        # exists at all.
        "declared": ["locale", "resolution"],
    },
    "geometry": {"outlines": ""},
}


class Config:
    """One project's settings, resolved against the plugin's defaults."""

    def __init__(self, root: Path, declared: dict[str, Any], source: Path | None):
        self.root = root
        self.source = source
        self._declared = declared
        self._merged = _merge(DEFAULTS, declared)
        if not self._merged["project"]["name"]:
            self._merged["project"]["name"] = root.name

    # -- reading ----------------------------------------------------------------

    def get(self, address: str, explicit: Any = None) -> Any:
        """Resolve one value: the explicit argument, then the file, then the default."""
        if explicit is not None:
            return explicit
        table, _, key = address.partition(".")
        if not key or table not in DEFAULTS:
            raise PolyweaveError(
                "config.unknown-address",
                f"{address!r} is not a setting",
                f"name one of {', '.join(self.addresses()[:6])}, and so on",
            )
        value = self._merged
        for part in address.split("."):
            if not isinstance(value, dict) or part not in value:
                raise PolyweaveError(
                    "config.unknown-address",
                    f"{address!r} is not a setting",
                    f"read {table} to see what it holds",
                )
            value = value[part]
        return _expand(value, address)

    def path(self, address: str, explicit: str | Path | None = None) -> Path:
        """Resolve a path setting to somewhere inside the tree, absolute.

        Only a binary may be absolute. Everything else is refused where it points out of
        the project, because nothing is written outside it and nothing read from outside
        it is reproducible.
        """
        raw = self.get(address, str(explicit) if explicit is not None else None)
        candidate = Path(str(raw)).expanduser()
        if address in _BINARIES:
            return candidate
        if candidate.is_absolute():
            raise PolyweaveError(
                "config.path-outside",
                f"{address} is {candidate}, which is not inside {self.root}",
                f"write it relative to the project root; only "
                f"{' and '.join(_BINARIES)} may be absolute",
            )
        resolved = (self.root / candidate).resolve()
        if not resolved.is_relative_to(self.root):
            raise PolyweaveError(
                "config.path-outside",
                f"{address} climbs out of {self.root} to {resolved}",
                "write a path that stays inside the project",
            )
        return resolved

    def table(self, name: str) -> dict:
        """One whole table, with every value resolved."""
        if name not in DEFAULTS:
            raise PolyweaveError(
                "config.unknown-address",
                f"there is no [{name}] table",
                f"name one of {', '.join(sorted(DEFAULTS))}",
            )
        return {k: _expand(v, f"{name}.{k}") for k, v in self._merged[name].items()}

    def addresses(self) -> list[str]:
        """Every setting a project may declare, as `table.key`."""
        return [f"{t}.{k}" for t in sorted(DEFAULTS) for k in sorted(DEFAULTS[t])]

    def declared(self, address: str) -> bool:
        """Whether the project stated this itself, rather than taking the default."""
        table, _, key = address.partition(".")
        return key in self._declared.get(table, {})

    # -- the one read that is a decision ---------------------------------------

    def budget(self, today: date | None = None) -> dict:
        """What may be spent, which is a person's decision written down.

        An expired or absent budget means no spend at all. The plugin never reads the
        absence of a ceiling as permission, because the balance being spent is real.
        """
        credits = int(self.get("budget.credits"))
        expires = str(self.get("budget.expires")).strip()
        if credits <= 0:
            return {
                "credits": credits,
                "expires": expires or None,
                "spendable": False,
                "why": f"no credits are declared in [budget] of {FILENAME}",
            }
        if not expires:
            return {
                "credits": credits,
                "expires": None,
                "spendable": False,
                "why": "the budget has no expiry, and one without a date never lapses",
            }
        try:
            when = date.fromisoformat(expires)
        except ValueError:
            raise PolyweaveError(
                "config.bad-type",
                f"[budget] expires is {expires!r}, which is not a date",
                "write it as YYYY-MM-DD",
            ) from None
        if when < (today or date.today()):
            return {
                "credits": credits,
                "expires": expires,
                "spendable": False,
                "why": f"the budget expired on {expires}",
            }
        return {
            "credits": credits,
            "expires": expires,
            "spendable": True,
            "why": "",
        }


def load(root: str | Path = ".") -> Config:
    """Read this project's settings, now rather than at startup."""
    where = Path(root).expanduser().resolve()
    source = where / FILENAME
    if not source.is_file():
        return Config(where, {}, None)
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "config.malformed",
            f"{source} is not readable as TOML",
            "fix the syntax the detail below points at",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise PolyweaveError(
            "config.malformed",
            f"{source} could not be read",
            "check that it is a file and readable",
            detail=str(exc),
        ) from exc
    _check(declared, source)
    declared_root = declared.get("project", {}).get("root")
    if declared_root:
        where = (where / str(declared_root)).resolve()
    return Config(where, declared, source)


def _check(declared: dict, source: Path) -> None:
    """Refuse a key nothing declares, rather than ignoring it.

    §3 of the tool surface: an unknown field in any input is refused. A config key that
    is silently dropped is a setting the caller believes is in effect and is not.
    """
    for table, values in declared.items():
        if table not in DEFAULTS:
            near = difflib.get_close_matches(table, DEFAULTS, n=1)
            raise PolyweaveError(
                "config.unknown-table",
                f"{source.name} declares [{table}], which is not a table",
                f"did you mean [{near[0]}]?"
                if near
                else f"the tables are {', '.join(sorted(DEFAULTS))}",
            )
        if not isinstance(values, dict):
            raise PolyweaveError(
                "config.bad-type",
                f"[{table}] is a table, and {source.name} gives it a value",
                f"write it as [{table}] with keys under it",
            )
        for key, value in values.items():
            _check_key(table, key, value, source)


def _check_key(table: str, key: str, value: Any, source: Path) -> None:
    allowed = DEFAULTS[table]
    if key not in allowed:
        near = difflib.get_close_matches(key, allowed, n=1)
        raise PolyweaveError(
            "config.unknown-key",
            f"{source.name} sets {table}.{key}, which is not a setting",
            f"did you mean {table}.{near[0]}?"
            if near
            else f"[{table}] takes {', '.join(sorted(allowed))}",
        )
    default = allowed[key]
    if f"{table}.{key}" in _OPEN_TABLES:
        return
    if isinstance(default, bool) != isinstance(value, bool) or not isinstance(
        value, type(default) if not isinstance(default, int | float) else int | float
    ):
        raise PolyweaveError(
            "config.bad-type",
            f"{table}.{key} is a {type(default).__name__}, and {source.name} gives "
            f"a {type(value).__name__}",
            f"write it as a {type(default).__name__}",
        )


def _merge(base: dict, over: dict, at: str = "") -> dict:
    out: dict[str, Any] = {}
    for key, value in base.items():
        address = f"{at}.{key}" if at else key
        stated = over.get(key)
        if isinstance(value, dict) and address in _OPEN_TABLES:
            # Keyed by names the project chooses, so what it states replaces the
            # default outright: a project that renames its rungs would otherwise
            # inherit samples for rungs it does not have.
            out[key] = dict(stated) if stated else dict(value)
        elif isinstance(value, dict):
            out[key] = _merge(value, stated or {}, address)
        elif key in over:
            out[key] = stated
        else:
            out[key] = list(value) if isinstance(value, list) else value
    for key, value in over.items():
        out.setdefault(key, value)
    return out


def _expand(value: Any, address: str) -> Any:
    """Resolve `${NAME}` against the environment, now rather than at startup."""
    if isinstance(value, list):
        return [_expand(v, address) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v, f"{address}.{k}") for k, v in value.items()}
    if not isinstance(value, str):
        return value

    def one(match: re.Match) -> str:
        name = match.group(1)
        found = os.environ.get(name)
        if found is None:
            raise PolyweaveError(
                "config.env-unset",
                f"{address} names ${{{name}}}, and {name} is not set here",
                f"set {name} in this environment, or write the value in {FILENAME}",
            )
        return found

    return _ENV_REF.sub(one, value)
