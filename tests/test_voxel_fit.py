"""A voxel model's proportions found against a reference (§PW98).

Every reference here has a known answer: a drawing three times as wide as it is tall, a
box three deep. The fit has to land on it without being told.
"""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave.errors import PolyweaveError
from polyweave.geometry import solid as S
from polyweave.geometry import voxel_fit as F


def plate(width="w", depth=1.0, voxels=None, search=None):
    document = {
        "name": "ship",
        "version": 1,
        "params": {"w": 4.0, "d": 1.0},
        "materials": {},
        "nodes": [
            {"id": "hull", "op": "plate", "rect": [0, 0, width, 2], "depth": depth}
        ],
        "output": "hull",
        "voxels": voxels or {"cell": 0.25},
    }
    if search:
        document["search"] = search
    return document


def banner(tmp_path, name="ref.png", boxes=((0, 0, 300, 100),), size=(300, 100)):
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    for left, top, right, bottom in boxes:
        picture.paste((200, 60, 60, 255), (left, top, right, bottom))
    picture.save(tmp_path / name)
    return tmp_path / name


def test_a_drawing_three_wide_fits_a_plate_three_wide(tmp_path):
    found = F.fit(
        plate(),
        banner(tmp_path),
        ranges={"w": {"min": 1.0, "max": 10.0}},
        root=tmp_path,
    )
    assert found["best"]["w"] == pytest.approx(6.0, abs=0.3)
    assert found["views"]["front"] > 0.95


def test_a_mesh_is_compared_in_every_view_asked_for(tmp_path):
    target = S.plate([0, 0, 6, 2], 3.0)
    found = F.fit(
        plate(width=6, depth="d"),
        target,
        ranges={"d": {"min": 0.5, "max": 6.0}},
        views=["front", "side", "top"],
        root=tmp_path,
    )
    assert found["best"]["d"] == pytest.approx(3.0, abs=0.3)
    assert set(found["views"]) == {"front", "side", "top"}
    assert min(found["views"].values()) > 0.9


def test_a_sample_that_leaves_a_piece_floating_scores_nothing(tmp_path):
    document = {
        "name": "pair",
        "version": 1,
        "params": {"gap": 0.0},
        "materials": {},
        "nodes": [
            {"id": "left", "op": "plate", "rect": [0, 0, 2, 2], "depth": 1},
            {"id": "right", "op": "plate", "rect": ["2 + gap", 0, 2, 2], "depth": 1},
            {"id": "pair", "op": "union", "inputs": ["left", "right"]},
        ],
        "output": "pair",
        "voxels": {"cell": 0.5},
    }
    apart = banner(
        tmp_path, boxes=((0, 0, 100, 100), (200, 0, 300, 100)), size=(300, 100)
    )
    found = F.fit(
        document,
        apart,
        ranges={"gap": {"min": 0.0, "max": 2.0, "step": 0.5}},
        root=tmp_path,
    )
    # Two separate boxes would overlap the drawing best, and they float: the fit keeps
    # the model in one piece and says how well that matches.
    assert found["best"]["gap"] == 0.0
    assert found["score"] > 0


def test_the_documents_own_ranges_are_used_when_none_are_given(tmp_path):
    found = F.fit(
        plate(search={"w": {"min": 1.0, "max": 10.0}}), banner(tmp_path), root=tmp_path
    )
    assert found["best"]["w"] == pytest.approx(6.0, abs=0.3)


def test_the_best_model_and_its_sheet_come_back(tmp_path):
    found = F.fit(
        plate(),
        banner(tmp_path),
        ranges={"w": {"min": 1.0, "max": 10.0}},
        root=tmp_path,
        sheet="fit.png",
    )
    assert (tmp_path / "fit.png").is_file()
    assert found["model"]["says"].startswith("a voxel model")


def test_a_drawing_cannot_stand_for_a_view_it_does_not_show(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        F.fit(
            plate(),
            banner(tmp_path),
            ranges={"w": {"min": 1, "max": 10}},
            views=["front", "side"],
            root=tmp_path,
        )
    assert refused.value.code == "geom.bad-fit"


def test_a_fit_with_nothing_to_move_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        F.fit(plate(), banner(tmp_path), root=tmp_path)
    assert refused.value.code == "geom.bad-fit"


def test_a_range_over_a_parameter_the_shape_lacks_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        F.fit(
            plate(),
            banner(tmp_path),
            ranges={"span": {"min": 1, "max": 2}},
            root=tmp_path,
        )
    assert refused.value.code == "geom.unknown-name"
