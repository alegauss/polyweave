"""A letter's edge is a number a bound can hold (§PW79).

Cottony's wordmark is cream type on a red panel, and the way type fails is a letter
going soft, not a median drifting. `edge_p99` is the steepest lightness step inside the
subject, so a blur lowers it and the step to transparent at the outline never counts.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw, ImageFilter

from polyweave.layers.geometry.render import ladder
from polyweave.loop import measure

RED = (150, 40, 60, 255)


def panel(tmp_path, *, bar: bool = True, blur: float = 0.0):
    """A red panel with a cream bar across it, on transparent, as the wordmark is."""
    picture = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    draw.rectangle((10, 10, 69, 49), fill=RED)
    if bar:
        draw.rectangle((20, 25, 59, 34), fill=(250, 230, 215, 255))
    if blur:
        rgb = picture.convert("RGB").filter(ImageFilter.GaussianBlur(blur))
        rgb.putalpha(picture.getchannel("A"))
        picture = rgb
    path = tmp_path / f"panel-{bar}-{blur}.png"
    picture.save(path)
    return path


def edge_p99(path) -> float:
    (found,) = measure.measure(path, ["edge_p99"], region="subject", root=path.parent)
    return found["value"]


def test_a_crisp_letter_measures_steeper_than_a_soft_one(tmp_path):
    crisp = edge_p99(panel(tmp_path))
    soft = edge_p99(panel(tmp_path, blur=2.0))
    assert crisp > 0.2
    assert soft < crisp * 0.6


def test_the_outline_against_transparent_is_not_an_edge(tmp_path):
    assert edge_p99(panel(tmp_path, bar=False)) == pytest.approx(0.0)


def test_it_is_taken_at_the_final_rung():
    assert ladder.rung_for("edge_p99") == "final"
