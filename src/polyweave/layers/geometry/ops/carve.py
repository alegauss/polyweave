"""The `carve` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import solver
from . import _shared as H

NAME = "carve"

#: What it reads beyond the fields every node has.
FIELDS = ("into", "cutter", "bevel", "segments", "profile")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    return solver.build(
        built[node["into"]],
        cutter=built[node["cutter"]],
        bevel_by=float(instance.get("bevel", 0.0)),
        **H._beveled(node, instance),
    )


def bounds(model, node, instance):
    return model.bounds(node["into"])


def inside(model, node, instance, points):
    into = model.inside(node["into"], points)
    cut = model.inside(node["cutter"], points).inside
    return into.only(into.inside & ~cut)


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = (
        f"{takes[0]} with {takes[1]} cut out of it" if len(takes) > 1 else "a cut"
    )
    return what, rest
