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
from dataclasses import dataclass

from .errors import PolyweaveError

#: The packages whose operations belong to every project rather than to one layer.
CORE = ("kernel", "loop", "services", "surface")

#: What a layer may say it needs, and how each is found: a binary is probed by
#: `capabilities`, an optional extra by whether its module imports.
REQUIREMENTS = {
    "blender": "the blender binary, or bpy importable",
    "godot": "the godot binary",
    "audio": "the audio extra: pip install polyweave[audio]",
    "text": "the text extra: pip install polyweave[text]",
}

#: The module each optional extra makes importable.
EXTRAS = {"audio": "pedalboard", "text": "fontTools"}


@dataclass(frozen=True)
class Layer:
    """One medium's declaration: what it registers and what it needs to run."""

    name: str
    summary: str
    #: The modules that register operations, by their full dotted name.
    modules: tuple[str, ...]
    #: Without one of these the layer is present but cannot run (`REQUIREMENTS`).
    requires: tuple[str, ...] = ()
    # What later lines contribute to the shared loop, empty until each lands: error
    # codes (§PW507), config tables (§PW508), census entries (§PW511), judges (§PW501),
    # staleness checks and record kinds (§PW502), and report sections (§PW505).
    codes: tuple = ()
    config: tuple = ()
    census: tuple = ()
    judges: tuple = ()
    staleness: tuple = ()
    kinds: tuple = ()
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
    return found


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
