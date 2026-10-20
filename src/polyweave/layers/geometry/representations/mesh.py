"""Triangles: a declaration built as a mesh and written as glTF (§PW514)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polyweave.kernel.errors import PolyweaveError

from .. import build as B
from . import Representation


def write(
    document: dict,
    out: str | Path,
    *,
    root: str | Path = ".",
    manifold: bool = False,
    **given: Any,
) -> dict:
    """The declaration built as triangles and written with its materials.

    A `paint` node repaints cells, and triangles have none, so it is refused here,
    by the representation that cannot build it (§PW237).
    """
    from ..normalise import write_mesh

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
    where = Path(out)
    if not where.is_absolute():
        where = Path(root).resolve() / where
    # A material's `image` is a path under the project, as every path a declaration
    # names is, resolved here where the root is known (§PW78). Its values are resolved
    # too, as the review's are, so a finish over the params reaches the shader.
    from .. import expand
    from ..looks import godot as engine

    resolved = expand(document, **given)["materials"] or {}
    _under_root(where, root, resolved)
    made = B.build(document, root=root, manifold=manifold, **given)
    # A material no face wears is lost somewhere in the graph, and said here rather
    # than found in a render (§PW576), as the voxel build says a cell wears nothing.
    wearing = {one["material"] for one in made["output"].get("groups") or ()}
    made["report"]["warnings"] += [
        f"no face wears {name}, which the declaration names"
        for name in resolved if name not in wearing
    ]
    materials = {
        name: {**one, "image": str(Path(root).resolve() / one["image"])}
        if isinstance(one, dict) and one.get("image") else one
        for name, one in resolved.items()
    }
    written = write_mesh(
        made["output"], where, materials=materials, smooth=document.get("smooth")
    )
    # glTF carries a colour and a roughness and drops a look, so a material that asks
    # for one is also written as Godot loads it, with the bake's numbers (§PW495).
    godot, worn = [], {}
    for name, one in resolved.items():
        for path in engine(one, name, where.parent, where.stem, root):
            godot.append(str(path))
            if str(path).endswith(".tres"):
                worn[name] = Path(path)
    # And the mesh is imported wearing them, so the game loads the judged look with the
    # model and holds no code to swap it in (§PW570).
    from ..finish import wire_import

    wired = wire_import(Path(written), worn, root)
    return {**made, "artefact": str(written), "materials": godot,
            **({"import": str(wired)} if wired else {})}


def _under_root(where: Path, root: str | Path, resolved: dict) -> None:
    """Refuse a build outside the project whose materials the engine is written for.

    The engine's materials name their shader by a res:// path, which only a file under
    the project has, so the build is refused before anything is written rather than
    crashing half way through (§PW575).
    """
    from ..looks import for_godot

    here = Path(root).resolve()
    if where.resolve().is_relative_to(here):
        return
    asking = {name: looked for name, one in resolved.items()
              if (looked := for_godot(one))}
    if not asking:
        return
    first = next(iter(asking))
    raise PolyweaveError(
        "geom.out-outside-project",
        f"{where.parent} is outside the project {here}, and {first} asks for "
        f"{', '.join(asking[first])}, whose Godot material names its shader by a "
        "res:// path under the project",
        "write under the project; a trial build can go under .polyweave/, or drop the "
        "finish from the materials to try the shape alone",
        at=f"materials.{first}",
        given=str(where.parent),
    )


def member(document: dict, folder: Path, here: Path, given: dict, preview: bool,
           wanted: bool, answer: dict, mesh: Path) -> dict:
    """One member of a family built as triangles, as the command line reports it."""
    from ..make import _silhouette

    written = write(document, mesh, root=here, **given)
    answer["warnings"] += [
        one for one in written["report"]["warnings"] if one not in answer["warnings"]
    ]
    answer["says"] = f"a mesh of {len(written['output']['faces'])} faces"
    answer["outputs"] = [written["artefact"], *written.get("materials", ())]
    if preview:
        answer["outputs"].append(_silhouette(written["output"], folder, document))
    return answer


REPRESENTATION = Representation(
    name="mesh",
    table=None,
    write=write,
    member=member,
)
