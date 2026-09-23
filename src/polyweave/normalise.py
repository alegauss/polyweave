"""Putting a fetched mesh into the project's own frame, once, on arrival.

The evidence is §PW20: Cottony's hammer came back standing upright where the drawing
leans it, and the fix was two angles found by re-rendering until it looked right — a
parameter search spent on something that is not a judgement at all.

Orientation, scale and origin are **mechanical**:

- the **principal axes** of the vertex cloud give a candidate frame;
- the **bounding box** gives the scale;
- the **base of the silhouette** gives the origin, which is §6's own convention.

What the axes cannot settle is which of them is up and which way is forward — a frame is
determined only up to twenty-four signed permutations. That last step is settled against
the reference drawing: each candidate's front outline is rasterised here and the one
that overlaps the drawing most is taken. Rasterised rather than rendered, because
deciding which way round a mesh goes is not worth twenty-four pictures. Where there is
no drawing and no hint, the ambiguity is **reported rather than guessed**, because
guessing is the judgement this plugin does not make.

The transform is applied once and recorded, so the stored mesh sits in the project's
convention and nothing downstream carries a correction angle. A deliberate lean or a
pose is still a parameter — it just starts from a known frame.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import numpy as np

from .errors import PolyweaveError
from .post.mesh import as_mesh

#: How far a mesh may be from three real dimensions before its axes mean nothing.
FLAT = 1e-9

#: The grid a candidate orientation is ranked on. Coarse on purpose: this decides which
#: of twenty-four ways round a mesh goes, not what it will look like.
GRID = 128

#: Samples per pixel of projected area, so a triangle leaves no holes behind it.
DENSITY = 4

#: The most samples one projection splats, whatever the mesh's face count.
CEILING = 2_000_000


def axes(vertices: np.ndarray) -> np.ndarray:
    """The mesh's own three axes, longest first.

    Principal component analysis over the vertex cloud: the direction things vary most
    in is the object's longest dimension, whatever the generator thought.
    """
    points = np.asarray(vertices, dtype=float).reshape(-1, 3)
    if len(points) < 3:
        raise PolyweaveError(
            "mesh.too-few-vertices",
            f"{len(points)} vertices do not determine a frame",
            "normalise a mesh with at least three vertices",
        )
    centred = points - points.mean(axis=0)
    _, spread, directions = np.linalg.svd(centred, full_matrices=False)
    if float(spread[-1]) <= FLAT * max(1.0, float(spread[0])):
        raise PolyweaveError(
            "mesh.degenerate",
            "the mesh is flat or collinear, so its axes fix no orientation",
            "orient it against a reference drawing, or state the rotation",
        )
    frame = np.array(directions)
    if np.linalg.det(frame) < 0:  # keep it a rotation rather than a reflection
        frame[2] = -frame[2]
    return frame


def rotations(frame: np.ndarray) -> list[np.ndarray]:
    """Every way the mesh's own axes could map onto the interface's, as rotations.

    Twenty-four of them — six orderings by three sign choices, halved by keeping the
    determinant positive. A frame from the axes alone is determined only this far, which
    is exactly the ambiguity the reference drawing is for.
    """
    out = []
    for order in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            candidate = np.array(
                [frame[order[i]] * signs[i] for i in range(3)], dtype=float
            )
            if np.linalg.det(candidate) > 0:
                out.append(candidate)
    return out


def bounds_of(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return points.min(axis=0), points.max(axis=0)


def normalise(
    subject: Any,
    *,
    rotation: np.ndarray | None = None,
    height: float | None = 1.0,
) -> dict:
    """Put a mesh in the project's frame: oriented, scaled, sitting on the origin.

    `height` is the size along the up axis in metres, §6's unit. `None` keeps the mesh's
    own size, for an asset that arrives already to scale.
    """
    points, faces = as_mesh(subject)
    if not len(points):
        raise PolyweaveError(
            "mesh.too-few-vertices",
            "the mesh has no vertices to normalise",
            "check that the file imported",
        )
    turned = points if rotation is None else points @ np.asarray(rotation, float).T

    low, high = bounds_of(turned)
    span = high - low
    scale = 1.0
    if height is not None:
        tall = float(span[1])
        if tall <= FLAT:
            raise PolyweaveError(
                "mesh.degenerate",
                "the mesh has no height, so it cannot be scaled to one",
                "pass height=None to keep the size it arrived at",
            )
        scale = float(height) / tall
    scaled = turned * scale

    # §6: the origin is the centre of the footprint, on the ground plane — the base of
    # the silhouette, never the centre of the box. A prop whose origin is its middle is
    # a prop that floats.
    low, high = bounds_of(scaled)
    offset = np.array([(low[0] + high[0]) / 2.0, low[1], (low[2] + high[2]) / 2.0])
    placed = scaled - offset

    low, high = bounds_of(placed)
    return {
        "vertices": placed,
        "faces": faces,
        "scale": round(scale, 9),
        "rotation": (np.eye(3) if rotation is None else np.asarray(rotation, float))
        .round(9)
        .tolist(),
        "offset": (-offset * 1.0).round(9).tolist(),
        "size": (high - low).round(9).tolist(),
        "bounds": [low.round(9).tolist(), high.round(9).tolist()],
    }


def as_matrix(found: dict) -> np.ndarray:
    """The whole normalisation as one 4×4, for a record or a downstream transform."""
    matrix = np.eye(4)
    matrix[:3, :3] = np.array(found["rotation"], dtype=float) * found["scale"]
    matrix[:3, 3] = np.array(found["offset"], dtype=float) * found["scale"]
    return matrix


def footprint(found: dict) -> np.ndarray:
    """Where the mesh meets the ground, which should be the origin and nothing else."""
    low, high = bounds_of(np.asarray(found["vertices"], dtype=float))
    return np.array([(low[0] + high[0]) / 2.0, low[1], (low[2] + high[2]) / 2.0])


def choose(
    subject: Any,
    look: Any,
    *,
    height: float | None = 1.0,
    limit: int | None = None,
) -> dict:
    """Pick the orientation whose front view matches the drawing best.

    `look` scores one normalisation — given the placed vertices and faces it returns how
    well that candidate's front silhouette matches the reference. Everything about
    rendering is on the far side of it, so the maths here is testable on its own.
    """
    points, _ = as_mesh(subject)
    candidates = rotations(axes(points))
    if limit:
        candidates = candidates[: int(limit)]

    best, scored = None, []
    for rotation in candidates:
        placed = normalise(subject, rotation=rotation, height=height)
        score = float(look(placed))
        scored.append(score)
        if best is None or score > best["score"]:
            best = {**placed, "score": score}
    if best is None:  # pragma: no cover - rotations always yields twenty-four
        raise PolyweaveError(
            "mesh.degenerate",
            "no orientation could be formed for this mesh",
            "orient it against a reference drawing, or state the rotation",
        )
    if len({round(s, 6) for s in scored}) == 1:
        raise PolyweaveError(
            "mesh.ambiguous-forward",
            "every orientation matches the reference equally, so which way is forward "
            "is not decidable from it",
            "give a reference that distinguishes the front, or state the rotation; "
            "guessing an orientation is a judgement this does not make",
        )
    best["tried"] = len(scored)
    return best


# -- the outline, rasterised rather than rendered --------------------------------------


def _van_der_corput(index: np.ndarray) -> np.ndarray:
    out = np.zeros(len(index), dtype=float)
    rest, denominator = index.astype(np.int64).copy(), 1.0
    while rest.any():
        denominator *= 2.0
        out += (rest % 2) / denominator
        rest //= 2
    return out


def _barycentric(count: int = 4096) -> np.ndarray:
    """Where inside a triangle it gets sampled — a fixed low-discrepancy set.

    Fixed rather than random, because an orientation that turns on a seed is not an
    answer.
    """
    along = (np.arange(count, dtype=float) + 0.5) / count
    across = _van_der_corput(np.arange(count))
    root = np.sqrt(along)
    return np.stack([1.0 - root, root * (1.0 - across), root * across], axis=1)


_SAMPLES = _barycentric()


def triangles(faces: Any) -> np.ndarray:
    """Every face as triangles, by the fan a convex face makes."""
    out: list[tuple[int, int, int]] = []
    for face in faces:
        corners = list(face)
        out.extend(
            (corners[0], corners[k], corners[k + 1]) for k in range(1, len(corners) - 1)
        )
    return np.array(out, dtype=int) if out else np.zeros((0, 3), dtype=int)


def _splat(mask: np.ndarray, points: np.ndarray) -> None:
    columns = np.clip(points[:, 0].astype(np.int64), 0, mask.shape[1] - 1)
    rows = np.clip(points[:, 1].astype(np.int64), 0, mask.shape[0] - 1)
    mask[rows, columns] = True


def _neighbours(mask: np.ndarray):
    for down in (-1, 0, 1):
        for across in (-1, 0, 1):
            yield np.roll(np.roll(mask, down, axis=0), across, axis=1)


def _closed(mask: np.ndarray) -> np.ndarray:
    """Dilate then erode, so a sampled face has no pinholes left in it.

    The roll wraps at the border, which is harmless: the fit below leaves a pixel of
    margin all the way round, so there is never anything at the edge to wrap.
    """
    grown = mask.copy()
    for shifted in _neighbours(mask):
        grown |= shifted
    out = grown.copy()
    for shifted in _neighbours(grown):
        out &= shifted
    return out


def _fit(low: np.ndarray, high: np.ndarray, grid: int):
    """Map a bounding box onto the grid, keeping its proportions and its centre."""
    span = float(max(high - low))
    if span <= FLAT:
        raise PolyweaveError(
            "mesh.degenerate",
            "the mesh projects to a single point, so it has no outline to compare",
            "orient it against a reference drawing, or state the rotation",
        )
    scale = (grid - 2) / span
    centre = (low + high) / 2.0
    return lambda points: (points - centre) * scale + (grid / 2.0)


def project(subject: Any, *, grid: int = GRID) -> np.ndarray:
    """The front view's silhouette, worked out here rather than rendered.

    Ranking twenty-four ways round with the renderer costs twenty-four pictures. The
    outline is all that ranks them, and the outline is arithmetic.

    §6's azimuth zero puts the camera on +Z looking back along it with +Y up, so the
    mask's columns run with x and its rows against y. It is fitted to its own bounding
    box, exactly as `drawing` fits the reference, so what gets compared is proportion
    and outline and never how either one was framed.
    """
    vertices, faces = as_mesh(subject)
    if not len(vertices):
        raise PolyweaveError(
            "mesh.too-few-vertices",
            "the mesh has no vertices to project",
            "check that the file imported",
        )
    flat = np.stack([vertices[:, 0], -vertices[:, 1]], axis=1)
    to_pixels = _fit(flat.min(axis=0), flat.max(axis=0), grid)
    pixels = to_pixels(flat)

    mask = np.zeros((grid, grid), dtype=bool)
    faced = triangles(faces)
    if len(faced):
        a, b, c = pixels[faced[:, 0]], pixels[faced[:, 1]], pixels[faced[:, 2]]
        area = (
            np.abs(
                (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
            )
            / 2.0
        )
        per = np.clip(np.ceil(area * DENSITY), 1, None).astype(np.int64)
        if int(per.sum()) > CEILING:
            per = np.maximum(1, (per * (CEILING / int(per.sum()))).astype(np.int64))
        which = np.repeat(np.arange(len(faced)), per)
        within = np.arange(int(per.sum())) - np.repeat(np.cumsum(per) - per, per)
        weights = _SAMPLES[within % len(_SAMPLES)]
        _splat(
            mask,
            weights[:, 0:1] * a[which]
            + weights[:, 1:2] * b[which]
            + weights[:, 2:3] * c[which],
        )
    _splat(mask, pixels)  # so a mesh of loose edges still leaves an outline
    return _closed(mask)


def drawing(reference: str | Path, *, grid: int = GRID, alpha_floor: float):
    """The reference's own outline, on the same grid and fitted the same way."""
    from .image import load as load_image

    mask = load_image(reference).subject(alpha_floor)
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    if not rows.size or not columns.size:
        raise PolyweaveError(
            "fetch.no-reference",
            f"every pixel of {reference} is background, so it draws no shape",
            "point it at the drawing that asked for this shape",
        )
    box = mask[rows[0] : rows[-1] + 1, columns[0] : columns[-1] + 1]
    tall, wide = box.shape
    span, inner = max(tall, wide), grid - 2
    height = max(1, round(tall / span * inner))
    width = max(1, round(wide / span * inner))
    down = ((np.arange(height) + 0.5) * tall / height).astype(int).clip(0, tall - 1)
    across = ((np.arange(width) + 0.5) * wide / width).astype(int).clip(0, wide - 1)

    out = np.zeros((grid, grid), dtype=bool)
    top, left = (grid - height) // 2, (grid - width) // 2
    out[top : top + height, left : left + width] = box[down][:, across]
    return out


