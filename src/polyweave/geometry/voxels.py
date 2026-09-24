"""The same declaration, answered as cells instead of triangles.

The evidence is §PW93. Starship draws its ship and its enemies as cubes and breaks them
apart when they are shot, so what it has to read is which cells exist and what each one
wears. A triangle mesh says neither: its faces are where the surface is, not what is
inside it, and a boolean hands back topology no game wants to walk.

**Evaluated on the grid, not traced off a mesh.** Each op answers "is this point
inside" at the centres of the cells: a primitive by its own formula, a prism by the
crossing test on its ring and its depth range, a plate as the rounded rectangle it is, a
transform by moving the sample points the other way, a union and a carve as the set
operations they are. That is exact, needs no Blender and no MANIFOLD, and runs in
milliseconds, so a search can afford thousands of builds. The ops with no test of their
own — `inflate`, `crowned`, `annulus` and `custom` — are built as meshes and read by
ray parity.

**A later node paints.** A cell wears the material of the last node in the document that
covers it and carries one, so a cockpit declared after the hull is the cockpit's colour.
Document order rather than `order`'s, because `order` breaks ties by name and a cockpit
called `canopy` would lose to a hull called `hull` for no reason anyone wrote down.

A `bevel` passes its input through. It rounds an edge by less than the cells it would be
sampled at, and a carve done beside it is the op that changes which cells exist.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..errors import PolyweaveError
from . import expand, refers_to
from . import outline as O
from . import solid as S
from .expr import evaluate

__all__ = ["SUFFIX", "TRACED", "says", "voxelize", "write"]

#: What the cells are written as, beside the cubes' mesh.
SUFFIX = ".voxels.json"

#: The ops with no inside-test of their own, voxelised from the mesh they build. A
#: `mesh` node is one (§PW100): filled by parity, a closed hull comes out solid.
TRACED = ("inflate", "crowned", "annulus", "custom", "mesh")

#: What a painted cell's key is lifted by, so any node carrying a material outranks any
#: node that does not, whatever their order.
_PAINTED = 1 << 20

_EPS = 1e-9


@dataclass
class _Found:
    """Which of the sample points are inside, and who decides what each one wears.

    `wears` is per point and not per node, because a `cells` node paints each of its
    cells from its own legend (§PW95).
    """

    inside: np.ndarray
    key: np.ndarray
    owner: np.ndarray
    wears: np.ndarray

    @classmethod
    def of(cls, inside: np.ndarray, rank: int) -> _Found:
        mark = np.where(inside, rank, -1)
        return cls(inside, mark.copy(), mark, np.full(len(inside), "", dtype=object))

    @classmethod
    def drawn(cls, inside: np.ndarray, rank: int, wears: np.ndarray) -> _Found:
        """Cells that each name what they wear, painting where they name anything."""
        worn = inside & (wears != "")
        key = np.where(inside, np.where(worn, rank + _PAINTED, rank), -1)
        return cls(inside, key, np.where(inside, rank, -1), np.where(inside, wears, ""))

    def painted(self, rank: int, material: str) -> _Found:
        return _Found(
            self.inside,
            np.where(self.inside, rank + _PAINTED, self.key),
            np.where(self.inside, rank, self.owner),
            np.where(self.inside, material, self.wears),
        )

    def only(self, kept: np.ndarray) -> _Found:
        return _Found(
            kept,
            np.where(kept, self.key, -1),
            np.where(kept, self.owner, -1),
            np.where(kept, self.wears, ""),
        )


def _merge(one: _Found, other: _Found) -> _Found:
    """Both sets of cells, the later key deciding where they overlap."""
    takes = other.inside & (~one.inside | (other.key > one.key))
    return _Found(
        one.inside | other.inside,
        np.where(takes, other.key, one.key),
        np.where(takes, other.owner, one.owner),
        np.where(takes, other.wears, one.wears),
    )


class _Model:
    """One resolved document, able to say where each node is and what is inside it."""

    def __init__(
        self, document: dict, root: Path, given: dict, cell: float | None = None
    ) -> None:
        self.document, self.root, self.given = document, root, given
        self.resolved = expand(document, **given)
        self.stated = {node["id"]: node for node in document["nodes"]}
        self.instanced = {node["id"]: node for node in self.resolved["nodes"]}
        self.rank = {node["id"]: at for at, node in enumerate(document["nodes"])}
        self.cell = cell or stated_cell(document, self.resolved["params"])
        self._meshes: dict | None = None
        self._traced_by: dict[int, dict] = {}

    # -- where a node is ---------------------------------------------------------------

    def bounds(self, one: str) -> tuple[np.ndarray, np.ndarray]:
        node = self.stated[one]
        boxes = []
        for instance in self.instanced[one]["instances"]:
            low, high = self._op_bounds(node, instance)
            if node["op"] != "transform" and instance.get("at") is not None:
                shift = np.asarray(S._triple(instance["at"]))
                low, high = low + shift, high + shift
            boxes.append((low, high))
        return (
            np.min([low for low, _ in boxes], axis=0),
            np.max([high for _, high in boxes], axis=0),
        )

    def _op_bounds(self, node: dict, instance: dict) -> tuple[np.ndarray, np.ndarray]:
        op = node["op"]
        if op == "primitive":
            half = float(instance.get("size", 1.0)) / 2.0
            depth = 0.0 if instance.get("kind", "cube") == "plane" else half
            return np.array([-half, -half, -depth]), np.array([half, half, depth])
        if op in ("prism", "plate"):
            ring, near, far = self._slab(op, instance)
            return (
                np.array([*ring.min(axis=0), near]),
                np.array([*ring.max(axis=0), far]),
            )
        if op == "transform":
            low, high = self.bounds(refers_to(node)[0])
            corners = np.array(
                [
                    [x, y, z]
                    for x in (low[0], high[0])
                    for y in (low[1], high[1])
                    for z in (low[2], high[2])
                ]
            )
            moved = _forward(corners, instance)
            return moved.min(axis=0), moved.max(axis=0)
        if op == "union":
            boxes = [self.bounds(one) for one in refers_to(node)]
            return (
                np.min([low for low, _ in boxes], axis=0),
                np.max([high for _, high in boxes], axis=0),
            )
        if op == "carve":
            return self.bounds(node["into"])
        if op == "bevel":
            return self.bounds(refers_to(node)[0])
        if op == "cells":
            size = self.size_of(node, instance)
            return np.zeros(3), np.asarray(lattice(node)["size"], dtype=float) * size
        if op == "mirror":
            low, high = self.bounds(refers_to(node)[0])
            along, plane = _mirrored(node, instance)
            flipped_low, flipped_high = low.copy(), high.copy()
            flipped_low[along] = 2 * plane - high[along]
            flipped_high[along] = 2 * plane - low[along]
            return np.minimum(low, flipped_low), np.maximum(high, flipped_high)
        points = np.asarray(self._traced(node, instance)["vertices"], dtype=float)
        return points.min(axis=0), points.max(axis=0)

    # -- what is inside it -------------------------------------------------------------

    def inside(self, one: str, points: np.ndarray) -> _Found:
        node = self.stated[one]
        found = None
        for instance in self.instanced[one]["instances"]:
            here = points
            if node["op"] != "transform" and instance.get("at") is not None:
                here = points - np.asarray(S._triple(instance["at"]))
            part = self._op_inside(node, instance, here)
            found = part if found is None else _merge(found, part)
        if node.get("material"):
            found = found.painted(self.rank[one], node["material"])
        return found

    def _op_inside(self, node: dict, instance: dict, points: np.ndarray) -> _Found:
        op, rank = node["op"], self.rank[node["id"]]
        if op == "primitive":
            return _Found.of(_primitive(instance, points), rank)
        if op in ("prism", "plate"):
            ring, near, far = self._slab(op, instance)
            depth = (points[:, 2] >= near - _EPS) & (points[:, 2] <= far + _EPS)
            within = np.zeros(len(points), dtype=bool)
            if depth.any():
                within[depth] = S._inside(ring, points[depth, :2])
            return _Found.of(within, rank)
        if op == "transform":
            return self.inside(refers_to(node)[0], _backward(points, instance))
        if op == "union":
            found = None
            for one in refers_to(node):
                part = self.inside(one, points)
                found = part if found is None else _merge(found, part)
            return found
        if op == "carve":
            into = self.inside(node["into"], points)
            cut = self.inside(node["cutter"], points).inside
            return into.only(into.inside & ~cut)
        if op == "bevel":
            return self.inside(refers_to(node)[0], points)
        if op == "cells":
            return self._drawn(node, instance, points)
        if op == "mirror":
            # A point is in the mirror where it or its reflection is in the half, so a
            # column on the plane is one set of cells and never counted twice.
            source = refers_to(node)[0]
            along, plane = _mirrored(node, instance)
            reflected = points.copy()
            reflected[:, along] = 2 * plane - reflected[:, along]
            return _merge(self.inside(source, points), self.inside(source, reflected))
        return _Found.of(_parity(self._traced(node, instance), points), rank)

    def _drawn(self, node: dict, instance: dict, points: np.ndarray) -> _Found:
        """A `cells` node: which drawn cell each point falls in, and what it wears."""
        grid, size = lattice(node), self.size_of(node, instance)
        index = np.floor(points / size + _EPS).astype(np.int64, copy=False)
        within = np.all((index >= 0) & (index < np.asarray(grid["size"])), axis=1)
        wears = np.full(len(points), "", dtype=object)
        filled = np.zeros(len(points), dtype=bool)
        if within.any():
            at = tuple(index[within].T)
            filled[within] = grid["filled"][at]
            wears[within] = grid["wears"][at]
        return _Found.drawn(filled, self.rank[node["id"]], wears)

    def size_of(self, node: dict, instance: dict) -> float:
        """How big a `cells` node's cells are: its own `cell`, or the document's."""
        size = instance.get("cell") or self.cell
        if not size or float(size) <= 0:
            raise PolyweaveError(
                "geom.bad-cells",
                f"{node['id']} draws cells and nothing says how big one is",
                "give the node a `cell`, or give [voxels] a `cell` rather than only "
                "`across`; the drawing's cells cannot wait for the bounds they make",
            )
        return float(size)

    # -- the pieces the tests are made of ----------------------------------------------

    def _slab(self, op: str, instance: dict) -> tuple[np.ndarray, float, float]:
        """A prism's or a plate's ring, and the depth range it is swept through."""
        from .build import _outline

        if op == "plate":
            x, y, wide, tall = (float(v) for v in instance["rect"])
            ring = O.rounded_square((wide, tall), float(instance.get("corner", 0.0)))
            ring = ring + np.array([x + wide / 2, y + tall / 2])
        else:
            ring = O._ring(_outline(instance, self.root))
        front = float(instance.get("front", 0.0))
        far = front + float(instance["depth"])
        return ring, min(front, far), max(front, far)

    def _traced(self, node: dict, instance: dict) -> dict:
        """The mesh an op with no inside-test builds, for ray parity to read.

        Built once per instance: the bounds and every inside-test ask for it, and a
        `mesh` node reading its file through Blender each time would cost a load per
        question.
        """
        kept = self._traced_by.get(id(instance))
        if kept is None:
            kept = self._traced_by[id(instance)] = self._trace(node, instance)
        return kept

    def _trace(self, node: dict, instance: dict) -> dict:
        from .build import BUILDS

        built = {}
        if refers_to(node):
            if self._meshes is None:
                from .build import build

                self._meshes = build(self.document, root=self.root, **self.given)[
                    "built"
                ]
            built = self._meshes
        return BUILDS[node["op"]](node, instance, built, self.root)


def _primitive(instance: dict, points: np.ndarray) -> np.ndarray:
    kind = str(instance.get("kind", "cube"))
    half = float(instance.get("size", 1.0)) / 2.0 + _EPS
    if kind == "cube":
        return np.all(np.abs(points) <= half, axis=1)
    if kind == "sphere":
        return np.linalg.norm(points, axis=1) <= half
    if kind == "cylinder":
        return (np.linalg.norm(points[:, :2], axis=1) <= half) & (
            np.abs(points[:, 2]) <= half
        )
    if kind == "plane":
        return np.zeros(len(points), dtype=bool)
    raise PolyweaveError(
        "geom.unknown-shape",
        f"there is no primitive called {kind!r}",
        "name one of cube, plane, cylinder, sphere",
    )


def _mirrored(node: dict, instance: dict) -> tuple[int, float]:
    """A mirror's axis and where its plane sits along it."""
    return S.axis(node.get("axis", "x")), float(instance.get("plane", 0.0))


