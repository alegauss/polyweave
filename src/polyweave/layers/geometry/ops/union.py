"""The `union` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from .. import refers_to
from .. import solid as S
from ..representations.voxels import model as V
from . import _shared as H

NAME = "union"

#: What it reads beyond the fields every node has.
FIELDS = H.TAKES

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    return S.union(*(built[one] for one in refers_to(node)))


def bounds(model, node, instance):
    boxes = [model.bounds(one) for one in refers_to(node)]
    return (
        np.min([low for low, _ in boxes], axis=0),
        np.max([high for _, high in boxes], axis=0),
    )


def inside(model, node, instance, points):
    found = None
    for one in refers_to(node):
        part = model.inside(one, points)
        found = part if found is None else V._merge(found, part)
    return found


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"{' and '.join(takes)} joined" if takes else "a join"
    return what, rest
