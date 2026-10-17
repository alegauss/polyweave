"""The `mesh` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import review as R
from .. import solid as S
from ..representations.voxels import model as V

NAME = "mesh"

#: What it reads beyond the fields every node has.
FIELDS = ("path", "colours")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = True


def build(node, instance, built, root):
    # A mesh file as a node, in the project's own axes (§PW100): a hull bought from the
    # service becomes the block a declaration cuts and paints, rather than the end.
    from ..build import mesh_file
    from ..normalise import read_mesh

    found = read_mesh(mesh_file(node, instance, root))
    return S.mesh(found["vertices"], found["faces"])


def inside(model, node, instance, points):
    """A mesh node's cells: its own colours where it wears no material (§PW100)."""
    if not node.get("material"):
        return model._textured(node, instance, points)
    return V._Found.of(V._parity(model._traced(node, instance), points),
                       model.rank[node["id"]])


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"the mesh in {instance.get('path', '?')}"
    rest = R._fields(instance, (*skip, "path"))
    return what, rest
