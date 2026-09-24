"""One half declared and the other made from it (§PW96).

Every half here sits on one side of its plane, so where the whole ends up is arithmetic.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave.errors import PolyweaveError
from polyweave.geometry import build as B
from polyweave.geometry import review
from polyweave.geometry import voxels as V
from polyweave.post.mesh import check_mesh

HALF = {
    "id": "hull_half",
    "op": "plate",
    "rect": [0, 0, 4, 2],
    "depth": 1.0,
    "material": "hull",
}


def shape(*nodes, params=None, voxels=None):
    document = {
        "name": "ship",
        "version": 1,
        "params": params or {},
        "materials": {"hull": {"colour": "#808080"}},
        "nodes": [dict(node) for node in nodes],
        "output": nodes[-1]["id"],
    }
    if voxels is not None:
        document["voxels"] = voxels
    return document


def mirror(of="hull_half", **fields):
    return {"id": "ship", "op": "mirror", "of": of, **fields}


def signed_volume(mesh):
    points = np.asarray(mesh["vertices"], dtype=float)
    total = 0.0
    for face in mesh["faces"]:
        for second in range(1, len(face) - 1):
            a, b, c = points[face[0]], points[face[second]], points[face[second + 1]]
            total += float(np.dot(a, np.cross(b, c))) / 6.0
    return total


def test_the_mesh_is_the_half_and_its_reflection():
    half = B.build(shape(HALF))["output"]
    whole = B.build(shape(HALF, mirror()))["output"]
    low, high = check_mesh(whole)["bounds"]
    assert (low[0], high[0]) == (-4.0, 4.0)
    assert len(whole["faces"]) == 2 * len(half["faces"])


def test_the_reflected_half_still_faces_out():
    half = B.build(shape(HALF))["output"]
    whole = B.build(shape(HALF, mirror()))["output"]
    assert signed_volume(whole) == pytest.approx(2 * signed_volume(half))
    assert signed_volume(half) > 0


def test_what_the_half_wears_comes_with_both_halves():
    whole = B.build(shape(HALF, mirror()))["output"]
    faces = len(whole["faces"])
    assert whole["groups"] == [
        {"material": "hull", "faces": [0, faces // 2]},
        {"material": "hull", "faces": [faces // 2, faces]},
    ]


def test_a_plane_off_the_origin_reflects_about_itself():
    half = dict(HALF, rect=[2, 0, 2, 2])
    whole = B.build(shape(half, mirror(plane=2)))["output"]
    low, high = check_mesh(whole)["bounds"]
    assert (low[0], high[0]) == (0.0, 4.0)


@pytest.mark.parametrize(("axis", "index"), [("y", 1), ("Z", 2)])
def test_any_axis_can_be_the_one_reflected(axis, index):
    whole = B.build(shape(HALF, mirror(axis=axis)))["output"]
    low, high = check_mesh(whole)["bounds"]
    assert low[index] == pytest.approx(-high[index])


def test_an_axis_that_is_not_one_is_refused():
    with pytest.raises(PolyweaveError) as refused:
        B.build(shape(HALF, mirror(axis="w")))
    assert refused.value.code == "geom.bad-solid"


def test_an_axis_is_a_letter_even_where_a_parameter_has_its_name():
    whole = B.build(shape(HALF, mirror(axis="x"), params={"x": 5}))["output"]
    low, _ = check_mesh(whole)["bounds"]
    assert low[0] == -4.0


def test_the_cells_are_the_half_and_its_reflection():
    made = V.voxelize(shape(HALF, mirror(), voxels={"cell": 1.0}))
    assert made["size"] == [8, 2, 1]
    assert made["count"] == 16
    assert {entry["name"] for entry in made["palette"]} == {"hull"}


def test_a_column_on_the_plane_is_one_set_of_cells():
    across = dict(HALF, rect=[-0.5, 0, 3.5, 1])
    made = V.voxelize(shape(across, mirror(), voxels={"cell": 1.0}))
    assert made["size"] == [6, 1, 1]
    assert made["count"] == 6


def test_the_readback_says_what_was_mirrored_and_where():
    said = review.describe(shape(HALF, mirror()))["reads"]
    assert said[-1] == "ship: hull_half mirrored across x = 0"


def test_a_half_that_already_reaches_across_is_warned_about():
    across = dict(HALF, rect=[-1, 0, 4, 2])
    warned = B.build(shape(across, mirror()))["report"]["warnings"]
    assert any("already reaches both sides of x = 0" in one for one in warned)
    clean = B.build(shape(HALF, mirror()))["report"]["warnings"]
    assert not any("both sides" in one for one in clean)
