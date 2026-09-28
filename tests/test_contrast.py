"""How well a target stands out from what lies behind it (§PW272).

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


@pytest.mark.parametrize(
    "targets", [[], [{"at": [500, 500]}], [{"size": 3}]],
)
def test_a_target_that_cannot_be_measured_is_refused(tmp_path, targets):
    field(tmp_path / "combat.png")
    with pytest.raises(PolyweaveError) as refused:
        contrast.measured("combat.png", targets=targets, root=str(tmp_path))
    assert refused.value.code == "spec.no-targets"
