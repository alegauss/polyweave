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

import json
import re
import shutil
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
PROVES = {"spec", "fixture"}

_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _bad(where: Path, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError(
        "kits.bad", f"{where.parent.name}/kit.toml {what}", remedy, **extra
    )


def read(folder: Path) -> dict:
    """One kit's declaration, every key and named file checked, or a refusal."""
    where = folder / "kit.toml"
    try:
        held = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise _bad(
            where, "is missing", "write a kit.toml beside the kit's files"
        ) from None
    except tomllib.TOMLDecodeError as exc:
        raise _bad(
            where, "is not TOML", "fix the syntax the detail points at", detail=str(exc)
        ) from exc
    unknown = sorted(set(held) - TOP)
    if unknown:
        raise _bad(
            where,
            f"declares {', '.join(unknown)}",
            f"use some of {', '.join(sorted(TOP))}",
            given=unknown[0],
            allowed=sorted(TOP),
        )
    name = held.get("name")
    if not isinstance(name, str) or not _NAME.match(name) or name != folder.name:
        raise _bad(
            where,
            f"is named {name!r}",
            f'name it as its folder, in lower case: name = "{folder.name}"',
        )
    if not isinstance(held.get("version"), str) or not _VERSION.match(held["version"]):
        raise _bad(
            where,
            f"has version {held.get('version')!r}",
            'write the version as major.minor.patch, such as "0.1.0"',
        )
    if not isinstance(held.get("summary"), str) or not held["summary"].strip():
        raise _bad(where, "has no summary", "say in one line what the kit does")
    requires = held.get("requires", [])
    if not isinstance(requires, list) or not all(isinstance(r, str) for r in requires):
        raise _bad(where, f"requires {requires!r}", "list the kits it needs by name")
    for table, keys in (("installs", INSTALLS), ("proves", PROVES)):
        own = held.get(table)
        if not isinstance(own, dict):
            raise _bad(
                where,
                f"has no [{table}] table",
                f"write [{table}] with {', '.join(sorted(keys))}",
            )
        extra = sorted(set(own) - keys)
        if extra:
            raise _bad(
                where,
                f"[{table}] declares {', '.join(extra)}",
                f"use some of {', '.join(sorted(keys))}",
            )
    if "core" not in held["installs"]:
        raise _bad(where, "installs no core", 'write core = "core" under [installs]')
    if "fixture" not in held["proves"]:
        raise _bad(
            where,
            "has no fixture to be proved in",
            'write fixture = "fixture" under [proves]: a minimal Godot project shaped '
            "to exercise the kit, where polyweave's gate proves it (§PW342)",
        )
    if "spec" not in held["proves"]:
        raise _bad(
            where,
            "proves nothing",
            'write spec = "proof.accept.toml" under [proves]: a kit is worth '
            "more than a snippet only while its proof holds",
        )
    named = [
        held["installs"]["core"],
        held["installs"].get("scene"),
        held["proves"]["spec"],
        held["proves"]["fixture"],
    ]
    for one in (n for n in named if n is not None):
        if not isinstance(one, str) or not (folder / one).exists():
            raise _bad(
                where,
                f"names {one!r}, which the kit does not hold",
                "name a path inside the kit's folder",
            )
    declares = held.get("declares", {})
    if not isinstance(declares, dict):
        raise _bad(
            where,
            "has a [declares] that is not a table",
            "write the declaration it proposes as [declares]",
        )
    return {
        "name": name,
        "version": held["version"],
        "summary": held["summary"].strip(),
        "requires": list(requires),
        "installs": dict(held["installs"]),
        "declares": dict(declares),
        "proves": dict(held["proves"]),
        "folder": str(folder),
    }


def every(under: Path | None = None) -> dict[str, dict]:
    """Every kit under a folder, checked, what each requires present and acyclic."""
    under = KITS if under is None else under
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
                given=missing[0],
                allowed=sorted(found),
            )
    for name in found:
        _acyclic(name, found, [])
    return found


def _acyclic(name: str, kits: dict, path: list) -> None:
    if name in path:
        loop = " -> ".join([*path[path.index(name) :], name])
        raise PolyweaveError(
            "kits.bad",
            f"kits require each other in a loop: {loop}",
            "break the loop; a kit is installed after what it needs",
        )
    for needed in kits[name]["requires"]:
        _acyclic(needed, kits, [*path, name])


