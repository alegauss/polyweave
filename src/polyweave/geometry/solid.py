"""The 3D operations a declaration composes, read off the scripts that exist.

The evidence is §PW31, and the list is not a survey of what a modelling package offers
— it is what Cottony's own models are actually made of: a prism, a rounded plate, a
crowned plate, an annulus, a boolean carve, a bevel, and a primitive for the cheap rung.

**Extrusion is first-class.** `prism` over a traced outline is how a star's silhouette
becomes a mesh that is not merely similar to the drawn sprite but is the drawn sprite,
extruded — which is the whole reason the outline half exists.

Two things the scripts learned the expensive way and this keeps:

- **A concave cap has to be triangulated.** Cottony's first star came back with black
  triangles laid across its arms, which is a cap filled as though its points were a
  convex hull. `convex` on the outline decides it, so a rounded rectangle keeps its
  single n-gon cap and a star does not.
- **A boolean against a bevelled object comes back empty**, with no error: 2402 faces
  for one cut and 0 for the same cut after a bevel. So **the boolean runs before the
  bevel** wherever a node asks for both, and the result is asserted non-empty.

A mesh here is the same `{"vertices": …, "faces": …}` the rest of the plugin passes
around, built in numpy, and it carries `uv` where something worked the coordinates out
(§PW68). Nothing in this module needs Blender.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..errors import PolyweaveError
from . import outline as O

#: How many segments a primitive gets around, when nothing says otherwise.
STEPS = 32


def mesh(vertices: Any, faces: Any, uv: Any = None) -> dict:
    """The currency everything here passes around, with its texture coordinates.

    `uv` is one pair per vertex and is **absent unless something computed it** (§PW68),
    by the same rule that keeps a normalisation free of a seed: a mesh carrying zeros
    for coordinates nobody worked out claims to have them.
    """
    made = {
        "vertices": np.asarray(vertices, dtype=float).reshape(-1, 3),
        "faces": list(faces),
    }
    if uv is not None:
        made["uv"] = np.asarray(uv, dtype=float).reshape(-1, 2)
    return made


def planar_uv(points: Any, rect: Any = None) -> np.ndarray:
    """A texture coordinate per vertex, read off where it sits in XY.

    The projection a drawn panel wants: the picture that gave the shape its outline lies
    on the shape in the plane it was drawn in, so u and v are just x and y normalised
    over the extent. `rect` states that extent as `[x, y, width, height]` where the
    drawing's own frame is bigger than the shape it holds; otherwise the shape's own
    bounds are it, and the outline touches 0 and 1 on each axis.

    Not for a prism's walls. A plane projected onto a face perpendicular to it smears,
    which is why this is applied where the surface faces the drawing and not everywhere.
    """
    made = np.asarray(points, dtype=float).reshape(-1, 3)[:, :2]
    if rect is None:
        low, high = made.min(axis=0), made.max(axis=0)
        span = np.where(high - low > 1e-12, high - low, 1.0)
    else:
        x, y, wide, tall = (float(v) for v in rect)
        low = np.array([x, y])
        span = np.array([wide or 1.0, tall or 1.0])
    return (made - low) / span


def _fan(count: int, start: int = 0) -> list[tuple[int, ...]]:
    """One cap as a single n-gon, which is right for a convex ring."""
    return [tuple(range(start, start + count))]


def _triangulated(ring: np.ndarray, start: int, flip: bool) -> list[tuple[int, ...]]:
    """One cap as triangles, by ear clipping — what a concave ring needs.

    Cottony's star is why: a concave cap filled as one n-gon comes back with triangles
    laid across the arms, because the tessellator fills the convex hull of its points.
    """
    order = list(range(len(ring)))
    if _signed(ring) < 0:
        order.reverse()
    out: list[tuple[int, ...]] = []
    guard = len(order) * len(order)
    while len(order) > 3 and guard > 0:
        guard -= 1
        for index in range(len(order)):
            ear = [order[index - 1], order[index], order[(index + 1) % len(order)]]
            if _is_ear(ring, order, ear):
                out.append(tuple(start + one for one in ear))
                order.pop(index)
                break
        else:  # pragma: no cover - a ring with no ear is self-intersecting
            break
    out.append(tuple(start + one for one in order[:3]))
    return [one[::-1] if flip else one for one in out]


def _signed(ring: np.ndarray) -> float:
    return float(
        np.sum(
            ring[:, 0] * np.roll(ring[:, 1], -1) - np.roll(ring[:, 0], -1) * ring[:, 1]
        )
        / 2.0
    )


def _is_ear(ring: np.ndarray, order: list[int], ear: list[int]) -> bool:
    a, b, c = ring[ear[0]], ring[ear[1]], ring[ear[2]]
    if O.cross(b - a, c - a) <= 1e-12:
        return False  # a reflex corner is not an ear
    inside = [one for one in order if one not in ear]
    if not inside:
        return True
    points = ring[inside]
    return not np.any(_within(points, a, b, c))


def _within(points: np.ndarray, a, b, c) -> np.ndarray:
    def side(p, q, r):
        return (q[0] - p[0]) * (r[:, 1] - p[1]) - (q[1] - p[1]) * (r[:, 0] - p[0])

    one, two, three = side(a, b, points), side(b, c, points), side(c, a, points)
    return ((one > 0) & (two > 0) & (three > 0)) | ((one < 0) & (two < 0) & (three < 0))


def _caps(ring: np.ndarray, back: int, count: int) -> list[tuple[int, ...]]:
    if O.convex(ring):
        return [_fan(count)[0][::-1], _fan(count, back)[0]]
    return _triangulated(ring, 0, True) + _triangulated(ring, back, False)


# -- the solids ------------------------------------------------------------------------


def prism(points: Any, depth: float, *, front: float = 0.0) -> dict:
    """One closed outline swept back by `depth`. The operation everything else is.

    The cap is one n-gon where the outline is convex and triangles where it is not,
    which is the star's lesson kept.
    """
    ring = O._ring(points)
    count = len(ring)
    near = np.column_stack([ring, np.full(count, float(front))])
    far = np.column_stack([ring, np.full(count, float(front) + float(depth))])
    sides = [
        (i, (i + 1) % count, count + (i + 1) % count, count + i) for i in range(count)
    ]
    return mesh(np.vstack([near, far]), sides + _caps(ring, count, count))


def plate(rect: Any, depth: float, corner: float = 0.0, *, front: float = 0.0) -> dict:
    """A rounded plate: the shape most of a built model is made of.

    `rect` is `[x, y, width, height]`, as the declaration writes it, so a plate is
    stated where it sits rather than centred and then moved.
    """
    x, y, wide, tall = (float(v) for v in rect)
    ring = O.rounded_square((wide, tall), corner)
    return prism(ring + np.array([x + wide / 2, y + tall / 2]), depth, front=front)


def crowned(
    points: Any, depth: float, crown: float, *, front: float = 0.0, steps: int = 6
) -> dict:
    """A plate with a domed face: a plate whose far cap is pushed out in rings.

    The dome is made by shrinking the outline inward in steps and lifting each ring, so
    the silhouette of the plate is untouched and only the face swells.

    **How a ring shrinks depends on whether the outline is concave** (§PW66), which is
    the same question and the same answer as the cap above: `offset` moves each corner
    along its miter, which points inward at a convex corner and *outward* at a reflex
    one. Cottony's star came back reaching 82 units past its own silhouette that way —
    the op promising the silhouette is untouched, breaking it on the one outline whose
    whole point is being concave. A concave ring is scaled toward its centroid instead,
    which nests by construction whatever the corners do. A convex one keeps the miter,
    because that holds a corner radius constant as it shrinks where a scale would not,
    and because nothing that works today should move.
    """
    ring = O._ring(points)
    count = len(ring)
    rings = [np.column_stack([ring, np.full(count, float(front))])]
    reach = float(np.ptp(ring, axis=0).max()) / 2.0
    convex = O.convex(ring)
    middle = ring.mean(axis=0)

    for step in range(int(steps) + 1):
        along = step / float(steps)
        inward = reach * (1.0 - math.cos(along * math.pi / 2))
        lift = float(depth) + float(crown) * math.sin(along * math.pi / 2)
        if inward <= 1e-9:
            shrunk = ring
        elif convex:
            shrunk = O.offset(ring, -inward)
        else:
            # Toward the centroid by the same distance the miter would have moved it,
            # as a share of the reach — so the two shrink at the same rate.
            shrunk = middle + (ring - middle) * max(0.0, 1.0 - inward / reach)
        rings.append(np.column_stack([shrunk, np.full(count, float(front) + lift)]))

    faces = []
    for level in range(len(rings) - 1):
        low, high = level * count, (level + 1) * count
        faces += [
            (low + i, low + (i + 1) % count, high + (i + 1) % count, high + i)
            for i in range(count)
        ]
    faces += (
        _triangulated(ring, 0, True) if not O.convex(ring) else [_fan(count)[0][::-1]]
    )
    # The last ring closes on itself at the apex; one cap over it finishes the dome.
    top = (len(rings) - 1) * count
    faces += (
        _triangulated(ring, top, False) if not O.convex(ring) else [_fan(count, top)[0]]
    )
    return mesh(np.vstack(rings), faces)


def annulus(
    outer: Any, inner: Any, depth: float, *, steps: int = STEPS, front: float = 0.0
) -> dict:
    """A ring between two edges, which is a prism whose cap has a hole in it.

    **Two edges, not two radii** (§PW65). A number is the radius of a circle, which is
    what a round ring wants and was all this took; an outline is that outline, which is
    what Cottony's tray rim is — a rounded rectangle with the same rounded rectangle
    offset inward by the piping width inside it. The vocabulary drew both of those rings
    already and had no op that would take them.

    A boolean would give the same silhouette for a solver call, a Blender round trip and
    whatever topology MANIFOLD leaves. This is numpy and predictable.

    **The two edges are walked in step**, so they must have the same number of points.
    That is not a burden in practice and it is the construction: an inner edge is an
    `offset` of the outer one, which keeps its count and its order by definition. Two
    rings generated independently are refused rather than skinned into a twist.
    """
    out, hole = _edge(outer, steps), _edge(inner, steps)
    if len(out) != len(hole):
        raise PolyweaveError(
            "geom.bad-solid",
            f"an annulus has {len(out)} points outside and {len(hole)} inside, and the "
            f"two edges are walked in step",
            "make the inner edge an `offset` of the outer one, which keeps its count; "
            "two rings generated apart do not correspond and would skin into a twist",
        )
    if O.area(hole) >= O.area(out):
        raise PolyweaveError(
            "geom.bad-solid",
            f"an annulus encloses {O.area(out):g} outside and {O.area(hole):g} inside, "
            f"so there is no ring between them",
            "make the inner edge smaller than the outer one; a negative `offset` is "
            "how an outline is brought inward",
        )
    count = len(out)
    levels = [float(front), float(front) + float(depth)]
    points = np.vstack(
        [np.column_stack([r, np.full(count, z)]) for z in levels for r in (out, hole)]
    )
    # Four rings: near-outer, near-inner, far-outer, far-inner.
    a, b, c, d = 0, count, 2 * count, 3 * count
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces += [
            (a + i, a + j, c + j, c + i),  # the outside wall
            (b + j, b + i, d + i, d + j),  # the inside wall
            (a + j, a + i, b + i, b + j),  # the near cap
            (c + i, c + j, d + j, d + i),  # the far cap
        ]
    return mesh(points, faces)


def _edge(stated: Any, steps: int) -> np.ndarray:
    """One edge of a ring: a number is a circle's radius, anything else an outline."""
    if isinstance(stated, int | float):
        return O.circle(float(stated), steps=int(steps))
    return O._ring(stated)


