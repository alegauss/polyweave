"""The two operations that need a solver rather than arithmetic.

A boolean and a bevel are not constructions, they are solves, and this is the one part
of the vocabulary that goes through Blender. Everything in `solid.py` is numpy and stays
that way.

**The solver is MANIFOLD.** Cottony measured Blender's EXACT solver returning an empty
mesh, with no error and no warning, whenever the object it cuts had been bevelled — 2402
faces to 0 on the tray, against 6590 for the same cut unbevelled — and moved to MANIFOLD
because of it.

**That failure does not reproduce on Blender 5.2.1**, and saying so is the point of
measuring rather than inheriting. Rebuilt here, on the same shape: the tray's plate
bevelled and then cut by all sixty-four seats returns 3210 faces under EXACT and 3206
under MANIFOLD, and a single pocket returns 966 against 884. Neither empties. So the
choice is kept for the reason it was made and not for a symptom this version still has:
MANIFOLD is the one measured to work on the case that broke, it costs nothing here, and
a silent empty result is not a thing to gamble a build on.

**What actually protects the build is the assertion**, which is why §PW2 asked for it.
A boolean returning nothing raises `post.boolean-empty` whichever solver produced it and
whichever version of Blender is installed, and that outlives any finding about either.

**The cutter's normals are recalculated first.** An inconsistent solid reads as one big
half-space and the difference takes the whole front off — the other silent trap, also
paid for once already.

**The boolean runs before the bevel** wherever a node asks for both. That order came
from the same episode, and it stays: it costs nothing, and it is the arrangement the
measurement above was taken under.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.post.mesh import as_mesh, check_mesh

#: Blender's own name for the solver that does not empty a cut against a bevel.
SOLVER = "MANIFOLD"


def available() -> dict:
    """Whether a solver is reachable here, for a caller planning a build."""
    try:
        from .render import blender

        blender.require()
    except PolyweaveError as refused:
        return {"solver": SOLVER, "ready": False, "why": refused.message}
    return {"solver": SOLVER, "ready": True, "why": ""}


def _object(bpy: Any, subject: Any, name: str) -> Any:
    """The subject as a Blender object, each material it wears a slot of its own.

    What a face wears goes in as its polygon's material index (§PW564), so the solve
    carries it: a bevel's new faces take the face they grew from, and a carve's cut
    faces the cutter's.
    """
    from .render import blender

    points, faces = as_mesh(subject)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [blender.to_blender(p) for p in points], [], [list(face) for face in faces]
    )
    worn = subject.get("groups") if isinstance(subject, dict) else None
    if worn:
        names = list(dict.fromkeys(str(one["material"]) for one in worn))
        for material in names:
            mesh.materials.append(
                bpy.data.materials.get(material) or bpy.data.materials.new(material)
            )
        index = np.zeros(len(faces), dtype=np.int32)
        for one in worn:
            start, end = (int(v) for v in one["faces"])
            index[start:end] = names.index(str(one["material"]))
        mesh.polygons.foreach_set("material_index", index)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _back(obj: Any) -> dict:
    """The object's mesh, back in the interface's own axes, with what each face wears.

    Faces are ordered by their material, so each material is one run of them, as a
    group is.
    """
    world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    out: dict = {"vertices": np.array([(v.x, v.z, -v.y) for v in world], dtype=float)}
    slots = [slot.material for slot in obj.material_slots]
    if not slots or not any(slots):
        return {**out, "faces": faces}
    worn = [min(p.material_index, len(slots) - 1) for p in obj.data.polygons]
    order = sorted(range(len(faces)), key=lambda i: worn[i])
    out["faces"] = [faces[i] for i in order]
    groups, start = [], 0
    for slot, material in enumerate(slots):
        count = sum(1 for i in order if worn[i] == slot)
        if count and material is not None:
            groups.append({"material": material.name, "faces": [start, start + count]})
        start += count
    out["groups"] = groups
    return out


def _recalculated(bpy: Any, obj: Any) -> None:
    """Outward-facing normals, or the difference takes the whole front off."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def carve(into: Any, cutter: Any, *, min_faces: int = 1) -> dict:
    """`into` minus `cutter`, with the solver that does not silently return nothing."""
    from .render import blender

    bpy = blender.require()
    blender.reset()
    target = _object(bpy, into, "into")
    knife = _object(bpy, cutter, "cutter")
    _recalculated(bpy, knife)

    before = len(target.data.polygons)
    modifier = target.modifiers.new("carve", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = knife
    modifier.solver = SOLVER
    # the cut's walls wear the cutter's materials, added to the target's slots (§PW564)
    if hasattr(modifier, "material_mode"):
        modifier.material_mode = "TRANSFER"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    after = len(target.data.polygons)
    if after < min_faces:
        raise PolyweaveError(
            "post.boolean-empty",
            f"the carve returned {after} faces from {before}",
            f"the cutter may not be a closed solid, or it may not reach the target; "
            f"this ran under the {SOLVER} solver, and an empty boolean raises nothing "
            f"on its own, which is what this assertion is for",
        )
    return {**_back(target), "before": before, "after": after, "solver": SOLVER}


def bevel(
    subject: Any, offset: float, *, segments: int = 3, profile: float = 0.5
) -> dict:
    """Soften every edge. Applied **after** a boolean, never before one."""
    from .render import blender

    bpy = blender.require()
    # bmesh is Blender's and exists only once bpy is loaded: imported first, a process
    # whose first Blender call is a bevel had none (§PW563)
    import bmesh

    blender.reset()
    obj = _object(bpy, subject, "bevelled")
    working = bmesh.new()
    working.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(working, faces=working.faces[:])
    if float(offset) > 0:
        bmesh.ops.bevel(
            working,
            geom=working.verts[:] + working.edges[:] + working.faces[:],
            offset=float(offset),
            segments=int(segments),
            profile=float(profile),
            affect="EDGES",
            # a new face wears the faces it grew between, not the first slot (§PW564)
            material=-1,
        )
    working.to_mesh(obj.data)
    working.free()
    return _back(obj)


def build(
    subject: Any, *, cutter: Any = None, bevel_by: float = 0.0, **how: Any
) -> dict:
    """A node's boolean and its bevel, in the order that works.

    The order is the finding: a cut against an already-bevelled object comes back empty,
    so the boolean goes first and the bevel second, whatever order the document wrote
    them in.
    """
    out = carve(subject, cutter) if cutter is not None else {**as_dict(subject)}
    if float(bevel_by) > 0:
        out = {**out, **bevel(out, float(bevel_by), **how)}
    check_mesh(out)
    return out


def as_dict(subject: Any) -> dict:
    """The subject's points and faces, and what they wear where it says (§PW564)."""
    points, faces = as_mesh(subject)
    worn = subject.get("groups") if isinstance(subject, dict) else None
    return {"vertices": points, "faces": faces, **({"groups": worn} if worn else {})}
