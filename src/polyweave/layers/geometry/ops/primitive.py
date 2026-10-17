"""The `primitive` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import solid as S
from .. import voxels as V
from . import _shared as H

NAME = "primitive"

#: What it reads beyond the fields every node has.
FIELDS = (
        "kind",
        "size",
        "steps",
        "axis",
        "bottom",
        "top",
        "height",
        "major",
        "minor",
        "radius",
    )

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    shaped = ("bottom", "top", "height", "major", "minor", "radius")
    return S.primitive(
        str(instance.get("kind", "cube")),
        instance.get("size", 1.0),
        **H._rest(instance, "front", "profile", "resolution", "crown"),
        **{k: v for k, v in instance.items() if k in shaped},
        axis=node.get("axis", "z"),
    )


def bounds(model, node, instance):
    return S.shape_box(S.shape({**instance, "axis": node.get("axis", "z")}))


def inside(model, node, instance, points):
    rank = model.rank[node["id"]]
    return V._Found.of(
        V._primitive({**instance, "axis": node.get("axis", "z")}, points), rank
    )


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"a {instance.get('kind', 'cube')}"
    return what, rest
