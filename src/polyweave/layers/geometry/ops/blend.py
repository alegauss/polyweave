"""The `blend` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from polyweave.kernel.errors import PolyweaveError

from .. import refers_to
from .. import solid as S
from . import _shared as H

NAME = "blend"

#: What it reads beyond the fields every node has.
FIELDS = (*H.TAKES, "radius", "steps")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = True


def build(node, instance, built, root):
    # Parts joined by a fillet where they meet (§PW498), each read as its own distance
    # field, which only a primitive and what moves one carry.
    from ..blend import blend

    takes = refers_to(node)
    bare = [one for one in takes if not built[one].get("field")]
    if bare or len(takes) < 2:
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} blends {', '.join(bare) or 'fewer than two parts'}, and a "
            "blend joins two or more primitives, or transforms and repeats of them",
            "make each part a primitive (a rounded_box, capsule, sphere, cylinder, "
            "cone, frustum, torus or cube), moved by a transform where it needs to be",
            at=f"nodes.{node['id']}",
        )
    radius = float(instance.get("radius", 0.0))
    if radius <= 0:
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} blends with a radius of {radius:g}, which is no fillet",
            "give the blend a radius above 0, in the declaration's units; a union "
            "joins parts with none",
            at=f"nodes.{node['id']}.radius",
        )
    parts = [part for one in takes for part in built[one]["field"]]
    points = np.vstack([np.asarray(built[one]["vertices"]) for one in takes])
    made = blend(parts, radius, points.min(axis=0), points.max(axis=0),
                 int(instance.get("steps", S.STEPS)))
    smallest = min(float(np.min(np.ptp(np.asarray(built[one]["vertices"]), axis=0)))
                   for one in takes)
    if radius > smallest:
        made["warnings"] = [f"its radius of {radius:g} is larger than its smallest "
                            f"part, {smallest:g} across, so the fillet swallows it"]
    return made


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    # The radius is the one number a blend asks for, so it is said (§PW498).
    radius = instance.get("radius")
    stated = isinstance(radius, int | float)
    fillet = f" by a fillet of {radius:g}" if stated else ""
    what = f"{' and '.join(takes)} flowing together{fillet}"
    return what, rest