def overlap(one: np.ndarray, other: np.ndarray) -> float:
    """Intersection over union, the same measure a shape check is held to."""
    union = int(np.count_nonzero(one | other))
    return round(float(np.count_nonzero(one & other) / union), 6) if union else 0.0


def orient(
    subject: Any,
    *,
    against: str | Path,
    height: float | None = 1.0,
    grid: int = GRID,
    alpha_floor: float,
) -> dict:
    """Normalise a mesh the way the drawing says it stands.

    §PW20's hammer: the drawing already knew which way was forward, and the two angles
    found by re-rendering were a parameter search spent on something that was never a
    judgement in the first place.
    """
    wanted = drawing(against, grid=grid, alpha_floor=alpha_floor)
    found = choose(
        subject,
        lambda placed: overlap(project(placed, grid=grid), wanted),
        height=height,
    )
    found["against"] = str(against)
    found["silhouette_iou"] = found["score"]
    return found


# -- on arrival ------------------------------------------------------------------------


def read_mesh(path: str | Path) -> dict:
    """Vertices and faces of a mesh file, in the interface's own axes."""
    from .render import blender

    blender.reset()  # nothing from an earlier ingest still standing in the scene
    obj = blender.load_mesh(path)
    world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return {
        "vertices": np.array([(v.x, v.z, -v.y) for v in world], dtype=float),
        "faces": [tuple(p.vertices) for p in obj.data.polygons],
    }


