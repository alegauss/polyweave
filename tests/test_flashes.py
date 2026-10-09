"""Flashes counted in a captured run, against the photosensitivity guidance (§PW354).

Each run is drawn here, frame by frame, as capture.movie would write it: numbered PNGs
and a sequence.json carrying the rate.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import accept, flashes
from polyweave.errors import PolyweaveError

SIZE = (160, 90)


def run(tmp_path, colours, fps=60, name="run"):
    """A capture.movie folder whose frames are drawn by `colours(i)`."""
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, draw in enumerate(colours):
        picture = Image.new("RGB", SIZE, draw[0])
        if len(draw) > 1:
            picture.paste(draw[1], draw[2])
        file = f"{i + 1:04d}.png"
        picture.save(folder / file)
        frames.append({"file": file, "tick": i})
    (folder / "sequence.json").write_text(json.dumps({"fps": fps, "frames": frames}))
    if not (tmp_path / "polyweave.toml").exists():
        (tmp_path / "polyweave.toml").write_text("")
    return name


DARK, LIGHT = (30, 30, 30), (240, 240, 240)


def toggling(every, frames=120, on=LIGHT, off=DARK):
    return [((on if (i // every) % 2 else off),) for i in range(frames)]


def test_a_steady_run_has_no_flash(tmp_path):
    found = flashes.flashes(run(tmp_path, [(DARK,)] * 90), root=str(tmp_path))
    assert found["flashes"] == 0
    assert found["passed"] is True
    assert found["worst"]["frame"] is None
    assert "not found" in found["certifies"]


def test_a_strobe_names_its_worst_second_its_frame_and_its_share(tmp_path):
    found = flashes.flashes(run(tmp_path, toggling(4)), root=str(tmp_path))
    assert found["passed"] is False
    assert found["worst"]["kind"] == "general"
    assert found["flashes"] >= 7
    assert found["worst"]["file"] == "0005.png"
    assert found["flash_share"] == pytest.approx(1.0)
    assert "over the 3 allowed" in found["says"]


def test_two_flashes_a_second_are_within_the_limit(tmp_path):
    found = flashes.flashes(run(tmp_path, toggling(15)), root=str(tmp_path))
    assert found["flashes"] == 2
    assert found["passed"] is True


def test_a_flash_over_too_small_an_area_is_not_counted(tmp_path):
    small = [(DARK, LIGHT if (i // 4) % 2 else DARK, (0, 0, 8, 8)) for i in range(120)]
    found = flashes.flashes(run(tmp_path, small), root=str(tmp_path))
    assert found["flashes"] == 0


def test_a_change_between_two_bright_states_is_no_general_flash(tmp_path):
    bright = toggling(4, on=(255, 255, 255), off=(235, 235, 235))
    found = flashes.flashes(run(tmp_path, bright), root=str(tmp_path))
    assert found["general"]["flashes"] == 0


def test_a_saturated_red_flash_at_one_luminance_is_a_red_flash(tmp_path):
    red = toggling(4, on=(255, 0, 0), off=(127, 127, 127))
    found = flashes.flashes(run(tmp_path, red), root=str(tmp_path))
    assert found["general"]["flashes"] == 0
    assert found["red"]["flashes"] >= 7
    assert found["worst"]["kind"] == "red"


def test_a_ramp_over_several_frames_counts_as_the_change_it_is(tmp_path):
    ramp = []
    for i in range(120):
        phase = i % 10
        level = 30 + (210 * phase // 4 if phase < 5 else 210 * (9 - phase) // 4)
        ramp.append(((level, level, level),))
    found = flashes.flashes(run(tmp_path, ramp), root=str(tmp_path))
    assert found["general"]["flashes"] >= 5


def test_the_project_config_overrides_the_guidance(tmp_path):
    name = run(tmp_path, toggling(4))
    (tmp_path / "polyweave.toml").write_text("[flashes]\nlimit = 10\n")
    found = flashes.flashes(name, root=str(tmp_path))
    assert found["limit"] == 10
    assert found["passed"] is True


def test_a_spec_bounds_the_flashes_of_a_capture(tmp_path):
    run(tmp_path, toggling(4), name="captures/boss")
    (tmp_path / "boss.accept.toml").write_text(
        'asset = "boss"\nartefact = "captures/boss/sequence.json"\n\n'
        '[[predicate]]\nid = "photosensitive"\nmeasure = "flashes"\nmax = 3\n'
    )
    found = accept.checked("boss.accept.toml", "captures/boss/sequence.json",
                           root=str(tmp_path))
    [predicate] = found["predicates"]
    assert predicate["passed"] is False
    assert predicate["value"] >= 7
    assert "not found" in predicate["certifies"]


def test_a_folder_with_no_frames_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("")
    with pytest.raises(PolyweaveError) as caught:
        flashes.flashes("nowhere", root=str(tmp_path))
    assert caught.value.code == "capture.no-frames"
