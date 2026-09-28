"""A store's capsule set, cut from one key art (§PW268).

Starship wrote a crop script of its own for Steam's ten shapes. The key art here is a
gradient with a bright marker at the focus, so a crop can be seen to keep it, and the
logo is bars of known thickness, so its stroke at each size is arithmetic.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave import provenance, store
from polyweave.errors import PolyweaveError


def key_art(where, size=(3840, 2160), focus=(0.7, 0.4)):
    across = np.linspace(0, 255, size[0], dtype=np.uint8)
    pixels = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    pixels[..., 0] = across
    pixels[..., 3] = 255
    x, y = round(focus[0] * size[0]), round(focus[1] * size[1])
    pixels[y - 40 : y + 40, x - 40 : x + 40, :3] = 255
    Image.fromarray(pixels).save(where)


def wordmark(where, size=(1600, 400), stroke=40):
    """Bars `stroke` pixels thick, standing in for a wordmark's letters."""
    pixels = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    for left in range(0, size[0], stroke * 3):
        pixels[40 : size[1] - 40, left : left + stroke] = (240, 240, 240, 255)
    Image.fromarray(pixels).save(where)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "art").mkdir()
    key_art(tmp_path / "art" / "key-art.png")
    wordmark(tmp_path / "art" / "wordmark.png")
    return tmp_path


def test_every_steam_shape_is_cut_at_its_size_and_recorded(project):
    made = store.capsules("art/key-art.png", "art/wordmark.png", out="store/steam",
                          focus=[0.7, 0.4], root=str(project))
    assert made["ok"] is True and len(made["capsules"]) == 10
    for name, one in made["capsules"].items():
        with Image.open(project / one["file"]) as capsule:
            assert list(capsule.size) == one["size"], name
        assert provenance.read(one["file"], root=str(project))["kind"] == "picture"
    assert made["capsules"]["library_hero"]["logo"] == "none"
    assert made["capsules"]["library_hero"]["stroke"] is None


def test_the_crop_keeps_the_focus(project):
    made = store.capsules("art/key-art.png", "art/wordmark.png", out="store/steam",
                          focus=[0.7, 0.4], root=str(project))
    # The square spans the art's full height, so the crop moves across it only: the
    # marker lands in the middle column, 40% down.
    with Image.open(project / made["capsules"]["community_icon"]["file"]) as icon:
        seen = icon.convert("RGB").getpixel((92, round(0.4 * 184)))
    assert min(seen) > 240  # the white marker, not the red gradient around it


def test_the_library_logo_is_the_logo_alone_on_alpha(project):
    made = store.capsules("art/key-art.png", "art/wordmark.png", out="store/steam",
                          root=str(project))
    with Image.open(project / made["capsules"]["library_logo"]["file"]) as logo:
        assert logo.getpixel((0, 0))[3] == 0


def test_a_logo_too_thin_to_read_at_the_small_capsule_fails_it(project):
    wordmark(project / "art" / "thin.png", stroke=4)
    made = store.capsules("art/key-art.png", "art/thin.png", out="store/steam",
                          root=str(project))
    assert made["ok"] is False
    assert "small_capsule" in made["failed"]
    assert made["capsules"]["small_capsule"]["stroke"] < 2.0
    assert "would not read on" in made["says"]


def test_a_key_art_smaller_than_a_shape_is_refused_before_anything_is_written(project):
    key_art(project / "art" / "small.png", size=(1920, 1080))
    with pytest.raises(PolyweaveError) as refused:
        store.capsules("art/small.png", "art/wordmark.png", out="store/steam",
                       root=str(project))
    assert refused.value.code == "store.too-small"
    assert "library_hero needs 3840x1240" in refused.value.message
    assert not (project / "store").exists()
    # Starship's key art is 2560x1440: every shape but the hero can be cut now.
    cuttable = refused.value.as_dict()["allowed"]
    assert "library_hero" not in cuttable and "small_capsule" in cuttable
    made = store.capsules("art/small.png", "art/wordmark.png", out="store/steam",
                          shapes=cuttable, root=str(project))
    assert sorted(made["capsules"]) == sorted(cuttable)


@pytest.mark.parametrize(
    ("call", "code"),
    [
        ({"store": "itch"}, "store.unknown"),
        ({"focus": [1.5, 0.5]}, "store.bad-focus"),
        ({"logo": "art/none.png"}, "store.no-picture"),
    ],
)
def test_what_cannot_be_cut_is_refused_with_a_code(project, call, code):
    asked = {"key_art": "art/key-art.png", "logo": "art/wordmark.png",
             "out": "store/x", "root": str(project), **call}
    with pytest.raises(PolyweaveError) as refused:
        store.capsules(**asked)
    assert refused.value.code == code


def test_a_project_declares_a_store_of_its_own(project):
    (project / "mine.toml").write_text(
        'name = "mine"\n[shape.banner]\nsize = [800, 200]\nlogo = "centre"\n',
        encoding="utf-8")
    made = store.capsules("art/key-art.png", "art/wordmark.png", out="store/mine",
                          store="mine.toml", root=str(project))
    assert list(made["capsules"]) == ["banner"] and made["store"] == "mine"
