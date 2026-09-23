"""What must be true of a mesh before the operation that made it returns.

The evidence is §PW2: Blender's EXACT boolean returns an empty mesh when the object it
cuts has been bevelled — 2402 faces for one cut, 0 for the same cut after a bevel — and
raises nothing at all. The face count is the whole test, and it costs nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from ..errors import PolyweaveError

ACCEPTS_MESH = frozenset({"min_faces"})
ACCEPTS_BOOLEAN = frozenset({"operands", "min_faces"})


def as_mesh(subject: Any) -> tuple[np.ndarray, list[Sequence[int]]]:
    """Read vertices and faces off whatever shape the caller had them in."""
    if hasattr(subject, "vertices") and hasattr(subject, "faces"):
        vertices, faces = subject.vertices, subject.faces
    elif isinstance(subject, dict) and "vertices" in subject and "faces" in subject:
        vertices, faces = subject["vertices"], subject["faces"]
    elif isinstance(subject, tuple) and len(subject) == 2:
        vertices, faces = subject
    else:
        raise PolyweaveError(
            "post.not-a-mesh",
            f"a {type(subject).__name__} carries no vertices and faces",
            "pass a mesh, a {'vertices': …, 'faces': …} mapping, or a pair of the two",
        )
    if len(vertices):
        array = np.asarray(vertices, dtype=float).reshape(-1, 3)
    else:
        array = np.zeros((0, 3), dtype=float)
    return array, list(faces)


def check_mesh(subject: Any, *, min_faces: int = 1) -> dict:
    """At least one face, finite bounds, no NaN in any vertex."""
    vertices, faces = as_mesh(subject)
    if len(faces) < min_faces:
        raise PolyweaveError(
            "post.mesh-empty",
            f"the mesh has {len(faces)} faces, and {min_faces} was the minimum",
            "the operation produced nothing; check its inputs before rendering it",
        )
    if np.isnan(vertices).any():
        bad = int(np.isnan(vertices).any(axis=1).sum())
        raise PolyweaveError(
            "post.mesh-nan",
            f"{bad} of {len(vertices)} vertices carry NaN coordinates",
            "a degenerate transform or a zero-length normal made them; check the last "
            "modifier applied",
        )
    if len(vertices) and not np.isfinite(vertices).all():
        raise PolyweaveError(
            "post.mesh-unbounded",
            "the mesh has vertices at infinity, so it has no bounds to fit or frame",
            "a division by a zero scale is the usual cause; check the scale of every "
            "operand",
        )
    lo = vertices.min(axis=0).tolist() if len(vertices) else [0.0, 0.0, 0.0]
    hi = vertices.max(axis=0).tolist() if len(vertices) else [0.0, 0.0, 0.0]
    measured = {"faces": len(faces), "vertices": len(vertices), "bounds": [lo, hi]}
    uv = subject.get("uv") if isinstance(subject, dict) else None
    if uv is not None:
        measured["uv"] = _check_uv(uv, len(vertices))
    return measured


def _check_uv(uv: Any, vertices: int) -> int:
    """One texture coordinate per vertex, and every one of them a number (§PW68).

    A mesh may carry no coordinates at all, and most do. What it may not carry is a set
    that does not line up with its own vertices: a picture placed by an array one short
    is on the wrong part of the shape after that vertex, and nothing about the render
    says so.
    """
    array = np.asarray(uv, dtype=float)
    if array.ndim != 2 or array.shape[1] != 2 or len(array) != vertices:
        raise PolyweaveError(
            "post.uv-mismatched",
            f"the mesh has {vertices} vertices and {array.shape} texture coordinates",
            "give one pair per vertex, in the same order, or leave them off; an array "
            "that does not line up puts the picture on the wrong part of the shape",
        )
    if not np.isfinite(array).all():
        raise PolyweaveError(
            "post.uv-mismatched",
            "some texture coordinates are not numbers",
            "a zero-extent projection is the usual cause; check what the coordinates "
            "were normalised over",
        )
    return len(array)


def check_boolean(subject: Any, *, operands: Sequence[Any], min_faces: int = 1) -> dict:
    """A face count that is not zero where both operands had faces.

    Stated apart from `mesh` because the diagnosis differs: an empty boolean is not a
    broken mesh, it is two shapes that did not meet the way the caller thought.
    """
    counts = [len(as_mesh(o)[1]) if not isinstance(o, int) else o for o in operands]
    if len(counts) != 2:
        raise PolyweaveError(
            "post.bad-operands",
            f"a boolean has two operands, and {len(counts)} were named",
            "pass operands as the two meshes, or as their two face counts",
        )
    try:
        measured = check_mesh(subject, min_faces=min_faces)
    except PolyweaveError as exc:
        if exc.code != "post.mesh-empty" or not all(c > 0 for c in counts):
            raise
        raise PolyweaveError(
            "post.boolean-empty",
            f"the boolean returned no faces from operands of {counts[0]} "
            f"and {counts[1]}",
            "Blender's EXACT solver empties a cut whose target was bevelled: bevel "
            "after the boolean, or switch the solver to FAST",
        ) from exc
    measured["operands"] = counts
    return measured


def check_manifold(subject: Any) -> dict:
    """Every edge shared by exactly two faces.

    Opt-in, because it walks every edge of every face: on a dense mesh it costs more
    than the operation that produced it, which is the line §2 draws between a cheap
    assertion and an expensive one.
    """
    _, faces = as_mesh(subject)
    seen: dict[tuple[int, int], int] = {}
    for face in faces:
        for a, b in zip(face, list(face[1:]) + [face[0]], strict=True):
            edge = (a, b) if a <= b else (b, a)
            seen[edge] = seen.get(edge, 0) + 1
    loose = sum(1 for n in seen.values() if n != 2)
    if loose:
        raise PolyweaveError(
            "post.mesh-non-manifold",
            f"{loose} of {len(seen)} edges are not shared by exactly two faces",
            "close the holes, or drop `manifold` from the checks this operation runs",
        )
    return {"edges": len(seen), "manifold": True}
