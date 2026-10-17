"""The `prism` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from .. import review as R
from .. import solid as S
from ..representations.voxels import model as V
from . import _shared as H

NAME = "prism"

#: What it reads beyond the fields every node has.
FIELDS = ("outline", "depth", "front")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    return S.prism(
        H._outline(instance, root),
        float(instance["depth"]),
        **H._rest(instance, "steps"),
    )


def bounds(model, node, instance):
    op = node["op"]
    ring, near, far = model._slab(op, instance)
    return (
        np.array([*ring.min(axis=0), near]),
        np.array([*ring.max(axis=0), far]),
    )


def inside(model, node, instance, points):
    op = node["op"]
    rank = model.rank[node["id"]]
    ring, near, far = model._slab(op, instance)
    depth = (points[:, 2] >= near - V._EPS) & (points[:, 2] <= far + V._EPS)
    within = np.zeros(len(points), dtype=bool)
    if depth.any():
        # A point on the ring's edge is inside, as one on a primitive's face
        # is: the crossing number alone took a left edge and not a right one,
        # so one box as a plate and as a cube filled different cells (§PW274).
        flat = points[depth, :2]
        within[depth] = S._inside(ring, flat) | (S._to_edge(ring, flat) <= V._EPS)
    return V._Found.of(within, rank)


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"{R._outline_words(instance.get('outline'))}, extruded"
    return what, rest
