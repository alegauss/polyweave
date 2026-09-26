"""Two voxel models compared cell by cell (§PW240)."""

from __future__ import annotations

import json

import pytest

from polyweave import cli
from polyweave.errors import PolyweaveError
from polyweave.geometry import voxel_compare as C
from polyweave.geometry import voxels as V

PAINT = {"hull": {"colour": "#808080"}, "glass": {"colour": "#40C0FF"}}


def ship(*extra, materials=PAINT):
    nodes = [
        {"id": "hull", "op": "plate", "rect": [0, 0, 4, 2], "depth": 1,
         "material": "hull"},
        *extra,
    ]
    output = nodes[-1]["id"]
    return {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": materials,
        "nodes": nodes,
        "output": output,
        "voxels": {"cell": 1.0},
    }


def drawn(rows):
    """The same hull drawn by hand as cells, the rewrite Spinhold had to prove."""
    return {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": PAINT,
        "nodes": [
            {"id": "art", "op": "cells", "legend": {"#": "hull"}, "layers": [rows]}
        ],
        "output": "art",
        "voxels": {"cell": 1.0},
    }


def test_a_rewrite_that_builds_the_same_model_is_the_same():
    found = C.compare(V.voxelize(ship()), V.voxelize(drawn(["####", "####"])))
    assert found["same"] is True
    assert found["says"] == "the same 8 cells, each wearing the same material"


def test_an_empty_row_moves_the_grid_and_not_the_cells():
    """The old drawing carried an empty row; the cells are still the same."""
    found = C.compare(
        V.voxelize(drawn(["....", "####", "####"])), V.voxelize(ship())
    )
    assert found["same"] is True
    assert found["grid"]["differs"] is True
    assert found["grid"]["first"]["size"] != found["grid"]["second"]["size"]
    assert "the grids differ" in found["says"]


def test_a_repainted_cell_is_named_by_material_not_slot():
    canopy = {"id": "canopy", "op": "plate", "rect": [1, 1, 1, 1], "depth": 1,
              "material": "glass"}
    both = {"id": "ship", "op": "union", "inputs": ["hull", "canopy"]}
    found = C.compare(V.voxelize(ship()), V.voxelize(ship(canopy, both)))
    assert found["same"] is False
    assert found["repainted"]["count"] == 1
    moved = found["repainted"]["at"][0]
    assert (moved["was"], moved["now"]) == ("hull", "glass")
    assert moved["at"] == [1.5, 1.5, 0.5]


def test_a_cell_only_in_one_is_named_where_it_sits():
    fin = {"id": "fin", "op": "plate", "rect": [4, 0, 1, 1], "depth": 1,
           "material": "hull"}
    both = {"id": "ship", "op": "union", "inputs": ["hull", "fin"]}
    found = C.compare(V.voxelize(ship()), V.voxelize(ship(fin, both)))
    assert found["only_first"]["count"] == 0
    assert found["only_second"] == {"count": 1, "at": [[4.5, 0.5, 0.5]]}


def test_cells_of_different_sizes_are_not_compared():
    coarse = V.voxelize(ship(), cell=2.0)
    found = C.compare(V.voxelize(ship()), coarse)
    assert found["same"] is False
    assert "different sizes" in found["says"]


def test_the_operation_compares_a_built_file_with_a_declaration(tmp_path):
    written = V.write(ship(), "ship.glb", root=tmp_path, mesh=False, sheet=False)
    (tmp_path / "ship.toml").write_text(
        'name = "ship"\nversion = 1\noutput = "art"\n\n[params]\n\n[materials.hull]\n'
        'colour = "#808080"\n\n[voxels]\ncell = 1.0\n\n[[nodes]]\nid = "art"\n'
        'op = "cells"\nlegend = { "#" = "hull" }\nlayers = [["####", "####"]]\n',
        encoding="utf-8",
    )
    found = cli.compare_two(written["voxels"], "ship.toml", root=str(tmp_path))
    assert found["same"] is True, found["says"]


def test_a_path_that_is_no_model_is_refused(tmp_path):
    (tmp_path / "other.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        C.compared("other.json", "missing.json", root=tmp_path)
    assert refused.value.code == "geom.bad-voxels"
