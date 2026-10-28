"""A picture's first spec, written from its measurements (§PW637)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave.kernel import describe
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import accept


def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    pixels = np.full((20, 20, 4), 255, np.uint8)
    pixels[..., :3] = 100
    pixels[18:, :, :3] = 200
    where = tmp_path / "ui" / "holo.normal.png"
    where.parent.mkdir()
    Image.fromarray(pixels, "RGBA").save(where)
    return "ui/holo.normal.png"


def test_a_first_spec_is_measured_written_and_holds_its_picture(tmp_path):
    picture = project(tmp_path)
    found = accept.first(picture, [
        {"measure": "luma_p50", "region": "frame", "bound": "both"},
        {"id": "tail", "measure": "luma_p99", "region": "frame", "bound": "min"},
    ], root=str(tmp_path))
    assert found["spec"] == "docs/accept/holo.accept.toml"
    assert found["passed"] is True
    body, tail = found["predicates"]
    assert body["id"] == "luma_p50-frame"
    assert body["min"] < body["measured"] < body["max"]
    # Luma's range is 0 to 1, and a tenth of it is more room than a tenth of 0.13.
    assert body["max"] == pytest.approx(body["measured"] + 0.1, abs=1e-4)
    assert body["room_from"] == "range"
    assert set(tail) == {"id", "measure", "measured", "min", "room_from"}
    spec = accept.read(tmp_path / found["spec"])
    assert spec.artefact == picture
    for p in spec.predicates:
        # read off the picture with a rule's room, never a person's bar
        assert {o["origin"] for o in p.origins.values()} == {"margin"}
    assert accept.verify(str(tmp_path))["passed"] is True


def test_a_spec_already_there_is_not_written_over(tmp_path):
    picture = project(tmp_path)
    accept.first(picture, [{"measure": "luma_p50"}], root=str(tmp_path))
    with pytest.raises(PolyweaveError) as refused:
        accept.first(picture, [{"measure": "luma_p99"}], root=str(tmp_path))
    assert refused.value.code == "spec.exists"


@pytest.mark.parametrize("asked, code", [
    ([], "spec.no-predicates"),
    ([{"region": "frame"}], "spec.no-measure"),
    ([{"measure": "luma_p50", "max": 0.5}], "spec.unknown-field"),
    ([{"measure": "luma_p50", "bound": "under"}], "spec.bad-bound"),
])
def test_a_predicate_that_cannot_be_measured_is_refused_before_writing(
        tmp_path, asked, code):
    picture = project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        accept.first(picture, asked, root=str(tmp_path))
    assert refused.value.code == code
    assert not (tmp_path / "docs/accept").exists()


def test_a_picture_not_there_is_refused(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        accept.first("ui/gone.png", [{"measure": "luma_p50"}], root=str(tmp_path))
    assert refused.value.code == "spec.no-artefact"


def test_it_is_an_operation():
    assert "accept.first" in describe.operations()


def test_a_bound_near_zero_is_given_room_from_the_measure_s_range(tmp_path):
    # Spinhold's dark glass measured 0.0049 and got a max of 0.006 (§PW656).
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    pixels = np.zeros((20, 20, 4), np.uint8)
    pixels[..., :3] = 4
    pixels[..., 3] = 255
    Image.fromarray(pixels, "RGBA").save(tmp_path / "glass.png")
    found = accept.first("glass.png", [{"measure": "luma_p99", "region": "frame",
                                        "bound": "max"}], root=str(tmp_path))
    [glass] = found["predicates"]
    assert glass["max"] == pytest.approx(glass["measured"] + 0.1, abs=1e-4)
    assert glass["room_from"] == "range"


def test_a_measure_with_no_range_keeps_a_share_of_its_value(tmp_path):
    picture = project(tmp_path)
    found = accept.first(picture, [{"measure": "luma_std", "region": "frame",
                                    "bound": "max"}], root=str(tmp_path))
    [spread] = found["predicates"]
    assert spread["room_from"] == "value"


def test_a_bound_stays_inside_the_measure_s_range(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    pixels = np.full((20, 20, 4), 255, np.uint8)
    Image.fromarray(pixels, "RGBA").save(tmp_path / "white.png")
    found = accept.first("white.png", [{"measure": "luma_p50", "region": "frame",
                                        "bound": "both"}], root=str(tmp_path))
    [white] = found["predicates"]
    assert white["max"] == 1.0 and white["min"] == pytest.approx(0.9, abs=1e-4)