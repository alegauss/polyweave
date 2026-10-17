"""The `transform` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from .. import refers_to
from .. import solid as S
from ..representations.voxels import model as V
from . import _shared as H

NAME = "transform"

#: What it reads beyond the fields every node has.
FIELDS = (*H.TAKES, "scale", "rotate")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    return S.transform(
        built[refers_to(node)[0]],
        at=instance.get("at", (0, 0, 0)),
        scale=instance.get("scale", (1, 1, 1)),
        rotate=instance.get("rotate", (0, 0, 0)),
    )


def bounds(model, node, instance):
    low, high = model.bounds(refers_to(node)[0])
    corners = np.array(
        [
            [x, y, z]
            for x in (low[0], high[0])
            for y in (low[1], high[1])
            for z in (low[2], high[2])
        ]
    )
    moved = V._forward(corners, instance)
    return moved.min(axis=0), moved.max(axis=0)


def inside(model, node, instance, points):
    return model.inside(refers_to(node)[0], V._backward(points, instance))


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"{takes[0]}, moved" if takes else "a transform"
    return what, rest