def write_mesh(found: dict, out: str | Path, *, materials: dict | None = None) -> Path:
    """Write the mesh out, so nothing downstream carries the correction.

    **Everything the mesh worked out comes with it** (§PW69). This used to write
    vertices and faces alone, which is right for a normalisation and wrong for a build:
    a panel would lose the coordinates that put its drawing on it and a tray would lose
    the groups that keep its rope rim cream. Those were the two things the geometry
    block had just learned to carry, dropped by the one call that could take them out.

    `materials` is the document's own table, name to shader inputs, and it is needed
    because a group names a material and a file needs the material itself.
    """
    from .render import blender

    bpy = blender.require()
    blender.reset()
    where = Path(out)
    where.parent.mkdir(parents=True, exist_ok=True)
    mesh = bpy.data.meshes.new("polyweave-normalised")
    mesh.from_pydata(
        [blender.to_blender(p) for p in np.asarray(found["vertices"], dtype=float)],
        [],
        [list(face) for face in found["faces"]],
    )
    mesh.update()
    _write_uv(mesh, found.get("uv"))
    obj = bpy.data.objects.new("normalised", mesh)
    bpy.context.scene.collection.objects.link(obj)
    if found.get("groups"):
        blender.apply_material(
            obj,
            {
                name: blender.as_inputs(one or {})
                for name, one in (materials or {}).items()
            },
            groups=found["groups"],
        )
    for other in bpy.context.scene.objects:
        other.select_set(other is obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(where),
        use_selection=True,
        export_format="GLB" if where.suffix.lower() == ".glb" else "GLTF_SEPARATE",
    )
    return where


