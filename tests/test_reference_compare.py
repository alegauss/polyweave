"""A rebuilt level laid against the video it copies (§PW382).

Both sides are drawn here: the reference shows three cyan enemies from 1.0 s, five from
2.0 s; the game's capture starts half a second later, shows them from 1.5 s, and only
three where the reference has five, which is the gap the comparison must find.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image, ImageDraw

from polyweave import provenance, reference_compare
from polyweave.errors import PolyweaveError

KINDS = {"enemy": {"colour": "#3fe8ff", "size": [40, 400]}}


def side(tmp_path, name, delay, late_five):
    folder = tmp_path / ".polyweave" / "references" / name
    folder.mkdir(parents=True)
    listed = []
    for n in range(14):
        at = n * 0.25
        image = Image.new("RGB", (640, 360), (8, 8, 20))
        draw = ImageDraw.Draw(image)
        shown = 0 if at < 1.0 + delay else (5 if at >= 2.0 + delay and late_five else 3)
        for k in range(shown):
            draw.rectangle((80 + 90 * k, 150, 92 + 90 * k, 162), fill=(63, 232, 255))
        file = f"t{int(at * 1000):08d}.png"
        image.save(folder / file)
        listed.append({"ms": int(at * 1000), "file": file})
    (folder / "frames.json").write_text(json.dumps({"frames": listed}),
                                        encoding="utf-8")
    return f".polyweave/references/{name}"


@pytest.fixture
def both(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    return (side(tmp_path, "video", 0.0, True), side(tmp_path, "game", 0.5, False))


def test_two_sides_are_aligned_by_their_first_object(tmp_path, both):
    made = reference_compare.compare(*both, KINDS, anchor="first", root=str(tmp_path))
    assert made["offset"] == pytest.approx(0.5)
    # Aligned, the only gap is where the reference shows five and the game three.
    assert {g["at"] for g in made["gaps"]} == set()
    made = reference_compare.compare(*both, KINDS, anchor="first", bound=1,
                                     root=str(tmp_path))
    assert {g["at"] for g in made["gaps"]} == {2.0, 2.25, 2.5, 2.75}
    # Aligned past the end of the game's footage: said, never compared with its edge.
    assert made["unmatched"] == [3.0, 3.25]
    first = made["gaps"][0]
    assert (first["reference"], first["game"], first["game_at"]) == (5, 3, 2.5)


def test_without_alignment_the_late_start_reads_as_gaps(tmp_path, both):
    made = reference_compare.compare(*both, KINDS, bound=2, root=str(tmp_path))
    assert {g["at"] for g in made["gaps"]} == {1.0, 1.25}


# The rebuilt level declared five: three at one second, two more at two (§PW406).
WAVE = ([{"second": 1.0, "kind": "enemy", "weight": 1, "until": 3.5}] * 3
        + [{"second": 2.0, "kind": "enemy", "weight": 1, "until": 3.5}] * 2)


def test_a_gap_carries_what_the_declared_wave_asked_for_then(tmp_path, both):
    made = reference_compare.compare(*both, KINDS, anchor="first", bound=1,
                                     wave=WAVE, root=str(tmp_path))
    first = made["gaps"][0]
    # The game shows three where the declaration asked for five: two never spawned.
    assert (first["reference"], first["game"], first["declared"]) == (5, 3, 5)
    written = json.loads((tmp_path / made["compare"]).read_text("utf-8"))
    assert written["declared"]["alive"][:3] == [0.0, 3.0, 5.0]


def test_a_wave_written_by_the_game_is_read_from_its_file_and_recorded(tmp_path, both):
    (tmp_path / "wave.json").write_text(json.dumps({"events": WAVE}), "utf-8")
    made = reference_compare.compare(*both, KINDS, anchor="first", bound=1,
                                     wave_file="wave.json", wave_at=0.5,
                                     root=str(tmp_path))
    # Placed half a second later, the gap at 2.0 s falls in the wave's first second.
    assert made["gaps"][0]["declared"] == 3.0
    record = provenance.read(made["compare"], root=str(tmp_path))
    assert "wave" in {one["role"] for one in record["inputs"]}


def test_without_a_wave_a_gap_says_nothing_declared(tmp_path, both):
    made = reference_compare.compare(*both, KINDS, anchor="first", bound=1,
                                     root=str(tmp_path))
    assert "declared" not in made["gaps"][0]


def test_the_comparison_is_recorded_with_both_sides_and_drawn(tmp_path, both):
    made = reference_compare.compare(*both, KINDS, anchor="first", root=str(tmp_path))
    record = provenance.read(made["compare"], root=str(tmp_path))
    roles = {one["role"] for one in record["inputs"]}
    assert roles == {"reference", "capture"}
    assert (tmp_path / made["chart"]).is_file()
    with Image.open(tmp_path / made["sheets"][0]) as sheet:
        assert sheet.width == 2 * reference_compare.TILE


def test_an_anchor_nothing_shows_on_is_refused(tmp_path, both):
    with pytest.raises(PolyweaveError) as refused:
        reference_compare.compare(*both, {"x": {"colour": "#ff00ff", "size": [4, 40]}},
                                  anchor="first", root=str(tmp_path))
    assert refused.value.code == "capture.bad-kinds"