def _forward(points: np.ndarray, instance: dict) -> np.ndarray:
    """Scale, then rotate, then place — `solid.transform`'s order."""
    stretch = np.asarray(S._triple(instance.get("scale", (1, 1, 1))), dtype=float)
    turn = S._turn(instance.get("rotate", (0, 0, 0)))
    return (points * stretch) @ turn.T + np.asarray(
        S._triple(instance.get("at", (0, 0, 0)))
    )


def _backward(points: np.ndarray, instance: dict) -> np.ndarray:
    """Where a point came from before the transform, so the input can be asked."""
    stretch = np.asarray(S._triple(instance.get("scale", (1, 1, 1))), dtype=float)
    turn = S._turn(instance.get("rotate", (0, 0, 0)))
    moved = (points - np.asarray(S._triple(instance.get("at", (0, 0, 0))))) @ turn
    with np.errstate(divide="ignore", invalid="ignore"):
        # A zero scale flattens its input to nothing, and a NaN is inside no test.
        return np.where(
            stretch == 0.0, np.nan, moved / np.where(stretch == 0.0, 1.0, stretch)
        )


def _parity(mesh: dict, points: np.ndarray) -> np.ndarray:
    """Inside a closed mesh: a ray up from the point crosses its surface an odd number
    of times.

    The ray starts a hair off the point in x and y, so a cell centre lined up exactly
    with an edge of the mesh is counted by one of the two triangles sharing it and not
    by both — a grid and a built mesh line up far more often than chance would.
    """
    vertices = np.asarray(mesh["vertices"], dtype=float)
    out = np.zeros(len(points), dtype=bool)
    if not len(vertices) or not len(points):
        return out
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    near = np.all((points >= low - _EPS) & (points <= high + _EPS), axis=1)
    if not near.any():
        return out
    probe = points[near] + np.array([1.3e-7, 0.7e-7, 0.0])
    crossings = np.zeros(len(probe), dtype=int)
    for face in mesh["faces"]:
        for second in range(1, len(face) - 1):
            a, b, c = (
                vertices[face[0]],
                vertices[face[second]],
                vertices[face[second + 1]],
            )
            crossings += _crosses(a, b, c, probe)
    out[near] = crossings % 2 == 1
    return out