def _write_uv(mesh: Any, uv: Any) -> None:
    """The per-vertex coordinates onto the per-loop layer a file actually stores.

    A mesh states one pair per vertex, because that is what a build computes and what
    the arithmetic is over. Blender and glTF store one per face corner, so every corner
    takes its own vertex's pair on the way out.
    """
    if uv is None:
        return
    pairs = np.asarray(uv, dtype=float).reshape(-1, 2)
    layer = mesh.uv_layers.new(name="polyweave")
    for loop in mesh.loops:
        layer.data[loop.index].uv = tuple(pairs[loop.vertex_index])


def ingest(
    path: str | Path,
    *,
    out: str | Path | None = None,
    against: str | Path | None = None,
    rotation: np.ndarray | None = None,
    height: float | None = 1.0,
    alpha_floor: float | None = None,
    root: str | Path = ".",
) -> dict:
    """Put an arriving mesh in the project's frame, once, and write it there.

    `against` is the drawing that asked for the shape and settles which way is forward.
    Without one the mesh keeps the way round it arrived, unless `rotation` states it —
    what never happens is a guess.

    This is the operation, so it is where the tolerance is resolved; `orient` and
    `drawing` below it take the number and default nothing (§PW40).
    """
    from .config import load as load_config

    source = Path(path)
    arrived = read_mesh(source)
    bars: dict = {}
    if against is not None:
        # All six together, so the record can carry what was in force rather than what
        # the file holds when it is read back (§PW51). The floor actually used is the
        # explicit argument where there is one, so the record says what decided the
        # mask and not what the project would decide today.
        settings = load_config(root)
        floor = float(settings.get("tolerance.alpha_floor", alpha_floor))
        bars = {**settings.tolerances().as_dict(), "alpha_floor": floor}
        found = orient(arrived, against=against, height=height, alpha_floor=floor)
    else:
        # No drawing, so nothing here was measured against a bar, and a record carrying
        # six numbers it did not use would claim it had.
        found = normalise(arrived, rotation=rotation, height=height)

    written = write_mesh(
        found, out or source.with_name(f"{source.stem}.normalised.glb")
    )
    record = {
        "source": str(source),
        "mesh": str(written),
        "scale": found["scale"],
        "rotation": found["rotation"],
        "offset": found["offset"],
        "size": found["size"],
        "matrix": as_matrix(found).round(9).tolist(),
        "vertices": len(found["vertices"]),
        "faces": len(found["faces"]),
    }
    for key in ("against", "silhouette_iou", "tried"):
        if key in found:
            record[key] = found[key]
    record["provenance"] = str(_record_derivation(record, found, root, bars))
    return record


