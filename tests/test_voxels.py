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


def test_a_drum_stood_on_y_fills_what_the_turned_unit_cylinder_did():
    """§PW233: the plinth once was a unit cylinder scaled and turned a quarter."""
    unit = {"id": "unit", "op": "primitive", "kind": "cylinder", "size": 1.0}
    turned = {
        "id": "plinth",
        "op": "transform",
        "of": "unit",
        "scale": [12, 12, 1.5],
        "rotate": [90, 0, 0],
    }
    drum = {
        "id": "plinth",
        "op": "primitive",
        "kind": "cylinder",
        "size": [12, 1.5, 12],
        "axis": "y",
    }
    before = V.voxelize(shape(unit, turned, voxels={"cell": 1.0}))
    after = V.voxelize(shape(drum, voxels={"cell": 1.0}))
    assert after["size"] == before["size"]
    assert abs(after["count"] - before["count"]) <= 4


def test_a_frustum_holds_its_own_volume():
    hull = {
        "id": "hull",
        "op": "primitive",
        "kind": "frustum",
        "bottom": 20.0,
        "top": 8.0,
        "height": 6.0,
    }
    made = V.voxelize(shape(hull, voxels={"cell": 0.5}))
    volume = math.pi * 6.0 / 3 * (10**2 + 10 * 4 + 4**2)
    assert made["count"] * 0.5**3 == pytest.approx(volume, rel=0.05)
    assert made["size"] == [40, 40, 12]


BODY = {"id": "body", "op": "primitive", "kind": "sphere", "size": 12.0}
BAND = {"id": "band", "op": "plate", "rect": [-8, -1, 16, 2], "depth": 16, "front": -8}
SEAM = {"glow": {"colour": "#FF2020"}}


def test_a_paint_repaints_the_body_and_adds_no_cell():
    """§PW237: a band round a sphere, without the slab sticking out of it."""
    paint = {
        "id": "seam",
        "op": "paint",
        "on": "body",
        "where": "band",
        "material": "glow",
    }
    made = V.voxelize(shape(BODY, BAND, paint, voxels={"cell": 1.0}, materials=SEAM))
    bare = V.voxelize(shape(BODY, voxels={"cell": 1.0}))
    assert cells_of(made) == cells_of(bare)
    names = [entry["name"] for entry in made["palette"]]
    worn = [names[slot] for slot in made["cells"]["palette"]]
    glowing = {c for c, w in zip(cells_of_list(made), worn, strict=True) if w == "glow"}
    assert glowing and all(abs(y - 5.5) <= 1 for _, y, _ in glowing)
    assert len(glowing) < made["count"] / 3


def cells_of_list(model):
    found = model["cells"]
    return list(zip(found["x"], found["y"], found["z"], strict=True))


def test_a_paint_is_the_two_carves_it_replaces_cell_for_cell():
    outside = {"id": "outside", "op": "carve", "into": "body", "cutter": "band"}
    within = {
        "id": "within",
        "op": "carve",
        "into": "body",
        "cutter": "outside",
        "material": "glow",
    }
    trick = {"id": "seamed", "op": "union", "inputs": ["body", "within"]}
    paint = {
        "id": "seamed",
        "op": "paint",
        "on": "body",
        "where": ["band"],
        "material": "glow",
    }
    was = V.voxelize(
        shape(BODY, BAND, outside, within, trick, voxels={"cell": 1.0}, materials=SEAM)
    )
    now = V.voxelize(shape(BODY, BAND, paint, voxels={"cell": 1.0}, materials=SEAM))

    def worn(model):
        names = [entry["name"] for entry in model["palette"]]
        return dict(
            zip(
                cells_of_list(model),
                (names[slot] for slot in model["cells"]["palette"]),
                strict=True,
            )
        )

    assert worn(now) == worn(was)


def test_a_paint_whose_mark_sits_between_cell_centres_is_named():
    """§PW252: the Viglet V's blush sat between cell centres, and built clean."""
    # Cell centres sit at .5 steps on this grid, so 0.6 to 1.4 holds none of them.
    between = {"id": "blush_marks", "op": "plate", "rect": [-3, 0.6, 2, 0.8],
               "depth": 12, "front": -6}
    paint = {"id": "face", "op": "paint", "on": "body",
             "where": ["band", "blush_marks"], "material": "glow"}
    made = V.voxelize(
        shape(BODY, BAND, between, paint, voxels={"cell": 1.0}, materials=SEAM)
    )
    named = [f for f in made["checks"]["findings"] if f["check"] == "paint"]
    assert [(f["node"], f["member"]) for f in named] == [("face", "blush_marks")]
    assert "sits between them" in named[0]["says"]