def _order(name: str, kits: dict, done: list) -> list:
    """The kits to install for `name`, what each requires first."""
    for needed in kits[name]["requires"]:
        _order(needed, kits, done)
    if name not in done:
        done.append(name)
    return done


def _toml(value: Any) -> str:
    """A declared value as TOML spells it: text, number, bool, or a list of them."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_toml(one) for one in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k} = {_toml(v)}" for k, v in value.items()) + " }"
    raise PolyweaveError(
        "kits.bad",
        f"a declaration holds {value!r}",
        "declare text, numbers, booleans, lists and tables",
    )


def _game(here: Path) -> dict:
    """What a kit reads of the game before it installs (§PW341)."""
    from configparser import ConfigParser

    project = here / "project.godot"
    if not project.is_file():
        raise PolyweaveError(
            "kits.no-game",
            f"there is no project.godot at {here}, so there is no game to install into",
            "install a kit from the Godot project's own folder",
        )
    parsed = ConfigParser(strict=False, interpolation=None)
    parsed.optionxform = str
    text = project.read_text(encoding="utf-8-sig")
    parsed.read_string("[_top]\n" + text)

    def said(section: str, key: str) -> str:
        return parsed.get(section, key, fallback="").strip().strip('"')

    folder = here / "addons" / "polyweave"
    present = {}
    for manifest in sorted(folder.glob("*/kit.json")) if folder.is_dir() else ():
        held = json.loads(manifest.read_text(encoding="utf-8"))
        present[held["name"]] = held["version"]
    return {
        "main_scene": said("application", "run/main_scene") or None,
        "renderer": said("rendering", "renderer/rendering_method") or None,
        "actions": sorted(parsed.options("input"))
        if parsed.has_section("input")
        else [],
        "exports": (here / "export_presets.cfg").is_file(),
        "kits": present,
    }


@operation("kit.install")
def install(
    name: Annotated[str, Param("the kit, as kit.list names it")],
    *,
    write: Annotated[
        bool, Param("false answers what it would do and writes nothing")
    ] = (True),
    root: Annotated[str, Param("the Godot project the kit lands in")] = ".",
) -> dict:
    """Land one kit in the game and prove it there, in one call (§PW341).

    Reads the project, installs first what the kit requires, writes the declaration it
    proposes as `[kit.<name>]` only where the project has none, copies its core to
    res://addons/polyweave/<name>/ (replaced whole) and its scene once, records the kit
    and its version, and runs its proof through accept.verify. The answer is ready to
    decide: ok or the first finding with its remedy, what is the project's to change,
    and any question that is a person's. `write=false` answers it, writing nothing.
    """
    from . import accept, provenance
    from .config import load

    config = load(root)
    here = config.root
    kits = every()
    if name not in kits:
        raise PolyweaveError(
            "kits.unknown",
            f"the plugin carries no kit {name!r}",
            "name one kit.list answers",
            given=name,
            allowed=sorted(kits),
        )
    game = _game(here)
    order = _order(name, kits, [])
    declared = config.table("kit") if (here / "polyweave.toml").is_file() else {}
    landed, proposed, scenes, proofs = [], {}, [], []
    for one in order:
        kit = kits[one]
        source = Path(kit["folder"])
        core = here / "addons" / "polyweave" / one
        landed.append(
            {
                "name": one,
                "version": kit["version"],
                "was": game["kits"].get(one),
                "core": provenance.relative(core, here),
            }
        )
        if one not in declared and kit["declares"]:
            proposed[one] = kit["declares"]
        scene = kit["installs"].get("scene")
        target = here / "kits" / one / Path(scene).name if scene else None
        if target is not None and not target.exists():
            scenes.append(provenance.relative(target, here))
        spec = config.path("paths.specs") / "kits" / one / "proof.accept.toml"
        proofs.append(spec)
        if not write:
            continue
        if core.exists():
            shutil.rmtree(core)
        shutil.copytree(source / kit["installs"]["core"], core)
        if target is not None and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / scene, target)
        spec.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / kit["proves"]["spec"], spec)
        manifest = core / "kit.json"
        manifest.write_text(
            json.dumps({"name": one, "version": kit["version"]}, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        provenance.write(
            provenance.build(
                "borrow",
                manifest,
                engine={"name": "kit.install"},
                inputs=[provenance.source("kit", source / "kit.toml", root=here)],
                extra={"kit": {"name": one, "version": kit["version"]}},
                root=here,
            ),
            here,
        )
    if write and proposed:
        config_file = here / "polyweave.toml"
        before = (
            config_file.read_text(encoding="utf-8") if config_file.is_file() else ""
        )
        added = "".join(
            f"\n[kit.{one}]\n"
            + "".join(f"{k} = {_toml(v)}\n" for k, v in table.items())
            for one, table in proposed.items()
        )
        config_file.write_text(
            before.rstrip("\n") + ("\n" if before else "") + added,
            encoding="utf-8",
            newline="\n",
        )
    proved = None
    if write:
        verdicts = [accept.verify(str(here), under=str(spec.parent)) for spec in proofs]
        failing = next((v for v in verdicts if not v.get("passed")), None)
        proved = {
            "passed": failing is None,
            "first": _first(failing) if failing else None,
        }
    return {
        "kit": name,
        "order": order,
        "game": game,
        "installed": landed,
        "declared": proposed,
        "scenes": scenes,
        "proved": proved,
        "ok": bool(write) and bool(proved and proved["passed"]),
        "change": [
            f"{s} is the project's from now on: change it as the game needs"
            for s in scenes
        ],
        "questions": [],
        "wrote": bool(write),
    }


def _first(verdict: dict) -> dict:
    """The first thing a kit's proof found, as the answer carries it."""
    for one in verdict.get("specs", ()):
        if one.get("status") not in ("passed", "unanchored"):
            return {
                "spec": one.get("spec"),
                "status": one.get("status"),
                "said": one.get("failed") or one.get("why"),
            }
    return {"said": "the proof did not pass"}


