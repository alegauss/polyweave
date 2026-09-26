"""Two voxel models, compared cell by cell and material by material (§PW240).

A declaration rewritten into other words, a variant and a fit all ask the same thing:
which cells moved and which changed what they wear. Spinhold proved a rewrite of its
ship built the same model with a one-off script that set-diffed positions; this is
that answer, kept.

**Cells are compared where they sit, not where they are indexed.** Two grids can hold
the same cells at different indices when one carries an empty row, which moves its
origin and the box it is centred on. So each cell is placed at its middle in the
model's units, and the grids' own difference is reported beside the cells rather than
read as every cell having moved. **Materials are compared by name**, since a palette's
order is whatever the build met first.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ..errors import PolyweaveError

__all__ = ["compare", "load"]

#: How many cells a difference lists before it only counts them.
NAMED = 12


def load(stated: str | Path, *, root: str | Path = ".") -> dict:
    """A built model from its `.voxels.json`, or a declaration built to cells now."""
    here = Path(root).resolve()
    where = Path(stated)
    where = where if where.is_absolute() else here / where
    if not where.is_file():
        raise PolyweaveError(
            "geom.bad-voxels",
            f"there is no voxel model or declaration at {where}",
            "name a .voxels.json a build wrote, or a declaration with a [voxels] table",
        )
    if where.suffix == ".json":
        model = json.loads(where.read_text(encoding="utf-8"))
        if "cells" not in model or "cell" not in model:
            raise PolyweaveError(
                "geom.bad-voxels",
                f"{where.name} is not a voxel model: it has no cells",
                "name the .voxels.json a voxel build wrote",
            )
        return model
    from . import read
    from .voxels import voxelize

    document = read(where, root=here)
    if not document.get("voxels"):
        raise PolyweaveError(
            "geom.bad-voxels",
            f"{where.name} builds triangles, and there are no cells to compare",
            "give the declaration a [voxels] table, or name a .voxels.json",
        )
    return voxelize(document, root=here)


def _placed(model: dict) -> dict[tuple[int, int, int], str]:
    """Each cell's middle, in half cells from the model's zero, and what it wears."""
    cells, cell = model["cells"], float(model["cell"])
    at = np.column_stack([cells["x"], cells["y"], cells["z"]]).astype(float)
    middle = np.asarray(model["origin"], dtype=float) + (at + 0.5) * cell
    keys = np.rint(middle / cell * 2.0).astype(np.int64)
    names = [entry.get("name", "") for entry in model["palette"]]
    return {
        tuple(int(v) for v in key): names[slot]
        for key, slot in zip(keys, cells["palette"], strict=True)
    }


def _box(model: dict) -> dict:
    size = [int(n) for n in model["size"]]
    origin = [float(v) for v in model["origin"]]
    cell = float(model["cell"])
    return {
        "size": size,
        "origin": origin,
        "centre": [o + n * cell / 2.0 for o, n in zip(origin, size, strict=True)],
    }


def _listed(keys: list, cell: float) -> list[list[float]]:
    return [[k * cell / 2.0 for k in key] for key in sorted(keys)[:NAMED]]


def compare(first: dict, second: dict) -> dict:
    """What differs between two voxel models, cell by cell.

    `same` holds where every cell of each is a cell of the other wearing the same
    material. The grids may still differ, which is named under `grid` and does not
    count against `same`: an empty row moves a model's box, not its cells.
    """
    cells = [float(first["cell"]), float(second["cell"])]
    grids = [_box(first), _box(second)]
    grid = {
        "first": grids[0],
        "second": grids[1],
        "differs": grids[0]["size"] != grids[1]["size"]
        or not np.allclose(grids[0]["origin"], grids[1]["origin"]),
    }
    if not np.isclose(*cells):
        return {
            "same": False,
            "cell": cells,
            "grid": grid,
            "says": f"the cells are different sizes ({cells[0]:g} and {cells[1]:g}), "
            f"so no cell of one is a cell of the other",
        }
    one, other = _placed(first), _placed(second)
    only_first = [key for key in one if key not in other]
    only_second = [key for key in other if key not in one]
    repainted = sorted(
        (key, one[key], other[key])
        for key in one
        if key in other and one[key] != other[key]
    )
    same = not only_first and not only_second and not repainted
    cell = cells[0]
    said = (
        f"the same {len(one)} cells, each wearing the same material"
        if same
        else f"{len(only_first)} cells only in the first, {len(only_second)} only in "
        f"the second and {len(repainted)} wearing a different material"
    )
    if grid["differs"]:
        said += (
            f"; the grids differ, {_spelt(grids[0])} against {_spelt(grids[1])}, which "
            f"moves the box each is centred on"
        )
    return {
        "same": same,
        "cell": cells,
        "cells": [len(one), len(other)],
        "only_first": {"count": len(only_first), "at": _listed(only_first, cell)},
        "only_second": {"count": len(only_second), "at": _listed(only_second, cell)},
        "repainted": {
            "count": len(repainted),
            "at": [
                {"at": [k * cell / 2.0 for k in key], "was": was, "now": now}
                for key, was, now in repainted[:NAMED]
            ],
        },
        "grid": grid,
        "says": said,
    }


def _spelt(box: dict) -> str:
    size = " by ".join(str(n) for n in box["size"])
    origin = ", ".join(f"{v:g}" for v in box["origin"])
    return f"{size} from ({origin})"


def compared(first: Any, second: Any, *, root: str | Path = ".") -> dict:
    """Two models by path, each a `.voxels.json` or a voxel declaration."""
    return compare(load(first, root=root), load(second, root=root))
