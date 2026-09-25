"""A project's config proposed from its own tree (§PW218).

Starship's `polyweave.toml` was written by hand, one key at a time, against a spec an
agent had to read before its first call. `python -m polyweave init`, and the
`project.init` operation behind it, reads the tree instead and proposes the file:

- `[project] name` from `project.godot`'s `config/name`, or from the directory;
- `[paths] godot` as `${GODOT}` where that variable is set, and never a binary's
  absolute path, which is one desk's and not the project's;
- `meshes`, `renders` and `specs` from folders that already exist, else the defaults;
- `[style]` and `[words]` only where there is something to point them at: a folder
  named `canon`, a translation CSV Godot imports;
- a `[service]` only for a key variable that is already set.

By default it answers with the proposal and writes nothing. `write` writes it, and
refuses a file that exists unless `merge` says to add only the tables it lacks, never
changing a value a person wrote. The text is checked by the loader every call uses
before anything is written, so a key nothing declares cannot land.

**It never writes a `[budget]`.** A ceiling is a person's to set, and an agent that
could set its own would be spending on its own judgement. The answer names the table as
missing and who fills it.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Annotated

from .config import DEFAULTS, FILENAME, _check
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: The services this plugin has a client for, and the variable each key is read from.
SERVICES = {
    "meshy": ("https://api.meshy.ai", "MESHY_API_KEY"),
    "ideogram": ("https://api.ideogram.ai", "IDEOGRAM_API_KEY"),
}

#: Where each produced kind is looked for, in order, before the default is proposed.
FOLDERS = {
    "meshes": ("assets/3d", "assets/models", "models"),
    "renders": ("docs/renders", "renders"),
}

#: What is missing from every proposal, and who supplies it.
MISSING_BUDGET = {
    "table": "budget",
    "who": "a person: a spending ceiling is theirs to set, with an expiry, and the "
    "plugin spends nothing until one is written",
}


@operation("project.init")
def init(
    root: Annotated[str, Param("the project whose tree is read")] = ".",
    write: Annotated[bool, Param("write it, not only propose it")] = False,
    merge: Annotated[bool, Param("add only the tables a file lacks")] = False,
) -> dict:
    """Propose polyweave.toml from what the project's tree already holds.

    Nothing is written unless `write` is true, a file that exists is refused unless
    `merge` is, and a `[budget]` is never proposed: it is named as missing instead.
    """
    here = Path(root).expanduser().resolve()
    tables = proposed(here)
    target = here / FILENAME
    existing = read_text_retrying(target)
    if existing is not None and write and not merge:
        raise PolyweaveError(
            "config.exists",
            f"{target} already exists, and init does not overwrite a person's file",
            "pass merge to add only the tables it lacks, or edit the file by hand",
        )
    held: dict = {}
    if existing is not None:
        try:
            held = tomllib.loads(existing)
        except tomllib.TOMLDecodeError as exc:
            raise PolyweaveError(
                "config.malformed",
                f"{target} is not readable as TOML, so nothing can be merged into it",
                "fix the syntax the detail points at, then run init again",
                detail=str(exc),
            ) from exc
    if merge and existing is not None:
        # A service is one table or several named ones, never both, so an existing
        # file that declares any keeps its own.
        tables = {
            name: values
            for name, values in tables.items()
            if name not in held and not (name == "service" and "service" in held)
        }
    text = _as_toml(tables)
    combined = (existing.rstrip() + "\n\n" + text) if merge and existing else text
    _check(tomllib.loads(combined), target)
    wrote = False
    if write and (tables or existing is None):
        write_atomic(target, combined)
        wrote = True
    missing = [] if "budget" in held else [dict(MISSING_BUDGET)]
    return {
        "file": FILENAME,
        "proposed": text,
        "tables": sorted(tables),
        "wrote": wrote,
        "merged": bool(merge and existing is not None),
        "missing": missing,
        "says": "written" if wrote else "proposed only; pass write to write it",
    }


def proposed(here: Path) -> dict[str, dict]:
    """Every table the tree gives a reason to write, and only those."""
    tables: dict[str, dict] = {"project": {"name": _name(here)}}
    paths: dict = {}
    if os.environ.get("GODOT"):
        paths["godot"] = "${GODOT}"
    for key, candidates in FOLDERS.items():
        found = next((c for c in candidates if (here / c).is_dir()), None)
        paths[key] = found or DEFAULTS["paths"][key]
    specs = _first(here, "*.accept.toml")
    paths["specs"] = (
        _relative(specs.parent, here) if specs else DEFAULTS["paths"]["specs"]
    )
    tables["paths"] = paths
    canon = next(
        (d for d in _walk(here, "canon") if d.is_dir()),
        None,
    )
    if canon is not None:
        tables["style"] = {"canon": _relative(canon, here)}
    table = _translations(here)
    if table is not None:
        tables["words"] = {"table": _relative(table, here)}
    keyed = {n: s for n, s in SERVICES.items() if os.environ.get(s[1])}
    if len(keyed) == 1:
        base, variable = next(iter(keyed.values()))
        tables["service"] = {"base": base, "key_env": variable}
    elif keyed:
        tables["service"] = {
            name: {"base": base, "key_env": variable}
            for name, (base, variable) in keyed.items()
        }
    return tables


def _name(here: Path) -> str:
    """The game's own name, from project.godot, or the directory's."""
    text = read_text_retrying(here / "project.godot") or ""
    said = re.search(r'^config/name\s*=\s*"([^"]*)"', text, re.M)
    return said.group(1) if said and said.group(1).strip() else here.name


def _hidden(path: Path, here: Path) -> bool:
    return any(p.startswith(".") for p in path.relative_to(here).parts)


def _walk(here: Path, pattern: str):
    return sorted(p for p in here.rglob(pattern) if not _hidden(p, here))


def _first(here: Path, pattern: str) -> Path | None:
    return next(iter(_walk(here, pattern)), None)


def _translations(here: Path) -> Path | None:
    """The CSV Godot imports as translations, as its .import file says."""
    for imported in _walk(here, "*.csv.import"):
        text = read_text_retrying(imported) or ""
        if 'importer="csv_translation"' in text:
            source = imported.with_suffix("")
            if source.is_file():
                return source
    return None


def _relative(path: Path, here: Path) -> str:
    return path.relative_to(here).as_posix() or "."


def _as_toml(tables: dict[str, dict]) -> str:
    """The proposal as a person would write it: one table a block, strings quoted."""
    lines = [
        "# Proposed by `python -m polyweave init` from what this tree holds.",
        "# Edit it freely: init never overwrites a value a person wrote.",
        "# [budget] is left to a person: nothing is spent until one is written.",
    ]
    for name, values in tables.items():
        nested = {k: v for k, v in values.items() if isinstance(v, dict)}
        flat = {k: v for k, v in values.items() if not isinstance(v, dict)}
        if flat:
            lines += ["", f"[{name}]"]
            lines += [f"{key} = {_value(value)}" for key, value in flat.items()]
        for inner, own in nested.items():
            lines += ["", f"[{name}.{inner}]"]
            lines += [f"{key} = {_value(value)}" for key, value in own.items()]
    return "\n".join(lines) + "\n"


def _value(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
