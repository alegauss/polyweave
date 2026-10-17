"""The `crowned` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import review as R
from .. import solid as S
from . import _shared as H

NAME = "crowned"

#: What it reads beyond the fields every node has.
FIELDS = ("outline", "depth", "crown", "front", "steps")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = True


def build(node, instance, built, root):
    return S.crowned(
        H._outline(instance, root),
        float(instance["depth"]),
        float(instance["crown"]),
        **H._rest(instance, "crown"),
    )


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"{R._outline_words(instance.get('outline'))}, extruded with a domed face"
    return what, rest
