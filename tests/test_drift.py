"""Drift, refused by number before a person looks (§PW167).

Every picture here is drawn: a filled disc with a dark ring around it, on a transparent
ground, which is the shape of a flat drawing the canon would hold.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import style

GOLD, PLUM = "#f2c14e", "#3a2e39"
PROJECT = f'[style]\ncanon = "canon"\npalette = ["{GOLD}", "{PLUM}"]\n'


def drawn(path, fill=(242, 193, 78), ring=(58, 46, 57), width=4, radius=40):
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    box = (64 - radius, 64 - radius, 64 + radius, 64 + radius)
    pen.ellipse(box, fill=fill + (255,), outline=ring + (255,), width=width)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def canon(tmp_path, *variants):
    (tmp_path / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    entries = []
    for i, over in enumerate(variants):
        name = f"c{i}.png"
        drawn(tmp_path / "canon" / name, **over)
        entries.append({"picture": name, "sha256": str(i)})
    (tmp_path / "canon" / "canon.json").write_text(json.dumps(entries), "utf-8")
    return tmp_path


APPROVED = ({}, {"radius": 38}, {"fill": (240, 190, 80)})


def test_a_picture_like_the_canon_passes(tmp_path):
    where = canon(tmp_path, *APPROVED)
    drawn(where / "new.png", radius=39)
    found = style.drift("new.png", root=where)
    assert found["judged"] is True
    assert found["passed"] is True, found["drifted"]
    assert "whether it is still the same character or subject" in found["not_checked"]


def test_a_picture_off_the_palette_is_refused_and_says_which_way(tmp_path):
    where = canon(tmp_path, *APPROVED)
    drawn(where / "new.png", fill=(60, 110, 220))
    found = style.drift("new.png", root=where)
    assert found["passed"] is False
    palette = found["measures"]["palette_delta_e_p95"]
    assert palette["drifted"] and palette["which_way"] == "cooler"
    assert palette["value"] > palette["canon"] + palette["floor"]


def test_heavier_lines_are_refused_as_thicker(tmp_path):
    where = canon(tmp_path, *APPROVED)
    drawn(where / "new.png", width=12)
    found = style.drift("new.png", root=where)
    line = found["measures"]["line_weight"]
    assert line["drifted"]
    assert line["which_way"].startswith("thicker lines")


def test_a_canon_of_one_has_no_floor_and_says_so(tmp_path):
    where = canon(tmp_path, {})
    drawn(where / "new.png", fill=(60, 110, 220))
    found = style.drift("new.png", root=where)
    assert found["judged"] is False
    assert found["passed"] is None
    assert found["floor"].startswith("none: the canon holds 1 picture")


def test_an_empty_frame_is_refused(tmp_path):
    where = canon(tmp_path, *APPROVED)
    Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(where / "empty.png")
    with pytest.raises(Exception) as caught:
        style.drift("empty.png", root=where)
    assert caught.value.code == "style.no-subject"
