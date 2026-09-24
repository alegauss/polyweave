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
from dataclasses import dataclass, fields
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

#: Tables a project may add keys to while keeping the ones declared here. `[capture]`
#: is one because the settings a picture depends on are per project and short, and a
#: project that cannot name its own has to leave them to the machine (§PW25).
_FREE_TABLES = ("capture",)

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
        # Prepared references, committed with the tree: the input that actually made a
        # mesh is the one on file, not whichever original a person had open (§PW21).
        "references": "assets/references",
        "renders": "docs/renders",
        "specs": "docs/accept",
        "work": ".polyweave",
        # The ledger of what was paid for. Inside the tree and committed with it: a
        # purchase and its record are one artefact (§PW17).
        "purchases": "polyweave.purchases.json",
        # What one asset cost, made each way. Committed with the tree, because a
        # baseline that can be rewritten is not a baseline (§PW35).
        "loop": "polyweave.loop.json",
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
        # Keyed by rung, because the noise floor is not one number: two seeds of one
        # unchanged sphere measured 0.0234 apart at the sphere rung, 0.0195 at preview
        # and 0.0122 at final on Blender 5.2.1, against the 0.004 that used to be the
        # single default — so every preview comparison read as a change (§PW44). These
        # are what one machine measured, which is still a guess about another: a floor
        # measured from a twin render beats all of them, and `measure.same` takes one.
        "render_noise": {"sphere": 0.025, "preview": 0.020, "final": 0.013},
        "silhouette_iou": 0.97,
        "delta_e": 2.0,
        # How far from the colour at the frame's edge still counts as background when a
        # photograph is cut out. Perceptual, so it is the same number on any hue.
        "background_delta_e": 12.0,
        # The least of the frame a subject may fill and still be worth spending on.
        "subject_coverage": 0.12,
        # How far a rendered subject must reach across the frame along its longer axis
        # to be worth judging at all (§PW52). **Extent, not area**, and that is the
        # whole of why there is a second key rather than a reuse of the one above: a
        # rope framed exactly right covers 1.6% of the frame, so any area floor that
        # catches a two-pixel render refuses the rope too. Measured through the project
        # rig on the two real meshes the suite has — the booster hammer spans 0.578 and
        # the plush body 0.539 — against 0.016 for two stray pixels. 0.05 sits an order
        # of magnitude clear of both, which is the margin a number nobody can re-measure
        # on their own assets needs.
        "subject_extent": 0.05,
    },
    "cache": {"max_bytes": 8_000_000_000},
    "provenance": {
        # Files under a produced directory that a person made rather than the plugin, as
        # glob patterns relative to the root. §PW41: checking that every produced file
        # carries a record is only useful if a project can say which of them are not
        # produced — a report nobody can quieten is a report nobody reads, and this one
        # has to stay worth reading for the one week in a year when a mesh goes missing.
        "handmade": [],
    },
    "engine": {
        # The bounds a scene script runs under. Both of them, because the frame budget
        # is what ends a script the engine would otherwise sit in forever, and the wall
        # clock is what ends a run the engine never reaches a frame of (§PW22).
        "fixed_fps": 60,
        "frames": 6000,
        "timeout": 180,
    },
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
        # Whether a capture that stops reproducing is a refusal rather than a remark
        # (§PW75). Off, because the plugin cannot make an engine deterministic and a
        # project that has not pinned its captures would fail every run. A project that
        # has pinned them turns it on, and keeps what it earned.
        "reproducible": False,
    },
    "geometry": {"outlines": ""},
    "voxels": {
        # What a voxel build is checked against (§PW97). A game decides how many cubes
        # it can draw and how thin a part may be before it vanishes, so these are the
        # project's. A budget of zero is no ceiling and an empty extent no target.
        "budget": 0,
        # The longest run one cell thick before it is reported.
        "thread": 3,
        # [x, y, z] in the declaration's units; a document's own [voxels] extent wins.
        "extent": [],
        # A model at least this symmetric in x and short of whole is reported, because
        # that is what two halves drifting apart looks like.
        "near_symmetry": 0.9,
    },
    "sprites": {
        # What the 2D half of a clip is baked at. Configuration rather than decisions
        # taken inside code: a sheet's rate, its count and its trim are a project's
        # (§PW29). `frames` of zero takes every frame the clip has.
        "fps": 12,
        "frames": 0,
        "trim": True,
        "columns": 0,
    },
    "rig": {
        # Which body plan a mesh gets fitted with, and how the weights fall off. The
        # plan is the only one of these a project usually changes (§PW26).
        "plan": "plush",
        # One influence snaps every vertex to one bone and tears at every boundary.
        "influences": 4,
        # Both ends tear: high snaps a vertex to one bone, low spreads it onto bones
        # nowhere near it. Four sits in the trough, at 1.6x on the test figure.
        "falloff": 4.0,
        # How far a joint is pulled from the plan's own position onto the mesh's volume.
        "pull": 0.6,
        # How far an edge may stretch in a test pose before the rig is called wrong.
        "tear_ratio": 2.0,
    },
    "units": {
        # The scale the engine draws at. Stating it here is the weaker half; `source`
        # is the stronger one — `path/to.gd:NAME` reads it from wherever the game
        # already holds it, so the two numbers cannot drift apart (§PW24).
        "pixels_per_unit": 0.0,
        "source": "",
        "tolerance": 0.001,
    },
}


@dataclass(frozen=True)
class Tolerances:
    """The numbers that decide what counts as the same, resolved once.

    §PW40: `[tolerance] alpha_floor` was 0.02 in this file's defaults and 0.0 in the
    signature of every function that used it, and the two disagreed. An operation that
    resolved the setting measured the subject the project asked for; one that forgot
    measured every pixel in the frame, background included, and nothing reported that a
    choice had been made.

    The fix is that a tolerance has one home, and this is it. The library functions stay
    pure — they take numbers, read no files, and so can run inside Blender — and none of
    them invents a fallback any more. Resolving happens at the operation, once, and this
    is what it resolves to: all six together, so an operation that needs one cannot pick
    up a stale sibling, and so a provenance record can carry the values actually in
    force rather than whatever the file holds when it is read back.
    """

    alpha_floor: float
    render_noise: float
    silhouette_iou: float
    delta_e: float
    background_delta_e: float
    subject_coverage: float
    subject_extent: float

    def as_dict(self) -> dict[str, float]:
        """What was in force, for the record written beside the artefact."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


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

    def tolerances(self, rung: str | None = None) -> Tolerances:
        """Every tolerance in force, resolved together (§PW40).

        An operation reads this once and passes the numbers down. The functions below it
        take them and have no fallback of their own, so there is nowhere for a second
        value of one number to live.

        `render_noise` is keyed by rung in the file and a single number here, because
        the floor at four samples is not the floor at five hundred (§PW44) and yet the
        code comparing two pictures wants one bar. Naming no rung takes the strictest of
        them, which is the safe way to be wrong: too tight calls an unchanged render
        changed, and too loose calls a changed one unchanged.
        """
        table = self.table("tolerance")
        noise = table["render_noise"]
        if isinstance(noise, dict):
            noise = noise.get(rung, min(noise.values())) if noise else 0.0
        values = {
            f.name: float(table[f.name])
            for f in fields(Tolerances)
            if f.name != "render_noise"
        }
        return Tolerances(render_noise=float(noise), **values)

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
        if table in _FREE_TABLES:
            return
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
