"""The 2D shapes a solid is made from, including the ones already drawn.

The evidence is §PW31: a format covering only cubes and spheres would leave every real
asset in code, so the vocabulary is read off what the existing scripts actually do. The
outline half of that is a circle, a rounded square, a star, a lobed shape, a radial
array about a centre, and an outline grown or shrunk by a distance.

**And an outline traced from a drawing, which is the interesting one.** It is how a
star's silhouette becomes a mesh that is not merely *similar* to the drawn sprite but
**is** the drawn sprite, extruded — so tracing is a first-class operation here rather
than an escape into code.

An outline is a closed ring of points in **XY**, with no repeated last point, and a
solid extrudes it along **Z**. That is the plane the camera faces at azimuth zero, which
is what a sprite-baked asset wants: the drawn shape stays the drawn shape, and the depth
goes away from the viewer.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from ..errors import PolyweaveError

#: How many segments a full circle gets when nothing says otherwise.
STEPS = 64

#: How far a traced point may sit from the line it is dropped from, in pixels. A drawing
#: traced at one point per pixel is a thousand-point outline of a shape with eight
#: corners.
TOLERANCE = 1.0

#: How far a miter may stretch at a sharp corner before it is clamped. A spike's miter
#: goes to infinity, and an outline is not improved by a point a mile away.
SHARPEST = 8.0

#: The eight neighbours a boundary trace walks, clockwise from due east.
AROUND = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))


def _ring(points: Any) -> np.ndarray:
    out = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(out) < 3:
        raise PolyweaveError(
            "geom.bad-outline",
            f"an outline of {len(out)} points is not a shape",
            "give it at least three points",
        )
    # A ring that repeats its first point as its last is a ring stated twice at one
    # vertex, and every operation below would count that vertex twice.
    if len(out) > 3 and np.allclose(out[0], out[-1]):
        out = out[:-1]
    return out


# -- the generators --------------------------------------------------------------------


def circle(radius: float, *, steps: int = STEPS) -> np.ndarray:
    angles = np.linspace(0.0, 2 * math.pi, int(steps), endpoint=False)
    return np.stack([np.cos(angles), np.sin(angles)], axis=1) * float(radius)


def rounded_square(size: Any, corner: float = 0.0, *, steps: int = 8) -> np.ndarray:
    """A rectangle with its corners turned, which most of a built model is made of."""
    wide, tall = (
        (float(size), float(size))
        if np.isscalar(size)
        else (
            float(size[0]),
            float(size[1] if len(size) > 1 else size[0]),
        )
    )
    radius = min(float(corner), wide / 2, tall / 2)
    x, y = wide / 2, tall / 2
    if radius <= 0:
        return np.array([[-x, -y], [x, -y], [x, y], [-x, y]])

    centres = [
        (x - radius, y - radius),
        (-x + radius, y - radius),
        (-x + radius, -y + radius),
        (x - radius, -y + radius),
    ]
    out = []
    for quarter, (cx, cy) in enumerate(centres):
        start = quarter * math.pi / 2
        for angle in np.linspace(start, start + math.pi / 2, int(steps) + 1):
            out.append([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
    return _ring(out)


def star(
    points: int, outer: float, inner: float, *, rotation: float = 0.0
) -> np.ndarray:
    """Alternating radii: the shape whose cap Blender's tessellator gets wrong.

    Cottony's first star came back with black triangles across its arms, which is a
    concave cap filled as though its points were a convex hull. That is the solid's
    problem to solve, and this is why it knows it has one.
    """
    if int(points) < 2:
        raise PolyweaveError(
            "geom.bad-outline",
            f"a star of {points} points is not a star",
            "give it at least two points",
        )
    turn = math.radians(float(rotation))
    out = []
    for index in range(int(points) * 2):
        angle = turn + index * math.pi / int(points)
        radius = float(outer) if index % 2 == 0 else float(inner)
        out.append([radius * math.cos(angle), radius * math.sin(angle)])
    return _ring(out)


def lobed(lobes: int, radius: float, depth: float, *, steps: int = STEPS) -> np.ndarray:
    """A circle with a wave around it — a flower, a cloud, a scalloped edge."""
    angles = np.linspace(0.0, 2 * math.pi, int(steps), endpoint=False)
    radii = float(radius) + float(depth) * np.cos(int(lobes) * angles)
    return np.stack([np.cos(angles) * radii, np.sin(angles) * radii], axis=1)


def radial(points: Any, about: Any = (0.0, 0.0), *, steps: int = 6) -> np.ndarray:
    """One set of points arrayed about a centre, `steps` of them.

    Cottony's own operation. The points are given once and turned, so a shape with six
    identical petals is stated as one petal.
    """
    ring = _ring(points) - np.asarray(about, dtype=float)
    out = []
    for step in range(int(steps)):
        angle = 2 * math.pi * step / int(steps)
        turn = np.array(
            [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
        )
        out.append(ring @ turn.T)
    return np.vstack(out) + np.asarray(about, dtype=float)


def offset(points: Any, distance: float) -> np.ndarray:
    """An outline grown or shrunk, by moving each point along its own corner.

    Each vertex moves along the **miter** of its two edges, not merely along the
    bisector: a square grown by one has to move each corner by the diagonal, and a unit
    step along the bisector grows a ten-unit square to 11.4 rather than to 12.

    It is **not** a clipping offset. Shrink a shape past its own width and the edges
    cross rather than the shape disappearing, and nothing here repairs that. A corner
    sharper than `SHARPEST` is clamped, because a miter at a spike goes to infinity.
    """
    ring = _ring(points)
    before = _unit(ring - np.roll(ring, 1, axis=0))
    after = _unit(np.roll(ring, -1, axis=0) - ring)
    one = np.stack([before[:, 1], -before[:, 0]], axis=1)
    two = np.stack([after[:, 1], -after[:, 0]], axis=1)
    # The miter: (n1 + n2) / (1 + n1·n2). At a right angle that is a vector of length
    # root two, which is exactly how far a square's corner has to move.
    together = np.clip(
        1.0 + np.sum(one * two, axis=1, keepdims=True), 1.0 / SHARPEST, None
    )
    return ring + (one + two) / together * float(distance)


def cross(one: np.ndarray, two: np.ndarray) -> np.ndarray:
    """The 2D cross product, written out.

    `np.cross` deprecated two-dimensional vectors in NumPy 2, and every turn test here
    is two-dimensional.
    """
    return one[..., 0] * two[..., 1] - one[..., 1] * two[..., 0]


def _unit(vectors: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(vectors, axis=1, keepdims=True)
    return np.divide(vectors, length, out=np.zeros_like(vectors), where=length > 1e-12)


GENERATORS = {
    "circle": circle,
    "rounded_square": rounded_square,
    "star": star,
    "lobed": lobed,
}


def generate(named: str, **how: Any) -> np.ndarray:
    """One named generator, by the name a declaration writes."""
    if named not in GENERATORS:
        raise PolyweaveError(
            "geom.unknown-shape",
            f"there is no outline generator called {named!r}",
            f"name one of {', '.join(sorted(GENERATORS))}, or trace an image",
        )
    try:
        return GENERATORS[named](**how)
    except TypeError as exc:
        raise PolyweaveError(
            "geom.unknown-shape",
            f"{named} does not take those arguments: {exc}",
            f"check what {named} takes",
        ) from exc


# -- the one traced from a drawing -----------------------------------------------------


def trace(mask: np.ndarray) -> np.ndarray:
    """The outer boundary of the largest island in a mask, walked once round.

    Moore-neighbour tracing: find the first set pixel, then keep turning about the
    current one until the next boundary pixel appears, until it comes back to where it
    started. Deterministic and exact — every point it returns is a pixel that is really
    on the edge.
    """
    filled = np.asarray(mask, dtype=bool)
    where = np.argwhere(filled)
    if not len(where):
        raise PolyweaveError(
            "geom.nothing-to-trace",
            "every pixel of the drawing is background, so it draws no outline",
            "point it at a drawing with a subject in it",
        )
    start = (int(where[0][1]), int(where[0][0]))  # x, y

    def solid(point):
        x, y = point
        return 0 <= y < filled.shape[0] and 0 <= x < filled.shape[1] and filled[y, x]

    out = [start]
    at, came_from = start, 4  # we arrived at the first pixel from its west
    for _ in range(filled.size * 4):
        for turn in range(8):
            index = (came_from + 1 + turn) % 8
            step = (at[0] + AROUND[index][0], at[1] + AROUND[index][1])
            if solid(step):
                came_from = (index + 4) % 8
                at = step
                break
        else:  # pragma: no cover - a single isolated pixel
            break
        if at == start:
            break
        out.append(at)
    return np.array(out, dtype=float)


def simplify(points: Any, tolerance: float = TOLERANCE) -> np.ndarray:
    """Drop every point that sits within `tolerance` of the line it lies on.

    Ramer-Douglas-Peucker. A drawing traced at one point per pixel is a thousand-point
    outline of a shape with eight corners, and every one of those points becomes
    vertices in the mesh.
    """
    ring = _ring(points)
    kept = _rdp(np.vstack([ring, ring[:1]]), float(tolerance))
    return _ring(kept)


def _rdp(points: np.ndarray, tolerance: float) -> np.ndarray:
    if len(points) < 3:
        return points
    first, last = points[0], points[-1]
    along = last - first
    length = float(np.linalg.norm(along))
    if length <= 1e-12:
        away = np.linalg.norm(points - first, axis=1)
    else:
        away = np.abs(cross(np.broadcast_to(along, points.shape), points - first))
        away = away / length
    worst = int(np.argmax(away))
    if away[worst] <= tolerance:
        return np.vstack([first, last])
    return np.vstack(
        [_rdp(points[: worst + 1], tolerance)[:-1], _rdp(points[worst:], tolerance)]
    )


def image(
    path: str | Path,
    *,
    root: str | Path = ".",
    alpha_floor: float | None = None,
    tolerance: float = TOLERANCE,
    size: float | None = None,
) -> np.ndarray:
    """An outline traced off a drawing's own alpha, in the drawing's own proportions.

    `size` scales the longer side to that many units, which is how a drawn star becomes
    a star of a stated width. Without it the outline is in pixels.

    The y axis is flipped: an image counts rows downward and §6 counts y upward, and an
    outline that came back mirrored is a sprite extruded backwards.

    The floor comes from the project rather than from a default here (§PW40): what
    counts as the drawing and what counts as the paper around it is the same decision
    the rest of the plugin makes, and a second answer to it traces the page.
    """
    from ..config import load as load_config
    from ..image import load as load_image

    where = Path(path)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    floor = float(load_config(root).get("tolerance.alpha_floor", alpha_floor))
    picture = load_image(where)
    ring = simplify(trace(picture.subject(floor)), tolerance)

    ring[:, 1] = picture.height - ring[:, 1]
    ring = ring - ring.mean(axis=0)
    if size:
        span = float(np.ptp(ring, axis=0).max())
        if span > 1e-9:
            ring = ring * (float(size) / span)
    return ring


# -- reading what the document asked for -----------------------------------------------


def resolve(stated: Any, *, root: str | Path = ".") -> np.ndarray:
    """One outline, however the declaration wrote it.

    A mapping naming a `shape` is a generator; one naming an `image` is a drawing; one
    naming `points` is the points themselves. `offset` and `radial` wrap whichever of
    those they were given.
    """
    if isinstance(stated, list | np.ndarray):
        return _ring(stated)
    if not isinstance(stated, dict):
        raise PolyweaveError(
            "geom.bad-outline",
            f"{stated!r} is not an outline",
            "give it a shape, an image, or a list of points",
        )

    how = {
        k: v
        for k, v in stated.items()
        if k not in ("shape", "image", "points", "offset", "radial", "of")
    }
    if "shape" in stated:
        ring = generate(str(stated["shape"]), **how)
    elif "image" in stated:
        ring = image(stated["image"], root=root, **how)
    elif "points" in stated:
        ring = _ring(stated["points"])
    elif "of" in stated:
        ring = resolve(stated["of"], root=root)
    else:
        raise PolyweaveError(
            "geom.bad-outline",
            f"{sorted(stated)} names no outline",
            "give it a shape, an image, points, or an `of` naming another outline",
        )

    if "radial" in stated:
        ring = radial(
            ring, stated.get("about", (0.0, 0.0)), steps=int(stated["radial"])
        )
    if "offset" in stated:
        ring = offset(ring, float(stated["offset"]))
    return ring


def bounds(points: Any) -> tuple[float, float, float, float]:
    """The outline's own rectangle, for a report that says how big a shape came out."""
    ring = _ring(points)
    low, high = ring.min(axis=0), ring.max(axis=0)
    return (float(low[0]), float(low[1]), float(high[0]), float(high[1]))


def area(points: Any) -> float:
    """The shoelace area, positive whichever way round the ring was written."""
    ring = _ring(points)
    return float(
        abs(
            np.sum(
                ring[:, 0] * np.roll(ring[:, 1], -1)
                - np.roll(ring[:, 0], -1) * ring[:, 1]
            )
            / 2.0
        )
    )


def convex(points: Any) -> bool:
    """Whether every corner turns the same way.

    The solid needs to know: a convex cap renders correctly as one n-gon, and Blender's
    tessellator fills a concave one as though its points were a convex hull.
    """
    ring = _ring(points)
    edges = np.roll(ring, -1, axis=0) - ring
    turns = cross(edges, np.roll(edges, -1, axis=0))
    return bool(np.all(turns >= -1e-9) or np.all(turns <= 1e-9))
