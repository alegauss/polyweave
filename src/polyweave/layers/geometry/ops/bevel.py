"""The `bevel` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import refers_to, solver
from . import _shared as H

NAME = "bevel"

#: What it reads beyond the fields every node has.
FIELDS = (*H.TAKES, "bevel", "segments", "profile")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    return solver.build(
        built[refers_to(node)[0]],
        bevel_by=float(instance.get("bevel", 0.0)),
        **H._beveled(node, instance),
    )


def bounds(model, node, instance):
    return model.bounds(refers_to(node)[0])


def inside(model, node, instance, points):
    return model.inside(refers_to(node)[0], points)


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"{takes[0]}, with its edges softened" if takes else "a bevel"
    return what, rest
