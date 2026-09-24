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


def test_the_readback_names_the_file():
    said = review.describe(hull("art/hull.glb"))["reads"]
    assert said == ["hull: the mesh in art/hull.glb"]
