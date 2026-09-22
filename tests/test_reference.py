"""Preparing the picture before the credits go on it.

§PW21's case: a photograph of a plush toy came back with the logo the toy had been
sitting on fused into the mesh. Every check that would have caught it is a routine image
operation, and these are them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import reference
from polyweave.errors import PolyweaveError


def photo(where, *, size=(120, 120), ground=(210, 205, 200), blobs=()):
    """A photograph: opaque everywhere, a subject and whatever else was in shot."""
    canvas = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    canvas[:, :, :3] = ground
    canvas[:, :, 3] = 255
    for (left, top, wide, tall), colour in blobs:
        canvas[top : top + tall, left : left + wide, :3] = colour
    PILImage.fromarray(canvas, "RGBA").save(where)
    return where


def drawing(where, *, size=(120, 120), box=(30, 20, 60, 80)):
    """A drawing: the background is already gone."""
    canvas = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    left, top, wide, tall = box
    canvas[top : top + tall, left : left + wide] = (40, 60, 180, 255)
    PILImage.fromarray(canvas, "RGBA").save(where)
    return where


def toy_on_a_logo(where):
    """Cottony's own picture: the subject, and the thing it was standing on."""
    return photo(
        where,
        blobs=(
            ((35, 15, 50, 70), (180, 90, 70)),  # the toy
            ((10, 100, 26, 10), (60, 60, 60)),  # the logo on the table
        ),
    )


# -- a drawing is not a photograph --------------------------------------------------


def test_a_drawing_is_recognised_by_having_no_background(tmp_path):
    assert reference.is_drawing(drawing(tmp_path / "cap.png"))


def test_a_photograph_is_not(tmp_path):
    assert not reference.is_drawing(photo(tmp_path / "cap.jpg".replace("jpg", "png")))


def test_an_opaque_picture_with_an_alpha_channel_is_still_a_photograph(tmp_path):
    where = photo(tmp_path / "opaque.png")
    assert not reference.is_drawing(where)


def test_the_drawing_wins_over_the_photograph(tmp_path):
    chosen = reference.pick(
        photo(tmp_path / "shot.png"), drawing(tmp_path / "cap.png"), root=tmp_path
    )
    assert chosen["drawing"] is True
    assert chosen["reference"].endswith("cap.png")
    assert "no background to cut" in chosen["why"]


def test_a_photograph_wins_only_when_there_is_no_drawing(tmp_path):
    chosen = reference.pick(photo(tmp_path / "shot.png"), root=tmp_path)
    assert chosen["drawing"] is False
    assert chosen["reference"].endswith("shot.png")


