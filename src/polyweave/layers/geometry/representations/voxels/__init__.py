"""Cells: a declaration built as a voxel model, beside the cubes' mesh (§PW93, §PW514).

`model` builds and writes the cells, `fit` fits a declaration's parameters to a
reference, `compare` holds two models cell by cell, `sheet` lays a model out for a
person, and `colour` is its palette.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import Representation


def _write(document: dict, out: str | Path, *, root: str | Path = ".",
          manifold: bool = False, **given: Any) -> dict:
    """The declaration built as cells; `out` holds the same cubes as a mesh."""
    from .model import write as cells

    return cells(document, out, root=root, **given)


def _member(document: dict, folder: Path, here: Path, given: dict, preview: bool,
           wanted: bool, answer: dict, mesh: Path) -> dict:
    """One member of a family built as cells, as the command line reports it."""
    from ...make import _cell_said, _has_blender, _unwanted
    from . import model

    if not wanted:
        _unwanted(mesh)
    written = model.write(
        document, mesh, root=here, mesh=wanted and _has_blender(), sheet=preview,
        **given,
    )
    answer["says"] = written["says"]
    answer["reads"] += _cell_said(written["model"], answer["warnings"])
    answer["findings"] = [
        f"{one['check']}: {one['says']}"
        for one in written["model"]["checks"]["findings"]
    ]
    answer["outputs"] = [
        written[key] for key in ("artefact", "voxels", "sheet") if written.get(key)
    ]
    return answer


def _fit(document: dict, reference: Any, **how: Any) -> dict:
    """A voxel declaration's [search] parameters fitted to a drawing or a mesh."""
    from .fit import fit as fitted

    return fitted(document, reference, **how)


def _compare(first: str, second: str, *, root: str | Path = ".") -> dict:
    """Two voxel models compared cell by cell."""
    from .compare import compared

    return compared(first, second, root=root)


REPRESENTATION = Representation(
    name="voxels",
    table="voxels",
    write=_write,
    member=_member,
    fit=_fit,
    compare=_compare,
)
