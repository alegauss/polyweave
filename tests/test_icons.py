"""A declared icon set, built at its sizes and held to legibility (§PW331)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import icons, provenance
from polyweave.errors import PolyweaveError

SET = """name = "pad"
sizes = [32, 64]

[accept]
symbol_contrast_min = 3.0
background_contrast_min = 1.5

[icon.a]
shape = "circle"
fill = "#3BA935"
symbol = "A"

[icon.cross]
shape = "circle"
fill = "#2A2D35"
symbol = "cross"
symbol_colour = "#8DB4E8"

[icon.up]
shape = "dpad"
direction = "up"

[icon.menu]
shape = "rounded"
symbol = "menu"
"""


def declared(tmp_path, body=SET):
    (tmp_path / "pad.icons.toml").write_text(body, encoding="utf-8")
    return "pad.icons.toml"


def test_each_icon_lands_at_each_size_with_its_record(tmp_path):
    found = icons.build(declared(tmp_path), sitting=False, root=str(tmp_path))
    assert len(found["files"]) == 8
    with Image.open(tmp_path / "pad" / "a_32.png") as small:
        assert small.size == (32, 32) and small.mode == "RGBA"
    record = provenance.read("pad/a_64.png", root=tmp_path)
    assert record["inputs"][0]["role"] == "icons"
    assert found["passed"], found["failed"]


def test_an_icon_has_a_dark_outline_a_lit_rim_and_a_shaded_face(tmp_path):
    image, face, symbol = icons.draw({**icons._STYLE, "shape": "circle",
                                      "fill": "#3BA935"}, 128)
    pixels = image.load()
    edge, rim = pixels[64, 2], pixels[64, 14]
    top, foot = pixels[64, 30], pixels[64, 100]
    assert sum(edge[:3]) < 100
    assert sum(rim[:3]) > sum(top[:3]) > sum(foot[:3])


def test_a_bound_the_set_fails_is_named_per_icon(tmp_path):
    faint = SET.replace('symbol_colour = "#8DB4E8"', 'symbol_colour = "#30333B"')
    found = icons.build(declared(tmp_path, faint), sitting=False, root=str(tmp_path))
    assert list(found["failed"]) == ["cross"]
    assert found["failed"]["cross"][0].startswith("symbol_contrast")


def test_an_atlas_maps_each_name_to_its_box(tmp_path):
    found = icons.build(declared(tmp_path, SET.replace("sizes = [32, 64]",
                                                       "sizes = [32]\natlas = true")),
                        sitting=False, root=str(tmp_path))
    assert found["files"] == ["pad/pad_32.png"]
    boxes = json.loads((tmp_path / "pad" / "pad_32.json").read_text("utf-8"))
    assert boxes["a"] == [0, 0, 32, 32] and len(boxes) == 4


def test_the_set_waits_on_a_sitting(tmp_path):
    found = icons.build(declared(tmp_path), root=str(tmp_path))
    assert found["sitting"]


@pytest.mark.parametrize("body", [
    SET.replace('shape = "circle"', 'shape = "hex"', 1),
    SET.replace("sizes = [32, 64]", "sizes = [4]"),
    'name = "empty"\n',
    SET + '\n[icon.b]\nshape = "circle"\nglow = 1\n',
])
def test_a_set_that_cannot_be_drawn_is_refused(tmp_path, body):
    with pytest.raises(PolyweaveError) as refused:
        icons.build(declared(tmp_path, body), sitting=False, root=str(tmp_path))
    assert refused.value.code == "compose.bad-icons"
