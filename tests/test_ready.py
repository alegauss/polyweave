"""A bought mesh held to an engine-ready bar on arrival (§PW447).

The bar is an acceptance spec's cost predicates. What needs no judgement is fixed on the
way, seams welded and triangles reduced to the ceiling; what still misses a bound is
refused before a sitting is drawn of it.
"""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import cost, normalise

SPEC = """asset = "drone"

[[predicate]]
id = "budget"
measure = "triangles"
max = 1500

[[predicate]]
id = "closed"
measure = "holes"
max = 0
"""


def exported(tmp_path, name, make):
    bpy = pytest.importorskip("bpy", reason="Blender is not importable here")
    from polyweave.layers.geometry.render import blender

    blender.reset()
    make(bpy)
    path = tmp_path / f"{name}.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
    return path


def sphere(bpy):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)


def sheet(bpy):
    # a tube with no caps: it has a volume to stand up by, and two open rims
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, depth=2.0, end_fill_type="NOTHING")


def test_the_topology_is_read_off_the_file(tmp_path):
    closed = cost.read(exported(tmp_path, "sphere", sphere))
    assert closed["holes"] == 0 and closed["non_manifold"] == 0
    assert closed["triangles"] > 3000
    opened = cost.read(exported(tmp_path, "sheet", sheet))
    assert opened["holes"] == 64  # its two rims, 32 edges each


def test_a_mesh_over_its_ceiling_arrives_under_it_with_the_change_recorded(tmp_path):
    source = exported(tmp_path, "sphere", sphere)
    (tmp_path / "drone.accept.toml").write_text(SPEC, encoding="utf-8")
    said = normalise.ingest(source, out=tmp_path / "drone.glb",
                            ready=tmp_path / "drone.accept.toml", root=tmp_path)
    before, after = said["ready"]["fixed"]["triangles"]
    assert before > 3000 and after <= 1500
    assert cost.read(tmp_path / "drone.glb")["triangles"] <= 1500
    record = json.loads((tmp_path / "drone.glb.prov.json").read_text("utf-8"))
    assert record["params"]["ready"]["fixed"]["triangles"] == [before, after]


def test_a_mesh_with_holes_is_refused_before_any_sitting(tmp_path):
    source = exported(tmp_path, "sheet", sheet)
    (tmp_path / "drone.accept.toml").write_text(SPEC, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        normalise.ingest(source, out=tmp_path / "drone.glb",
                         ready=tmp_path / "drone.accept.toml", root=tmp_path)
    assert refused.value.code == "mesh.not-ready"
    said = json.loads(refused.value.as_dict()["detail"])
    assert [one["measure"] for one in said["failed"]] == ["holes"]
