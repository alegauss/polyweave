"""A kit: a part every game repeats, made once, proved, and installed (§PW340).

Starship's bindings and Cottony's settings each solved the same screen alone, and what
cost them was not the typing but the details only a run reveals: an orphaned focus
neighbour, the Switch's swapped face buttons, a filter that leaves a resource out of
the export. A kit is that part written once, with the proof that it holds.

A kit lives at `kits/<name>/` inside the plugin, so it ships with it as the Godot addons
do, and carries a `kit.toml`:

    name = "input"
    version = "0.1.0"
    summary = "rebindable controls, read from the project's InputMap"
    requires = []                 # kits installed before this one

    [installs]
    core = "core"                 # to res://addons/polyweave/<name>/, never edited
    scene = "scene/controls.tscn" # copied once, the project's from then on

    [declares]                    # the [kit.<name>] table it proposes in polyweave.toml
    layouts = ["xbox", "playstation", "switch", "generic", "keyboard"]

    [proves]
    spec = "proof.accept.toml"    # its acceptance spec, run in the game it lands in

Every kit keeps one contract, five steps: read the project, propose the declaration,
install, prove, answer ready to decide. A kit carries no palette or theme of its own
and assumes no genre; a question it leaves is a person's, never an analysis for the
agent. `kit.list` answers the kits the plugin carries, each checked against this shape.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Annotated, Any

from .describe import Param, operation
from .errors import PolyweaveError

#: Where the plugin's kits live: beside this module, so they ship with it.
KITS = Path(__file__).parent / "kits"

#: Every key a kit.toml may hold, and the keys of each of its tables.
TOP = {"name", "version", "summary", "requires", "installs", "declares", "proves"}
INSTALLS = {"core", "scene"}
PROVES = {"spec"}

_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _bad(where: Path, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("kits.bad", f"{where.parent.name}/kit.toml {what}", remedy,
                          **extra)


def read(folder: Path) -> dict:
    """One kit's declaration, every key and named file checked, or a refusal."""
    where = folder / "kit.toml"
    try:
        held = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise _bad(where, "is missing",
                   "write a kit.toml beside the kit's files") from None
    except tomllib.TOMLDecodeError as exc:
        raise _bad(where, "is not TOML", "fix the syntax the detail points at",
                   detail=str(exc)) from exc
    unknown = sorted(set(held) - TOP)
    if unknown:
        raise _bad(where, f"declares {', '.join(unknown)}",
                   f"use some of {', '.join(sorted(TOP))}", given=unknown[0],
                   allowed=sorted(TOP))
    name = held.get("name")
    if not isinstance(name, str) or not _NAME.match(name) or name != folder.name:
        raise _bad(where, f"is named {name!r}",
                   f'name it as its folder, in lower case: name = "{folder.name}"')
    if not isinstance(held.get("version"), str) or not _VERSION.match(held["version"]):
        raise _bad(where, f"has version {held.get('version')!r}",
                   'write the version as major.minor.patch, such as "0.1.0"')
    if not isinstance(held.get("summary"), str) or not held["summary"].strip():
        raise _bad(where, "has no summary", "say in one line what the kit does")
    requires = held.get("requires", [])
    if not isinstance(requires, list) or not all(isinstance(r, str) for r in requires):
        raise _bad(where, f"requires {requires!r}", "list the kits it needs by name")
    for table, keys in (("installs", INSTALLS), ("proves", PROVES)):
        own = held.get(table)
        if not isinstance(own, dict):
            raise _bad(where, f"has no [{table}] table",
                       f"write [{table}] with {', '.join(sorted(keys))}")
        extra = sorted(set(own) - keys)
        if extra:
            raise _bad(where, f"[{table}] declares {', '.join(extra)}",
                       f"use some of {', '.join(sorted(keys))}")
    if "core" not in held["installs"]:
        raise _bad(where, "installs no core", 'write core = "core" under [installs]')
    if "spec" not in held["proves"]:
        raise _bad(where, "proves nothing",
                   'write spec = "proof.accept.toml" under [proves]: a kit is worth '
                   "more than a snippet only while its proof holds")
    named = [held["installs"]["core"], held["installs"].get("scene"),
             held["proves"]["spec"]]
    for one in (n for n in named if n is not None):
        if not isinstance(one, str) or not (folder / one).exists():
            raise _bad(where, f"names {one!r}, which the kit does not hold",
                       "name a path inside the kit's folder")
    declares = held.get("declares", {})
    if not isinstance(declares, dict):
        raise _bad(where, "has a [declares] that is not a table",
                   "write the declaration it proposes as [declares]")
    return {"name": name, "version": held["version"],
            "summary": held["summary"].strip(), "requires": list(requires),
            "installs": dict(held["installs"]),
            "declares": dict(declares), "proves": dict(held["proves"]),
            "folder": str(folder)}


def every(under: Path = KITS) -> dict[str, dict]:
    """Every kit under a folder, checked, what each requires present and acyclic."""
    found = {}
    folders = sorted(p for p in under.iterdir() if p.is_dir()) if under.is_dir() else []
    for folder in folders:
        if (folder / "kit.toml").is_file():
            found[folder.name] = read(folder)
    for name, kit in found.items():
        missing = [r for r in kit["requires"] if r not in found]
        if missing:
            raise PolyweaveError(
                "kits.bad",
                f"kit {name} requires {', '.join(missing)}, which no kit is",
                "require kits the plugin carries, or add the one it needs",
                given=missing[0], allowed=sorted(found),
            )
    for name in found:
        _acyclic(name, found, [])
    return found


def _acyclic(name: str, kits: dict, path: list) -> None:
    if name in path:
        loop = " -> ".join([*path[path.index(name):], name])
        raise PolyweaveError("kits.bad", f"kits require each other in a loop: {loop}",
                             "break the loop; a kit is installed after what it needs")
    for needed in kits[name]["requires"]:
        _acyclic(needed, kits, [*path, name])


@operation("kit.list")
def listed(
    root: Annotated[str, Param("unused; kits are the plugin's own")] = ".",
) -> dict:
    """The kits the plugin carries, each its name, version, summary and requirements.

    Every kit.toml is checked against the contract of docs/specs/kit.md (§PW340), so a
    kit that names a file it lacks or proves nothing is refused here, before any
    project receives it.
    """
    kits = every()
    return {
        "kits": [
            {k: kit[k] for k in ("name", "version", "summary", "requires")}
            for kit in kits.values()
        ],
        "says": f"{len(kits)} kit(s) the plugin carries"
        + ("" if kits else "; none yet"),
    }
