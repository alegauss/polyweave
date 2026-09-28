"""How well a target stands out from what lies behind it (Â§PW272).

Starship's shots were measured against the box beside each, twice per shot, in a script
of the project's own. The pictures here are flat fields with known greys, so each ratio
is the WCAG arithmetic on two luminances.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave import accept, contrast
from polyweave.errors import PolyweaveError


def field(where, *, back=(40, 40, 40), shots=(((20, 20), (255, 255, 255)),)):
    """A dark field with a small square shot at each point, of its own colour."""
    pixels = np.zeros((64, 96, 4), dtype=np.uint8)
    pixels[..., :3] = back
    pixels[..., 3] = 255
    for (x, y), colour in shots:
        pixels[y - 2 : y + 3, x - 2 : x + 3, :3] = colour
    Image.fromarray(pixels).save(where)
    return where


def luminance(value: int) -> float:
    channel = value / 255
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def test_a_white_shot_on_a_dark_field_reads_at_the_wcag_ratio(tmp_path):
    field(tmp_path / "combat.png")
    said = contrast.measured("combat.png", targets=[{"at": [20, 20], "radius": 2}],
                             root=str(tmp_path))
    expected = (1.0 + 0.05) / (luminance(40) + 0.05)
    assert said["targets"][0]["ratio"] == pytest.approx(expected, rel=1e-3)
    assert said["contrast_min"] == said["targets"][0]["ratio"]
    assert said["delta_e_min"] > 50


def test_the_worst_target_is_the_one_named(tmp_path):
    field(tmp_path / "combat.png", shots=(((20, 20), (255, 255, 255)),
                                          ((60, 30), (60, 60, 60))))
    said = contrast.measured(
        "combat.png",
        targets=[{"at": [20, 20], "radius": 2}, {"box": [58, 28, 62, 32]}],
        root=str(tmp_path))
    assert said["worst"]["box"] == [58, 28, 62, 32]
    assert said["contrast_min"] < 1.5 < said["contrast_median"]


def test_targets_come_from_the_line_the_game_printed(tmp_path):
    field(tmp_path / "combat.png", shots=(((20, 20), (255, 255, 255)),
                                          ((60, 30), (255, 80, 80))))
    (tmp_path / "run.log").write_text(
        "noise\ntarget: 20 20 2\ntarget: box 58 28 62 32\nmore\n", encoding="utf-8")
    said = contrast.measured("combat.png", log="run.log", root=str(tmp_path))
    assert len(said["targets"]) == 2
    assert said["targets"][0]["at"] == [20.0, 20.0]


def test_a_spec_bounds_the_worst_shot(tmp_path):
    field(tmp_path / "combat.png", shots=(((20, 20), (255, 255, 255)),
                                          ((60, 30), (60, 60, 60))))
    (tmp_path / "run.log").write_text("target: 20 20 2\ntarget: 60 30 2\n", "utf-8")
    where = tmp_path / "shots.accept.toml"
    where.write_text(
        'asset = "shots"\n[[predicate]]\nid = "legible"\nmeasure = "contrast_min"\n'
        'targets = "run.log"\nmin = 3.0\n', encoding="utf-8")
    found = accept.checked("shots.accept.toml", "combat.png", root=str(tmp_path))
    assert found["failed"] == ["legible"]


def big_shots(where, *, back=(40, 40, 40), fore=(255, 255, 255)):
    """Two shots 20 px across, larger than the default radius sees."""
    pixels = np.zeros((64, 96, 4), dtype=np.uint8)
    pixels[..., :3] = back
    pixels[..., 3] = 255
    for x, y in ((24, 30), (70, 30)):
        rows, cols = np.mgrid[0:64, 0:96]
        pixels[np.hypot(cols - x, rows - y) <= 10, :3] = fore
    Image.fromarray(pixels).save(where)
    return where


def spec(where, **fields):
    lines = ['asset = "shots"', "[[predicate]]", 'id = "legible"',
             'measure = "contrast_min"', "min = 4.5"]
    lines += [f"{k} = {v!r}" if isinstance(v, str) else f"{k} = {v}"
              for k, v in fields.items()]
    where.write_text("\n".join(lines).replace("'", '"') + "\n", encoding="utf-8")
    return where.name


def test_a_spec_gives_the_ring_and_a_default_radius_to_a_json_file(tmp_path):
    big_shots(tmp_path / "shots.png")
    (tmp_path / "orbs.json").write_text(
        '[{"at": [24, 30]}, {"at": [70, 30]}]', encoding="utf-8")
    name = spec(tmp_path / "shots.accept.toml", targets="orbs.json", ring=12, radius=11)
    found = accept.checked(name, "shots.png", root=str(tmp_path))
    assert found["passed"], found
    assert found["predicates"][0]["value"] > 4.5


def test_a_json_file_may_wrap_its_list(tmp_path):
    big_shots(tmp_path / "shots.png")
    (tmp_path / "orbs.json").write_text(
        '{"targets": [{"at": [24, 30], "radius": 11}]}', encoding="utf-8")
    said = contrast.measured("shots.png", log="orbs.json", root=str(tmp_path))
    assert said["targets"][0]["radius"] == 11


def test_a_log_line_carries_its_own_radius_over_the_default(tmp_path):
    big_shots(tmp_path / "shots.png")
    (tmp_path / "run.log").write_text("target: 24 30 11\ntarget: 70 30\n", "utf-8")
    said = contrast.measured("shots.png", log="run.log", radius=12, root=str(tmp_path))
    assert [t["radius"] for t in said["targets"]] == [11.0, 12.0]


def test_a_spec_fails_the_frame_whose_shots_are_lost_in_the_background(tmp_path):
    big_shots(tmp_path / "old.png", back=(200, 200, 200), fore=(230, 230, 230))
    (tmp_path / "orbs.json").write_text('[{"at": [24, 30]}]', encoding="utf-8")
    name = spec(tmp_path / "shots.accept.toml", targets="orbs.json", ring=12, radius=11)
    found = accept.checked(name, "old.png", root=str(tmp_path))
    assert found["failed"] == ["legible"]


def test_a_ring_inside_the_shot_is_refused_rather_than_read_as_one(tmp_path):
    big_shots(tmp_path / "shots.png")
    with pytest.raises(PolyweaveError) as refused:
        contrast.measured("shots.png", targets=[{"at": [24, 30]}], ring=5,
                          root=str(tmp_path))
    assert refused.value.code == "spec.ring-inside-target"
    assert "widen radius" in refused.value.remedy


def test_a_shot_that_truly_matches_its_background_still_reads_one(tmp_path):
    big_shots(tmp_path / "flat.png", fore=(40, 40, 40))
    said = contrast.measured("flat.png", targets=[{"at": [24, 30]}], ring=5,
                             root=str(tmp_path))
    assert said["contrast_min"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "targets", [[], [{"at": [500, 500]}], [{"size": 3}]],
)
def test_a_target_that_cannot_be_measured_is_refused(tmp_path, targets):
    field(tmp_path / "combat.png")
    with pytest.raises(PolyweaveError) as refused:
        contrast.measured("combat.png", targets=targets, root=str(tmp_path))
    assert refused.value.code == "spec.no-targets"