def _crosses(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, probe: np.ndarray
) -> np.ndarray:
    """Which points a triangle sits above, seen straight down the z axis."""
    denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(denominator) < 1e-15:
        return np.zeros(len(probe), dtype=int)
    x, y = probe[:, 0] - c[0], probe[:, 1] - c[1]
    u = ((b[1] - c[1]) * x + (c[0] - b[0]) * y) / denominator
    v = ((c[1] - a[1]) * x + (a[0] - c[0]) * y) / denominator
    w = 1.0 - u - v
    over = (u >= 0) & (v >= 0) & (w >= 0)
    height = u * a[2] + v * b[2] + w * c[2]
    return (over & (height > probe[:, 2])).astype(int)


# -- cells drawn as text ---------------------------------------------------------------

#: The character a `cells` drawing leaves empty.
EMPTY = "."


def lattice(node: dict) -> dict:
    """A `cells` node's drawing, read into arrays over its own grid (§PW95).

    `layers` is a list of slices along z, the first at the front; each is a list of
    rows written top to bottom, one character a cell, so a row reads as it looks.
    `legend` names what each character wears and `.` is empty. A character the legend
    does not name is refused rather than left empty, since a typo that erased a cell
    would look exactly like a cell that was meant not to be there.
    """
    layers, legend = node.get("layers"), dict(node.get("legend") or {})
    named = node.get("id", "a cells node")
    if (
        not isinstance(layers, list)
        or not layers
        or not all(
            isinstance(layer, list) and layer and all(isinstance(r, str) for r in layer)
            for layer in layers
        )
    ):
        raise PolyweaveError(
            "geom.bad-cells",
            f"{named} has no layers of rows to read",
            "give it `layers`, a list of slices, each a list of strings of one "
            "character per cell",
        )
    tall, wide = len(layers[0]), len(layers[0][0])
    for depth, layer in enumerate(layers):
        if len(layer) != tall or any(len(row) != wide for row in layer):
            raise PolyweaveError(
                "geom.bad-cells",
                f"{named}: layer {depth} is not {wide} by {tall} like the first one",
                "make every row and every layer the same size; pad with `.` where a "
                "slice has fewer cells",
            )
    unknown = sorted(
        {c for layer in layers for row in layer for c in row} - set(legend) - {EMPTY}
    )
    if unknown:
        raise PolyweaveError(
            "geom.bad-cells",
            f"{named} draws {', '.join(repr(c) for c in unknown)}, which its legend "
            f"does not name",
            "add each one to `legend` with the material it wears, or write `.` for an "
            "empty cell",
        )
    size = (wide, tall, len(layers))
    filled = np.zeros(size, dtype=bool)
    wears = np.full(size, "", dtype=object)
    for z, layer in enumerate(layers):
        for row, text in enumerate(layer):
            y = tall - 1 - row
            for x, character in enumerate(text):
                if character != EMPTY:
                    filled[x, y, z] = True
                    wears[x, y, z] = str(legend[character] or "")
    return {"size": size, "filled": filled, "wears": wears}