@operation("kit.prove")
def prove(
    name: Annotated[str, Param("one kit; every kit the plugin carries if unset")] = "",
    root: Annotated[str, Param("unused; a kit is proved in its own fixture")] = ".",
) -> dict:
    """Every kit installed into its own fixture and proved there (§PW342).

    A kit is worth more than a snippet only while its proof holds, so each is proved
    before any project receives it: its fixture, a minimal Godot project shaped to
    exercise it, is copied fresh, the kit is installed into it with what it requires,
    and its proof runs. A kit whose proof needs a running game is skipped, said as
    such, where no engine is present. polyweave's own gate runs this, so a Godot
    upgrade re-proves every kit at once.
    """
    import os
    import tempfile

    from . import accept

    kits = every()
    if name and name not in kits:
        raise PolyweaveError(
            "kits.unknown",
            f"the plugin carries no kit {name!r}",
            "name one kit.list answers",
            given=name,
            allowed=sorted(kits),
        )
    engine = bool(os.environ.get("GODOT"))
    said = []
    for one in [name] if name else sorted(kits):
        kit = kits[one]
        folder = Path(kit["folder"])
        spec = accept.read(folder / kit["proves"]["spec"])
        if spec.screen and not engine:
            said.append({"kit": one, "version": kit["version"], "status": "skipped",
                         "why": "its proof needs a running game, and no $GODOT is set"})
            continue
        with tempfile.TemporaryDirectory() as scratch:
            game = Path(scratch) / "game"
            shutil.copytree(folder / kit["proves"]["fixture"], game)
            try:
                answer = install(one, root=str(game))
            except PolyweaveError as refused:
                said.append({"kit": one, "version": kit["version"], "status": "failed",
                             "why": refused.message})
                continue
        held = answer["ok"]
        said.append({
            "kit": one,
            "version": kit["version"],
            "status": "held" if held else "failed",
            **({} if held else {"why": answer["proved"]["first"]}),
        })
    counted = {s: sum(1 for one in said if one["status"] == s)
               for s in ("held", "failed", "skipped")}
    return {
        "kits": said,
        **counted,
        "passed": not counted["failed"],
        "says": f"{counted['held']} kit(s) held, {counted['failed']} failed, "
        f"{counted['skipped']} skipped for want of an engine",
    }


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
