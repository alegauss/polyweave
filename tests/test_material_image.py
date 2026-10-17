"""A declared material may wear a picture through the mesh's UVs (§PW78).

Cottony's booster tray is a cushion inflated from a drawing whose rope and thread are
drawn on it. Built with a colour alone, the cushion came out as a flat cream lozenge
with none of them; the drawing is the picture on its face, as cloth.cushion laid it.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers import geometry
from polyweave.layers.geometry import build, cost

pytest.importorskip("bpy", reason="Blender writes the mesh")

DECLARED = """name    = "panel"
version = 1
output  = "panel"

[materials.cloth]
colour = "#E0D3C1"
image  = "{image}"

[[nodes]]
id        = "panel"
op        = "inflate"
material  = "cloth"
drawing   = "card.png"
thickness = 20.0
size      = 120
"""


def card(tmp_path):
    picture = Image.new("RGBA", (120, 60), (0, 0, 0, 0))
    cream = (230, 200, 160, 255)
    ImageDraw.Draw(picture).rounded_rectangle((4, 4, 116, 56), 20, fill=cream)
    picture.save(tmp_path / "card.png")


def test_the_drawing_is_the_picture_on_its_face(tmp_path):
    card(tmp_path)
    (tmp_path / "panel.toml").write_text(DECLARED.format(image="card.png"), "utf-8")
    declared = geometry.read("panel.toml", root=tmp_path)
    build.write(declared, "panel.glb", root=tmp_path)
    gltf, _ = cost._parsed(tmp_path / "panel.glb")
    (material,) = gltf["materials"]
    assert "baseColorTexture" in material["pbrMetallicRoughness"]
    assert len(gltf["images"]) == 1
    assert "TEXCOORD_0" in gltf["meshes"][0]["primitives"][0]["attributes"]


def test_a_picture_that_is_not_there_is_refused_by_name(tmp_path):
    card(tmp_path)
    (tmp_path / "panel.toml").write_text(DECLARED.format(image="gone.png"), "utf-8")
    declared = geometry.read("panel.toml", root=tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        build.write(declared, "panel.glb", root=tmp_path)
    assert refused.value.code == "render.missing-picture"
    assert "gone.png" in refused.value.message
