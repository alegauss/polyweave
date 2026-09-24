"""How a voxel model breaks, planned at build time (§PW99)."""

from __future__ import annotations

import pytest

from polyweave.errors import PolyweaveError
from polyweave.geometry import fracture as FR
from polyweave.geometry import voxels as V


def block(width=8, height=4, depth=2, fracture=None, nodes=None):
    document = {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": {"hull": {}, "glass": {}},
        "nodes": nodes
        or [
            {
                "id": "hull",
                "op": "plate",
                "rect": [0, 0, width, height],
                "depth": depth,
                "material": "hull",
            }
        ],
        "output": (nodes or [{"id": "hull"}])[-1]["id"],
        "voxels": {"cell": 1.0},
    }
    if fracture is not None:
        document["voxels"]["fracture"] = fracture
    return document


def test_every_cell_lands_in_one_fragment_of_the_size_asked_for():
    made = V.voxelize(block(fracture={"size": [3, 6], "seed": 1}))
    plan = made["fracture"]
    listed = sorted(one for fragment in plan["fragments"] for one in fragment["cells"])
    assert listed == list(range(made["count"]))
    assert all(fragment["mass"] <= 6 for fragment in plan["fragments"])
    assert (
        sum(fragment["mass"] >= 3 for fragment in plan["fragments"])
        >= len(plan["fragments"]) - 1
    )
    assert plan["count"] < made["count"]


def test_a_fragment_is_connected():
    made = V.voxelize(block(fracture={"size": [2, 5], "seed": 3}))
    found = made["cells"]
    cells = list(zip(found["x"], found["y"], found["z"], strict=True))
    for fragment in made["fracture"]["fragments"]:
        members = {cells[one] for one in fragment["cells"]}
        start = next(iter(members))
        reached, frontier = {start}, [start]
        while frontier:
            x, y, z = frontier.pop()
            for step in FR._FACES:
                near = (x + step[0], y + step[1], z + step[2])
                if near in members and near not in reached:
                    reached.add(near)
                    frontier.append(near)
        assert reached == members


def test_the_same_seed_breaks_the_same_way_and_another_does_not():
    one = V.voxelize(block(fracture={"size": [3, 6], "seed": 7}))["fracture"]
    same = V.voxelize(block(fracture={"size": [3, 6], "seed": 7}))["fracture"]
    other = V.voxelize(block(fracture={"size": [3, 6], "seed": 8}))["fracture"]
    assert one == same
    assert one["fragments"] != other["fragments"]


def test_a_fragment_does_not_cross_a_material():
    nodes = [
        {
            "id": "hull",
            "op": "plate",
            "rect": [0, 0, 8, 4],
            "depth": 2,
            "material": "hull",
        },
        {
            "id": "canopy",
            "op": "plate",
            "rect": [3, 1, 2, 2],
            "depth": 2,
            "material": "glass",
        },
        {"id": "ship", "op": "union", "inputs": ["hull", "canopy"]},
    ]
    made = V.voxelize(block(nodes=nodes, fracture={"size": [2, 20], "seed": 0}))
    slots = made["cells"]["palette"]
    for fragment in made["fracture"]["fragments"]:
        assert len({slots[one] for one in fragment["cells"]}) == 1
    glass = [f for f in made["fracture"]["fragments"] if f["palette"] == 1]
    # The canopy is eight cells under the largest fragment, so it flies off whole.
    assert [f["mass"] for f in glass] == [8]


def test_depth_counts_in_from_the_surface():
    made = V.voxelize(block(width=5, height=5, depth=5, fracture={"size": [1, 1]}))
    found = made["cells"]
    depth = dict(
        zip(
            zip(found["x"], found["y"], found["z"], strict=True),
            found["depth"],
            strict=True,
        )
    )
    assert depth[(0, 0, 0)] == 1
    assert depth[(1, 1, 1)] == 2
    assert depth[(2, 2, 2)] == 3
    assert made["fracture"]["deepest"] == 3


def test_a_fragment_says_where_its_middle_is():
    made = V.voxelize(block(width=2, height=1, depth=1, fracture={"size": [2, 2]}))
    (fragment,) = made["fracture"]["fragments"]
    assert fragment["centre"] == [1.0, 0.5, 0.5]
    assert fragment["mass"] == 2


@pytest.mark.parametrize("size", [None, [0, 3], [4, 2], [1.5, 3], "big"])
def test_a_size_no_fragment_can_have_is_refused(size):
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(block(fracture={"size": size}))
    assert refused.value.code == "geom.bad-fracture"


def test_no_plan_is_made_unless_one_is_asked_for():
    made = V.voxelize(block())
    assert "fracture" not in made
    assert "depth" not in made["cells"]
