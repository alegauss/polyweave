"""A look is a distribution, not a number.

The case §PW9 is drawn from is reconstructed below: two pictures whose mean saturation
agrees to within 0.01 and whose 99th percentiles are 0.20 apart. A comparison reporting
only means agrees with the one that is plainly wrong.
"""

from __future__ import annotations

import colorsys

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import measure
from polyweave.errors import PolyweaveError


def picture(tmp_path, name, pixels):
    """An image from a list of (count, (r, g, b)) runs, laid out in one strip."""
    rows = []
    for count, rgb in pixels:
        rows.extend([rgb] * count)
    side = int(len(rows) ** 0.5)
    data = np.array(rows[: side * side], dtype=np.uint8).reshape(side, side, 3)
    rgba = np.dstack([data, np.full((side, side), 255, dtype=np.uint8)])
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def values_of(taken, name):
    return next(m["value"] for m in taken if m["measure"] == name)


# -- the case this line exists for ---------------------------------------------------


def _hsl_rgb(h, s, lightness):
    r, g, b = colorsys.hls_to_rgb(h, lightness, s)
    return (round(r * 255), round(g * 255), round(b * 255))


def test_a_mean_agrees_while_the_99th_percentile_does_not(tmp_path):
    """Cottony's board against the concept art: 0.31 and 0.32, 0.68 and 0.88."""
    cream = _hsl_rgb(0.1, 0.30, 0.85)  # most of the board is cream tray
    board = picture(
        tmp_path, "board.png", [(3600, cream), (400, _hsl_rgb(0.1, 0.68, 0.5))]
    )
    art = picture(tmp_path, "art.png", [(3600, cream), (400, _hsl_rgb(0.1, 0.88, 0.5))])

    board_taken = measure.measure(board, ["saturation"], region="frame")
    art_taken = measure.measure(art, ["saturation"], region="frame")

    mean_gap = abs(
        values_of(board_taken, "saturation_mean")
        - values_of(art_taken, "saturation_mean")
    )
    p99_gap = abs(
        values_of(board_taken, "saturation_p99")
        - values_of(art_taken, "saturation_p99")
    )
    assert mean_gap < 0.03, "the means agree, which is the whole problem"
    assert p99_gap > 0.15, "and the 99th percentile is where the difference lives"


# -- a distribution comes back whole ---------------------------------------------------


def test_asking_for_a_measure_returns_all_five_statistics(tmp_path):
    path = picture(tmp_path, "p.png", [(64, (200, 30, 30))])
    taken = measure.measure(path, ["saturation"])
    assert [m["measure"] for m in taken] == [
        "saturation_p1",
        "saturation_p50",
        "saturation_p99",
        "saturation_mean",
        "saturation_std",
    ]


def test_a_predicate_may_name_one_statistic(tmp_path):
    path = picture(tmp_path, "p.png", [(64, (200, 30, 30))])
    taken = measure.measure(path, ["saturation_p99"])
    assert [m["measure"] for m in taken] == ["saturation_p99"]


def test_every_statistic_carries_its_region_and_rung(tmp_path):
    path = picture(tmp_path, "p.png", [(64, (200, 30, 30))])
    for m in measure.measure(path, ["luma"], region="frame", rung="final"):
        assert m["region"] == "frame"
        assert m["rung"] == "final"


def test_the_default_set_is_what_the_vocabulary_says(tmp_path):
    taken = measure.measure(picture(tmp_path, "d.png", [(64, (200, 30, 30))]))
    names = {m["measure"] for m in taken}
    assert "saturation_p99" in names
    assert "luma_mean" in names
    assert "alpha_coverage" in names


# -- the numbers themselves ------------------------------------------------------------


def test_saturation_is_zero_for_grey_and_one_for_a_pure_hue(tmp_path):
    grey = picture(tmp_path, "grey.png", [(64, (128, 128, 128))])
    pure = picture(tmp_path, "pure.png", [(64, (255, 0, 0))])
    assert values_of(measure.measure(grey, ["saturation"]), "saturation_mean") == 0.0
    assert values_of(measure.measure(pure, ["saturation"]), "saturation_mean") == 1.0