def _record_derivation(
    record: dict, found: dict, root: str | Path, tolerances: dict | None = None
) -> Path:
    """Write the sidecar that says what this mesh was derived from (§PW46).

    The ledger holds the bytes that arrived and their digest, which stays true, but the
    file the rest of the project loads is this one — and to `verify` that was a file
    nothing recorded, which is the shape of the problem §PW17 exists to prevent arriving
    from the other direction.

    The parent is named **by hash and by path**, and the hash is what matters: a mesh
    that moved is the same parent and one that changed is not. That is also what settles
    the same mesh normalised twice against two drawings — two records naming one parent
    is a fact, where two files and no records is a question nobody can answer later.

    Everything in `params` is what the normalisation already computed, so the chain from
    the credits spent to the mesh in the scene is one a person can follow without
    guessing which file came first.

    `tolerances` is what the silhouette IoU beside it was taken against (§PW51), and it
    is empty where no drawing was given — a normalisation with no reference measured
    nothing against a bar, and six numbers it never read would claim otherwise.
    """
    from . import provenance

    parent = provenance.source("mesh", record["source"], root=root)
    written = provenance.build(
        "mesh",
        record["mesh"],
        inputs=[parent],
        params={
            "scale": record["scale"],
            "rotation": record["rotation"],
            "offset": record["offset"],
            "matrix": record["matrix"],
            **{k: found[k] for k in ("against", "tried") if k in found},
        },
        measurements={
            "size": record["size"],
            "vertices": record["vertices"],
            "faces": record["faces"],
            **{k: found[k] for k in ("silhouette_iou",) if k in found},
        },
        tolerances=tolerances,
        root=root,
    )
    return provenance.write(written, root=root)
