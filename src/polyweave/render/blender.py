"""The boundary with Blender: the only module that imports bpy.

Blender is optional. The plugin reports whether it is reachable (`capabilities`) and
refuses a render without it, rather than failing on an import nobody asked for — so
`import polyweave` never costs a renderer.

`docs/specs/tool-surface.md` §6 fixes the axes as **Y up, −Z forward**, which is the
engine's convention and the one every other module here works in. Blender is Z-up, and
this is the one place that difference exists.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError
from .rig import Rig, bounds_of, camera_for, lights_for

#: Blender's own colour pipeline. `Standard` is the one that puts back what was put in;
#: a filmic or AgX transform makes a measured colour a different number from the
#: authored one, and every predicate in an acceptance spec compares the two.
VIEW_TRANSFORM = "Standard"


def to_blender(point) -> tuple[float, float, float]:
    """Y-up, −Z-forward to Blender's Z-up. The conversion, in one place."""
    x, y, z = point
    return (x, -z, y)


def available() -> dict:
    """Whether bpy is importable here, and which Blender it is."""
    try:
        import bpy
    except Exception as exc:  # noqa: BLE001 - any import failure is "not available"
        return {"found": False, "version": None, "why": f"{type(exc).__name__}: {exc}"}
    return {"found": True, "version": bpy.app.version_string, "why": None}


def require():
    """The bpy module, or a refusal that says how to get one."""
    try:
        import bpy
    except Exception as exc:  # noqa: BLE001
        raise PolyweaveError(
            "render.no-renderer",
            "Blender is not importable in this interpreter, so nothing can render",
            "install the bpy module (`pip install bpy`), or point `[paths] blender` at "
            "a Blender that runs this plugin's worker",
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
    return bpy


# -- the scene -------------------------------------------------------------------


def reset() -> Any:
    """An empty scene, so nothing from a previous render is still standing."""
    bpy = require()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def primitive(kind: str = "sphere", radius: float = 1.0) -> Any:
    """The shape a material is read on."""
    bpy = require()
    if kind != "sphere":
        raise PolyweaveError(
            "render.unknown-primitive",
            f"there is no {kind!r} primitive",
            "use 'sphere', which is the shape a surface is read on",
        )
    # Smooth enough for a surface to read on, and a fraction of the faces a character
    # carries — the cheap rung being cheap is the whole point of it.
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=32, ring_count=16)
    obj = bpy.context.object
    bpy.ops.object.shade_smooth()
    return obj


def load_mesh(path: str | Path) -> Any:
    """Import a mesh and return the object that arrived.

    glTF is the interchange the rest of this plugin speaks, and its axes are the ones §6
    fixes, so the importer's own conversion is the right one.
    """
    bpy = require()
    where = Path(path)
    if not where.is_file():
        raise PolyweaveError(
            "render.no-mesh",
            f"there is no mesh at {where}",
            "check the path, or build the mesh before rendering it",
        )
    before = set(bpy.data.objects)
    if where.suffix.lower() in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(where))
    elif where.suffix.lower() == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(where))
    else:
        raise PolyweaveError(
            "render.unknown-format",
            f"{where.suffix or 'that file'} is not a mesh format this reads",
            "export the mesh as .glb, .gltf or .fbx",
        )
    arrived = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    if not arrived:
        raise PolyweaveError(
            "render.no-mesh",
            f"{where} imported without a single mesh in it",
            "check what the exporter wrote; an empty scene imports without an error",
        )
    return _join(arrived)


def decimate(obj: Any, ratio: float) -> Any:
    """Fewer faces for the same silhouette, which is what a preview rung is."""
    bpy = require()
    if not 0.0 < ratio <= 1.0:
        raise PolyweaveError(
            "render.bad-ratio",
            f"a decimation ratio is a fraction of one, and {ratio!r} is not",
            "pass a ratio above 0 and at most 1",
        )
    if ratio == 1.0:
        return obj
    modifier = obj.modifiers.new("polyweave-decimate", "DECIMATE")
    modifier.ratio = ratio
    with bpy.context.temp_override(object=obj):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def apply_material(obj: Any, material: dict | None) -> Any:
    """Put a surface on the subject, so a sphere and a mesh carry the same one."""
    bpy = require()
    if not material:
        return obj
    made = bpy.data.materials.new("polyweave")
    made.use_nodes = True
    bsdf = made.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:  # pragma: no cover - a Blender without the standard shader
        raise PolyweaveError(
            "render.no-material",
            "this Blender has no Principled BSDF to build a material on",
            "render with a Blender that ships the standard shader nodes",
        )
    unknown = sorted(k for k in material if _socket(bsdf, k) is None)
    if unknown:
        raise PolyweaveError(
            "render.unknown-material-field",
            f"a material has no {', '.join(unknown)}",
            f"use one of {', '.join(_socket_names(bsdf))}",
        )
    for key, value in material.items():
        socket = _socket(bsdf, key)
        socket.default_value = _coerce(value, socket)
    obj.data.materials.clear()
    obj.data.materials.append(made)
    return obj


