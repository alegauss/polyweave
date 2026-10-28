"""A declared icon set, built at its sizes and held to legibility (§PW331)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store import icons

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
    SET + '\n[icon.m]\nmodel = "slime.png"\n',
    SET + '\n[icon.m]\nmodel = "slime.glb"\nview = "top"\n',
    SET + '\n[icon.m]\nmodel = "slime.glb"\nlight = { glow = 1 }\n',
    SET + '\n[icon.m]\nmodel = "slime.glb"\nbackground = "red"\n',
    SET + '\n[icon.m]\nmodel = "slime.glb"\nshape = "circle"\n',
    SET + '\n[icon.m]\nmodel = "nowhere.glb"\n',
])
def test_a_set_that_cannot_be_drawn_is_refused(tmp_path, body):
    with pytest.raises(PolyweaveError) as refused:
        icons.build(declared(tmp_path, body), sitting=False, root=str(tmp_path))
    assert refused.value.code == "compose.bad-icons"


def _disc(side: int, radius: float):
    import numpy as np

    y, x = np.mgrid[:side, :side]
    inside = (x - side / 2) ** 2 + (y - side / 2) ** 2 < radius ** 2
    rgba = np.zeros((side, side, 4), np.uint8)
    rgba[inside] = (200, 60, 60, 255)
    return Image.fromarray(rgba, "RGBA")


def test_a_model_s_icon_is_held_to_what_it_fills_and_keeps_at_its_smallest():
    """§PW610: a palette tile reads only if the actor's outline survives the shrink."""
    plain = {"background": "transparent"}
    whole = icons.model_legibility(_disc(128, 50), plain, 32)
    assert whole["coverage"] > 0.4 and whole["silhouette_kept"] > 0.9
    speck = icons.model_legibility(_disc(128, 3), plain, 16)
    assert speck["coverage"] < 0.01 and speck["silhouette_kept"] < 0.5
    on_red = icons.model_legibility(_disc(128, 50), {"background": "#C83C3C"}, 32)
    assert on_red["background_contrast"] == 1.0
    assert whole["background_contrast"] > 1.0


#: A set with a rendered actor beside a drawn button, as a palette mixes them.
MODELLED = """name = "palette"
sizes = [16, 32]

[accept]
coverage_min = 0.05
silhouette_kept_min = 0.5

[icon.cone]
model = "cone.glb"
view = "front"
background = "#20242C"
rung = "preview"

[icon.a]
shape = "circle"
symbol = "A"
"""


def test_an_icon_rendered_from_a_model_goes_stale_with_it(tmp_path):
    """§PW610: rendered from the mesh and recorded against it, so an edit shows."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    import bpy

    from polyweave.kernel import config as C

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 48\nfinal_size = 48\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )

    def cone(radius: float) -> None:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cone_add(radius1=radius, depth=2.0, vertices=32)
        bpy.ops.export_scene.gltf(filepath=str(tmp_path / "cone.glb"),
                                  export_format="GLB")

    cone(1.0)
    (tmp_path / "palette.icons.toml").write_text(MODELLED, encoding="utf-8")
    found = icons.build("palette.icons.toml", sitting=False, root=str(tmp_path))
    assert sorted(found["files"]) == ["palette/a_16.png", "palette/a_32.png",
                                      "palette/cone_16.png", "palette/cone_32.png"]
    assert found["passed"], found["failed"]
    assert set(found["measured"]["cone"]) == {"coverage", "silhouette_kept",
                                              "background_contrast"}
    with Image.open(tmp_path / "palette" / "cone_32.png") as tile:
        assert tile.size == (32, 32)
        assert tile.convert("RGBA").getpixel((0, 0)) == (0x20, 0x24, 0x2C, 255)
    record = provenance.read("palette/cone_32.png", root=tmp_path)
    assert [one["role"] for one in record["inputs"]] == ["icons", "mesh"]
    assert provenance.outdated(root=str(tmp_path))["sound"] is True

    cone(0.4)
    stale = {one["artefact"] for one in provenance.outdated(root=str(tmp_path))
             ["outdated"]}
    assert {"palette/cone_16.png", "palette/cone_32.png"} <= stale
    assert "palette/a_32.png" not in stale
    icons.build("palette.icons.toml", sitting=False, root=str(tmp_path))
    stale = {one["artefact"] for one in provenance.outdated(root=str(tmp_path))
             ["outdated"]}
    assert not {one for one in stale if one.startswith("palette/")}


TOOLS = """name = "tools"
sizes = [32, 64]

[style]
shape = "rounded"

[icon.add]
symbol = "+"

[icon.remove]
symbol = "-"

[icon.left]
symbol = "left"

[icon.ring]
symbol = "ring"

[icon.speck]
symbol = "square"
symbol_scale = 0.2
"""


def test_a_text_symbol_fills_its_face_as_a_glyph_does(tmp_path):
    # Spinhold's toolbar measured "+" at 0.024 and "-" at 0.004 of the face (§PW642).
    found = icons.build(declared(tmp_path, TOOLS), sitting=False, root=str(tmp_path))
    shares = {name: one["symbol_share"] for name, one in found["measured"].items()}
    assert shares["add"] > 0.06 and shares["remove"] > 0.02, shares
    assert shares["add"] >= shares["ring"] * 0.5, shares
    # Text no glyph draws is fitted by its ink, larger than its font size drew it.
    letter = icons.legibility({**icons._STYLE, "shape": "rounded", "symbol": "?"}, 64)
    assert letter["symbol_share"] > 0.04, letter
    # Bound or no bound, a symbol far under the set's median is named.
    assert "speck" in found["measured"]["speck"]
    assert "speck" not in found["measured"]["add"]


def test_a_plus_and_a_minus_are_glyphs_too():
    plus = icons.legibility({**icons._STYLE, "shape": "rounded", "symbol": "plus"}, 64)
    minus = icons.legibility({**icons._STYLE, "shape": "rounded", "symbol": "minus"},
                             64)
    assert plus["symbol_share"] > minus["symbol_share"] > 0.03


@pytest.mark.parametrize("scale", ["0.1", "3", "true"])
def test_a_symbol_scale_out_of_range_is_refused(tmp_path, scale):
    body = TOOLS.replace("symbol_scale = 0.2", f"symbol_scale = {scale}")
    with pytest.raises(PolyweaveError) as refused:
        icons.build(declared(tmp_path, body), sitting=False, root=str(tmp_path))
    assert refused.value.code == "compose.bad-icons"
