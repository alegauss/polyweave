"""What one geometry declaration can be built as, one module each (§PW514).

A declaration is a graph of ops; triangles and cells are two answers to it. Each
representation says which declarations it claims, which ops it cannot build, and how it
writes, reports and (where it can) fits and compares what it builds, so a third form is
a third module and not one more branch in `build.write`.
"""

from __future__ import annotations

import functools
import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass

from polyweave.kernel.errors import PolyweaveError


@dataclass(frozen=True)
class Representation:
    name: str
    #: The declaration's table that asks for this representation, or None for the one
    #: a declaration naming none of them is built as.
    table: str | None
    #: `(document, out, *, root, manifold, **given) -> dict`: built and written.
    write: Callable
    #: `(document, folder, here, given, preview, wanted, answer, mesh) -> dict`: one
    #: member of a family built, written and reported for the command line.
    member: Callable
    #: `(document, reference, **how) -> dict`, where it can fit to a reference.
    fit: Callable | None = None
    #: `(first, second, *, root) -> dict`, where two of its builds can be compared.
    compare: Callable | None = None


@functools.cache
def every() -> dict[str, Representation]:
    """Every representation this folder holds, by name."""
    found = {}
    for one in pkgutil.iter_modules(__path__):
        if one.name.startswith("_"):
            continue
        declared = importlib.import_module(f"{__name__}.{one.name}").REPRESENTATION
        found[declared.name] = declared
    return found


def claim(document: dict) -> Representation:
    """The one representation that builds this declaration: the one whose table it
    declares, or the default where it declares none. Two tables are refused, since a
    build chosen by order is a build chosen by accident."""
    found = every().values()
    claiming = [one for one in found if one.table and document.get(one.table)]
    if not claiming:
        claiming = [one for one in found if one.table is None]
    if len(claiming) != 1:
        raise PolyweaveError(
            "geom.bad-voxels",
            f"{document.get('name')!r} is claimed by "
            f"{', '.join(one.name for one in claiming) or 'no representation'}",
            "declare the tables of one representation: [voxels] for cells, none for "
            "triangles",
            allowed=sorted(every()),
        )
    return claiming[0]
