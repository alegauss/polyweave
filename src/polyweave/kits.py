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
TOP = {
    "name",
    "version",
    "summary",
    "requires",
    "installs",
    "declares",
    "proves",
    "changes",
    "tab",
}
INSTALLS = {"core", "scene"}
PROVES = {"spec", "fixture", "script"}

#: The line a kit's proof script prints when it holds, and the one when it does not.
PROVED = r"^KIT PROVED$"

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
    if "spec" not in held["proves"] and "script" not in held["proves"]:
        raise _bad(
            where,
            "proves nothing",
            'write spec = "proof.accept.toml" under [proves], or script = '
            '"core/proof.gd" where only a running game can say it holds: a kit is '
            "worth more than a snippet only while its proof holds",
        )
    script = held["proves"].get("script")
    if script is not None and not str(script).startswith(
        str(held["installs"]["core"]).rstrip("/") + "/"
    ):
        raise _bad(
            where,
            f"proves with {script!r}, outside its core",
            "keep the proof script inside the core, so it lands in the game",
        )
    named = [
        held["installs"]["core"],
        held["installs"].get("scene"),
        held["proves"].get("spec"),
        held["proves"]["fixture"],
        script,
    ]
    for one in (n for n in named if n is not None):
        if not isinstance(one, str) or not (folder / one).exists():
            raise _bad(
                where,
                f"names {one!r}, which the kit does not hold",
                "name a path inside the kit's folder",
            )
    tab = held.get("tab")
    rows = folder / held["installs"]["core"] / "options.gd"
    if tab is not None and (not isinstance(tab, str) or not rows.is_file()):
        raise _bad(
            where,
            f"contributes the tab {tab!r} and keeps no options.gd in its core",
            "write core/options.gd with const TAB and static func options() (§PW347)",
        )
    if tab is None and rows.is_file():
        raise _bad(
            where,
            "keeps an options.gd and declares no tab",
            'name the tab it contributes to the options screen: tab = "controls"',
        )
    changes = held.get("changes", {})
    if not isinstance(changes, dict) or not all(
        _VERSION.match(str(v)) and isinstance(t, str) for v, t in changes.items()
    ):
        raise _bad(
            where,
            "has a [changes] that is not versions to sentences",
            'write [changes] as "0.2.0" = "what that version changed"',
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
        "changes": dict(changes),
        "tab": tab,
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
    project = here / "project.godot"
    if not project.is_file():
        raise PolyweaveError(
            "kits.no-game",
            f"there is no project.godot at {here}, so there is no game to install into",
            "install a kit from the Godot project's own folder",
        )
    # Godot writes a value over several lines (an input action's events, a dictionary),
    # which an INI reader refuses, so a key is a name at the start of a line, in its
    # section, and only the one-line values are read.
    sections: dict[str, dict[str, str]] = {"": {}}
    current = ""
    for line in project.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("[") and line.rstrip().endswith("]"):
            current = line.strip()[1:-1]
            sections.setdefault(current, {})
            continue
        found = re.match(r"^([A-Za-z0-9_./-]+)=(.*)$", line)
        if found:
            sections[current][found[1]] = found[2]

    def said(section: str, key: str) -> str:
        return sections.get(section, {}).get(key, "").strip().strip('"')

    folder = here / "addons" / "polyweave"
    present = {}
    for manifest in sorted(folder.glob("*/kit.json")) if folder.is_dir() else ():
        held = json.loads(manifest.read_text(encoding="utf-8"))
        present[held["name"]] = held["version"]
    return {
        "main_scene": said("application", "run/main_scene") or None,
        "renderer": said("rendering", "renderer/rendering_method") or None,
        "actions": sorted(sections.get("input", {})),
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
        if kit["proves"].get("spec"):
            proofs.append(spec)
        if not write:
            continue
        if core.exists():
            shutil.rmtree(core)
        shutil.copytree(source / kit["installs"]["core"], core)
        if target is not None and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / scene, target)
        if kit["proves"].get("spec"):
            spec.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / kit["proves"]["spec"], spec)
        manifest = core / "kit.json"
        files = _digests(core)
        manifest.write_text(
            json.dumps(
                {"name": one, "version": kit["version"], "files": files}, indent=1
            )
            + "\n",
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
        ran = _scripts(order, kits, here) if failing is None else []
        broken = next((r for r in ran if r["status"] == "failed"), None)
        if broken:
            proved = {"passed": False, "first": broken}
        proved["scripts"] = ran
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


def _scripts(order: list, kits: dict, here: Path) -> list[dict]:
    """Each kit's proof script, run in the game, where it has one and an engine is set.

    A proof that only a running game can give (every action has an icon in every
    family, say) is a GDScript in the kit's core, printing `KIT PROVED` when it holds
    and why it does not otherwise (§PW344). With no `$GODOT` it is skipped, and said.
    """
    import os

    from . import engine

    said = []
    for one in order:
        script = kits[one]["proves"].get("script")
        if not script:
            continue
        inside = Path(script).relative_to(kits[one]["installs"]["core"])
        at = Path("addons") / "polyweave" / one / inside
        if not os.environ.get("GODOT"):
            said.append(
                {
                    "kit": one,
                    "script": at.as_posix(),
                    "status": "skipped",
                    "why": "no $GODOT is set",
                }
            )
            continue
        # A proof ends itself, and one timing a load or a frame needs the wall clock:
        # headless frames run unbounded, so a frame budget would cut a threaded load
        # short (§PW349). The engine's timeout is what stops a proof that hangs.
        found = engine.run(
            at.as_posix(),
            expect=PROVED,
            root=here,
            headless=True,
            frames=10_000_000,
            fixed_fps=0,
        )
        log = Path(str(found.get("log") or ""))
        printed = log.read_text(encoding="utf-8", errors="replace") if (
            found.get("log") and log.is_file()) else ""
        if found.get("ok"):
            sounds = _sounds(printed, here)
            off = next((s for s in sounds if not s["held"]), None)
            said.append(
                {
                    "kit": one,
                    "script": at.as_posix(),
                    "status": "held" if off is None else "failed",
                    **({"sounds": sounds} if sounds else {}),
                    **({} if off is None else {"said": off["said"]}),
                }
            )
            continue
        lines = [ln for ln in printed.splitlines() if ln.startswith("KIT ")]
        said.append(
            {
                "kit": one,
                "script": at.as_posix(),
                "status": "failed",
                "said": lines[-1] if lines else found.get("verdict"),
            }
        )
    return said


#: A sound a proof script captured in the game, and the bounds it is held to.
SOUND = re.compile(
    r"^KIT SOUND (?P<path>\S+) (?P<measure>\w+) (?P<low>-?[\d.]+) (?P<high>-?[\d.]+)$",
    re.MULTILINE,
)


def _sounds(printed: str, here: Path) -> list[dict]:
    """Each sound a proof script heard in the game, held to its bounds by sound.measure.

    What a game mixes is only heard while it runs, so the script writes it beside the
    game and prints `KIT SOUND <path> <measure> <min> <max>`; the measure is the one a
    track is held to, so a bus is held as a track is (§PW351).
    """
    from . import sound

    out = []
    for line in SOUND.finditer(printed):
        low, high, named = float(line["low"]), float(line["high"]), line["measure"]
        try:
            value = sound.measure(here / line["path"]).get(named)
        except PolyweaveError as refused:
            value, why = None, refused.message
        else:
            why = f"{named} has no value" if value is None else ""
        held = value is not None and low <= value <= high
        out.append(
            {
                "path": line["path"],
                "measure": named,
                "value": value,
                "min": low,
                "max": high,
                "held": held,
                **(
                    {}
                    if held
                    else {
                        "said": f"{line['path']} {named} "
                        + (why or f"{value}, outside [{low}, {high}]")
                    }
                ),
            }
        )
    return out


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


def _digests(core: Path) -> dict[str, str]:
    """Every file a kit's core laid down, by its path in the core, with its SHA-256."""
    from .provenance import sha256_of

    return {
        one.relative_to(core).as_posix(): sha256_of(one)[0]
        for one in sorted(core.rglob("*"))
        if one.is_file()
        and one.name not in ("kit.json", "kit.json.prov.json")
        and not one.name.endswith(".prov.json")
    }


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(n) for n in str(text).split("."))


