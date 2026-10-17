"""The `annulus` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import solid as S
from . import _shared as H

NAME = "annulus"

#: What it reads beyond the fields every node has.
FIELDS = ("outer", "inner", "depth", "front", "steps")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = True


def build(node, instance, built, root):
    # A number is a radius and anything else is an outline (§PW65), so the two edges
    # resolve the same way every other outline on a node does.
    return S.annulus(
        H._edge(instance["outer"], root),
        H._edge(instance["inner"], root),
        float(instance["depth"]),
        **H._rest(instance, "profile", "resolution", "crown"),
    )


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = "a ring"
    return what, rest