def stated_cell(document: dict, params: dict) -> float | None:
    """The cell size `[voxels]` gives outright, or None where it gives only `across`."""
    stated = (document.get("voxels") or {}).get("cell")
    if stated in (None, ""):
        return None
    return float(evaluate(stated, params, where="voxels.cell"))


def drawn_mesh(node: dict, size: float) -> dict:
    """A `cells` node as cubes, for a document built as triangles rather than cells."""
    grid = lattice(node)
    where = np.argwhere(grid["filled"])
    names = list(dict.fromkeys(grid["wears"][tuple(where.T)].tolist()))
    slot = {one: at for at, one in enumerate(names)}
    return cubes(
        {
            "cell": size,
            "size": list(grid["size"]),
            "origin": [0.0, 0.0, 0.0],
            "palette": [{"name": one} for one in names],
            "cells": {
                "x": where[:, 0].tolist(),
                "y": where[:, 1].tolist(),
                "z": where[:, 2].tolist(),
                "palette": [slot[one] for one in grid["wears"][tuple(where.T)]],
            },
        }
    )


# -- the grid --------------------------------------------------------------------------


def _cell(document: dict, params: dict, extent: np.ndarray, **stated: Any) -> float:
    """The size of one cell, from `cell` or from `across`, and never from both."""
    table = {**(document.get("voxels") or {}), **{k: v for k, v in stated.items() if v}}
    given = [one for one in ("cell", "across") if table.get(one) not in (None, "")]
    if len(given) != 1:
        raise PolyweaveError(
            "geom.bad-voxels",
            f"{document['name']} asks for cells and says "
            + (
                "neither how big one is nor how many go across"
                if not given
                else "both how big one is and how many go across"
            ),
            "give [voxels] one of `cell`, a size, or `across`, a count of cells along "
            "the longest side",
        )
    value = evaluate(table[given[0]], params, where=f"voxels.{given[0]}")
    if value <= 0:
        raise PolyweaveError(
            "geom.bad-voxels",
            f"{document['name']}: voxels.{given[0]} is {value:g}, and a cell has to "
            f"have a size",
            "give it a value above zero",
        )
    if given[0] == "cell":
        return float(value)
    longest = float(np.max(extent))
    return longest / max(1, round(value)) if longest > 0 else 1.0


