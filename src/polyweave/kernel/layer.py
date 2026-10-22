"""A layer says what it adds, in one file the kernel finds by walking (§PW500).

Each `layers/<name>/layer.py` holds one `LAYER`. The kernel never lists the layers: it
walks `polyweave.layers`, so a new medium is a new folder and no kernel file changes.
`kernel/`, `loop/`, `services/` and `surface/` declare no layer. They are what layers
plug into, and an operation one of them registers belongs to every project.

Importing a `layer.py` costs nothing: it holds data and imports this module alone, so
`describe` can read every declaration before it imports a single operation.
"""

from __future__ import annotations

import functools
import importlib
import importlib.util
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import PolyweaveError

#: The packages whose operations belong to every project rather than to one layer.
CORE = ("kernel", "loop", "services", "surface")

#: What a layer may say it needs, and how each is found: a binary is probed by
#: `capabilities`, an optional extra by whether its module imports.
REQUIREMENTS = {
    "blender": "the blender binary, or bpy importable",
    "godot": "the godot binary",
    "audio": "the audio extra: pip install polyweave-gamekit[audio]",
    "text": "the text extra: pip install polyweave-gamekit[text]",
}

#: The module each optional extra makes importable.
EXTRAS = {"audio": "pedalboard", "text": "fontTools"}


@dataclass(frozen=True)
class Judge:
    """Where a person's verdict on one kind of member is kept (§PW501).

    `verdict.judge` writes the shared record, then hands each member to the one judge
    that claims it and reports what that judge kept under its `name`. The target is a
    `module:function` imported only when a verdict reaches it, so declaring a judge
    costs a `layer.py` nothing.
    """

    #: The key the judge's return is reported under in each member's answer.
    name: str
    #: One sentence saying where the verdict lives, which `describe` shows.
    about: str
    #: Whether this judge keeps the member's verdict.
    claims: Callable[[dict], bool]
    #: `module:function`, called as (member, *, accepted, choice, why, when, root).
    target: str

    def judged(self, member: dict, **said: Any) -> Any:
        return call(self.target, member, **said)


def call(target: str, *args: Any, **kwargs: Any) -> Any:
    """Call a `module:function` a layer declared, importing it only now."""
    return function(target)(*args, **kwargs)


def function(target: str) -> Callable:
    """The callable a `module:function` names, imported now."""
    module, name = target.split(":")
    return getattr(importlib.import_module(module), name)


@dataclass(frozen=True)
class Subject:
    """A file a layer measures for an acceptance spec, off the picture (§PW503).

    `accept.check` hands each predicate whose measure this subject names to `target`,
    called (predicate, subject, root, seen) -> {"value", "of", ...}: what the file
    measures, which file it was, and anything the layer adds to the predicate's
    report. `seen` is shared across one check, so a file measured once is not again.
    """

    #: What is measured, in a few words, which a refusal and `describe` show.
    about: str
    #: `module:NAME`, the layer's own table of the measures it answers, name to meaning.
    measures: str
    #: `module:function`, imported only when a spec bounds one of its measures.
    target: str

    def names(self) -> dict[str, str]:
        module, name = self.measures.split(":")
        return dict(getattr(importlib.import_module(module), name))


@dataclass(frozen=True)
class Producer:
    """Something a search can turn, and how one sample of it is made (§PW504).

    `search.sweep` asks the spec's producer for each sample and checks the spec against
    what it made; its passes, budget, trace and return are the same for every one.
    """

    #: What `search.sweep` names it by.
    name: str
    #: What one sample is, in a few words.
    about: str
    #: `module:function` making one sample, called (report, *, out, rung, root,
    #: inline, **values) -> dict with the `artefact` written and, where it has one,
    #: the `cache_key` a contact sheet is assembled from. A job runs the same target.
    target: str
    #: `module:function` answering which rung carries a spec's measures, called
    #: (asking=, floor=, root=) -> {"rung": ...}; none where the producer has no ladder.
    plan: str = ""
    #: `module:function` saying one parameter back with its unit, for a refusal.
    described: str = ""


