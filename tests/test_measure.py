"""The picture and the numbers as one answer.

§PW8's cost is turns: eight samples at three calls each is twenty-four round trips for
what should be eight. So these are about the shape of the answer, not about a renderer.
"""

from __future__ import annotations

import base64

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import measure
from polyweave.errors import PolyweaveError


def png(tmp_path, name="shot.png", *, size=(8, 8), coverage=1.0):
    """A picture whose subject covers a known fraction of the frame."""
    rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    rows = max(1, int(round(size[1] * coverage)))
    rgba[:rows, :, 3] = 255
    rgba[:rows, :, 0] = np.arange(size[0], dtype=np.uint8)[None, :]
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


# -- a measurement names its region and its rung ------------------------------------


def test_a_measurement_carries_its_region_and_its_rung(tmp_path):
    taken = measure.measure(png(tmp_path), ["alpha_coverage"], rung="preview")
    assert taken == [
        {
            "measure": "alpha_coverage",
            "region": "subject",
            "rung": "preview",
            "value": 1.0,
        }
    ]


def test_the_rung_is_reported_and_never_inferred(tmp_path):
    """A verdict taken on a sphere is never mistaken for one taken on the final mesh."""
    assert measure.measure(png(tmp_path), ["alpha_coverage"])[0]["rung"] is None


def test_the_default_region_is_the_subject_where_there_is_alpha(tmp_path):
    only = ["alpha_coverage"]
    assert measure.measure(png(tmp_path, coverage=0.5), only)[0]["region"] == "subject"


def test_the_default_region_is_the_frame_without_alpha(tmp_path):
    flat = tmp_path / "flat.png"
    PILImage.fromarray(np.full((4, 4, 3), 90, dtype=np.uint8), "RGB").save(flat)
    assert measure.measure(flat, ["alpha_coverage"])[0]["region"] == "frame"


def test_the_frame_and_the_subject_are_different_answers(tmp_path):
    """The masking is half the value: a prop is not diluted by its background."""
    path = png(tmp_path, coverage=0.5)
    only = ["alpha_coverage"]
    frame = measure.measure(path, only, region="frame")[0]["value"]
    subject = measure.measure(path, only, region="subject")[0]["value"]
    assert frame == 0.5  # half the frame is the asset
    assert subject == 1.0  # all of the asset is the asset


def test_a_rectangle_measures_only_inside_itself(tmp_path):
    """A region answers about itself, or it would only report its own size."""
    path = png(tmp_path, size=(8, 8), coverage=0.5)
    only = ["alpha_coverage"]
    covered = measure.measure(path, only, region=[0, 0, 8, 4])[0]
    assert covered["region"] == [0, 0, 8, 4]
    assert covered["value"] == 1.0  # the top half is all subject
    empty = measure.measure(path, only, region=[0, 4, 8, 8])[0]
    assert empty["value"] == 0.0  # the bottom half is all background


def test_a_rectangle_outside_the_image_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(png(tmp_path), region=[0, 0, 99, 99])
    assert caught.value.code == "spec.bad-region"
    assert "8x8" in caught.value.message


def test_a_mask_file_is_a_region(tmp_path):
    path = png(tmp_path, size=(4, 4), coverage=0.5)  # the top half is the asset

    def mask_over(rows) -> str:
        mask = np.zeros((4, 4, 4), dtype=np.uint8)
        mask[rows, :, 3] = 255
        where = tmp_path / f"mask{rows.start}.png"
        PILImage.fromarray(mask, "RGBA").save(where)
        return where

    only = ["alpha_coverage"]
    assert measure.measure(path, only, region=mask_over(slice(0, 2)))[0]["value"] == 1.0
    assert measure.measure(path, only, region=mask_over(slice(2, 4)))[0]["value"] == 0.0


def test_a_mask_of_another_size_is_refused(tmp_path):
    path = png(tmp_path, size=(8, 8))
    PILImage.fromarray(np.zeros((4, 4, 4), dtype=np.uint8), "RGBA").save(
        tmp_path / "small.png"
    )
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(path, region=tmp_path / "small.png")
    assert caught.value.code == "spec.bad-region"


def test_something_that_is_not_a_region_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(png(tmp_path), region="middle-ish")
    assert caught.value.code == "spec.bad-region"