def voxelize(
    document: dict,
    *,
    root: str | Path = ".",
    cell: float | None = None,
    across: int | None = None,
    **given: Any,
) -> dict:
    """Which cells a declaration fills, and what each one wears.

    The grid is centred on what the output covers, so a symmetric shape comes back
    symmetric, and a cell is filled where its centre is inside. A document with a
    `cells` node is the exception: its grid sits on whole cells from the origin, so a
    drawn cell is a cell of the model and not split between two. `cell` or `across`
    override the document's own `[voxels]` for this call.
    """
    model = _Model(document, Path(root).resolve(), given, cell=cell)
    output = document["output"]
    low, high = model.bounds(output)
    extent = high - low
    size = _cell(document, model.resolved["params"], extent, cell=cell, across=across)
    if any(node["op"] == "cells" for node in document["nodes"]):
        origin = np.floor(low / size + 1e-6) * size
        counts = np.maximum(np.ceil((high - origin) / size - 1e-6).astype(int), 1)
    else:
        counts = np.maximum(np.ceil(extent / size - 1e-6).astype(int), 1)
        origin = (low + high) / 2.0 - counts * size / 2.0

    index = np.stack(
        np.meshgrid(*(np.arange(n) for n in counts), indexing="ij"), axis=-1
    ).reshape(-1, 3)
    found = model.inside(output, origin + (index + 0.5) * size)
    filled = index[found.inside]
    owners = found.owner[found.inside]

    names = [node["id"] for node in document["nodes"]]
    wears = [str(one) for one in found.wears[found.inside].tolist()]
    materials = model.resolved["materials"]
    palette_names = [one for one in materials if one in set(wears)]
    palette_names += sorted({one for one in wears if one not in palette_names})
    palette = [
        {"name": one, **(materials.get(one) or {})} if one else {"name": ""}
        for one in palette_names
    ]
    at = {one: slot for slot, one in enumerate(palette_names)}

    made = {
        "name": document["name"],
        "cell": float(size),
        "size": [int(n) for n in counts],
        "origin": [float(v) for v in origin],
        "palette": palette,
        "nodes": names,
        "cells": {
            "x": filled[:, 0].tolist(),
            "y": filled[:, 1].tolist(),
            "z": filled[:, 2].tolist(),
            "palette": [at[one] for one in wears],
            "node": owners.tolist(),
        },
        "count": len(filled),
    }
    made["says"] = says(made)
    made["checks"] = _checked(made, document, model.resolved["params"], root)
    stated = (document.get("voxels") or {}).get("fracture")
    if stated:
        from .fracture import plan

        made["fracture"] = plan(made, stated)
    return made


