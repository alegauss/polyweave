"""Cells placed by hand, drawn as text (§PW95).

A drawing is read the way it looks: the first layer is the front, the first row is the
top. Each test writes a drawing whose cells can be counted by eye.
"""

from __future__ import annotations

import pytest

from polyweave.errors import PolyweaveError
from polyweave.geometry import build as B
from polyweave.geometry import review
from polyweave.geometry import voxels as V

PAINT = {"hull": {"colour": "#808080"}, "glass": {"colour": "#40C0FF"}}

COCKPIT = {
    "id": "cockpit",
    "op": "cells",
    "legend": {"h": "hull", "g": "glass"},
    "layers": [
        ["..hhhh..", ".hhhhhh.", "hhhhhhhh", ".hhhhhh.", "..hhhh.."],
        ["........", "..gggg..", ".gggggg.", "..gggg..", "........"],
        ["........", "........", "...gg...", "........", "........"],
    ],
}


def shape(*nodes, voxels=None, params=None):
    return {
        "name": "ship",
        "version": 1,
        "params": params or {},
        "materials": PAINT,
        "nodes": [dict(node) for node in nodes],
        "output": nodes[-1]["id"],
        "voxels": voxels if voxels is not None else {"cell": 1.0},
    }


def worn(made):
    names = [entry["name"] for entry in made["palette"]]
    found = made["cells"]
    return {
        (x, y, z): names[slot]
        for x, y, z, slot in zip(
            found["x"], found["y"], found["z"], found["palette"], strict=True
        )
    }


def test_a_drawing_is_read_the_way_it_looks():
    corner = {
        "id": "corner",
        "op": "cells",
        "legend": {"#": "hull"},
        "layers": [["#.", "##"], [".#", ".."]],
    }
    cells = set(worn(V.voxelize(shape(corner))))
    # The first row is the top and the first layer is the front.
    assert cells == {(0, 1, 0), (0, 0, 0), (1, 0, 0), (1, 1, 1)}


def test_each_character_wears_what_its_legend_names():
    made = V.voxelize(shape(COCKPIT))
    counted = list(worn(made).values())
    assert counted.count("hull") == 4 + 6 + 8 + 6 + 4
    assert counted.count("glass") == 4 + 6 + 4 + 2
    assert made["size"] == [8, 5, 3]


def test_the_readback_counts_what_was_drawn():
    said = review.describe(shape(COCKPIT))["reads"]
    assert said == ["cockpit: 3 layers of 8 by 5, 44 cells in hull and glass"]


def test_a_drawing_paints_over_a_hull_declared_before_it():
    hull = {
        "id": "hull",
        "op": "plate",
        "rect": [0, 0, 8, 5],
        "depth": 3.0,
        "material": "hull",
    }
    stripe = {
        "id": "stripe",
        "op": "cells",
        "legend": {"g": "glass"},
        "layers": [["........", "........", "gggggggg", "........", "........"]],
    }
    ship = {"id": "ship", "op": "union", "inputs": ["hull", "stripe"]}
    made = V.voxelize(shape(hull, stripe, ship))
    cells = worn(made)
    assert made["count"] == 8 * 5 * 3
    assert cells[(3, 2, 0)] == "glass"
    assert cells[(3, 2, 1)] == "hull"
    assert cells[(3, 3, 0)] == "hull"


def test_a_drawing_can_be_carved():
    block = {
        "id": "block",
        "op": "cells",
        "legend": {"#": "hull"},
        "layers": [["###", "###", "###"]],
    }
    vent = {
        "id": "vent",
        "op": "primitive",
        "kind": "cube",
        "size": 1.0,
        "at": [1.5, 1.5, 0.5],
    }
    cut = {"id": "cut", "op": "carve", "into": "block", "cutter": "vent"}
    made = V.voxelize(shape(block, vent, cut))
    assert made["count"] == 8
    assert (1, 1, 0) not in worn(made)


def test_placed_cells_land_on_whole_cells_of_the_model():
    hull = {"id": "hull", "op": "plate", "rect": [0, 0, 3.5, 1], "depth": 1.0}
    mark = {
        "id": "mark",
        "op": "cells",
        "legend": {"#": "glass"},
        "layers": [["#"]],
        "at": [5, 0, 0],
    }
    both = {"id": "both", "op": "union", "inputs": ["hull", "mark"]}
    made = V.voxelize(shape(hull, mark, both))
    assert made["origin"] == [0.0, 0.0, 0.0]
    assert worn(made)[(5, 0, 0)] == "glass"


def test_a_row_that_spells_a_parameter_stays_a_drawing():
    dot = {"id": "dot", "op": "cells", "legend": {"a": "hull"}, "layers": [["a"]]}
    made = V.voxelize(shape(dot, params={"a": 3}))
    assert made["count"] == 1


@pytest.mark.parametrize(
    "node",
    [
        {"legend": {"#": "hull"}, "layers": [["##", "#"]]},
        {"legend": {"#": "hull"}, "layers": [["##"], ["##", "##"]]},
        {"legend": {"#": "hull"}, "layers": [["#x"]]},
        {"legend": {"#": "hull"}, "layers": []},
    ],
)
def test_a_drawing_that_is_not_a_block_is_refused(node):
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(shape({"id": "bad", "op": "cells", **node}))
    assert refused.value.code == "geom.bad-cells"


def test_a_drawing_needs_a_size_that_does_not_wait_for_the_bounds():
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(shape(COCKPIT, voxels={"across": 16}))
    assert refused.value.code == "geom.bad-cells"
    made = V.voxelize(shape(dict(COCKPIT, cell=0.5), voxels={"across": 16}))
    assert made["size"] == [16, 10, 6]


def test_a_drawing_builds_as_cubes_in_a_mesh_document():
    document = shape(COCKPIT)
    found = B.build(document)
    mesh = found["output"]
    assert {one["material"] for one in mesh["groups"]} == {"hull", "glass"}
    xs = [point[0] for point in mesh["vertices"]]
    assert (min(xs), max(xs)) == (0.0, 8.0)


def test_a_legend_naming_an_undeclared_material_is_warned_about():
    document = shape(dict(COCKPIT, legend={"h": "hull", "g": "glas"}))
    said = review.warn(document)
    assert any("draws 'g' in glas" in one for one in said)
