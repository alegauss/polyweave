"""A render answered as two digests (§PW141).

"Did my bevel change the outline" used to mean measuring both pictures again. A bake now
leaves two short hashes, one over the outline and one over the look, each quantised at
the rung's noise floor, so the question is a string comparison across sessions.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import measure
from polyweave.image import load

NOISE = 0.02
FLOOR = 0.02


def disc(tmp_path, name, *, centre=(32, 32), radius=16, colour=(200, 80, 60), jitter=0):
    """A flat disc on a transparent frame, with optional per-pixel noise."""
    ys, xs = np.mgrid[0:64, 0:64]
    inside = (xs - centre[0]) ** 2 + (ys - centre[1]) ** 2 <= radius**2
    rgba = np.zeros((64, 64, 4), dtype=np.int16)
    rgba[inside] = [*colour, 255]
    if jitter:
        noise = np.random.default_rng(7).integers(-jitter, jitter + 1, (64, 64, 3))
        rgba[..., :3] = np.where(inside[..., None], rgba[..., :3] + noise, 0)
    where = tmp_path / name
    PILImage.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(where)
    return where


def digested(path, **kw):
    return measure.digests(load(path), alpha_floor=FLOOR, noise=NOISE, **kw)


def test_the_figures_are_the_outline_and_the_look(tmp_path):
    found = measure.figures(load(disc(tmp_path, "a.png")), alpha_floor=FLOOR)
    assert found["shape"]["box"] == [16 / 64, 16 / 64, 49 / 64, 49 / 64]
    assert found["shape"]["anchor"] == [32.5 / 64, 49 / 64]
    assert 0.19 < found["shape"]["coverage"] < 0.21
    assert set(found["look"]["luma"]) == {"p5", "p50", "p95"}
    assert len(found["look"]["palette"]) == 3


def test_noise_alone_moves_neither_digest(tmp_path):
    clean = digested(disc(tmp_path, "a.png"))
    noisy = digested(disc(tmp_path, "b.png", jitter=1))
    assert noisy["shape_digest"] == clean["shape_digest"]
    assert noisy["look_digest"] == clean["look_digest"]


def test_a_restyle_moves_the_look_and_not_the_outline(tmp_path):
    before = digested(disc(tmp_path, "a.png"))
    after = digested(disc(tmp_path, "b.png", colour=(60, 90, 200)))
    assert after["shape_digest"] == before["shape_digest"]
    assert after["look_digest"] != before["look_digest"]


def test_a_changed_outline_moves_the_shape_digest(tmp_path):
    before = digested(disc(tmp_path, "a.png"))
    after = digested(disc(tmp_path, "b.png", radius=22))
    assert after["shape_digest"] != before["shape_digest"]


def test_the_triangle_count_is_part_of_the_outline(tmp_path):
    picture = disc(tmp_path, "a.png")
    one = digested(picture, triangles=960)
    assert one["shape_digest"] != digested(picture, triangles=480)["shape_digest"]
    assert one["look_digest"] == digested(picture, triangles=480)["look_digest"]


def test_an_empty_picture_is_refused_rather_than_hashed(tmp_path):
    empty = tmp_path / "empty.png"
    PILImage.new("RGBA", (16, 16), (0, 0, 0, 0)).save(empty)
    with pytest.raises(measure.PolyweaveError) as refused:
        digested(empty)
    assert refused.value.code == "spec.empty-region"


def test_the_operation_digests_a_picture_by_path(tmp_path):
    disc(tmp_path, "a.png")
    found = measure.digest("a.png", rung="preview", root=str(tmp_path))
    assert len(found["shape_digest"]) == len(found["look_digest"]) == 16
    assert found["rung"] == "preview"
    assert found["quantum"] == pytest.approx(0.02)


def test_a_bake_returns_and_records_both_digests(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C
    from polyweave import provenance, render

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, *a, **k):
            pass

    at = {"rung": "sphere", "root": tmp_path, "inline": False}
    first = render.bake(Quiet(), out="a.png", **at)
    again = render.bake(Quiet(), out="b.png", **at)
    record = provenance.read("a.png", root=str(tmp_path))
    assert len(first["shape_digest"]) == 16
    assert record["digest"]["shape_digest"] == first["shape_digest"]
    assert again["cached"] is True
    assert again["look_digest"] == first["look_digest"]
