"""The `cells` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from polyweave.kernel.errors import PolyweaveError

from .. import review as R
from .. import voxels as V

NAME = "cells"

#: What it reads beyond the fields every node has.
FIELDS = ("layers", "legend", "cell", "axis")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    # Cells drawn as text build as their cubes here, so a drawing is not voxel-only
    # (§PW95): a canopy painted in cells sits on a hull built as triangles.
    from ..voxels import drawn_mesh

    size = instance.get("cell")
    if not size:
        raise PolyweaveError(
            "geom.bad-cells",
            f"{node['id']} draws cells and nothing says how big one is",
            "give the node a `cell`, or give the document a [voxels] `cell`",
        )
    return drawn_mesh(node, float(size))


def bounds(model, node, instance):
    size = model.size_of(node, instance)
    return np.zeros(3), np.asarray(V.lattice(node)["size"], dtype=float) * size


def inside(model, node, instance, points):
    return model._drawn(node, instance, points)


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = R._drawing(node)
    return what, rest
