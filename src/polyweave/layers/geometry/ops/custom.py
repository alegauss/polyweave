"""The `custom` op: how it is built, read, bounded, filled and said (§PW513)."""

from __future__ import annotations

from .. import custom

NAME = "custom"

#: What it reads beyond the fields every node has.
FIELDS = None

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = True


def build(node, instance, built, root):
    return custom.build(node, instance, built, root=root)


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    what = f"whatever {node.get('fn', 'a project function')} builds"
    return what, rest
