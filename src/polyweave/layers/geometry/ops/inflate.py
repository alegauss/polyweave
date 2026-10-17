"""The `inflate` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from polyweave.kernel.errors import PolyweaveError

from .. import review as R
from .. import solid as S
from . import _shared as H

NAME = "inflate"

#: What it reads beyond the fields every node has.
FIELDS = (
        "outline",
        "thickness",
        "profile",
        "resolution",
        "drawing",
        "size",
        "soften",
        "cell",
        "floor",
        "sides",
    )

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = True


def build(node, instance, built, root):
    # Two profiles, and what the node was given decides which (§PW68). An outline knows
    # only where the shape stops, so it swells by distance from the edge; a drawing
    # carries what is inside it too, so the alpha itself is blurred into the height.
    if instance.get("drawing"):
        return S.stuffed(
            H._alpha(instance["drawing"], root),
            float(instance["thickness"]),
            **{
                k: v
                for k, v in instance.items()
                if k in ("size", "soften", "cell", "floor", "sides")
            },
        )
    # An outline already swells both faces (§PW492), so only a drawing has a choice.
    if instance.get("sides", 2) != 2:
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} inflates an outline on {instance['sides']!r} sides, and an "
            "outline swells both faces",
            "leave sides out on an outline; sides = 1 is a drawing's relief",
        )
    return S.inflate(
        H._outline(instance, root),
        float(instance["thickness"]),
        **H._rest(instance, "steps", "front", "crown"),
    )


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    # Two profiles, and which one it gets is worth saying: an outline swells from
    # its edge, a drawing from its own alpha (§PW68).
    both = " on both faces" if instance.get("sides") == 2 else ""
    what = (
        f"{instance['drawing']}, given volume by its own alpha{both}"
        if instance.get("drawing")
        else f"{R._outline_words(instance.get('outline'))}, given volume"
    )
    return what, rest
