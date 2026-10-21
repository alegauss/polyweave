"""The `model` op: another declaration's model, placed with its materials (§PW588).

Spinhold's worlds are each a voxel diorama of the kit pieces the ring already has, each
piece its own declaration, built and accepted. Of the ops only `mesh` read another file,
and a piece's `.glb` brings none of its named materials, so reusing one meant copying
its nodes into the diorama or placing it in game code, outside every check.

A `model` node names the piece's declaration by `path` and moves it as `transform` does
(`scale`, `rotate`, and the `at` and `repeat` every node has). Its cells are the piece's
own, evaluated at the diorama's grid, so a piece declared at another cell is resampled
rather than refused. Each keeps the material it wears there, named under the piece
(`kit_cottage.roof`) unless the diorama's own `[materials]` declares that name, which
then wins. A `material` on the node paints the whole piece, as on any other node.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from polyweave.kernel.errors import PolyweaveError

from ..representations.voxels import model as V

NAME = "model"

#: What it reads beyond the fields every node has.
FIELDS = ("path", "scale", "rotate")

#: Whether a voxel build traces its mesh rather than reading its own bounds.
TRACED = False


def build(node, instance, built, root):
    # The piece's materials live in its own [materials], which a mesh's groups could
    # only reach by name through this document's: so the op is the voxel build's alone.
    raise PolyweaveError(
        "geom.bad-solid",
        f"{node['id']} places another declaration's model, which only a voxel build "
        "does, and this declaration builds a mesh",
        "give the declaration a [voxels] table, or name the piece's .glb with a mesh "
        "node",
        at=f"nodes.{node['id']}.op",
    )


def _moved(instance: dict) -> dict:
    """The node's own move, `at` left to the placement every op gets."""
    return {key: instance[key] for key in ("scale", "rotate") if key in instance}


def _piece(model, node: dict, instance: dict):
    """The piece's own model, read once per path and refused where it cannot be."""
    from ... import geometry as G
    from ..representations.voxels.model import with_project_cell

    stated = instance.get("path")
    where = Path(str(stated or ""))
    if not where.is_absolute():
        where = Path(model.root) / where
    where = where.resolve()
    if not stated or where.suffix.lower() != ".toml" or not where.is_file():
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} places the model declared in {stated!r}, and there is no "
            "declaration there",
            "give `path` the piece's .toml under the project",
            at=f"nodes.{node['id']}.path",
        )
    if where in model.placing:
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} places {stated}, which is already being placed, so the "
            "model would contain itself",
            "place a piece that does not place this declaration",
            at=f"nodes.{node['id']}.path",
        )
    kept = model.pieces.get(where)
    if kept is None:
        document, _, _ = with_project_cell(G.read(where, root=model.root), model.root)
        kept = V._Model(document, model.root, {})
        kept.placing = (*model.placing, where)
        model.pieces[where] = kept
    return kept


def bounds(model, node, instance):
    piece = _piece(model, node, instance)
    low, high = piece.bounds(piece.document["output"])
    corners = np.array(
        [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1])
         for z in (low[2], high[2])]
    )
    moved = V._forward(corners, _moved(instance))
    return moved.min(axis=0), moved.max(axis=0)


def inside(model, node, instance, points):
    """The piece's cells where it stands, each wearing its own material, renamed."""
    piece = _piece(model, node, instance)
    where = V._backward(points, _moved(instance))
    found = piece.inside(piece.document["output"], where)
    name = piece.document["name"]
    declared = model.document.get("materials") or {}
    known = {**piece.found_materials, **piece.resolved["materials"]}
    renamed = {}
    for worn in {str(one) for one in found.wears[found.inside] if one}:
        # This document's own name for it wins; otherwise it is the piece's, by name.
        named = worn if worn in declared else f"{name}.{worn}"
        renamed[worn] = named
        if named not in declared:
            model.found_materials[named] = dict(known.get(worn) or {})
    wears = np.array([renamed.get(str(one), "") for one in found.wears], dtype=object)
    rank = model.rank[node["id"]]
    return V._Found.drawn(found.inside, rank, wears)


def words(node, instance, takes, rest, skip):
    """What the review sheet says this node is, and what is left to say."""
    from .. import review as R

    what = f"the model in {instance.get('path', '?')}"
    rest = R._fields(instance, (*skip, "path"))
    return what, rest