def _checked(made: dict, document: dict, params: dict, root: str | Path) -> dict:
    """What the cells are checked for (§PW97), with the project's own limits.

    `parts` and `extent` are the model's and come from its `[voxels]`; the budget, the
    thread length and the symmetry bar are the game's and come from the project config.
    """
    from .. import post
    from ..config import load

    settings = load(root)
    table = document.get("voxels") or {}
    extent = table.get("extent") or settings.get("voxels.extent")
    return post.check(
        "voxels",
        made,
        parts=int(evaluate(table.get("parts", 1), params, where="voxels.parts")),
        thread=int(settings.get("voxels.thread")),
        budget=int(settings.get("voxels.budget")),
        extent=[evaluate(v, params, where="voxels.extent") for v in extent or ()],
        near_symmetry=float(settings.get("voxels.near_symmetry")),
    )


def says(model: dict) -> str:
    """The voxel model in one line: the readback a mesh gets as a face count."""
    wide, deep, tall = model["size"]
    materials = len(model["palette"])
    return (
        f"a voxel model {wide} by {deep} by {tall}, {model['count']} cells in "
        f"{materials} material{'' if materials == 1 else 's'}"
    )


# -- the cubes, for everything that takes a mesh ---------------------------------------

#: Each face of a unit cell, as its four corners wound to face outward, and the
#: neighbour whose absence exposes it.
_FACES = (
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
)


