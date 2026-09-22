"""Change is perceptual, not byte-wise.

The measure this line has to meet is stated in `measurements.md`: sampler noise is the
noise floor any usable distance metric must sit above, **and the first implementation
has to demonstrate the separation on that case rather than assert it**. So the first
test builds Cottony's case — 29,696 pixels differing by no more than 1/255. The same
question is asked of a real path tracer in `test_render.py`, where there is one to run.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import config as C
from polyweave import measure
from polyweave.errors import PolyweaveError

SIDE = 1024  # so 29,696 differing pixels is the proportion Cottony measured: 2.8%


def scene(tmp_path, name, *, seed=0):
    """A picture with structure in it, so a difference has somewhere to hide."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:SIDE, 0:SIDE]
    rgba = np.zeros((SIDE, SIDE, 4), dtype=np.uint8)
    rgba[:, :, 0] = (x * 255 // SIDE).astype(np.uint8)
    rgba[:, :, 1] = (y * 255 // SIDE).astype(np.uint8)
    rgba[:, :, 2] = ((x + y) * 127 // SIDE).astype(np.uint8)
    rgba[:, :, 3] = 255
    del rng
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def with_noise(tmp_path, source, name, *, pixels=29_696, amount=1, seed=7):
    """The same picture with `pixels` of it moved by `amount`, and nothing else."""
    rgba = np.asarray(PILImage.open(source).convert("RGBA")).copy()
    rng = np.random.default_rng(seed)
    flat = rng.choice(SIDE * SIDE, size=pixels, replace=False)
    rows, columns = np.unravel_index(flat, (SIDE, SIDE))
    jitter = rng.choice([-amount, amount], size=(pixels, 3))
    patch = rgba[rows, columns, :3].astype(np.int16) + jitter
    rgba[rows, columns, :3] = np.clip(patch, 0, 255).astype(np.uint8)
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def project(tmp_path, text="") -> object:
    (tmp_path / C.FILENAME).write_text(text, encoding="utf-8")
    return tmp_path


# -- the separation, demonstrated ------------------------------------------------------


def test_sampler_noise_reads_as_the_same_picture(tmp_path):
    """29,696 pixels differing, none by more than 1/255 — a render nobody touched."""
    original = scene(tmp_path, "a.png")
    noisy = with_noise(tmp_path, original, "b.png")

    differing = int(
        (
            np.asarray(PILImage.open(original).convert("RGBA"))[:, :, :3]
            != np.asarray(PILImage.open(noisy).convert("RGBA"))[:, :, :3]
        )
        .any(axis=-1)
        .sum()
    )
    assert differing == 29_696, "the case is built, not assumed"

    found = measure.same(original, noisy, root=project(tmp_path), region="frame")
    assert found["same"] is True
    assert found["distance"] <= found["tolerance"]


def test_a_real_change_reads_as_a_change(tmp_path):
    """A highlight that moved: few pixels, far apart, which a mean would dilute away."""
    original = scene(tmp_path, "a.png")
    moved = np.asarray(PILImage.open(original).convert("RGBA")).copy()
    moved[20:40, 20:40, :3] = (255, 255, 255)  # 400 pixels of a million
    path = tmp_path / "c.png"
    PILImage.fromarray(moved, "RGBA").save(path)

    found = measure.same(original, path, root=project(tmp_path), region="frame")
    assert found["same"] is False
    assert found["distance"] > found["tolerance"]
    assert "past a tolerance" in found["why"]


def test_the_noise_floor_and_a_real_change_are_orders_apart(tmp_path):
    """Not merely on opposite sides of the bar, but far enough not to be delicate."""
    original = scene(tmp_path, "a.png")
    noisy = with_noise(tmp_path, original, "b.png")
    changed = np.asarray(PILImage.open(original).convert("RGBA")).copy()
    changed[20:40, 20:40, :3] = (255, 255, 255)
    path = tmp_path / "c.png"
    PILImage.fromarray(changed, "RGBA").save(path)

    noise = measure.measure(original, ["distance"], against=noisy, region="frame")[0][
        "value"
    ]
    real = measure.measure(original, ["distance"], against=path, region="frame")[0][
        "value"
    ]
    assert real > noise * 20


def test_a_small_change_is_not_diluted_by_the_frame_around_it(tmp_path):
    """§PW9's lesson here too: 0.04% of the frame still has to register."""
    original = scene(tmp_path, "a.png")
    changed = np.asarray(PILImage.open(original).convert("RGBA")).copy()
    changed[0:20, 0:20, :3] = (255, 255, 255)  # 400 pixels of a million
    path = tmp_path / "c.png"
    PILImage.fromarray(changed, "RGBA").save(path)

    found = measure.measure(original, ["distance"], against=path, region="frame")
    assert found[0]["value"] > 0.1


# -- the threshold is the project's ----------------------------------------------------


def test_the_tolerance_comes_from_the_project(tmp_path):
    original = scene(tmp_path, "a.png")
    noisy = with_noise(tmp_path, original, "b.png")
    where = project(
        tmp_path,
        "[tolerance]\nrender_noise = { sphere = 0.0, preview = 0.0, final = 0.0 }\n",
    )
    found = measure.same(original, noisy, root=where, region="frame")
    assert found["tolerance"] == 0.0
    assert "render_noise" in found["tolerance_from"]
    assert found["same"] is False  # nothing is identical to a path-traced twin


def test_a_caller_may_state_its_own_bar(tmp_path):
    """The bar for sampler noise is not the bar for a silhouette within three pixels."""
    original = scene(tmp_path, "a.png")
    noisy = with_noise(tmp_path, original, "b.png")
    strict = measure.same(
        original, noisy, tolerance=0.0, root=project(tmp_path), region="frame"
    )
    assert strict["tolerance"] == 0.0


# -- changed_fraction ------------------------------------------------------------------


def test_changed_fraction_counts_what_moved_past_a_stated_amount(tmp_path):
    original = scene(tmp_path, "a.png")
    noisy = with_noise(tmp_path, original, "b.png", pixels=40_000, amount=60)
    found = measure.measure(
        original, ["changed_fraction"], against=noisy, delta=0.05, region="frame"
    )
    assert found[0]["value"] == pytest.approx(40_000 / (SIDE * SIDE), abs=0.005)


def test_changed_fraction_refuses_to_guess_the_amount(tmp_path):
    original = scene(tmp_path, "a.png")
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(original, ["changed_fraction"], against=original)
    assert caught.value.code == "spec.measure-needs"
    assert "delta" in caught.value.remedy


# -- refusals --------------------------------------------------------------------------


def test_a_comparison_needs_something_to_compare_against(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(scene(tmp_path, "a.png"), ["distance"])
    assert caught.value.code == "spec.measure-needs"
    assert "against" in caught.value.remedy


def test_two_sizes_cannot_be_compared(tmp_path):
    original = scene(tmp_path, "a.png")
    small = tmp_path / "small.png"
    PILImage.open(original).resize((32, 32)).save(small)
    with pytest.raises(PolyweaveError) as caught:
        measure.measure(original, ["distance"], against=small, region="frame")
    assert caught.value.code == "spec.size-mismatch"


def test_a_picture_is_the_same_as_itself(tmp_path):
    original = scene(tmp_path, "a.png")
    found = measure.same(original, original, root=project(tmp_path), region="frame")
    assert found["same"] is True
    assert found["distance"] == 0.0
    assert found["changed_fraction"] == 0.0


# -- the floor moves with the rung, and measuring beats configuring (§PW44) ------------


def test_the_floor_is_read_for_the_rung_rather_than_being_one_number(tmp_path):
    """Two seeds of one sphere sit 0.0234 apart at the sphere rung and 0.0122 at final,
    so a single number calls one of them a change whichever number is chosen."""
    where = project(tmp_path)
    loose = C.load(where).tolerances("sphere").render_noise
    tight = C.load(where).tolerances("final").render_noise
    assert loose > tight, "a cheaper rung is noisier, and its bar has to be wider"


def test_naming_no_rung_takes_the_strictest_floor(tmp_path):
    """The safe way to be wrong: too tight calls an unchanged render changed, which is
    a wasted look, and too loose calls a changed one unchanged, which is a wrong answer.
    """
    where = project(tmp_path)
    every = C.load(where).table("tolerance")["render_noise"].values()
    assert C.load(where).tolerances().render_noise == min(every)


def test_a_verdict_says_which_floor_it_rested_on(tmp_path):
    original = scene(tmp_path, "a.png")
    found = measure.same(original, original, root=project(tmp_path), region="frame")
    assert "render_noise" in found["tolerance_from"]
    assert (
        measure.same(
            original, original, tolerance=0.5, root=project(tmp_path), region="frame"
        )["tolerance_from"]
        == "stated by the caller"
    )


def test_a_twin_render_measures_the_floor_instead_of_assuming_it(tmp_path):
    """The better of the two routes: one render, right at any sample count."""
    original = scene(tmp_path, "a.png")
    twin = with_noise(tmp_path, original, "twin.png")
    changed = with_noise(tmp_path, original, "c.png", pixels=400_000, amount=60, seed=3)

    found = measure.same(
        original, changed, twin=twin, root=project(tmp_path), region="frame"
    )
    assert found["tolerance_from"] == "measured from a twin render"
    assert found["tolerance"] == pytest.approx(
        measure.noise_floor(original, twin, region="frame", alpha_floor=0.0)
    )
    assert found["same"] is False, "and a real change still reads as one"


def test_the_measured_floor_forgives_exactly_the_noise_it_was_measured_from(tmp_path):
    original = scene(tmp_path, "a.png")
    twin = with_noise(tmp_path, original, "twin.png")
    found = measure.same(
        original, twin, twin=twin, root=project(tmp_path), region="frame"
    )
    assert found["same"] is True, "the floor is the distance, so it cannot be exceeded"


def test_a_twin_beats_a_stated_bar_which_beats_the_configured_one(tmp_path):
    """Stated in the order the answer prefers them, so the preference is checkable."""
    original = scene(tmp_path, "a.png")
    twin = with_noise(tmp_path, original, "twin.png")
    where = project(tmp_path)
    both = measure.same(
        original, twin, twin=twin, tolerance=0.9, root=where, region="frame"
    )
    assert both["tolerance_from"] == "measured from a twin render"


def test_the_rung_is_read_off_the_record_rather_than_asked_for(tmp_path):
    """§PW6 wrote it down, and a caller repeating it is one who can get it wrong."""
    from polyweave import provenance

    where = project(tmp_path)
    original = scene(tmp_path, "a.png")
    provenance.write(
        provenance.build("render", "a.png", rung="sphere", root=where), root=where
    )
    found = measure.same(original, original, root=where, region="frame")
    assert found["rung"] == "sphere"
    assert found["tolerance"] == C.load(where).tolerances("sphere").render_noise


def test_an_image_with_no_record_is_held_to_the_strictest_floor(tmp_path):
    original = scene(tmp_path, "a.png")
    found = measure.same(original, original, root=project(tmp_path), region="frame")
    assert found["rung"] is None