@dataclass(frozen=True)
class Layer:
    """One medium's declaration: what it registers and what it needs to run."""

    name: str
    summary: str
    #: The modules that register operations, by their full dotted name.
    modules: tuple[str, ...]
    #: Without one of these the layer is present but cannot run (`REQUIREMENTS`).
    requires: tuple[str, ...] = ()
    #: The other layers this one imports, each edge declared; no cycle (§PW506).
    uses: tuple[str, ...] = ()
    #: The most this layer's served tools may cost tools/list, in characters
    #: (§PW510). A layer that grows past it raises it here, where it is read.
    tools: int = 0
    #: Where a person's verdict on what this layer lays out is kept (§PW501).
    judges: tuple[Judge, ...] = ()
    #: The record kinds this layer declares (§PW502). Any layer may write one; only one
    #: declares it, and the kernel's closed set is theirs and its own together.
    kinds: tuple[str, ...] = ()
    #: A source role to the `module:function` that says whether a changed file still
    #: describes a record, called (source, record, input) -> bool (§PW502). A role no
    #: layer claims is stale whenever its hash moved.
    staleness: dict[str, str] = field(default_factory=dict)
    #: `module:function` answering which files a build of this project ships, called
    #: (root, preset) -> (preset, paths), or None where the project is not its kind.
    ships: str = ""
    #: A section of `provenance.outdated` by its name, to the `module:function` that
    #: answers it for a root (§PW502).
    outdated: dict[str, str] = field(default_factory=dict)
    #: What a search can turn in this layer, each made one sample at a time (§PW504).
    producers: tuple[Producer, ...] = ()
    #: The files this layer measures off the picture, for an acceptance spec (§PW503).
    subjects: tuple[Subject, ...] = ()
    #: Named reads the shared surfaces call, each to its `module:function` (§PW505).
    #: `brief:<key>`, `report:<key>` and `review:<key>` add a section under that key
    #: to `asset.brief` (path, root), `loop.report` (root) and `review.state` (root);
    #: `brief.read:<kind>` reads an inventory item's declaration in its kind's words
    #: (item, record, root); any other name, such as the page's `page.admit`, is
    #: one a surface asks for by that name.
    parts: dict[str, str] = field(default_factory=dict)
    #: Picture measures this layer computes, by name, to the `module:function` called
    #: (image, mask, *, key, **arguments): part of the closed vocabulary all the same.
    pictures: dict[str, str] = field(default_factory=dict)
    #: The module holding this layer's `AREAS` and `CODES`, the errors it raises
    #: (§PW507); the kernel's table is the union.
    codes: str = ""
    #: The module holding this layer's polyweave.toml tables: `TABLES`, and `FREE`,
    #: `OPEN`, `NAMED`, `SETTINGS` and `CHOICES` where it has them (§PW508).
    config: str = ""
    #: This layer's helper modules, or single functions, to their kind (`internal` or
    #: `pending`) and the reason, which the census reads (§PW511). A module whose
    #: name starts with `_` is internal without being listed.
    census: dict[str, tuple[str, str]] = field(default_factory=dict)
    reports: tuple = ()


@functools.cache
def layers() -> dict[str, Layer]:
    """Every layer under `polyweave.layers`, by name, each read from its `layer.py`."""
    import polyweave.layers as package

    found: dict[str, Layer] = {}
    for one in sorted(pkgutil.iter_modules(package.__path__), key=lambda m: m.name):
        if not one.ispkg:
            continue
        where = f"polyweave.layers.{one.name}"
        if importlib.util.find_spec(f"{where}.layer") is None:
            raise PolyweaveError(
                "layer.undeclared",
                f"{where} has no layer.py, so nothing says what it adds",
                f"write src/polyweave/layers/{one.name}/layer.py holding one LAYER",
                given=where,
            )
        declared = getattr(importlib.import_module(f"{where}.layer"), "LAYER", None)
        if not isinstance(declared, Layer) or declared.name != one.name:
            raise PolyweaveError(
                "layer.undeclared",
                f"{where}.layer holds no LAYER named {one.name!r}",
                f"set LAYER = Layer(name={one.name!r}, ...) in that file",
                given=where,
            )
        unknown = [need for need in declared.requires if need not in REQUIREMENTS]
        if unknown:
            raise PolyweaveError(
                "layer.unknown-requirement",
                f"layer {one.name} requires {', '.join(unknown)}, which nothing probes",
                "name one of the requirements polyweave knows",
                given=unknown[0],
                allowed=sorted(REQUIREMENTS),
            )
        found[one.name] = declared
    _acyclic(found)
    return found


