"""Parts joined by a smooth fillet where they meet and nowhere else (§PW498).

`union` is a join and `carve` a boolean, so where two parts meet the seam is a crease,
and a bevel after it rounds every edge alike. Moulded plastic flows: a tower's roof
pours into its walls, a tree's crown melts onto its trunk. A `blend` asks for exactly
that, a fillet of `radius` where the parts meet:

    [[nodes]]
    id     = "tree"
    op     = "blend"
    inputs = ["trunk", "crown"]
    radius = 0.15

**A distance field, meshed back to triangles.** Each part is the distance to its
surface, and the round union of two such fields is the union everywhere they are more
than `radius` from each other, and a circular fillet of that radius where they come
closer. So the fillet appears at the seam and nowhere else, and is the radius stated.

**The field is each primitive's own formula**, carried through `transform`, placement
and repeats, which is what the plastic city's pieces are made of: boxes, rounded boxes,
capsules, spheres, cylinders, cones and tori, moved and turned. A part with no field, a
prism or a mesh file, is refused by name; a field for an arbitrary mesh would be a
second geometry kernel, and the pieces this is for never need one.

The meshing is marching tetrahedra on a grid `2 x steps` cells across the longest side,
six tetrahedra a cube all split along one diagonal, so neighbouring cubes agree on every
face and the surface is closed. Each face wears the material of the part nearest it.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polyweave.kernel.errors import PolyweaveError

from . import solid as S

__all__ = ["blend", "distance", "round_union"]


def _cone(q: np.ndarray, y: np.ndarray, h: float, r1: float, r2: float) -> np.ndarray:
    """A capped cone's distance: `q` across its axis, `y` along it, half-height `h`."""
    k1 = np.array([r2, h])
    k2 = np.array([r2 - r1, 2.0 * h])
    across = np.where(y < 0.0, r1, r2)
    ca = np.stack([q - np.minimum(q, across), np.abs(y) - h], axis=1)
    point = np.stack([q, y], axis=1)
    reach = np.clip(((k1 - point) @ k2) / max(float(k2 @ k2), 1e-12), 0.0, 1.0)
    cb = point - k1 + k2 * reach[:, None]
    inside = (cb[:, 0] < 0.0) & (ca[:, 1] < 0.0)
    return np.where(inside, -1.0, 1.0) * np.sqrt(
        np.minimum((ca**2).sum(axis=1), (cb**2).sum(axis=1)))


def distance(found: dict, points: np.ndarray) -> np.ndarray:
    """How far each point is from a primitive's surface, negative inside.

    The primitive is the description `solid.shape` returns, in its own frame. A sphere
    of three extents is an ellipsoid, read to within its axes' ratio, and an oval
    cylinder or cone is read as round across its first axis.
    """
    kind = found["kind"]
    if kind == "plane":
        raise PolyweaveError(
            "geom.bad-solid",
            "a plane has no inside, so it has no distance field to blend",
            "blend solids: a cube, a rounded_box, a capsule, a sphere, a cylinder, a "
            "cone, a frustum or a torus",
        )
    if kind in ("cube", *S.ROUNDED):
        radius = found.get("radius", 0.0)
        reach = np.abs(points) - (np.asarray(found["extents"]) / 2.0 - radius)
        outside = np.linalg.norm(np.maximum(reach, 0.0), axis=1)
        return outside + np.minimum(reach.max(axis=1), 0.0) - radius
    if kind == "sphere":
        half = np.maximum(np.asarray(found["extents"]) / 2.0, 1e-9)
        k0 = np.linalg.norm(points / half, axis=1)
        k1 = np.maximum(np.linalg.norm(points / half**2, axis=1), 1e-12)
        return k0 * (k0 - 1.0) / k1
    u, v, w = (points[:, i] for i in found["order"])
    if kind == "torus":
        return np.hypot(np.hypot(u, v) - found["major"], w) - found["minor"]
    (bu, bv), (tu, tv) = found["radii"]
    stretch = bu / bv if bu and bv else (tu / tv if tu and tv else 1.0)
    return _cone(np.hypot(u, v * stretch), w, found["height"] / 2.0, bu, tu)


def _field_of(part: dict, points: np.ndarray) -> np.ndarray:
    """One part's distance at world points: its primitive, moved by its matrix."""
    matrix = np.asarray(part["matrix"], dtype=float)
    linear = matrix[:3, :3]
    local = (points - matrix[:3, 3]) @ np.linalg.inv(linear).T
    # A scale stretches distance; the least stretch keeps it a bound, never an
    # overstatement, so the surface lands where the zero is.
    least = float(np.linalg.svd(linear, compute_uv=False).min())
    return distance(part["shape"], local) * least


def round_union(a: np.ndarray, b: np.ndarray, radius: float) -> np.ndarray:
    """Two fields joined with a circular fillet of `radius` where they come close."""
    u, v = np.maximum(radius - a, 0.0), np.maximum(radius - b, 0.0)
    return np.maximum(radius, np.minimum(a, b)) - np.hypot(u, v)


