"""Taking a service's painted shading back out of a texture.

§PW49. The threshold is the interesting part: Cottony's own pass carried three constants
found by eye, and what replaces them is the texture's own statistics. So most of what is
asserted here is about where the bar lands on textures whose content is known, and the
rest is against Cottony's real hammer in `test_real_assets.py`.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import texture


def flat(value=0.5, side=64):
    """A texture with nothing in it, which must be found to have nothing in it."""
    out = np.full((side, side, 4), value, dtype=np.float32)
    out[:, :, 3] = 1.0
    return out


def noisy(side=64, amount=0.02, seed=3):
    """Ordinary texture detail: variation everywhere, nothing that is a mark."""
    rng = np.random.default_rng(seed)
    out = flat(side=side)
    out[:, :, :3] += rng.normal(0.0, amount, (side, side, 3)).astype(np.float32)
    return np.clip(out, 0.0, 1.0)


def painted(side=64, depth=0.3, seed=3):
    """The same, with a dark line drawn across it: a shadow that cannot move."""
    out = noisy(side=side, seed=seed)
    out[side // 2 : side // 2 + 2, :, :3] -= depth
    return np.clip(out, 0.0, 1.0)


# -- what a mark is ---------------------------------------------------------------


def test_a_painted_mark_is_found():
    found = texture.marks(painted())
    assert found["fraction"] > 0.0
    assert found["darkest"] > 0.2, "the line is a third of the range below its ground"


def test_the_bar_is_read_off_the_texture_rather_than_stated():
    """The whole point: Cottony's three constants were found by eye."""
    faint = texture.marks(noisy(amount=0.01))
    coarse = texture.marks(noisy(amount=0.08))
    assert coarse["variation"] > faint["variation"]
    assert coarse["bar"] > faint["bar"], "a noisier texture needs a higher bar"


def test_ordinary_detail_is_not_a_mark():
    """A texture with variation everywhere and nothing painted into it."""
    found = texture.marks(noisy())
    assert found["fraction"] < 0.02, f"detail is not a mark: {found['fraction']}"


def test_a_flat_texture_has_nothing_in_it():
    found = texture.marks(flat())
    assert found["fraction"] == 0.0
    assert found["darkest"] == pytest.approx(0.0, abs=1e-6)


def test_the_mark_is_what_separates_and_not_the_darkness():
    """A texture that is dark all over has no marks; one dark line has one."""
    assert texture.marks(flat(0.1))["fraction"] == 0.0
    assert texture.marks(painted())["fraction"] > 0.0


# -- the repair -------------------------------------------------------------------


def test_scrubbing_lifts_the_mark_towards_its_surroundings():
    before = painted()
    after, found = texture.scrub(before)
    line = slice(32, 34)
    assert after[line, :, :3].mean() > before[line, :, :3].mean()
    assert found["fraction"] > 0.0


def test_a_scrubbed_texel_keeps_its_own_hue():
    """A gain rather than a replacement, so the detail a mark crosses survives it."""
    before = painted()
    before[32, 10, :3] = [0.30, 0.10, 0.05]  # a mark over something orange
    after, _ = texture.scrub(before)
    was, now = before[32, 10, :3], after[32, 10, :3]
    assert now.sum() > was.sum(), "it was lifted"
    assert np.argmax(now) == np.argmax(was), "and it is still orange"


def test_a_mark_with_no_light_left_takes_the_colour_round_it():
    """§PW80: a near-black dash lifted by a gain came back the hue of its own noise."""
    before = flat(side=64)
    before[:, :, :3] = [0.85, 0.65, 0.10]  # the wand star's yellow
    before[30:34, 8:56, :3] = [0.03, 0.02, 0.01]  # a dash painted in near-black
    after, found = texture.scrub(before, grow=1)
    assert found["fraction"] > 0.0
    assert np.allclose(after[30:34, 8:56, :3], [0.85, 0.65, 0.10], atol=0.02)


def test_the_rim_of_a_stroke_goes_with_it():
    """Antialiased, a stroke's edge is below the bar and darker than the ground."""
    before = flat(side=64)
    before[:, :, :3] = [0.85, 0.65, 0.10]
    before[31:33, 8:56, :3] = [0.03, 0.02, 0.01]
    before[30, 8:56, :3] = before[33, 8:56, :3] = [0.75, 0.57, 0.09]  # the rim
    after, _ = texture.scrub(before, grow=1)
    assert np.allclose(after[30, 8:56, :3], [0.85, 0.65, 0.10], atol=0.02)


def test_a_darker_shade_of_the_grounds_hue_is_a_mark():
    """§PW80: the hammer's seam is purple on pink, dark in colour more than in light."""
    before = flat(side=64)
    before[:, :, :3] = [0.94, 0.41, 0.65]  # the hammer's pink
    before[30:36, 8:56, :3] = [0.75, 0.33, 0.55]  # a soft purple dash
    assert texture.marks(before)["shaded"][32, 30]
    after, _ = texture.scrub(before, grow=1)
    assert np.allclose(after[32, 30, :3], [0.94, 0.41, 0.65], atol=0.03)


def test_another_colours_island_is_not_a_shade():
    """A UV sheet packs the brown handle by the pink head; brown is not dark pink."""
    before = flat(side=64)
    before[:, :, :3] = [0.94, 0.41, 0.65]
    before[:, 40:, :3] = [0.60, 0.36, 0.15]
    assert not texture.marks(before)["shaded"].any()


def test_the_reach_follows_the_size_of_the_sheet():
    """A window of 21 texels on a 4096 sheet sat inside the wand's dashes (§PW80)."""
    assert texture.marks(flat(side=64))["reach"] == texture.REACH
    assert texture.scaled(texture.REACH, (4096, 4096)) == 40


def test_scrubbing_a_clean_texture_changes_nothing():
    before = noisy()
    after, found = texture.scrub(before)
    assert found["fraction"] < 0.02
    assert np.allclose(after, before, atol=0.02)


def test_a_stricter_bar_catches_less():
    loose, _ = texture.scrub(painted(), strictness=1.0)
    tight, _ = texture.scrub(painted(), strictness=6.0)
    assert (
        texture.marks(painted(), strictness=1.0)["fraction"]
        >= texture.marks(painted(), strictness=6.0)["fraction"]
    )
    assert loose.mean() >= tight.mean()


def test_something_that_is_not_a_texture_says_so():
    with pytest.raises(PolyweaveError) as caught:
        texture.marks(np.zeros((8, 8)))
    assert caught.value.code == "texture.not-pixels"


# -- and whether it is worth running at all ---------------------------------------


def test_the_repair_is_only_worth_making_where_it_shows():
    """Measured on the real hammer: under the noise floor at preview, 2.5x it at final.

    A 4096-square texture is sampled far more finely at 1024 pixels than at 256, which
    is the whole of the difference, and a pass over sixteen million texels that changes
    nothing anybody can see is a pass not worth making.
    """
    assert texture.worth_scrubbing("final")
    assert not texture.worth_scrubbing("preview")
    assert not texture.worth_scrubbing("sphere")
