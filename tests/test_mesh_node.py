"""A mesh file as the starting block of a declaration (§PW100)."""

from __future__ import annotations

import pytest

from polyweave.errors import PolyweaveError
from polyweave.geometry import build as B
from polyweave.geometry import review
from polyweave.geometry import solid as S
from polyweave.geometry import voxels as V


def hull(path="hull.glb", **extra):
    return {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": {"hull": {"colour": "#808080"}, "glass": {}},
        "nodes": [{"id": "hull", "op": "mesh", "path": path, **extra}],
        "output": "hull",
        "voxels": {"cell": 1.0},
    }


def written(tmp_path, solid, name="hull.glb"):
    pytest.importorskip("bpy")
    from polyweave.normalise import write_mesh

    write_mesh(solid, tmp_path / name)
    return name


def test_a_closed_mesh_fills_solid_not_as_a_shell(tmp_path):
    name = written(tmp_path, S.plate([0, 0, 4, 4], 4.0))
    made = V.voxelize(hull(name), root=tmp_path)
    assert made["size"] == [4, 4, 4]
    assert made["count"] == 64


def test_the_mesh_wears_its_nodes_material(tmp_path):
    name = written(tmp_path, S.plate([0, 0, 4, 2], 2.0))
    made = V.voxelize(hull(name, material="hull"), root=tmp_path)
    assert [entry["name"] for entry in made["palette"]] == ["hull"]


def test_a_declaration_cuts_and_paints_the_mesh(tmp_path):
    name = written(tmp_path, S.plate([0, 0, 6, 2], 2.0))
    document = hull(name, material="hull")
    document["nodes"] += [
        {"id": "port", "op": "plate", "rect": [2, 0, 2, 2], "depth": 1, "front": 0},
        {"id": "cut", "op": "carve", "into": "hull", "cutter": "port"},
        {
            "id": "canopy",
            "op": "plate",
            "rect": [0, 0, 1, 2],
            "depth": 2,
            "material": "glass",
        },
        {"id": "ship", "op": "union", "inputs": ["cut", "canopy"]},
    ]
    document["output"] = "ship"
    made = V.voxelize(document, root=tmp_path)
    worn = [made["palette"][slot]["name"] for slot in made["cells"]["palette"]]
    assert made["count"] == 6 * 2 * 2 - 2 * 2 * 1
    assert worn.count("glass") == 4


def test_a_mesh_document_builds_the_file_as_it_is(tmp_path):
    name = written(tmp_path, S.plate([0, 0, 4, 2], 2.0))
    mesh = B.build(hull(name), root=tmp_path)["output"]
    assert len(mesh["faces"]) > 0


def test_a_path_with_no_file_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(hull("missing.glb"), root=tmp_path)
    assert refused.value.code == "geom.bad-solid"


def two_colours(tmp_path, name="painted.glb"):
    """Two unit cubes side by side along x, the left one red and the right one blue.

    Each cube's texture coordinates all land on one texel of a two-pixel image, so
    which colour a cell should wear is known before anything is voxelised.
    """
    bpy = pytest.importorskip("bpy")
    from polyweave.render import blender

    blender.reset()
    corners = [(x, y, z) for x in (0, 2) for y in (0, 2) for z in (0, 2)]
    quads = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    vertices, faces = [], []
    for shift in (0, 2):
        start = len(vertices)
        vertices += [(x + shift, y, z) for x, y, z in corners]
        faces += [tuple(start + i for i in quad) for quad in quads]
    mesh = bpy.data.meshes.new("painted")
    mesh.from_pydata(vertices, [], faces)
    layer = mesh.uv_layers.new(name="uv")
    for polygon in mesh.polygons:
        u = 0.25 if polygon.index < 6 else 0.75
        for index in polygon.loop_indices:
            layer.data[index].uv = (u, 0.5)
    image = bpy.data.images.new("paint", width=2, height=1)
    image.pixels[:] = [1, 0, 0, 1, 0, 0, 1, 1]
    material = bpy.data.materials.new("paint")
    material.use_nodes = True
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    shader = material.node_tree.nodes["Principled BSDF"]
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    mesh.materials.append(material)
    obj = bpy.data.objects.new("painted", mesh)
    bpy.context.scene.collection.objects.link(obj)
    for other in bpy.context.scene.objects:
        other.select_set(other is obj)
    bpy.ops.export_scene.gltf(
        filepath=str(tmp_path / name), use_selection=True, export_format="GLB"
    )
    return name


def test_a_textured_mesh_wears_its_textures_colours(tmp_path):
    name = two_colours(tmp_path)
    made = V.voxelize(hull(name), root=tmp_path)
    colours = {entry["colour"] for entry in made["palette"]}
    assert colours == {"#FF0000", "#0000FF"}
    names = [entry["name"] for entry in made["palette"]]
    found = made["cells"]
    worn = {
        made["palette"][slot]["colour"]
        for x, slot in zip(found["x"], found["palette"], strict=True)
        if x < made["size"][0] // 2
    }
    assert worn == {"#FF0000"}
    assert all(one.startswith("hull.") for one in names)


def test_a_texture_is_quantised_to_the_count_the_node_states(tmp_path):
    name = two_colours(tmp_path)
    made = V.voxelize(hull(name, colours=1), root=tmp_path)
    assert len(made["palette"]) == 1


def test_a_material_on_the_node_covers_the_texture(tmp_path):
    name = two_colours(tmp_path)
    made = V.voxelize(hull(name, material="hull"), root=tmp_path)
    assert [entry["name"] for entry in made["palette"]] == ["hull"]


def test_a_textured_mesh_writes_its_cubes_in_the_colours_it_found(tmp_path):
    name = two_colours(tmp_path)
    answer = V.write(hull(name), "cubes.glb", root=tmp_path, sheet=False)
    assert (tmp_path / "cubes.glb").is_file()
    assert answer["model"]["count"] == 16


def test_a_key_only_the_game_reads_rides_in_the_cells_and_not_the_mesh(tmp_path):
    name = written(tmp_path, S.plate([0, 0, 4, 2], 2.0))
    document = hull(name, material="hull")
    document["materials"]["hull"]["glow"] = 1.5
    answer = V.write(document, "cubes.glb", root=tmp_path, sheet=False)
    assert (tmp_path / "cubes.glb").is_file()
    assert answer["model"]["palette"][0]["glow"] == 1.5


def test_the_readback_names_the_file():
    said = review.describe(hull("art/hull.glb"))["reads"]
    assert said == ["hull: the mesh in art/hull.glb"]