def place(scene: Any, rig: Rig, subject: Any) -> dict:
    """Camera, lights and film, computed from the rig and the subject's own bounds."""
    bpy = require()
    lo, hi = _bounds(subject)
    camera = camera_for(rig, lo, hi)
    lights = lights_for(rig, lo, hi)

    data = bpy.data.cameras.new("polyweave-camera")
    data.lens = rig.focal_mm
    obj = bpy.data.objects.new("polyweave-camera", data)
    scene.collection.objects.link(obj)
    obj.location = to_blender(camera["location"])
    obj.rotation_euler = _look_at(obj.location, to_blender(camera["look_at"]))
    scene.camera = obj

    for light in lights:
        lamp = bpy.data.lights.new(f"polyweave-{light['role']}", "AREA")
        lamp.energy = light["energy"]
        lamp.size = camera["radius"] * 2.0
        holder = bpy.data.objects.new(f"polyweave-{light['role']}", lamp)
        scene.collection.objects.link(holder)
        holder.location = to_blender(light["location"])
        holder.rotation_euler = _look_at(holder.location, to_blender(camera["centre"]))

    scene.render.film_transparent = rig.transparent
    if scene.world is None:
        scene.world = bpy.data.worlds.new("polyweave-world")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Strength"].default_value = rig.ambient
    scene.view_settings.exposure = rig.exposure
    _standard_colour(scene)
    return camera


def render_to(
    scene: Any,
    path: str | Path,
    *,
    size: int,
    samples: int,
    seed: int,
) -> Path:
    """Render the scene to a PNG with alpha, and return where it landed."""
    bpy = require()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = int(samples)
    scene.cycles.seed = int(seed)
    scene.cycles.use_denoising = True
    scene.render.resolution_x = int(size)
    scene.render.resolution_y = int(size)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(out.resolve())
    bpy.ops.render.render(write_still=True)
    return out


def engine_record(scene: Any) -> dict:
    """What produced the picture, for the record beside it.

    The colour pipeline is in here because a render that moved because its view
    transform moved is otherwise indistinguishable from one whose scene moved.
    """
    bpy = require()
    return {
        "name": scene.render.engine.lower(),
        "version": bpy.app.version_string,
        "bindings": f"bpy {'.'.join(str(v) for v in bpy.app.version)}",
        "view_transform": scene.view_settings.view_transform,
        "display_device": scene.display_settings.display_device,
    }


# -- the small awkward parts ------------------------------------------------------


def _standard_colour(scene: Any) -> None:
    """Ask for the transform that puts back what was put in, and settle for what exists.

    An installation whose colour configuration is missing silently keeps whatever it
    had, so the transform actually in force is recorded rather than assumed.
    """
    # A build without the standard transform keeps the one it had, which is why
    # `engine_record` reports the transform in force rather than the one asked for.
    with contextlib.suppress(TypeError):
        scene.view_settings.view_transform = VIEW_TRANSFORM


def _socket_names(bsdf: Any) -> list[str]:
    return [i.name.lower().replace(" ", "_") for i in bsdf.inputs]


def _socket(bsdf: Any, key: str) -> Any:
    wanted = key.lower().replace("_", " ")
    for socket in bsdf.inputs:
        if socket.name.lower() == wanted:
            return socket
    return None


def _coerce(value: Any, socket: Any) -> Any:
    if isinstance(value, list | tuple):
        wide = list(value)
        while len(wide) < len(socket.default_value):
            wide.append(1.0)
        return wide[: len(socket.default_value)]
    return value


def _join(objects: list) -> Any:
    bpy = require()
    if len(objects) == 1:
        return objects[0]
    with bpy.context.temp_override(
        active_object=objects[0], selected_editable_objects=objects
    ):
        bpy.ops.object.join()
    return objects[0]


def _bounds(obj: Any) -> tuple[tuple, tuple]:
    """The subject's corners, back in the interface's axes."""
    world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not world:
        raise PolyweaveError(
            "render.no-mesh",
            "the subject has no vertices to frame",
            "check that the mesh loaded; an empty object renders as nothing",
        )
    return bounds_of([(v.x, v.z, -v.y) for v in world])


def _look_at(location, target):
    """Point a camera or a lamp at `target`.

    Blender's own tracking quaternion rather than hand-rolled Euler angles: both a
    camera and an area light emit down their local −Z with +Y up, and this is the
    routine that knows it.
    """
    from mathutils import Vector

    direction = Vector(target) - Vector(location)
    if direction.length == 0.0:  # pragma: no cover - a light inside the subject
        return (0.0, 0.0, 0.0)
    return direction.to_track_quat("-Z", "Y").to_euler()