#: A cube's corners, and its six tetrahedra all around the diagonal from 0 to 6, so two
#: cubes that share a face split it the same way and the surface has no crack.
_CORNERS = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                     [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
_TETRAHEDRA = np.array([[0, 5, 1, 6], [0, 1, 2, 6], [0, 2, 3, 6],
                        [0, 3, 7, 6], [0, 7, 4, 6], [0, 4, 5, 6]])


def _surface(field: np.ndarray, low: np.ndarray, cell: float) -> tuple:
    """The zero of a sampled field as welded triangles, each facing out."""
    nx, ny, nz = field.shape
    ids = np.arange(nx * ny * nz).reshape(field.shape)
    base = ids[:-1, :-1, :-1].reshape(-1)
    step = np.array([ny * nz, nz, 1])
    corner = base[:, None] + (_CORNERS @ step)[None, :]
    tets = corner[:, _TETRAHEDRA].reshape(-1, 4)
    values = field.reshape(-1)[tets]
    inside = values < 0.0
    count = inside.sum(axis=1)
    keep = (count > 0) & (count < 4)
    tets, values, inside, count = tets[keep], values[keep], inside[keep], count[keep]
    rank = np.argsort(~inside, axis=1, kind="stable")  # the inside corners first
    picked = np.take_along_axis(tets, rank, axis=1)

    def crossing(a, b):
        return np.stack([a, b], axis=1)

    triangles, inner = [], []
    one = count == 1
    three = count == 3
    for mask, lone, rest in ((one, 0, (1, 2, 3)), (three, 3, (0, 1, 2))):
        chosen = picked[mask]
        triangles.append(np.stack([crossing(chosen[:, lone], chosen[:, k])
                                   for k in rest], axis=1))
        inner.append(chosen[:, [0]] if lone == 0 else chosen[:, :3])
    two = picked[count == 2]
    quad = [crossing(two[:, 0], two[:, 2]), crossing(two[:, 0], two[:, 3]),
            crossing(two[:, 1], two[:, 3]), crossing(two[:, 1], two[:, 2])]
    for k in ((0, 1, 2), (0, 2, 3)):
        triangles.append(np.stack([quad[i] for i in k], axis=1))
        inner.append(two[:, :2])
    edges = np.concatenate([t.reshape(-1, 2) for t in triangles])
    if not len(edges):
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=int)
    edges = np.sort(edges, axis=1)
    unique, where = np.unique(edges, axis=0, return_inverse=True)
    grid = np.stack(np.unravel_index(np.arange(field.size), field.shape), axis=1)
    flat = field.reshape(-1)
    fa, fb = flat[unique[:, 0]], flat[unique[:, 1]]
    t = np.clip(fa / np.where(fa == fb, 1e-12, fa - fb), 0.0, 1.0)[:, None]
    points = low + cell * (grid[unique[:, 0]] + t * (grid[unique[:, 1]]
                                                     - grid[unique[:, 0]]))
    faces = where.reshape(-1).reshape(-1, 3)
    # Each triangle faces away from the inside corners of the tetrahedron it cut.
    centre = np.concatenate([
        (low + cell * grid[cut].mean(axis=1)) for cut in inner])
    a, b, c = (points[faces[:, i]] for i in range(3))
    normal = np.cross(b - a, c - a)
    backwards = np.sum(normal * ((a + b + c) / 3.0 - centre), axis=1) < 0.0
    faces[backwards] = faces[backwards][:, ::-1]
    area = np.linalg.norm(normal, axis=1)
    return points, faces[area > 1e-14]


def blend(parts: list[dict], radius: float, low: Any, high: Any,
          steps: int = S.STEPS) -> dict:
    """The parts' round union, a fillet of `radius` where they meet, as a mesh.

    `parts` are fields, each a primitive's description, the matrix that places it and
    the material it wears; `low` and `high` the box the parts fill. Faces wear the
    material of the nearest part, gathered into groups.
    """
    radius = float(radius)
    margin = radius + 1e-6
    low = np.asarray(low, dtype=float) - margin
    high = np.asarray(high, dtype=float) + margin
    cell = float(np.max(high - low)) / max(4, 2 * int(steps))
    counts = np.maximum(np.ceil((high - low) / cell).astype(int) + 1, 2)
    # One cell beyond the box all round, so the surface never meets the grid's edge.
    low = low - cell
    counts = counts + 2
    axes = [low[i] + cell * np.arange(counts[i]) for i in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    fields = [_field_of(part, grid) for part in parts]
    joined = fields[0]
    for one in fields[1:]:
        joined = round_union(joined, one, radius)
    points, faces = _surface(joined.reshape(tuple(counts)), low, cell)
    if not len(faces):
        raise PolyweaveError(
            "geom.bad-solid",
            "the blend came out empty: no part's surface crossed the grid",
            "give it parts with some size, or raise steps",
        )
    middle = points[faces].mean(axis=1)
    nearest = np.argmin([np.abs(_field_of(part, middle)) for part in parts], axis=0)
    worn = [part.get("material") for part in parts]
    order = np.argsort([str(worn[i]) for i in nearest], kind="stable")
    faces, nearest = faces[order], nearest[order]
    made = S.mesh(points, [tuple(int(v) for v in face) for face in faces])
    groups, start = [], 0
    for at in range(1, len(nearest) + 1):
        if at == len(nearest) or worn[nearest[at]] != worn[nearest[start]]:
            if worn[nearest[start]]:
                groups.append({"material": worn[nearest[start]], "faces": [start, at]})
            start = at
    if groups:
        made["groups"] = groups
    return made
