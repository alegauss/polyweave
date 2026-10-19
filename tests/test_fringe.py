"""A transparent picture's edge is a number a bound can hold (§PW548).

Spinhold's 4K logo is the transparent copy for stores and streams, and the one thing it
must keep is a clean edge: no dark or white halo round the letters, no wide soft fringe
left by a resize or a matte. `fringe_width` reads the ramp from opaque to clear, and
`fringe_luma` and `fringe_delta_e` the partly transparent pixels against the opaque
colour next to them.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageFilter

from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import ladder, measure

GOLD = (230, 180, 40)


def disc(tmp_path, name: str, *, matte=None, feather: float = 0.0):
    """A gold disc on transparent, drawn at four times its size and brought down, as
    picture.vector draws a mark; `matte` composites it on a colour first, as a copy
    resized over a background is, and `feather` softens its alpha."""
    big = Image.new("RGBA", (640, 640), (0, 0, 0, 0))
    from PIL import ImageDraw

    ImageDraw.Draw(big).ellipse((80, 80, 560, 560), fill=(*GOLD, 255))
    small = big.resize((160, 160), Image.LANCZOS)
    if matte is not None:
        under = Image.new("RGBA", small.size, (*matte, 255))
        flat = Image.alpha_composite(under, small).convert("RGB")
        flat.putalpha(small.getchannel("A"))
        small = flat
    if feather:
        alpha = small.getchannel("A").filter(ImageFilter.GaussianBlur(feather))
        small.putalpha(alpha)
    path = tmp_path / f"{name}.png"
    small.save(path)
    return path


def read(path, names):
    found = measure.measure(path, list(names), region="subject", root=path.parent)
    return {one["measure"]: one["value"] for one in found}


def test_a_drawn_edge_is_narrow_and_its_own_colour(tmp_path):
    # Pillow resizes premultiplied in 8 bits, so a faint pixel's colour is quantised:
    # the drawn disc reads about -0.04 and 2, where a dark matte reads -0.46 and 38.
    said = read(disc(tmp_path, "drawn"),
                ["fringe_width", "fringe_luma", "fringe_delta_e"])
    assert 0 < said["fringe_width"] <= 2
    assert abs(said["fringe_luma"]) < 0.1
    assert said["fringe_delta_e"] < 5


def test_a_dark_matte_reads_as_a_dark_coloured_halo(tmp_path):
    drawn = read(disc(tmp_path, "drawn"), ["fringe_luma", "fringe_delta_e"])
    matted = read(disc(tmp_path, "matted", matte=(0, 0, 0)),
                  ["fringe_luma", "fringe_delta_e"])
    assert matted["fringe_luma"] < -0.1
    assert matted["fringe_delta_e"] > drawn["fringe_delta_e"] + 10


def test_a_feathered_edge_reads_wider(tmp_path):
    crisp = read(disc(tmp_path, "drawn"), ["fringe_width"])["fringe_width"]
    soft = read(disc(tmp_path, "soft", feather=3.0), ["fringe_width"])["fringe_width"]
    assert soft >= crisp + 3


def test_a_picture_with_no_alpha_is_refused_by_name(tmp_path):
    flat = tmp_path / "flat.png"
    Image.new("RGB", (20, 20), GOLD).save(flat)
    with pytest.raises(PolyweaveError) as refused:
        read(flat, ["fringe_width"])
    assert refused.value.code == "spec.measure-needs"
    assert "no alpha" in refused.value.message


def test_the_vectorised_distance_is_the_scalar_one():
    rng = np.random.default_rng(548)
    one = rng.uniform([0, -80, -80], [100, 80, 80], size=(200, 3))
    two = rng.uniform([0, -80, -80], [100, 80, 80], size=(200, 3))
    many = measure.ciede2000_many(one, two)
    each = [measure.ciede2000(a, b) for a, b in zip(one, two, strict=True)]
    assert many == pytest.approx(each, abs=1e-9)


def test_they_are_taken_at_the_final_rung():
    for name in ("fringe_width", "fringe_luma", "fringe_delta_e"):
        assert ladder.rung_for(name) == "final"