def test_luma_weights_green_above_red_above_blue(tmp_path):
    def luma(rgb):
        path = picture(tmp_path, f"{rgb}.png", [(64, rgb)])
        return values_of(measure.measure(path, ["luma"]), "luma_mean")

    assert luma((0, 255, 0)) > luma((255, 0, 0)) > luma((0, 0, 255))


def test_luma_is_linear_luminance_not_the_stored_byte(tmp_path):
    """Mid grey stores as 128 and carries about 22% of the light, not 50%."""
    mid = picture(tmp_path, "mid.png", [(64, (128, 128, 128))])
    assert values_of(measure.measure(mid, ["luma"]), "luma_mean") == pytest.approx(
        0.2159, abs=0.005
    )


def test_black_and_white_are_the_ends_of_luma(tmp_path):
    black = picture(tmp_path, "black.png", [(64, (0, 0, 0))])
    white = picture(tmp_path, "white.png", [(64, (255, 255, 255))])
    assert values_of(measure.measure(black, ["luma"]), "luma_mean") == 0.0
    assert values_of(measure.measure(white, ["luma"]), "luma_mean") == 1.0


# -- hue is circular -------------------------------------------------------------------


def test_one_hue_has_no_spread(tmp_path):
    path = picture(tmp_path, "one.png", [(64, (200, 30, 30))])
    assert values_of(measure.measure(path, ["hue_spread"]), "hue_spread") == 0.0


def test_hues_across_the_wheel_spread_further_than_neighbours(tmp_path):
    near = picture(
        tmp_path,
        "near.png",
        [(32, _hsl_rgb(0.00, 1.0, 0.5)), (32, _hsl_rgb(0.05, 1.0, 0.5))],
    )
    far = picture(
        tmp_path,
        "far.png",
        [(32, _hsl_rgb(0.00, 1.0, 0.5)), (32, _hsl_rgb(0.50, 1.0, 0.5))],
    )
    assert values_of(measure.measure(far, ["hue_spread"]), "hue_spread") > values_of(
        measure.measure(near, ["hue_spread"]), "hue_spread"
    )


def test_hue_wraps_rather_than_averaging_through_the_middle(tmp_path):
    """355 and 5 degrees are neighbours; a linear mean calls them 180."""
    path = picture(
        tmp_path,
        "wrap.png",
        [(32, _hsl_rgb(0.99, 1.0, 0.5)), (32, _hsl_rgb(0.01, 1.0, 0.5))],
    )
    assert values_of(measure.measure(path, ["hue_spread"]), "hue_spread") < 0.05


def test_grey_reports_no_hue_spread_rather_than_a_random_one(tmp_path):
    """The hue of a grey pixel is arbitrary, so it is weighted out."""
    path = picture(tmp_path, "greys.png", [(32, (60, 60, 60)), (32, (200, 200, 200))])
    assert values_of(measure.measure(path, ["hue_spread"]), "hue_spread") == 0.0


# -- the masking is half the value -----------------------------------------------------


def test_the_subject_is_not_diluted_by_its_background(tmp_path):
    """A prop measured over its own pixels reads differently from one measured whole."""
    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[:2, :, :3] = (255, 0, 0)  # a small, deeply saturated subject
    rgba[:2, :, 3] = 255  # and nothing else is opaque
    path = tmp_path / "prop.png"
    PILImage.fromarray(rgba, "RGBA").save(path)

    whole = values_of(
        measure.measure(path, ["saturation"], region="frame"), "saturation_mean"
    )
    subject = values_of(
        measure.measure(path, ["saturation"], region="subject"), "saturation_mean"
    )
    assert subject == 1.0
    assert whole < subject / 3


# -- refusals --------------------------------------------------------------------------


def test_a_statistic_of_a_measure_that_is_one_number_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        path = picture(tmp_path, "p.png", [(64, (1, 2, 3))])
        measure.measure(path, ["hue_spread_p99"])
    assert caught.value.code == "spec.unknown-measure"
    assert "one number" in caught.value.message


def test_a_region_with_nothing_in_it_is_refused(tmp_path):
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)  # every pixel fully transparent
    path = tmp_path / "empty.png"
    PILImage.fromarray(rgba, "RGBA").save(path)
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(path, ["saturation"], region="subject")
    assert caught.value.code == "spec.empty-region"