def _acyclic(found: dict[str, Layer]) -> None:
    """Refuse a layer using one that does not exist, or a cycle among their uses."""
    for name, declared in found.items():
        unknown = [one for one in declared.uses if one not in found]
        if unknown:
            raise PolyweaveError(
                "layer.unknown",
                f"layer {name} uses {', '.join(unknown)}, which no layer is",
                "name layers that exist in uses",
                given=unknown[0],
                allowed=sorted(found),
            )
    state: dict[str, int] = {}

    def visit(name: str, path: list[str]) -> None:
        if state.get(name) == 1:
            loop = " -> ".join([*path[path.index(name):], name])
            raise PolyweaveError(
                "layer.cycle",
                f"the layers use each other in a circle: {loop}",
                "move what both need below both, or turn one edge into a part",
                given=name,
            )
        if state.get(name) == 2:
            return
        state[name] = 1
        for one in found[name].uses:
            visit(one, [*path, name])
        state[name] = 2

    for name in found:
        visit(name, [])


def used(name: str) -> set[str]:
    """Every layer `name` uses, directly or through another."""
    found, every = set(), layers()
    stack = list(every[name].uses)
    while stack:
        one = stack.pop()
        if one not in found:
            found.add(one)
            stack.extend(every[one].uses)
    return found


