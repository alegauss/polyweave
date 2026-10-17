"""The `paint` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

import numpy as np

from polyweave.kernel.errors import PolyweaveError

from .. import voxels as V

NAME = "paint"

#: What it reads beyond the fields every node has.
FIELDS = ("on", "where")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    # The body's own triangles: a repaint adds no shape, and only cells take it
    # (§PW237). A traced op in a voxel document builds the whole document through here,
    # so this passes the body on rather than refusing; `write` refuses a triangle build.
    return built[node["on"]]


def bounds(model, node, instance):
    return model.bounds(node["on"])


def inside(model, node, instance, points):
    rank = model.rank[node["id"]]
    # The body's cells, every one and no more, repainted where `where` covers
    # them: a band round a sphere without a slab sticking out of it (§PW237).
    if not node.get("on") or not V._named_list(node.get("where")):
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} paints and does not say "
            + ("on what" if not node.get("on") else "where"),
            "give it `on`, the body whose cells it repaints, and `where`, the "
            "node or list of nodes whose cells take its material",
            at=f"nodes.{node['id']}",
        )
    body = model.inside(node["on"], points)
    cover = np.zeros(len(points), dtype=bool)
    for one in V._named_list(node.get("where")):
        cover |= model.inside(one, points).inside
    return body.repainted(body.inside & cover, rank, node.get("material") or "")


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    # Said whole, material included, because the material is what it adds (§PW237).
    where = node.get("where")
    covers = " and ".join(where) if isinstance(where, list) else str(where)
    return (
        f"{node.get('on', 'nothing')} painted {node.get('material') or 'nothing'} "
        f"where {covers}"
    )
