"""A declaration answered as cells (§PW93).

Every shape here states the numbers its assertion depends on, so a count is arithmetic
and not a picture somebody once accepted.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from polyweave import geometry as G
from polyweave.errors import PolyweaveError
from polyweave.geometry import voxels as V


def shape(*nodes, output=None, voxels=None, materials=None, params=None):
    document = {
        "name": "ship",
        "version": 1,
        "params": params or {},
        "materials": materials or {},
        "nodes": [dict(node) for node in nodes],
        "output": output or nodes[-1]["id"],
    }
    if voxels is not None:
        document["voxels"] = voxels
    return document


def cells_of(model):
    found = model["cells"]
    return set(zip(found["x"], found["y"], found["z"], strict=True))


CUBE = {"id": "box", "op": "primitive", "kind": "cube", "size": 4.0}


# -- the grid --------------------------------------------------------------------------


def test_a_cube_fills_every_cell_of_its_own_grid():
    made = V.voxelize(shape(CUBE, voxels={"cell": 1.0}))
    assert made["size"] == [4, 4, 4]
    assert made["count"] == 64
    assert made["origin"] == [-2.0, -2.0, -2.0]


def test_across_sets_the_cell_from_the_longest_side():
    plate = {"id": "hull", "op": "plate", "rect": [0, 0, 16, 7], "depth": 5.0}
    made = V.voxelize(shape(plate, voxels={"across": 16}))
    assert made["cell"] == pytest.approx(1.0)
    assert made["size"] == [16, 7, 5]
    assert made["count"] == 16 * 7 * 5
    assert made["says"] == "a voxel model 16 by 7 by 5, 560 cells in 1 material"


def test_a_call_overrides_the_documents_own_cell():
    made = V.voxelize(shape(CUBE, voxels={"cell": 1.0}), cell=2.0)
    assert made["size"] == [2, 2, 2]


def test_a_cell_can_be_an_expression_over_the_parameters():
    made = V.voxelize(shape(CUBE, voxels={"cell": "unit / 2"}, params={"unit": 2.0}))
    assert made["cell"] == 1.0


def test_a_sphere_holds_about_its_own_volume():
    ball = {"id": "ball", "op": "primitive", "kind": "sphere", "size": 20.0}
    made = V.voxelize(shape(ball, voxels={"cell": 1.0}))
    assert made["count"] == pytest.approx(4 / 3 * math.pi * 10**3, rel=0.05)


@pytest.mark.parametrize(
    "voxels",
    [{}, {"cell": 1.0, "across": 4}, {"cell": 0}, {"across": -2}],
)
def test_a_cell_that_is_not_one_clear_size_is_refused(voxels):
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(shape(CUBE, voxels=voxels))
    assert refused.value.code == "geom.bad-voxels"


# -- the ops answer on the grid --------------------------------------------------------


def test_a_carve_takes_its_cutter_out():
    cutter = {"id": "hole", "op": "primitive", "kind": "cube", "size": 2.0}
    cut = {"id": "cut", "op": "carve", "into": "box", "cutter": "hole"}
    made = V.voxelize(shape(CUBE, cutter, cut, voxels={"cell": 1.0}))
    assert made["count"] == 64 - 8
    assert (1, 1, 1) not in cells_of(made)


def test_a_transform_turns_and_scales_the_cells_it_asks_for():
    plate = {"id": "hull", "op": "plate", "rect": [0, 0, 6, 2], "depth": 1.0}
    turned = {"id": "turned", "op": "transform", "of": "hull", "rotate": [0, 0, 90]}
    made = V.voxelize(shape(plate, turned, voxels={"cell": 1.0}))
    assert made["size"] == [2, 6, 1]
    assert made["count"] == 12

    grown = {"id": "grown", "op": "transform", "of": "hull", "scale": 2}
    made = V.voxelize(shape(plate, grown, voxels={"cell": 1.0}))
    assert made["size"] == [12, 4, 2]
    assert made["count"] == 96


def test_a_repeat_places_every_instance():
    row = {
        "id": "row",
        "op": "primitive",
        "kind": "cube",
        "size": 1.0,
        "repeat": [{"var": "i", "from": 0, "to": 2}],
        "at": ["i * 2", 0, 0],
    }
    made = V.voxelize(shape(row, voxels={"cell": 1.0}))
    assert made["size"] == [5, 1, 1]
    assert made["count"] == 3
    assert sorted(x for x, _, _ in cells_of(made)) == [0, 2, 4]


def test_an_op_with_no_test_of_its_own_is_read_off_its_mesh():
    ring = {"id": "ring", "op": "annulus", "outer": 10.0, "inner": 4.0, "depth": 2.0}
    made = V.voxelize(shape(ring, voxels={"cell": 0.5}))
    volume = math.pi * (10**2 - 4**2) * 2 / 0.5**3
    assert made["count"] == pytest.approx(volume, rel=0.05)
    middle = [n // 2 for n in made["size"]]
    assert tuple(middle) not in cells_of(made)


# -- what each cell wears --------------------------------------------------------------


HULL = {
    "id": "hull",
    "op": "plate",
    "rect": [0, 0, 8, 4],
    "depth": 2.0,
    "material": "hull",
}
CANOPY = {
    "id": "canopy",
    "op": "plate",
    "rect": [3, 1, 2, 2],
    "depth": 2.0,
    "material": "glass",
}
PAINT = {"hull": {"colour": "#808080"}, "glass": {"colour": "#40C0FF", "glow": 2.0}}


def wearing(made):
    names = [entry["name"] for entry in made["palette"]]
    found = made["cells"]
    return {
        (x, y, z): names[slot]
        for x, y, z, slot in zip(
            found["x"], found["y"], found["z"], found["palette"], strict=True
        )
    }


def test_a_later_node_paints_over_an_earlier_one():
    ship = {"id": "ship", "op": "union", "inputs": ["hull", "canopy"]}
    made = V.voxelize(shape(HULL, CANOPY, ship, voxels={"cell": 1.0}, materials=PAINT))
    worn = wearing(made)
    assert made["count"] == 8 * 4 * 2
    assert worn[(4, 2, 0)] == "glass"
    assert worn[(0, 0, 0)] == "hull"
    assert sum(1 for one in worn.values() if one == "glass") == 2 * 2 * 2
    canopy = made["nodes"].index("canopy")
    assert (
        made["cells"]["node"][list(cells_of_in_order(made)).index((4, 2, 0))] == canopy
    )


def cells_of_in_order(made):
    found = made["cells"]
    return zip(found["x"], found["y"], found["z"], strict=True)


def test_declared_first_it_is_painted_over_instead():
    ship = {"id": "ship", "op": "union", "inputs": ["canopy", "hull"]}
    made = V.voxelize(shape(CANOPY, HULL, ship, voxels={"cell": 1.0}, materials=PAINT))
    assert set(wearing(made).values()) == {"hull"}


def test_the_palette_carries_a_materials_keys_through_untouched():
    ship = {"id": "ship", "op": "union", "inputs": ["hull", "canopy"]}
    made = V.voxelize(shape(HULL, CANOPY, ship, voxels={"cell": 1.0}, materials=PAINT))
    assert made["palette"] == [
        {"name": "hull", "colour": "#808080"},
        {"name": "glass", "colour": "#40C0FF", "glow": 2.0},
    ]


def test_a_cell_nothing_paints_wears_the_unnamed_entry():
    made = V.voxelize(shape(CUBE, voxels={"cell": 1.0}))
    assert made["palette"] == [{"name": ""}]


# -- the cubes and the files -----------------------------------------------------------


def test_the_cubes_keep_only_the_faces_somebody_can_see():
    one = V.cubes(V.voxelize(shape(dict(CUBE, size=1.0), voxels={"cell": 1.0})))
    assert len(one["faces"]) == 6
    two = {"id": "two", "op": "plate", "rect": [0, 0, 2, 1], "depth": 1.0}
    pair = V.cubes(V.voxelize(shape(two, voxels={"cell": 1.0})))
    assert len(pair["faces"]) == 10


def test_every_cube_face_points_out_of_the_cell():
    made = V.voxelize(shape(dict(CUBE, size=1.0), voxels={"cell": 1.0}))
    mesh = V.cubes(made)
    points = np.asarray(mesh["vertices"])
    middle = points.mean(axis=0)
    for face in mesh["faces"]:
        a, b, c = (points[i] for i in face[:3])
        normal = np.cross(b - a, c - a)
        assert normal @ (points[list(face)].mean(axis=0) - middle) > 0


def test_the_cubes_are_grouped_by_what_they_wear():
    ship = {"id": "ship", "op": "union", "inputs": ["hull", "canopy"]}
    made = V.voxelize(shape(HULL, CANOPY, ship, voxels={"cell": 1.0}, materials=PAINT))
    groups = V.cubes(made)["groups"]
    assert [one["material"] for one in groups] == ["hull", "glass"]
    assert groups[0]["faces"][1] == groups[1]["faces"][0]


def test_the_cells_are_written_beside_the_mesh(tmp_path):
    answer = V.write(
        shape(CUBE, voxels={"cell": 2.0}), "out/box.glb", root=tmp_path, mesh=False
    )
    written = json.loads(
        (tmp_path / "out" / "box.voxels.json").read_text(encoding="utf-8")
    )
    assert written["size"] == [2, 2, 2]
    assert written["count"] == 8
    assert answer["says"] == "a voxel model 2 by 2 by 2, 8 cells in 1 material"
    assert "artefact" not in answer


def test_a_voxel_document_reads_its_table_and_one_without_has_none(tmp_path):
    (tmp_path / "ship.toml").write_text(
        'name = "ship"\noutput = "box"\n\n[voxels]\nacross = 8\n\n'
        '[[nodes]]\nid = "box"\nop = "primitive"\nkind = "cube"\nsize = 4\n',
        encoding="utf-8",
    )
    document = G.read("ship.toml", root=tmp_path)
    assert document["voxels"] == {"across": 8}
    assert "voxels" not in G.parse(
        {"name": "x", "nodes": [{"id": "a", "op": "primitive"}]}
    )


def test_build_write_answers_cells_for_a_voxel_document(tmp_path):
    pytest.importorskip("bpy")
    from polyweave.geometry import build as B

    answer = B.write(shape(CUBE, voxels={"cell": 1.0}), "box.glb", root=tmp_path)
    assert (tmp_path / "box.glb").is_file()
    assert (tmp_path / "box.voxels.json").is_file()
    assert answer["model"]["count"] == 64
