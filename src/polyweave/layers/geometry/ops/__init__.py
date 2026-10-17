"""The geometry vocabulary, one module per op (§PW513).

Each module says everything about its op: the fields it reads, how it is built, the
box and the cells a voxel build reads off it (or that it is traced), and what the review
sheet says it is. `build.BUILDS`, `build.FIELDS`, `voxels.TRACED` and the two chains
that used to repeat the vocabulary are read from here, so a new op is one new file.
"""

from __future__ import annotations

import functools
import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Op:
    name: str
    fields: tuple[str, ...] | None
    build: Callable
    traced: bool
    bounds: Callable | None
    inside: Callable | None
    words: Callable | None


@functools.cache
def every() -> dict[str, Op]:
    """Every op this folder holds, by name, in the order the vocabulary lists them."""
    found = {}
    for one in pkgutil.iter_modules(__path__):
        if one.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{one.name}")
        found[module.NAME] = Op(
            name=module.NAME,
            fields=module.FIELDS,
            build=module.build,
            traced=module.TRACED,
            bounds=getattr(module, "bounds", None),
            inside=getattr(module, "inside", None),
            words=getattr(module, "words", None),
        )
    return {name: found[name] for name in ORDER if name in found} | {
        name: op for name, op in found.items() if name not in ORDER}


#: The order the vocabulary is listed in, which the review sheet and describe keep.
ORDER = (
    "primitive",
    "prism",
    "plate",
    "crowned",
    "annulus",
    "inflate",
    "union",
    "blend",
    "transform",
    "carve",
    "bevel",
    "custom",
    "cells",
    "mirror",
    "mesh",
    "paint",
)