def test_the_alpha_floor_decides_what_counts_as_the_subject(tmp_path):
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[:2, :, 3] = 255
    rgba[2:, :, 3] = 3  # a faint haze, below a 2% floor and above none at all
    path = tmp_path / "haze.png"
    PILImage.fromarray(rgba, "RGBA").save(path)
    over = {"region": "frame"}
    only = ["alpha_coverage"]
    assert measure.measure(path, only, alpha_floor=0.0, **over)[0]["value"] == 1.0
    assert measure.measure(path, only, alpha_floor=0.02, **over)[0]["value"] == 0.5


# -- a colour at its median (§PW86) ---------------------------------------------------


def spotted(tmp_path, spots: int):
    """A cap in #E1714D, the drawn mushroom's, with `spots` white pixels in 16."""
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[..., :3] = (0xE1, 0x71, 0x4D)
    rgba[..., 3] = 255
    rgba.reshape(-1, 4)[:spots, :3] = 255
    path = tmp_path / f"cap-{spots}.png"
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def test_a_median_reads_the_body_through_its_spots(tmp_path):
    """The mean moves with the spot count; the median does not, until spots are most."""
    for spots in (0, 3, 6):
        found = measure.measure(
            spotted(tmp_path, spots), ["pixel_delta_e_p50"], target="#E1714D"
        )
        assert found[0]["value"] == pytest.approx(0.0, abs=1e-6)


def test_the_mean_is_what_the_spots_pull_away(tmp_path):
    """The reason for the measure, stated as the difference it makes."""
    at_mean = measure.measure(spotted(tmp_path, 6), ["delta_e"], target="#E1714D")
    assert at_mean[0]["value"] > 10.0


def test_the_worst_of_the_region_is_still_there_to_bound(tmp_path):
    found = measure.measure(spotted(tmp_path, 3), ["pixel_delta_e"], target="#E1714D")
    named = {one["measure"]: one["value"] for one in found}
    assert set(named) == {f"pixel_delta_e{s}" for s in measure.SUFFIXES}
    assert named["pixel_delta_e_p99"] > 20.0, "white is a different colour"


def test_a_pixel_distance_with_nothing_to_measure_to_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(spotted(tmp_path, 0), ["pixel_delta_e_p50"])
    assert caught.value.code == "spec.measure-needs"


def test_it_is_answered_where_every_colour_is():
    from polyweave.render.ladder import rung_for

    assert rung_for("pixel_delta_e_p50") == "sphere"


# -- the vocabulary is closed, and honest about what it cannot do yet -----------------


def test_a_measure_outside_the_vocabulary_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(png(tmp_path), ["vibes"])
    assert caught.value.code == "spec.unknown-measure"


def test_a_declared_measure_nothing_computes_yet_says_which_line_builds_it(
    tmp_path, monkeypatch
):
    """Refused by name beats an answer quietly missing the field that was asked for.

    Nothing is pending today — the vocabulary is entirely built — so the door is proven
    against a measure declared pending for the length of this test.
    """
    monkeypatch.setitem(
        measure.PENDING, "thickness", "PW99 measures how thick it reads"
    )
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(png(tmp_path), ["thickness"])
    assert caught.value.code == "spec.unmeasured"
    assert "PW99" in caught.value.remedy


def test_a_statistic_resolves_to_its_measure(tmp_path):
    for suffix in measure.SUFFIXES:
        assert measure.base_measure(f"saturation{suffix}") == "saturation"
    assert measure.base_measure("alpha_coverage") == "alpha_coverage"


def test_what_can_be_measured_now_is_answerable(tmp_path):
    found = measure.available()
    assert {"alpha_coverage", "saturation", "luma", "delta_e"} <= set(found["computed"])
    # Every name the vocabulary declares is computed, so nothing is pending.
    assert found["pending"] == {}


# -- the picture comes back too --------------------------------------------------------


def test_the_picture_is_carried_back_with_the_numbers(tmp_path):
    path = png(tmp_path, size=(12, 9))
    found = measure.inline_image(path)
    assert found["media_type"] == "image/png"
    assert found["width"] == 12
    assert found["height"] == 9
    assert base64.b64decode(found["base64"]) == path.read_bytes()


def test_the_picture_comes_back_at_the_size_it_was_rendered(tmp_path):
    """Not a thumbnail: an image worth looking at is the other half of the answer."""
    found = measure.inline_image(png(tmp_path, size=(256, 256)))
    assert (found["width"], found["height"]) == (256, 256)


def test_measurements_flatten_for_a_record(tmp_path):
    taken = measure.measure(
        png(tmp_path, coverage=0.5), ["alpha_coverage"], region="frame"
    )
    assert measure.summarise(taken) == {"alpha_coverage": 0.5}
