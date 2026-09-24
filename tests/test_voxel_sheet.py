"""Four views of a voxel model, drawn from the cells with no renderer (§PW94).

The orientation is what a wrong sheet gets wrong silently, so each view is checked on a
shape whose answer is written down: which cell is nearest, which side it lands on.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from polyweave.geometry import voxel_sheet as VS
from polyweave.geometry import voxels as V

RED, BLUE = "#FF0000", "#0000FF"


def model(*nodes, materials=None):
    document = {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": materials or {},
        "nodes": [dict(node) for node in nodes],
        "output": nodes[-1]["id"],
        "voxels": {"cell": 1.0},
    }
    return V.voxelize(document)


def views(made):
    filled, slot, _ = VS._grids(made)
    return VS._orthographic(filled, slot)


def box(name, x, y, z, size=1, colour=None):
    """A cube of `size` cells with its low corner at (x, y, z)."""
    node = {
        "id": name,
        "op": "plate",
        "rect": [x, y, size, size],
        "depth": size,
        "front": z,
    }
    if colour:
        node["material"] = colour
    return node


def test_the_front_view_shows_the_outline_the_right_way_up():
    ell = {
        "id": "ell",
        "op": "prism",
        "depth": 1.0,
        "outline": {"points": [[0, 0], [3, 0], [3, 1], [1, 1], [1, 3], [0, 3]]},
    }
    front = views(model(ell))["front"]
    assert front.shape == (3, 3)
    # Row 0 is the top of the picture, so the L's long foot is the last row.
    assert (front >= 0).tolist() == [
        [True, False, False],
        [True, False, False],
        [True, True, True],
    ]


def test_the_nearest_cell_is_the_one_seen():
    paint = {"near": {"colour": RED}, "far": {"colour": BLUE}}
    near = box("front_cell", 0, 0, 0, colour="near")
    far = box("back_cell", 0, 0, 1, colour="far")
    both = {"id": "both", "op": "union", "inputs": ["front_cell", "back_cell"]}
    made = model(near, far, both, materials=paint)
    names = [entry["name"] for entry in made["palette"]]
    front = views(made)["front"]
    assert names[front[0, 0]] == "near"


def test_the_side_view_looks_in_from_plus_x_with_the_back_on_the_left():
    paint = {"back": {"colour": BLUE}, "front": {"colour": RED}}
    back = box("back_cell", 0, 0, 2, colour="back")
    front = box("front_cell", 0, 0, 0, colour="front")
    both = {"id": "both", "op": "union", "inputs": ["back_cell", "front_cell"]}
    made = model(back, front, both, materials=paint)
    names = [entry["name"] for entry in made["palette"]]
    side = views(made)["side"]
    assert side.shape == (1, 3)
    assert names[side[0, 0]] == "back"
    assert names[side[0, -1]] == "front"


def test_the_top_view_puts_the_front_at_the_bottom():
    paint = {"back": {"colour": BLUE}, "front": {"colour": RED}}
    back = box("back_cell", 0, 0, 2, colour="back")
    front = box("front_cell", 0, 0, 0, colour="front")
    both = {"id": "both", "op": "union", "inputs": ["back_cell", "front_cell"]}
    made = model(back, front, both, materials=paint)
    names = [entry["name"] for entry in made["palette"]]
    top = views(made)["top"]
    assert top.shape == (3, 1)
    assert names[top[0, 0]] == "back"
    assert names[top[-1, 0]] == "front"


def test_a_colour_is_read_however_the_material_spells_it():
    assert VS._rgb({"name": "a", "colour": "#10FF20"}) == (16, 255, 32)
    assert VS._rgb({"name": "a", "color": [1.0, 0.5, 0.0]}) == (255, 128, 0)
    assert VS._rgb({"name": "a", "base_color": [0.0, 0.0, 1.0, 1.0]}) == (0, 0, 255)
    assert VS._rgb({"name": ""}) == VS.UNPAINTED


def test_the_isometric_view_shades_its_sides_darker_than_its_top():
    made = model(
        box("cube", 0, 0, 0, size=4, colour="paint"),
        materials={"paint": {"colour": "#C8C8C8"}},
    )
    filled, slot, _ = VS._grids(made)
    colours = np.asarray([VS._rgb(entry) for entry in made["palette"]])
    picture = np.asarray(VS._isometric(filled, slot, colours, 8))
    seen = {tuple(p[:3]) for p in picture.reshape(-1, 4) if p[3] == 255}
    assert (200, 200, 200) in seen  # the top keeps its colour
    assert (156, 156, 156) in seen  # the right side, at 0.78
    assert (120, 120, 120) in seen  # the front, at 0.6


def test_a_write_puts_the_sheet_beside_the_cells(tmp_path):
    document = {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": {"hull": {"colour": "#808080"}},
        "nodes": [
            {
                "id": "hull",
                "op": "plate",
                "rect": [0, 0, 6, 3],
                "depth": 2,
                "material": "hull",
            },
        ],
        "output": "hull",
        "voxels": {"cell": 1.0},
    }
    answer = V.write(
        document,
        "ship.glb",
        root=tmp_path,
        mesh=False,
        pixels=4,
        grid=True,
        labels=True,
    )
    where = tmp_path / "ship.voxels.png"
    assert answer["sheet"] == str(where)
    with Image.open(where) as picture:
        assert picture.width > 4 * (6 + 6 + 2)
        grey = np.asarray(picture.convert("RGB")).reshape(-1, 3)
        assert any((grey == (128, 128, 128)).all(axis=1))


def test_no_sheet_is_written_when_it_is_not_asked_for(tmp_path):
    document = {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": {},
        "nodes": [{"id": "box", "op": "primitive", "kind": "cube", "size": 2}],
        "output": "box",
        "voxels": {"cell": 1.0},
    }
    answer = V.write(document, "box.glb", root=tmp_path, mesh=False, sheet=False)
    assert "sheet" not in answer
    assert not (tmp_path / "box.voxels.png").exists()