def primitive(kind: str = "cube", size: float = 1.0, *, steps: int = STEPS) -> dict:
    """The cheap shapes the preview rung needs, and nothing more."""
    half = float(size) / 2.0
    if kind == "cube":
        corners = np.array(
            [
                [x, y, z]
                for x in (-half, half)
                for y in (-half, half)
                for z in (-half, half)
            ]
        )
        return mesh(
            corners,
            [
                (0, 1, 3, 2),
                (4, 6, 7, 5),
                (0, 4, 5, 1),
                (2, 3, 7, 6),
                (0, 2, 6, 4),
                (1, 5, 7, 3),
            ],
        )
    if kind == "plane":
        return prism(O.rounded_square(float(size)), 0.0)
    if kind == "cylinder":
        return prism(O.circle(half, steps=steps), float(size), front=-half)
    if kind == "sphere":
        return _sphere(half, steps)
    raise PolyweaveError(
        "geom.unknown-shape",
        f"there is no primitive called {kind!r}",
        "name one of cube, plane, cylinder, sphere",
        given=kind,
        allowed=("cube", "plane", "cylinder", "sphere"),
    )


def _sphere(radius: float, steps: int) -> dict:
    rings = max(3, int(steps) // 2)
    points, faces = [], []
    for row in range(rings + 1):
        polar = math.pi * row / rings
        for column in range(steps):
            around = 2 * math.pi * column / steps
            points.append(
                [
                    radius * math.sin(polar) * math.cos(around),
                    radius * math.cos(polar),
                    radius * math.sin(polar) * math.sin(around),
                ]
            )
    for row in range(rings):
        for column in range(steps):
            a = row * steps + column
            b = row * steps + (column + 1) % steps
            faces.append((a, b, b + steps, a + steps))
    return mesh(points, faces)


def transform(
    subject: Any,
    *,
    at: Any = (0, 0, 0),
    scale: Any = (1, 1, 1),
    rotate: Any = (0, 0, 0),
) -> dict:
    """Scale, then rotate, then place — which is the order a transform means.

    **What the mesh wears comes with it** (§PW88). A transform moves a mesh and never
    reorders it, so the picture on it and the ranges of faces each material covers are
    still where they were. Rebuilding from points and faces alone left Cottony's board
    tray, scaled from pixels into cells, wearing nothing.

    **A mirror keeps its faces pointing out.** A scale with an odd number of negative
    components turns the space inside out, and a face left in its old order then points
    in, which a renderer shades as the back of the surface. Reversing each face undoes
    that and moves no face, so the material ranges still hold.
    """
    from ..post.mesh import as_mesh

    stretch = np.asarray(_triple(scale), dtype=float)
    points, faces = as_mesh(subject)
    points = points * stretch
    points = points @ _turn(rotate).T
    if float(np.prod(stretch)) < 0.0:
        faces = [tuple(reversed(face)) for face in faces]
    worn = subject if isinstance(subject, dict) else {}
    made = mesh(points + np.asarray(_triple(at), dtype=float), faces, worn.get("uv"))
    if worn.get("groups"):
        made["groups"] = [dict(one) for one in worn["groups"]]
    return made


def _triple(value: Any) -> tuple[float, float, float]:
    if np.isscalar(value):
        return (float(value), float(value), float(value))
    stated = [float(v) for v in value]
    return (stated[0], stated[1], stated[2])


def _turn(degrees: Any) -> np.ndarray:
    x, y, z = (math.radians(float(v)) for v in _triple(degrees))
    about_x = np.array(
        [[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]]
    )
    about_y = np.array(
        [[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]]
    )
    about_z = np.array(
        [[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]]
    )
    return about_z @ about_y @ about_x


def union(*subjects: Any) -> dict:
    """Several meshes as one, with each one's faces moved onto its own vertices.

    A join and not a boolean union: the declaration's `union` composes parts that do not
    overlap, and two solids that do overlap are a `carve` away from saying so properly.
    """
    from ..post.mesh import as_mesh

    points, faces, offset = [], [], 0
    coordinates: list = []
    for subject in subjects:
        these, those = as_mesh(subject)
        points.append(these)
        faces += [tuple(i + offset for i in face) for face in those]
        offset += len(these)
        carried = subject.get("uv") if isinstance(subject, dict) else None
        coordinates.append(None if carried is None else np.asarray(carried))
    if not points:
        raise PolyweaveError(
            "geom.bad-solid",
            "a union of nothing is nothing",
            "give it at least one node to join",
        )
    # All of them or none (§PW68). Filling a part that has no coordinates with zeros
    # would claim a corner of the picture for every face of it.
    uv = None if any(one is None for one in coordinates) else np.vstack(coordinates)
    return mesh(np.vstack(points), faces, uv)


#: A mirror's axis, by the letter a document writes or the index it means.
AXES = {"x": 0, "y": 1, "z": 2}


def axis(stated: Any) -> int:
    """Which axis a mirror reflects along, refusing anything that is not one."""
    found = AXES.get(str(stated).lower()) if isinstance(stated, str) else stated
    if found not in (0, 1, 2) or isinstance(found, bool):
        raise PolyweaveError(
            "geom.bad-solid",
            f"a mirror across {stated!r} names no axis",
            "write axis as x, y or z",
        )
    return int(found)


def mirror(subject: Any, along: int, plane: float = 0.0) -> dict:
    """The subject and its reflection across a plane, joined (§PW96).

    The reflection is a scale of -1 on one axis, which `transform` already turns the
    faces of so they keep pointing out, placed so the plane stays where it is. The
    halves are joined rather than booleaned, like a `union`, and what each face wears
    comes with it twice.
    """
    flip, at = [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]
    flip[along], at[along] = -1.0, 2.0 * float(plane)
    reflected = transform(subject, scale=flip, at=at)
    joined = union(subject, reflected)
    worn = subject.get("groups") if isinstance(subject, dict) else None
    if worn:
        half = len(subject["faces"])
        joined["groups"] = [dict(one) for one in worn] + [
            {**one, "faces": [one["faces"][0] + half, one["faces"][1] + half]}
            for one in worn
        ]
    return joined


# -- a drawing given volume -----------------------------------------------------------


def inflate(
    points: Any,
    thickness: float,
    *,
    resolution: int = 24,
    profile: float = 0.5,
) -> dict:
    """A drawn panel with volume, as a stuffed cushion has it.

    The route a panel takes. The **silhouette is kept to the point**: every boundary
    vertex stays exactly where the outline put it, at zero depth, and only the inside
    swells — so a cushion made from a traced drawing still has the drawn outline.

    The swell is a function of how far a point is from the edge, which is what makes it
    look stuffed rather than extruded: `profile` of one is a cone, and a half is the
    rounded fall-off a sewn cushion actually has.
    """
    ring = O._ring(points)
    low, high = ring.min(axis=0), ring.max(axis=0)
    span = float(np.max(high - low))
    if span <= 1e-9:
        raise PolyweaveError(
            "geom.bad-solid",
            "the outline has no width to inflate",
            "give it an outline with some size",
        )

    step = span / max(2, int(resolution))
    xs = np.arange(low[0] + step / 2, high[0], step)
    ys = np.arange(low[1] + step / 2, high[1], step)
    grid = np.array([[x, y] for y in ys for x in xs], dtype=float).reshape(-1, 2)
    if len(grid):
        grid = grid[_inside(ring, grid)]
    if len(grid) < 3:
        raise PolyweaveError(
            "geom.bad-solid",
            f"the outline holds {len(grid)} sample points, which is not an inside",
            "give it an outline with some area, or raise the resolution",
        )

    reach = _to_edge(ring, grid)
    deepest = float(reach.max()) if len(reach) else 0.0
    if deepest <= 1e-9:
        # Nothing is far enough inside to swell, so the panel is a flat sheet.
        return prism(ring, 0.0)

    lift = float(thickness) / 2.0 * (reach / deepest) ** float(profile)
    return _pillow(ring, grid, lift)


#: How many pixels of a drawing one grid cell spans, when nothing says otherwise. Below
#: this the mesh grows faster than the shape improves; above it a soft shoulder steps.
CELL = 8


def stuffed(
    alpha: Any,
    thickness: float,
    *,
    size: float | None = None,
    soften: float = 0.40,
    cell: int = CELL,
    floor: float = 0.02,
) -> dict:
    """A drawing given volume **by its own alpha** rather than by its outline (§PW68).

    The second of `inflate`'s two profiles, and the one a drawn panel needs. `inflate`
    swells an outline by each point's distance from the edge, which knows only where the
    shape stops. This blurs the alpha itself and samples the blur as a height, so
    whatever the drawing has *inside* it shapes the surface too. The two agree on a
    plain blob and differ everywhere else.

    `soften` is the blur radius as a share of the drawing's shorter side, and it is what
    domes the face: Cottony read 0.45 and 0.40 off a render, because at 0.10 and 0.06
    the stuffing only rounded the rim and the cushion read as the flat card it was drawn
    as. The blur is normalised before it is lifted, so `thickness` means the same thing
    here as it does on an outline.

    **A relief and not a pillow.** One lifted surface, because that is what a panel seen
    front-on is and what the script this reads off builds. A cell whose corners are all
    below the floor is dropped, which is the drop shadow's faintest tail: built down to
    it, the panel showed a pale rectangle the size of the canvas.
    """
    mask = np.asarray(alpha, dtype=float)
    if mask.ndim != 2 or min(mask.shape) < 2:
        raise PolyweaveError(
            "geom.bad-solid",
            f"a drawing of {mask.shape} is not a surface to stuff",
            "give it the alpha of a drawing, as a two-dimensional array",
        )
    tall, wide = mask.shape
    body = (mask > 0.5).astype(float)
    rise = _stuffing(body, min(wide, tall) * float(soften))
    if rise.max() <= 1e-9:
        raise PolyweaveError(
            "geom.bad-solid",
            "nothing in the drawing clears the halfway mark, so there is no body",
            "point it at a drawing with a subject in it, not at its shadow alone",
        )
    rise = rise / rise.max() * float(thickness)

    step = max(1, int(cell))
    columns = list(range(0, wide, step)) + [wide - 1]
    rows = list(range(0, tall, step)) + [tall - 1]
    scale = (float(size) / max(wide, tall)) if size else 1.0
    middle = np.array([wide - 1, tall - 1]) / 2.0

    index, points, uv = {}, [], []
    for y in rows:
        for x in columns:
            index[x, y] = len(points)
            # y is flipped and the shape centred, as a traced outline is: an image
            # counts rows downward and §6 counts y upward.
            points.append(
                [
                    (x - middle[0]) * scale,
                    (middle[1] - y) * scale,
                    float(rise[y, x]),
                ]
            )
            uv.append([x / (wide - 1), y / (tall - 1)])

    faces = []
    for down in range(len(rows) - 1):
        for across in range(len(columns) - 1):
            x0, x1 = columns[across], columns[across + 1]
            y0, y1 = rows[down], rows[down + 1]
            corners = ((x0, y0), (x0, y1), (x1, y1), (x1, y0))
            if not any(mask[y, x] > floor for x, y in corners):
                continue
            faces.append(tuple(index[one] for one in corners))
    if not faces:
        raise PolyweaveError(
            "geom.bad-solid",
            f"every cell of the drawing is below the {floor:g} floor",
            "lower the floor, or point it at a drawing with something in it",
        )
    return mesh(points, faces, uv)


def _stuffing(body: np.ndarray, radius: float) -> np.ndarray:
    """The body blurred into stuffing, kept inside the body it came from.

    The power is what stops the dome being a cone: a straight blur falls off linearly
    from the rim and reads as a tent, and the shoulder is where a sewn cushion's is.
    """
    if radius <= 0:
        return body
    from PIL import Image as PILImage
    from PIL import ImageFilter

    picture = PILImage.fromarray((np.clip(body, 0, 1) * 255.0).astype(np.uint8), "L")
    wide = picture.filter(ImageFilter.GaussianBlur(radius))
    blurred = np.asarray(wide, dtype=float) / 255.0
    peak = max(float(blurred.max()), 1e-6)
    return np.clip(blurred / peak, 0.0, 1.0) ** 0.6 * body


def _inside(ring: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Which of these points are inside the ring, by crossing number."""
    out = np.zeros(len(points), dtype=bool)
    for index in range(len(ring)):
        one, two = ring[index], ring[(index + 1) % len(ring)]
        straddles = (one[1] > points[:, 1]) != (two[1] > points[:, 1])
        with np.errstate(divide="ignore", invalid="ignore"):
            at = one[0] + (points[:, 1] - one[1]) / (two[1] - one[1]) * (
                two[0] - one[0]
            )
        out ^= straddles & (at > points[:, 0])
    return out


def _to_edge(ring: np.ndarray, points: np.ndarray) -> np.ndarray:
    """How far each point is from the nearest edge of the ring."""
    if not len(points):
        return np.zeros(0)
    best = np.full(len(points), np.inf)
    for index in range(len(ring)):
        a, b = ring[index], ring[(index + 1) % len(ring)]
        along = b - a
        length = float(along @ along)
        if length <= 1e-12:
            best = np.minimum(best, np.linalg.norm(points - a, axis=1))
            continue
        where = np.clip(((points - a) @ along) / length, 0.0, 1.0)[:, None]
        best = np.minimum(best, np.linalg.norm(points - (a + where * along), axis=1))
    return best


def _pillow(ring: np.ndarray, grid: np.ndarray, lift: np.ndarray) -> dict:
    """The ring at zero depth, with the inside lifted both ways and skinned.

    A fan from each boundary vertex to its nearest inside point would tangle, so the two
    faces are built as triangle fans over the ring and a strip of quads inward, which is
    enough structure for a cushion and keeps every boundary vertex where it was.
    """
    count = len(ring)
    flat = np.column_stack([ring, np.zeros(count)])
    front = np.column_stack([grid, lift])
    back = np.column_stack([grid, -lift])
    points = np.vstack([flat, front, back])
    # A stuffed panel is the drawing given volume, so the drawing lies on it in the
    # plane it was drawn in (§PW68), over the ring's own bounds: the outline touches 0
    # and 1 on each axis.
    low, high = ring.min(axis=0), ring.max(axis=0)
    uv = planar_uv(points, [low[0], low[1], *(high - low)])

    faces = []
    # Each face is a fan from the inside point nearest to each boundary edge.
    nearest = _nearest(grid, ring)
    for index in range(count):
        a, b = index, (index + 1) % count
        one, two = nearest[index], nearest[(index + 1) % count]
        if one == two:
            faces.append((a, b, count + one))
            faces.append((b, a, count + len(grid) + one))
        else:
            faces.append((a, b, count + two, count + one))
            faces.append((b, a, count + len(grid) + one, count + len(grid) + two))
    faces += [
        tuple(count + one for one in face) for face in _triangulated(grid, 0, False)
    ]
    faces += [
        tuple(count + len(grid) + one for one in face)
        for face in _triangulated(grid, 0, True)
    ]
    return mesh(points, faces, uv)


def _nearest(grid: np.ndarray, ring: np.ndarray) -> list[int]:
    """The inside point nearest each boundary vertex, for the skin to reach to."""
    return [int(np.argmin(np.linalg.norm(grid - point, axis=1))) for point in ring]