def behind(root: str | Path = ".") -> list[dict]:
    """Every kit a project carries that the plugin now has in a newer version.

    Each with the version installed, the one the plugin carries, and the kit's own
    `[changes]` between the two, so a project hears of a fix rather than by luck
    (§PW343).
    """
    here = Path(root).resolve()
    folder = here / "addons" / "polyweave"
    if not folder.is_dir():
        return []
    try:
        carried = every()
    except PolyweaveError:
        return []
    found = []
    for manifest in sorted(folder.glob("*/kit.json")):
        held = json.loads(manifest.read_text(encoding="utf-8"))
        kit = carried.get(held.get("name"))
        if not kit or _version(kit["version"]) <= _version(
            held.get("version", "0.0.0")
        ):
            continue
        between = [
            {"version": v, "change": t}
            for v, t in sorted(kit["changes"].items(), key=lambda vt: _version(vt[0]))
            if _version(held["version"]) < _version(v) <= _version(kit["version"])
        ]
        found.append(
            {
                "kit": held["name"],
                "installed": held["version"],
                "carried": kit["version"],
                "changes": between,
            }
        )
    return found


@operation("kit.update")
def update(
    name: Annotated[str, Param("an installed kit")],
    *,
    write: Annotated[bool, Param("false answers what it would do, writing nothing")] = (
        True
    ),
    root: Annotated[str, Param("the Godot project the kit is installed in")] = ".",
) -> dict:
    """Bring an installed kit to the version the plugin carries, proved or not at all.

    The core is the plugin's and the project never edits it, so a core file whose hash
    differs from the one recorded at install is a finding naming the files, and nothing
    is overwritten. The scene is the project's and is left alone; the answer shows
    what the new version's scene differs by, for the agent to carry over. The proof is
    run again, and an upgrade whose proof fails is put back (§PW343).
    """
    import difflib
    import tempfile

    here = Path(root).resolve()
    core = here / "addons" / "polyweave" / name
    manifest = core / "kit.json"
    if not manifest.is_file():
        raise PolyweaveError(
            "kits.unknown",
            f"the project carries no kit {name!r}",
            "install it first with kit.install",
            given=name,
            allowed=sorted(p.parent.name for p in core.parent.glob("*/kit.json")),
        )
    held = json.loads(manifest.read_text(encoding="utf-8"))
    kits = every()
    if name not in kits:
        raise PolyweaveError(
            "kits.unknown",
            f"the plugin carries no kit {name!r}",
            "name one kit.list answers",
            given=name,
            allowed=sorted(kits),
        )
    kit = kits[name]
    recorded = held.get("files") or {}
    now = _digests(core)
    edited = sorted(
        path for path, digest in recorded.items() if now.get(path) != digest
    )
    answer = {
        "kit": name,
        "installed": held["version"],
        "carried": kit["version"],
        "changes": next((b["changes"] for b in behind(here) if b["kit"] == name), []),
    }
    if edited:
        return {
            **answer,
            "ok": False,
            "edited": edited,
            "says": f"the core of {name} was edited in the project: "
            f"{', '.join(edited)}; nothing was overwritten. Move the change into the "
            "kit, or put the files back, and update again",
        }
    if _version(kit["version"]) <= _version(held["version"]):
        return {**answer, "ok": True, "says": f"{name} is already at {held['version']}"}
    scene = kit["installs"].get("scene")
    ours = here / "kits" / name / Path(scene).name if scene else None
    if ours is not None and ours.is_file():
        theirs = (Path(kit["folder"]) / scene).read_text(encoding="utf-8").splitlines()
        mine = ours.read_text(encoding="utf-8").splitlines()
        answer["scene"] = {
            "path": ours.relative_to(here).as_posix(),
            "differs": list(
                difflib.unified_diff(
                    mine,
                    theirs,
                    "the project's",
                    f"{name} {kit['version']}",
                    lineterm="",
                )
            ),
        }
    if not write:
        return {**answer, "ok": None, "wrote": False}
    with tempfile.TemporaryDirectory() as scratch:
        kept = Path(scratch) / "core"
        shutil.copytree(core, kept)
        result = install(name, root=str(here))
        if not result["ok"]:
            shutil.rmtree(core)
            shutil.copytree(kept, core)
            return {
                **answer,
                "ok": False,
                "proved": result["proved"],
                "wrote": False,
                "says": f"{name} {kit['version']} did not prove in this game, so "
                f"{held['version']} was put back",
            }
    return {
        **answer,
        "ok": True,
        "proved": result["proved"],
        "wrote": True,
        "says": f"{name} is now {kit['version']}, proved in this game",
    }


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
        named = kit["proves"].get("spec")
        spec = accept.read(folder / named) if named else None
        if not engine and (spec is None or spec.screen):
            said.append(
                {
                    "kit": one,
                    "version": kit["version"],
                    "status": "skipped",
                    "why": "its proof needs a running game, and no $GODOT is set",
                }
            )
            continue
        with tempfile.TemporaryDirectory() as scratch:
            game = Path(scratch) / "game"
            shutil.copytree(folder / kit["proves"]["fixture"], game)
            try:
                answer = install(one, root=str(game))
            except PolyweaveError as refused:
                said.append(
                    {
                        "kit": one,
                        "version": kit["version"],
                        "status": "failed",
                        "why": refused.message,
                    }
                )
                continue
        held = answer["ok"]
        said.append(
            {
                "kit": one,
                "version": kit["version"],
                "status": "held" if held else "failed",
                **({} if held else {"why": answer["proved"]["first"]}),
            }
        )
    counted = {
        s: sum(1 for one in said if one["status"] == s)
        for s in ("held", "failed", "skipped")
    }
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