def mullions(*middles):
    """Upright mullions one cell wide on x, one per middle, painted on the body."""
    pieces = [
        {"id": f"m{i}", "op": "primitive", "kind": "cube", "size": [1.0, 12.0, 16.0],
         "at": [x, 0, 0]}
        for i, x in enumerate(middles)
    ]
    row = {"id": "mullions_x", "op": "union", "inputs": [p["id"] for p in pieces]}
    paint = {"id": "trim", "op": "paint", "on": "body", "where": "mullions_x",
             "material": "glow"}
    return V.voxelize(
        shape(BODY, *pieces, row, paint, voxels={"cell": 1.0}, materials=SEAM)
    )


def test_a_one_cell_region_whose_faces_fall_on_cell_centres_is_named():
    """§PW262: the citadel's mullions, centred on cell boundaries, took both cells."""
    made = mullions(0.0, 3.0)
    named = [f for f in made["checks"]["findings"] if f.get("axis")]
    assert [(f["node"], f["member"], f["axis"]) for f in named] == [
        ("trim", "mullions_x", "x")]
    assert "is 1 wide on x and covers 2 cells" in named[0]["says"]
    assert "move it by 0.5 on x" in named[0]["says"]


def filled_columns(node):
    """The columns a shape fills on the sphere's grid, whose centres sit at x.5."""
    both = {"id": "both", "op": "union", "inputs": ["body", node["id"]]}
    made = V.voxelize(shape(BODY, node, both, voxels={"cell": 1.0}, output="both"))
    mine = made["nodes"].index(node["id"])
    return sorted({x for x, owner in zip(made["cells"]["x"], made["cells"]["node"],
                                         strict=True) if owner == mine})


def test_a_plate_and_a_cube_over_one_box_fill_the_same_cells():
    """§PW274: faces on cell centres, a plate took one column and a cube two."""
    cube = {"id": "c", "op": "primitive", "kind": "cube", "size": [1.0, 4.0, 4.0],
            "at": [0, 0, -8]}
    plate = {"id": "p", "op": "plate", "rect": [-0.5, -2, 1, 4], "depth": 4,
             "front": -10}
    assert filled_columns(cube) == filled_columns(plate)
    assert len(filled_columns(plate)) == 2


def test_a_one_cell_region_on_one_cell_says_nothing():
    made = mullions(0.5, 3.5)
    assert [f for f in made["checks"]["findings"] if f.get("axis")] == []


def test_a_paint_that_paints_its_cells_says_nothing():
    paint = {"id": "seam", "op": "paint", "on": "body", "where": "band",
             "material": "glow"}
    made = V.voxelize(shape(BODY, BAND, paint, voxels={"cell": 1.0}, materials=SEAM))
    assert [f for f in made["checks"]["findings"] if f["check"] == "paint"] == []


def test_a_material_no_cell_wears_is_named():
    made = V.voxelize(
        shape(BODY, voxels={"cell": 1.0}, materials={"glow": {}, "blush": {}})
    )
    unworn = sorted(
        f["material"] for f in made["checks"]["findings"] if f["check"] == "material"
    )
    assert unworn == ["blush", "glow"]


def test_a_paint_that_does_not_say_where_is_refused():
    paint = {"id": "seam", "op": "paint", "on": "body", "material": "glow"}
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(shape(BODY, paint, voxels={"cell": 1.0}, materials=SEAM))
    assert refused.value.code == "geom.bad-solid"


def test_a_paint_reads_back_as_what_it_does():
    from polyweave.geometry import review

    paint = {
        "id": "seam",
        "op": "paint",
        "on": "body",
        "where": "band",
        "material": "glow",
    }
    found = review.describe(shape(BODY, BAND, paint, materials=SEAM))
    said = next(one["says"] for one in found["nodes"] if one["id"] == "seam")
    assert said == "body painted glow where band"


def test_a_paint_is_refused_on_triangles(tmp_path):
    from polyweave.geometry import build as B

    paint = {
        "id": "seam",
        "op": "paint",
        "on": "body",
        "where": "band",
        "material": "glow",
    }
    with pytest.raises(PolyweaveError) as refused:
        B.write(shape(BODY, BAND, paint, materials=SEAM), "seam.glb", root=tmp_path)
    assert refused.value.code == "geom.bad-voxels"
    assert "[voxels]" in refused.value.remedy


def test_a_torus_leaves_its_middle_empty():
    ring = {"id": "ring", "op": "primitive", "kind": "torus", "major": 6.0,
            "minor": 2.0, "axis": "x"}
    made = V.voxelize(shape(ring, voxels={"cell": 1.0}))
    assert made["size"] == [4, 16, 16]
    assert made["count"] == pytest.approx(2 * math.pi**2 * 6 * 2**2, rel=0.08)
    assert (2, 8, 8) not in cells_of(made)


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