def _once(what: str, pairs: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Each key to its value, refused where two layers declare one key."""
    found: dict[str, tuple[str, Any]] = {}
    for layer, key, value in pairs:
        if key in found:
            raise PolyweaveError(
                "layer.declared-twice",
                f"layers {found[key][0]} and {layer} both declare the {what} {key!r}",
                "keep it in the layer that owns it and drop it from the other",
                given=key,
            )
        found[key] = (layer, value)
    return {key: value for key, (_, value) in found.items()}


def record_kinds() -> tuple[str, ...]:
    """Every record kind a layer declares, each declared once (§PW502)."""
    return tuple(_once("record kind", [
        (name, kind, None) for name, one in layers().items() for kind in one.kinds
    ]))


def staleness() -> dict[str, str]:
    """Each source role a layer checks itself, to its check (§PW502)."""
    return _once("source role", [
        (name, role, target)
        for name, one in layers().items()
        for role, target in one.staleness.items()
    ])


def outdated_sections() -> dict[str, str]:
    """Each section a layer adds to `provenance.outdated`, to what answers it."""
    return _once("outdated section", [
        (name, section, target)
        for name, one in layers().items()
        for section, target in one.outdated.items()
    ])


def shipping() -> list[str]:
    """What answers which files a build ships, layer by layer (§PW502)."""
    return [one.ships for one in layers().values() if one.ships]


def subjects() -> dict[str, tuple[str, Subject]]:
    """Each measure a layer reads off a file, to that layer and its subject (§PW503)."""
    return _once("measure", [
        (name, measure, (name, one))
        for name, layer in layers().items()
        for one in layer.subjects
        for measure in one.names()
    ])


def producers() -> dict[str, Producer]:
    """Every producer a search can name, by its name (§PW504)."""
    return _once("producer", [
        (name, one.name, one) for name, layer in layers().items()
        for one in layer.producers
    ])


def parts() -> dict[str, str]:
    """Every named read a layer answers, to what answers it (§PW505)."""
    return _once("part", [
        (name, key, target) for name, layer in layers().items()
        for key, target in layer.parts.items()
    ])


def part(name: str) -> str | None:
    """What answers one named read, or None where no layer does."""
    return parts().get(name)


def needed(name: str) -> str:
    """What answers a named read a surface cannot do without, refused where none."""
    found = part(name)
    if found is None:
        raise PolyweaveError(
            "layer.missing-part",
            f"no layer answers {name!r}, which this call needs",
            "install the layer that declares it in its layer.py parts",
            given=name,
            allowed=sorted(parts()),
        )
    return found


def sections(surface: str) -> dict[str, str]:
    """Each section a layer adds to one surface (brief, report, review), by key."""
    prefix = f"{surface}:"
    return {
        key[len(prefix):]: target for key, target in parts().items()
        if key.startswith(prefix)
    }


def pictures() -> dict[str, str]:
    """Each picture measure a layer computes, to what computes it (§PW503)."""
    return _once("picture measure", [
        (name, measure, target)
        for name, layer in layers().items()
        for measure, target in layer.pictures.items()
    ])


def judges() -> dict[str, Judge]:
    """Every layer's judges, by the name each reports under."""
    found: dict[str, Judge] = {}
    for declared in layers().values():
        for one in declared.judges:
            if one.name in found:
                raise PolyweaveError(
                    "layer.two-judges",
                    f"two layers declare a judge named {one.name!r}",
                    "give one of them another name: it is the key its answer is "
                    "reported under",
                    given=one.name,
                )
            found[one.name] = one
    return found


def judge_of(member: dict) -> Judge | None:
    """The one judge that keeps this member's verdict, or None where no layer does.

    Two that claim one member are refused, never settled by which was asked first: a
    spoken take's `line` is the sound's verdict and never a line's because only the
    sound's judge claims it, not because its branch came earlier.
    """
    claiming = [one for one in judges().values() if one.claims(member)]
    if len(claiming) > 1:
        names = ", ".join(one.name for one in claiming)
        raise PolyweaveError(
            "verdict.judged-twice",
            f"{member.get('name')!r} is claimed by the judges {names}, so its verdict "
            "has two homes",
            "lay the member out with the keys of one medium only",
            given=str(member.get("name")),
            allowed=[one.name for one in claiming],
        )
    return claiming[0] if claiming else None


def on(root: str | Path = ".") -> frozenset[str]:
    """The layers a project uses: `[layers] on`, or every layer where it says none.

    A name no layer has is refused with the ones there are, since a typo here turns a
    whole medium off without a word.
    """
    from .config import load

    every = layers()
    named = [str(one) for one in load(root).get("layers.on") or ()]
    unknown = [one for one in named if one not in every]
    if unknown:
        raise PolyweaveError(
            "layer.unknown",
            f"[layers] on names {', '.join(unknown)}, which no layer is",
            "name layers capabilities lists, or drop [layers] for every one",
            given=unknown[0],
            allowed=sorted(every),
        )
    # A layer's uses do not switch the used layer's tools on: its own operations run
    # whatever is served, and serving more is the cost [layers] on exists to cut.
    return frozenset(named or every)


def off(layer: str | None, operation: str) -> PolyweaveError:
    """The refusal for an operation whose layer this project has off (§PW509)."""
    return PolyweaveError(
        "layer.off",
        f"{operation} is the {layer} layer's, and this project's [layers] on leaves "
        f"{layer} off",
        f'add "{layer}" to [layers] on in polyweave.toml',
        given=str(layer),
    )


def layer_of(module: str) -> str | None:
    """The layer a module's package is, or None for the core and anything outside."""
    parts = module.split(".")
    if len(parts) > 2 and parts[:2] == ["polyweave", "layers"]:
        return parts[2]
    return None


def owner(module: str) -> str | None:
    """The layer that names `module`, refused where its own layer does not (§PW500).

    A module under `layers/<name>/` registering an operation its layer never names
    would be found only by whoever imported it first, so the registry would hold it in
    one process and not in the next.
    """
    name = layer_of(module)
    if name is None:
        return None
    declared = layers().get(name)
    if declared is None or module not in declared.modules:
        raise PolyweaveError(
            "layer.unnamed-module",
            f"{module} registers an operation, and layer {name} does not name it",
            f"add {module!r} to modules in src/polyweave/layers/{name}/layer.py",
            given=module,
        )
    return name


def core_modules() -> list[str]:
    """Every module of the core packages, which `describe.load` imports whole."""
    out = []
    for package in CORE:
        here = importlib.import_module(f"polyweave.{package}")
        for found in pkgutil.walk_packages(here.__path__, f"{here.__name__}."):
            out.append(found.name)
    return sorted(out)


def missing(declared: Layer, present: dict[str, bool | None]) -> list[str]:
    """What `declared` requires that `present` says is absent; unknown is not absent."""
    return [need for need in declared.requires if present.get(need) is False]


def extra_present(name: str) -> bool:
    """Whether an optional extra's module would import here, without importing it."""
    return importlib.util.find_spec(EXTRAS[name]) is not None
