"""The `mirror` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from .. import refers_to
from .. import review as R
from .. import solid as S
from .. import voxels as V
from . import _shared as H

NAME = "mirror"

#: What it reads beyond the fields every node has.
FIELDS = (*H.TAKES, "axis", "plane")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    return S.mirror(
        built[refers_to(node)[0]],
        S.axis(node.get("axis", "x")),
        float(instance.get("plane", 0.0)),
    )


def bounds(model, node, instance):
    low, high = model.bounds(refers_to(node)[0])
    along, plane = V._mirrored(node, instance)
    flipped_low, flipped_high = low.copy(), high.copy()
    flipped_low[along] = 2 * plane - high[along]
    flipped_high[along] = 2 * plane - low[along]
    return np.minimum(low, flipped_low), np.maximum(high, flipped_high)


def inside(model, node, instance, points):
    # A point is in the mirror where it or its reflection is in the half, so a
    # column on the plane is one set of cells and never counted twice.
    source = refers_to(node)[0]
    along, plane = V._mirrored(node, instance)
    reflected = points.copy()
    reflected[:, along] = 2 * plane - reflected[:, along]
    return V._merge(model.inside(source, points), model.inside(source, reflected))


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    letter = str(node.get("axis", "x")).lower()
    plane = R._number(instance.get("plane", 0))
    what = f"{takes[0] if takes else 'nothing'} mirrored across {letter} = {plane}"
    rest = R._fields(instance, (*skip, "plane"))
    return what, rest
