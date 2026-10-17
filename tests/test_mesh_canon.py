"""A canon whose members are meshes, held together through their renders (§PW451).

A generator sees one mesh at a time, so a family of enemies drifting in palette or
proportion is what nothing measured: each new one passed its own spec.
"""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import style
from polyweave.loop import verdict

pytest.importorskip("bpy", reason="Blender draws a mesh's render")

FAMILY = """[style.enemies]
canon = "art/canon/enemies"
rig = { azimuth = 30.0, elevation = 20.0, seen = 48 }
"""


def made(tmp_path, name, colour, *, tall=1.0):
    import bpy

    from polyweave.layers.geometry.render import blender

    blender.reset()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
    body = bpy.context.active_object
    body.scale = (1.0, 1.0, tall)
    bpy.ops.object.transform_apply(scale=True)
    paint = bpy.data.materials.new(f"{name}-paint")
    paint.use_nodes = True
    paint.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        *colour, 1.0)
    body.data.materials.append(paint)
    path = tmp_path / "art" / "enemies" / f"{name}.glb"
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
    return path.relative_to(tmp_path).as_posix()


def judged(tmp_path, mesh):
    return verdict.judge(
        members=[{"name": mesh, "new": mesh, "canon": "enemies"}],
        choice="accept", why="one of the family", asset="enemy", root=str(tmp_path))


@pytest.fixture
def family(tmp_path):
    (tmp_path / "polyweave.toml").write_text(FAMILY, encoding="utf-8")
    for name, colour in (("drone", (0.8, 0.1, 0.1)), ("seeker", (0.7, 0.15, 0.1)),
                         ("keeper", (0.75, 0.1, 0.15))):
        judged(tmp_path, made(tmp_path, name, colour))
    return tmp_path


def test_a_mesh_joins_the_canon_only_by_a_verdict_and_keeps_it(family):
    held = style.admitted(style.read("enemies", root=str(family)))
    assert [e["picture"] for e in held] == ["drone.glb", "seeker.glb", "keeper.glb"]
    assert held[0]["verdict"]["why"] == "one of the family"
    ledger = json.loads((family / "art/canon/enemies/canon.json").read_text("utf-8"))
    assert ledger[0]["verdict"]["choice"] == "accept"


def test_a_member_in_the_family_palette_passes(family):
    said = style.drift(made(family, "gunship", (0.78, 0.12, 0.12)), family="enemies",
                       root=str(family))
    assert said["judged"] and said["passed"], said["drifted"]
    assert said["render"].endswith(".png")


def test_an_off_palette_enemy_drifts_from_a_named_member(family):
    said = style.drift(made(family, "ship", (0.1, 0.3, 0.9)), family="enemies",
                       root=str(family))
    assert not said["passed"]
    assert "hue_degrees" in said["drifted"]
    assert said["measures"]["hue_degrees"]["which_way"].startswith("hue turned")
    assert said["neighbour"]["member"] in ("drone.glb", "seeker.glb", "keeper.glb")
    assert said["neighbour"]["render"].endswith(".png")


def test_a_taller_enemy_is_told_taller(family):
    said = style.drift(made(family, "tower", (0.8, 0.1, 0.1), tall=2.0),
                       family="enemies", root=str(family))
    assert said["measures"]["height_to_width"]["which_way"] == "taller"


def test_a_rig_naming_what_bake_does_not_take_is_refused(family):
    (family / "polyweave.toml").write_text(
        FAMILY.replace("seen = 48", "seen = 48, zoom = 2"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        style.drift("art/enemies/drone.glb", family="enemies", root=str(family))
    assert refused.value.code == "style.bad-rig"
