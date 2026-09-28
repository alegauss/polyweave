"""How tall a silhouette stands for its width (§PW292).

Starship's owner holds every enemy to 0.6 at least, since a thin one is hard to shoot,
and four Lancer candidates came back flat with nothing to refuse them.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave import accept
from polyweave import measure as M
from polyweave.render.ladder import rung_for


def shape(where, width, height, *, size=(200, 200)):
    """An opaque rectangle of `width` by `height` on a transparent picture."""
    pixels = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    top, left = (size[1] - height) // 2, (size[0] - width) // 2
    pixels[top:top + height, left:left + width] = (200, 60, 255, 255)
    Image.fromarray(pixels, "RGBA").save(where)
    return where


@pytest.mark.parametrize(("width", "height", "aspect"), [(100, 50, 0.5), (60, 120, 2.0),
                                                         (80, 80, 1.0)])
def test_it_is_the_subject_s_height_over_its_width(tmp_path, width, height, aspect):
    picture = shape(tmp_path / "a.png", width, height)
    taken = M.measure(picture, ["silhouette_aspect"], root=tmp_path)[0]
    assert taken["value"] == pytest.approx(aspect)
    assert taken["region"] == "subject"


def test_it_answers_on_the_real_mesh_and_not_the_sphere():
    assert rung_for("silhouette_aspect") == "preview"


def test_a_spec_refuses_an_enemy_too_flat_to_hit(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    shape(tmp_path / "flat.png", 150, 45)
    shape(tmp_path / "tall.png", 100, 70)
    (tmp_path / "enemy.accept.toml").write_text(
        'asset = "enemy"\n[[predicate]]\nid = "tall-enough-to-hit"\n'
        'measure = "silhouette_aspect"\nmin = 0.6\n', encoding="utf-8")
    flat = accept.checked("enemy.accept.toml", "flat.png", root=str(tmp_path))
    tall = accept.checked("enemy.accept.toml", "tall.png", root=str(tmp_path))
    assert flat["failed"] == ["tall-enough-to-hit"]
    assert tall["passed"] is True