def cubes(model: dict) -> dict:
    """The cells as a mesh of their exposed faces, grouped by what they wear.

    Only the faces with no neighbour behind them, since a face between two cells is one
    nobody will see and every renderer would pay for.
    """
    cells = model["cells"]
    where = np.column_stack([cells["x"], cells["y"], cells["z"]]).astype(int)
    wears = np.asarray(cells["palette"], dtype=int)
    size = float(model["cell"])
    origin = np.asarray(model["origin"], dtype=float)
    filled = np.zeros(model["size"], dtype=bool)
    if len(where):
        filled[tuple(where.T)] = True
    padded = np.pad(filled, 1)

    vertices, faces, face_wears = [], [], []
    for step, corners in _FACES:
        ahead = where + np.asarray(step) + 1
        exposed = ~padded[tuple(ahead.T)] if len(where) else np.zeros(0, dtype=bool)
        for cell, worn in zip(where[exposed], wears[exposed], strict=True):
            start = len(vertices)
            vertices += [origin + (cell + np.asarray(c)) * size for c in corners]
            faces.append((start, start + 1, start + 2, start + 3))
            face_wears.append(int(worn))

    order = sorted(range(len(faces)), key=lambda one: face_wears[one])
    faces = [faces[one] for one in order]
    face_wears = [face_wears[one] for one in order]
    groups, begun = [], 0
    for slot, entry in enumerate(model["palette"]):
        count = face_wears.count(slot)
        if count and entry["name"]:
            groups.append({"material": entry["name"], "faces": [begun, begun + count]})
        begun += count
    made = S.mesh(np.asarray(vertices).reshape(-1, 3), faces)
    if groups:
        made["groups"] = groups
    return made


def write(
    document: dict,
    out: str | Path,
    *,
    root: str | Path = ".",
    mesh: bool = True,
    sheet: bool = True,
    **given: Any,
) -> dict:
    """The cells as `<stem>.voxels.json`, and beside it the same cubes as `out`.

    `out` is the mesh's path, as `build.write` takes it, so `bake` and every render read
    a voxel model unchanged. `mesh=False` writes the cells alone, needing no Blender.
    A contact sheet goes beside the cells as `<stem>.voxels.png` (§PW94) unless
    `sheet=False`; `pixels`, `grid` and `labels` are passed to it.
    """
    from . import voxel_sheet

    drawn = voxel_sheet.options(given)
    made = voxelize(document, root=root, **given)
    where = Path(out)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    cells = where.with_name(where.stem + SUFFIX)
    cells.parent.mkdir(parents=True, exist_ok=True)
    cells.write_text(json.dumps(_plain(made), indent=1) + "\n", encoding="utf-8")
    answer = {"model": made, "says": made["says"], "voxels": str(cells)}
    if sheet:
        looked = voxel_sheet.sheet(made, voxel_sheet.beside(cells), **drawn)
        answer["sheet"] = looked["sheet"]
    if mesh:
        from ..normalise import write_mesh

        written = write_mesh(cubes(made), where, materials=document.get("materials"))
        answer["artefact"] = str(written)
    return answer


def _plain(value: Any) -> Any:
    """What JSON can hold, from whatever numpy handed back through a material table."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
