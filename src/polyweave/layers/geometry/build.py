"""The twenty lines between a declaration and a mesh.

The evidence is §PW60. Every piece either side of this was built and nothing composed
them: each `op` is a function in `solid`, `solver` or `custom`; `expand` resolves every
expression and instances every repeat; `order` returns the nodes in an order where each
input is built before what needs it — a walker's scaffolding with no walker on it — and
`review.report` takes the built meshes from its caller, which every test supplied by
hand. So `docs/specs/geometry.md` described a build that no call in the package could
perform, and nothing under `src/` imported `polyweave.layers.geometry` at all.

**One module per op** (§PW513). `BUILDS` maps an `op` to the adapter that shapes a
node's own fields into the call, and it is read off `ops/`, where each op's module also
holds the fields it reads, its voxel bound and the words the review sheet says of it.
So a document naming an op nothing builds is a warning before it is a refusal, and a
new op is one new file rather than four lists that drift apart.

**A repeated node's id names the whole set.** Sixty-four seats build as sixty-four
meshes and are joined into the one mesh their id stands for, which is what lets the tray
be one boolean rather than sixty-four.

**`at` places an instance and is applied last**, because it is the field that makes a
repeat mean anything: a seat differs from its sixty-three siblings in nothing but where
it sits. `transform` is the exception, since `at` is its own argument there.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from polyweave.kernel.errors import PolyweaveError

from . import expand, order, refers_to
from . import solid as S
from .ops._shared import PROFILES, _outline, _rest  # noqa: F401 - read from here

__all__ = ["BUILDS", "build", "builds"]  # noqa: F822 - BUILDS is read lazily


def mesh_file(node: dict, instance: dict, root: Any) -> Path:
    """The file a `mesh` node names, refused where there is none."""
    stated = instance.get("path")
    where = Path(str(stated or ""))
    if not where.is_absolute():
        where = Path(root) / where
    if not stated or not where.is_file():
        raise PolyweaveError(
            "geom.bad-solid",
            f"{node['id']} takes its shape from {stated!r}, and there is no file there",
            "give `path` a mesh file under the project, as a .glb or a .blend",
        )
    return where


#: What every node may say, whatever its op: its name, what it builds, what it wears,
#: how it repeats and where it sits.
NODE_FIELDS = ("id", "op", "material", "repeat", "at")

#: The ops that consume `at` themselves, so the placement below leaves them alone.
PLACES = ("transform",)


def builds(op: str) -> bool:
    """Whether anything here builds that op. What `review` asks before warning."""
    return op in _builds()


def _builds() -> dict[str, Callable]:
    """Every op a declaration may name, and what builds it, from `ops/` (§PW513)."""
    from .ops import every

    return {name: op.build for name, op in every().items()}


def __getattr__(name: str):
    # `BUILDS` and `FIELDS` read as they always did, from the op modules (§PW513).
    from .ops import every

    if name == "BUILDS":
        return _builds()
    if name == "FIELDS":
        return {one: op.fields for one, op in every().items()}
    raise AttributeError(name)


def build(
    document: dict, *, root: str | Path = ".", manifold: bool = False, **given: Any
) -> dict:
    """The mesh a declaration describes, with the report that says what came out.

    Walks `order`, dispatches on `op`, collects into `built`, and hands the lot to
    `review.report` — which is the whole of what was missing. A shape that can only be
    checked by looking at a render is one whose construction errors are found in the
    expensive place, so the report comes back with the mesh and not on request.
    """
    from .review import report
    from .voxels import stated_cell, with_project_cell

    here = Path(root).resolve()
    document, _, _ = with_project_cell(document, here)
    resolved = expand(document, **given)
    stated = {node["id"]: node for node in document["nodes"]}
    instanced = {node["id"]: node for node in resolved["nodes"]}
    cell = stated_cell(document, resolved["params"])

    built: dict[str, dict] = {}
    for one in order(document):
        node, made = stated[one], []
        how = _builds().get(node["op"])
        if how is None:
            raise PolyweaveError(
                "geom.unknown-op",
                f"{one!r} has op {node['op']!r}, and nothing builds that",
                f"name one of {', '.join(sorted(_builds()))}, or write it as a "
                f"`custom` node pointing at a function of your own",
                given=node["op"],
                allowed=_builds(),
                at=f"nodes.{one}.op",
            )
        for instance in instanced[one]["instances"]:
            if node["op"] == "cells" and cell and not instance.get("cell"):
                instance = {**instance, "cell": cell}
            made.append(_placed(node, instance, how(node, instance, built, here)))
        # A repeated node's id names the whole set, which is what makes the tray one
        # boolean rather than sixty-four.
        whole = made[0] if len(made) == 1 else S.union(*made)
        if node.get("material") and whole.get("field"):
            # What a node wears goes with its field, so a blend paints each part.
            whole = {**whole, "field": [{**part, "material": node["material"]}
                                        for part in whole["field"]]}
        worn = _worn(node, whole, built)
        built[one] = {**whole, "groups": worn} if worn else whole

    return {
        "output": built[document["output"]],
        "built": built,
        "report": report(document, built, manifold=manifold, **given),
    }


def write(
    document: dict,
    out: str | Path,
    *,
    root: str | Path = ".",
    manifold: bool = False,
    **given: Any,
) -> dict:
    """Build a declaration and put it where the rest of the plugin can reach it.

    The call the block ended one short of (§PW69). A document could be read, reviewed,
    expanded, searched and built, and the only way to see the result was a test: `bake`
    takes its model as a path, so a mesh in memory had nowhere to go.

    **A file rather than a handle, and that is the decision.** The cache key and the
    provenance record key off a file and its hash already, and both are the discipline
    this plugin is built on — a mesh in memory has no sha256 until something defines a
    canonical serialisation for it, which is a second format to keep true. So a build
    writes what it made, `bake(model=…)` takes it unchanged from there, and a search
    that rebuilds per sample pays one file per sample beside the render it was going to
    pay for anyway.

    The materials go with it, because a group names one and a file needs the thing.

    A document declaring `[voxels]` answers cells instead (§PW93): the cells go beside
    `out` as `<stem>.voxels.json` and `out` holds the same cubes, so everything that
    takes a mesh still takes it.
    """
    from .normalise import write_mesh

    if document.get("voxels"):
        from .voxels import write as cells

        return cells(document, out, root=root, **given)

    painting = [node["id"] for node in document["nodes"] if node["op"] == "paint"]
    if painting:
        raise PolyweaveError(
            "geom.bad-voxels",
            f"{painting[0]} repaints cells, and {document['name']} is built as "
            f"triangles, which have no cells to repaint",
            "give the declaration a [voxels] table, or put the material on the node "
            "whose faces it is meant for",
            at=f"nodes.{painting[0]}.op",
        )
    made = build(document, root=root, manifold=manifold, **given)
    where = Path(out)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    # A material's `image` is a path under the project, as every path a declaration
    # names is, resolved here where the root is known (§PW78). Its values are resolved
    # too, as the review's are, so a finish over the params reaches the shader.
    from . import expand, finish

    resolved = expand(document, **given)["materials"] or {}
    materials = {
        name: {**one, "image": str(Path(root).resolve() / one["image"])}
        if isinstance(one, dict) and one.get("image") else one
        for name, one in resolved.items()
    }
    written = write_mesh(made["output"], where, materials=materials)
    # glTF carries a colour and a roughness and drops a finish, so a material that asks
    # for one is also written as Godot loads it, with the bake's numbers (§PW495).
    godot = [
        str(path)
        for name, one in resolved.items()
        if finish.asked(one)
        for path in finish.write_godot(one, name, where.parent, where.stem, root)
    ]
    return {**made, "artefact": str(written), "materials": godot}


def _worn(node: dict, made: dict, built: dict) -> list[dict]:
    """Which faces of this mesh wear which material (§PW67).

    A material sits on a node and a document names one output, so a model in two
    materials — Cottony's cream rope rim on its cushion face — could only be handed back
    as a join, and the join kept one material or none. The colours were in the document,
    survived `expand`, were read back by the review, and were gone from the mesh.

    Faces, because that is the one thing a join really does know: `union` lays its
    operands out in order, so where each one's faces landed is arithmetic. It is also
    what a renderer wants, since a material slot is assigned per polygon.

    **A boolean keeps what it cut into and nothing finer.** The cutter is gone from the
    result and the solver does not preserve face correspondence, so a carve or a bevel
    over one material is one group and over several is none. Claiming a range the solver
    reordered would be worse than saying nothing.
    """
    if node.get("material"):
        return [{"material": node["material"], "faces": [0, len(made["faces"])]}]
    if node["op"] == "union":
        groups, at = [], 0
        for one in refers_to(node):
            part = built[one]
            for group in part.get("groups") or ():
                start, stop = group["faces"]
                groups.append(
                    {"material": group["material"], "faces": [start + at, stop + at]}
                )
            at += len(part["faces"])
        return groups
    if node["op"] in ("carve", "bevel"):
        source = node.get("into") or (refers_to(node) or [""])[0]
        worn = {g["material"] for g in built.get(source, {}).get("groups") or ()}
        if len(worn) == 1:
            return [{"material": worn.pop(), "faces": [0, len(made["faces"])]}]
    return []


def _placed(node: dict, instance: dict, made: dict) -> dict:
    """One instance where its own `at` puts it, which is what a repeat varies."""
    at = instance.get("at")
    if at is None or node["op"] in PLACES:
        return made
    return S.transform(made, at=at)