def test_naming_nothing_is_refused_rather_than_answered(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        reference.pick(root=tmp_path)
    assert caught.value.code == "fetch.no-reference"


# -- the cut ---------------------------------------------------------------------------


def test_the_subject_is_cut_away_from_what_it_stood_on(tmp_path):
    found = reference.cut(toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path)
    mask = found["subject"]
    assert mask[40, 50], "the toy is the subject"
    assert not mask[5, 5], "the table is not"


def test_the_thing_the_subject_was_standing_on_does_not_come_too(tmp_path):
    """The whole of §PW21: the logo is a second thing in the picture, not the asset."""
    found = reference.cut(toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path)
    assert not found["subject"][104, 20], "the logo was left behind"


def test_a_pocket_of_background_colour_inside_the_subject_stays_subject(tmp_path):
    """The fill comes in from the edge, so an enclosed hole is not reachable."""
    where = photo(
        tmp_path / "ring.png",
        blobs=(((30, 20, 60, 80), (180, 90, 70)), ((50, 45, 12, 12), (210, 205, 200))),
    )
    found = reference.cut(where, root=tmp_path)
    assert found["subject"][50, 55], "the hole in the middle is still the toy"


def test_how_much_of_the_frame_the_subject_fills_is_reported(tmp_path):
    found = reference.cut(
        photo(tmp_path / "toy.png", blobs=(((30, 20, 60, 80), (180, 90, 70)),)),
        root=tmp_path,
    )
    assert found["coverage"] == pytest.approx((60 * 80) / (120 * 120), abs=0.02)


def test_a_silhouette_that_runs_off_the_frame_is_named(tmp_path):
    where = photo(tmp_path / "cropped.png", blobs=(((0, 20, 70, 100), (180, 90, 70)),))
    found = reference.cut(where, root=tmp_path)
    assert "left" in found["touches"]
    assert "bottom" in found["touches"]


def test_a_picture_that_stays_clear_of_the_edges_names_none(tmp_path):
    found = reference.cut(
        photo(tmp_path / "toy.png", blobs=(((30, 20, 60, 80), (180, 90, 70)),)),
        root=tmp_path,
    )
    assert found["touches"] == []


# -- what gets refused rather than fetched ---------------------------------------------


def test_a_background_that_cannot_be_told_from_the_subject_is_refused(tmp_path):
    """The service returns it as geometry, and that costs the whole fetch."""
    noise = np.zeros((120, 120, 4), dtype=np.uint8)
    rng = np.random.default_rng(7)
    noise[:, :, :3] = rng.integers(0, 256, size=(120, 120, 3), dtype=np.uint8)
    noise[:, :, 3] = 255
    where = tmp_path / "busy.png"
    PILImage.fromarray(noise, "RGBA").save(where)
    with pytest.raises(PolyweaveError) as caught:
        reference.cut(where, root=tmp_path)
    assert caught.value.code == "fetch.background-fused"
    assert "geometry" in caught.value.remedy


def test_a_subject_too_far_away_to_read_is_refused(tmp_path):
    small = photo(tmp_path / "far.png", blobs=(((58, 58, 6, 6), (180, 90, 70)),))
    with pytest.raises(PolyweaveError) as caught:
        reference.cut(small, root=tmp_path)
    assert caught.value.code == "fetch.subject-small"


def test_the_bar_for_that_is_the_project_s_to_set(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        "[tolerance]\nsubject_coverage = 0.001\n", encoding="utf-8"
    )
    small = photo(tmp_path / "far.png", blobs=(((58, 58, 6, 6), (180, 90, 70)),))
    found = reference.cut(small, root=tmp_path)
    assert found["coverage"] < 0.01


# -- the prepared picture is the one on file -------------------------------------------


def test_the_background_is_gone_and_flattened_in_what_gets_written(tmp_path):
    record = reference.prepare(toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path)
    written = np.asarray(PILImage.open(record["reference"]).convert("RGBA"))
    assert written[5, 5, 3] == 0, "the ground is transparent"
    assert tuple(written[5, 5, :3]) == (255, 255, 255), "and flat behind it"
    assert written[40, 50, 3] == 255, "the toy is kept"


def test_the_flat_colour_behind_it_is_the_caller_s_to_choose(tmp_path):
    record = reference.prepare(
        toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path, matte=(0, 0, 0)
    )
    written = np.asarray(PILImage.open(record["reference"]).convert("RGBA"))
    assert tuple(written[5, 5, :3]) == (0, 0, 0)


def test_it_lands_where_the_project_keeps_its_references(tmp_path):
    record = reference.prepare(toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path)
    assert Path(record["reference"]).parent == tmp_path / "assets" / "references"
    assert Path(record["reference"]).is_file()


def test_the_prepared_picture_is_the_one_a_record_can_name(tmp_path):
    """So the input that made the mesh is on file, not whichever original was open."""
    record = reference.prepare(toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path)
    assert len(record["sha256"]) == 64
    assert record["bytes"] == Path(record["reference"]).stat().st_size
    assert record["source"].endswith("toy.png")


def test_an_edge_that_was_touched_comes_back_as_a_warning_and_not_a_refusal(tmp_path):
    where = photo(tmp_path / "cropped.png", blobs=(((0, 20, 70, 100), (180, 90, 70)),))
    record = reference.prepare(where, root=tmp_path)
    assert record["touches"]
    assert any("past the edge" in note for note in record["warnings"])


def test_a_clean_picture_carries_no_warnings(tmp_path):
    record = reference.prepare(
        photo(tmp_path / "toy.png", blobs=(((30, 20, 60, 80), (180, 90, 70)),)),
        root=tmp_path,
    )
    assert record["warnings"] == []


def test_a_big_photograph_is_written_at_the_size_it_was_measured_at(tmp_path):
    big = photo(
        tmp_path / "big.png",
        size=(2400, 1600),
        blobs=(((600, 300, 900, 900), (180, 90, 70)),),
    )
    record = reference.prepare(big, root=tmp_path)
    assert max(record["size"]) == reference.LONGEST


# -- either kind, one answer -----------------------------------------------------------


def test_a_drawing_is_passed_through_rather_than_cut(tmp_path):
    record = reference.ready(drawing(tmp_path / "cap.png"), root=tmp_path)
    assert record["prepared"] is False
    assert record["reference"] == str(tmp_path / "cap.png")
    assert "already a drawing" in record["why"]


def test_a_photograph_is_prepared(tmp_path):
    record = reference.ready(toy_on_a_logo(tmp_path / "toy.png"), root=tmp_path)
    assert record["prepared"] is True
    assert record["reference"] != record["source"]


def test_either_way_the_caller_gets_a_path_and_a_digest(tmp_path):
    for subject in (drawing(tmp_path / "cap.png"), toy_on_a_logo(tmp_path / "toy.png")):
        record = reference.ready(subject, root=tmp_path)
        assert Path(record["reference"]).is_file()
        assert len(record["sha256"]) == 64
