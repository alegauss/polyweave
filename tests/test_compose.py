"""An asset judged where it will be seen, not on its own.

§PW10's case: a prop that read correctly in isolation and then sat on a sheet beside
five siblings that each had a shadow beneath them. It floated, and no measurement of the
lone file could reach that.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import compose, measure
from polyweave.errors import PolyweaveError


def asset(tmp_path, name, *, size=(16, 16), colour=(200, 40, 40), grounded=True):
    """A square asset, optionally with a gap under it so it reads as floating."""
    rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    bottom = size[1] if grounded else size[1] - 4
    rgba[:bottom, :, :3] = colour
    rgba[:bottom, :, 3] = 255
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def capture(tmp_path, name="screen.png", size=(128, 96)):
    rgba = np.full((size[1], size[0], 4), 40, dtype=np.uint8)
    rgba[:, :, 3] = 255
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


# -- the contact sheet ------------------------------------------------------------


def test_a_sheet_holds_every_asset_it_was_given(tmp_path):
    tiles = [asset(tmp_path, f"{i}.png") for i in range(5)]
    found = compose.sheet(tiles, cell=32, gap=4)
    assert found.width == 3 * 32 + 4 * 4  # three across
    assert found.height == 2 * 32 + 3 * 4  # two down


def test_the_columns_are_the_callers_if_it_says(tmp_path):
    tiles = [asset(tmp_path, f"{i}.png") for i in range(4)]
    found = compose.sheet(tiles, columns=4, cell=16, gap=2)
    assert found.width == 4 * 16 + 5 * 2
    assert found.height == 16 + 2 * 2


def test_every_tile_sits_on_the_bottom_of_its_cell(tmp_path):
    """A prop that floats is the failure this is for; a centred layout hides it."""
    grounded = asset(tmp_path, "a.png", grounded=True)
    floating = asset(tmp_path, "b.png", grounded=False)
    found = compose.sheet([grounded, floating], columns=2, cell=16, gap=0)

    # The bottom row of each cell: opaque under the grounded one, empty under the other.
    bottom = found.alpha[-1]
    assert bottom[:16].any()
    assert not bottom[16:].any()


def test_a_sheet_is_an_image_like_any_other(tmp_path):
    """So the comparison runs against the composite rather than the asset's own file."""
    tiles = [asset(tmp_path, f"{i}.png") for i in range(2)]
    found = compose.sheet(tiles, cell=16, gap=2)
    taken = measure.measure(found, ["alpha_coverage"], region="frame")
    assert 0.0 < taken[0]["value"] < 1.0


def test_a_sheet_can_be_written_where_it_was_asked_for(tmp_path):
    tiles = [asset(tmp_path, "a.png")]
    out = tmp_path / "sheets" / "contact.png"
    found = compose.sheet(tiles, cell=16, out=out)
    assert out.is_file()
    assert found.path == out


def test_a_sheet_of_nothing_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        compose.sheet([])
    assert caught.value.code == "compose.no-tiles"


def test_a_tile_keeps_its_proportions(tmp_path):
    wide = asset(tmp_path, "wide.png", size=(32, 8))
    found = compose.sheet([wide], columns=1, cell=16, gap=0)
    # 32x8 into a 16x16 cell is 16x4, so twelve rows of the cell stay empty.
    assert not found.alpha[:11].any()
    assert found.alpha[-1].any()


# -- in place ----------------------------------------------------------------------


def test_an_asset_lands_in_the_capture_it_belongs_to(tmp_path):
    found = compose.place(
        asset(tmp_path, "prop.png"), capture(tmp_path), at=(64, 80), width=16
    )
    assert found.size == (128, 96)
    # the prop is red where it landed, and the screen's grey everywhere else
    assert tuple(found.rgba[70, 64][:3]) == (200, 40, 40)
    assert tuple(found.rgba[10, 10][:3]) == (40, 40, 40)


def test_the_footprint_anchor_stands_the_asset_on_the_point_given(tmp_path):
    """§6 puts the origin at the base of the silhouette, which stops it floating."""
    grounded = compose.place(
        asset(tmp_path, "p.png"), capture(tmp_path), at=(64, 80), width=16
    )
    assert tuple(grounded.rgba[79, 64][:3]) == (200, 40, 40)  # the last row it covers
    assert tuple(grounded.rgba[81, 64][:3]) == (40, 40, 40)  # and nothing below it


def test_the_centre_anchor_puts_the_middle_on_the_point(tmp_path):
    found = compose.place(
        asset(tmp_path, "p.png"),
        capture(tmp_path),
        at=(64, 48),
        width=16,
        anchor="centre",
    )
    assert tuple(found.rgba[48, 64][:3]) == (200, 40, 40)


def test_it_is_drawn_at_the_size_it_will_actually_be_drawn(tmp_path):
    small = compose.place(
        asset(tmp_path, "p.png", size=(64, 64)), capture(tmp_path), at=(64, 90), width=8
    )
    covered = int((small.rgba[:, :, :3] == (200, 40, 40)).all(axis=-1).sum())
    assert covered == 8 * 8


def test_an_asset_placed_off_the_capture_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        compose.place(asset(tmp_path, "p.png"), capture(tmp_path), at=(900, 900))
    assert caught.value.code == "compose.outside"


def test_an_anchor_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        compose.place(
            asset(tmp_path, "p.png"), capture(tmp_path), at=(10, 10), anchor="top"
        )
    assert caught.value.code == "compose.unknown-anchor"


# -- what survives at display size ----------------------------------------------------


def gradient(tmp_path, name, steps):
    """A strip with `steps` distinct luminance levels across it."""
    side = 64
    rgba = np.zeros((side, side, 4), dtype=np.uint8)
    for i in range(side):
        step = int(round(i / max(1, side - 1) * (steps - 1)))
        level = step * (255 // max(1, steps - 1))
        rgba[:, i, :3] = level
    rgba[:, :, 3] = 255
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def test_detail_that_survives_the_screen_is_counted_there(tmp_path):
    """Cottony's fluff read at 1.2 and vanished at 1.0, at a third of its size."""
    path = gradient(tmp_path, "grad.png", steps=32)
    large = measure.measure(path, ["luma_bands"], display=64)[0]["value"]
    small = measure.measure(path, ["luma_bands"], display=4)[0]["value"]
    assert large > small


def test_luma_bands_refuses_to_guess_the_display_size(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(gradient(tmp_path, "g.png", steps=8), ["luma_bands"])
    assert caught.value.code == "spec.measure-needs"
    assert "display" in caught.value.remedy


def test_a_flat_asset_has_one_band_at_any_size(tmp_path):
    path = asset(tmp_path, "flat.png", size=(64, 64))
    assert measure.measure(path, ["luma_bands"], display=16)[0]["value"] == 1


def test_luma_bands_carries_its_region_and_rung(tmp_path):
    taken = measure.measure(
        gradient(tmp_path, "g.png", steps=8), ["luma_bands"], display=8, rung="final"
    )[0]
    assert taken["measure"] == "luma_bands"
    assert taken["rung"] == "final"
