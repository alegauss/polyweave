"""A menu panel built from a declaration, as nine-patch textures (§PW316)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave import panel, provenance
from polyweave.errors import PolyweaveError

HOLO = """\
[panel.holo]
size = [96, 64]
margin = 16
fill = "#0a1a2acc"
cut = 4
edge = { width = 2, colour = "#3fe0ff" }
brackets = { length = 10, width = 3, colour = "#ff4fd8" }
scan = { pitch = 3, colour = "#3fe0ff26" }

[panel.holo.states.focus]
edge = { colour = "#ffffff" }

[panel.holo.states.disabled]
fill = "#10101080"
"""


def panels(tmp_path, body: str = HOLO) -> str:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "ui").mkdir(exist_ok=True)
    (tmp_path / "ui" / "kit.panel.toml").write_text(body, encoding="utf-8")
    return "ui/kit.panel.toml"


def pixels(tmp_path, name: str) -> np.ndarray:
    with Image.open(tmp_path / name) as opened:
        return np.asarray(opened.convert("RGBA")).astype(int)


def test_each_state_is_drawn_with_its_record_and_stylebox(tmp_path):
    made = panel.build(panels(tmp_path), root=str(tmp_path))["panels"]["holo"]
    assert set(made) == {"normal", "focus", "disabled"}
    normal = made["normal"]
    assert normal["file"] == "ui/holo.normal.png"
    assert normal["size"] == [96, 64]
    record = provenance.read(str(tmp_path / normal["file"]), root=tmp_path)
    assert record["inputs"][0] == {
        **record["inputs"][0], "role": "declaration", "path": "ui/kit.panel.toml"
    }
    assert record["params"]["state"] == "normal"
    style = (tmp_path / normal["stylebox"]).read_text("utf-8")
    assert 'path="res://ui/holo.normal.png"' in style
    assert "texture_margin_left = 16.0" in style
    # Scan lines tile, so their pitch holds at any height.
    assert "axis_stretch_vertical = 2" in style


def test_the_parts_land_where_they_are_declared(tmp_path):
    panel.build(panels(tmp_path), root=str(tmp_path))
    normal = pixels(tmp_path, "ui/holo.normal.png")
    focus = pixels(tmp_path, "ui/holo.focus.png")
    # The corner is cut off: transparent at the very corner pixel.
    assert normal[0, 0, 3] == 0
    # A bracket in its colour along the top, just past the cut.
    assert tuple(normal[1, 6, :3]) == (0xFF, 0x4F, 0xD8)
    # The edge on the side away from the brackets, and white once focused.
    assert tuple(normal[32, 0, :3]) == (0x3F, 0xE0, 0xFF)
    assert tuple(focus[32, 0, :3]) == (0xFF, 0xFF, 0xFF)
    # The scan lines alternate with the fill down the middle.
    middle = normal[20:29, 48, :3].tolist()
    assert len({tuple(p) for p in middle}) == 2


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("length = 10", "length = 20"), "stretching would bend it"),
        (("margin = 16", "margin = 50"), "leave no middle"),
        (('fill = "#0a1a2acc"', 'fill = "teal"'), "not a colour"),
        (("cut = 4", "cuts = 4"), "did you mean 'cut'"),
        (("[panel.holo.states.focus]", "[panel.holo.states.glow]"), "no key 'glow'"),
    ],
)
def test_a_panel_that_cannot_be_drawn_true_is_refused(tmp_path, change, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, HOLO.replace(*change)), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert said in refused.value.message + refused.value.remedy


WIPES = """
[panel.holo.tick]
length = 20
width = 2
colour = "#ff4fd8"

[wipe.sweep]
kind = "sweep"
colour = "#05070cff"
angle = 0
bow = 0.2

[wipe.iris]
kind = "iris"
colour = "#000000"
"""


def test_a_panel_and_its_wipes_are_built_as_shaders_with_materials(tmp_path):
    made = panel.build(panels(tmp_path, HOLO + WIPES), shader=True, root=str(tmp_path))
    focus = made["panels"]["holo"]["focus"]
    assert focus["shader"] == "ui/holo.gdshader"
    material = (tmp_path / focus["material"]).read_text("utf-8")
    assert 'path="res://ui/holo.gdshader"' in material
    assert "shader_parameter/edge_colour = Color(1, 1, 1, 1)" in material
    # A float written as one: Godot drops an int given to a float uniform.
    assert "shader_parameter/tick_length = 20.0" in material
    program = (tmp_path / "ui/holo.gdshader").read_text("utf-8")
    assert "shader_type canvas_item" in program
    assert made["wipes"]["sweep"]["kind"] == "sweep"
    sweep = (tmp_path / made["wipes"]["sweep"]["material"]).read_text("utf-8")
    assert "shader_parameter/bow = 0.2" in sweep
    iris = (tmp_path / "ui/iris.gdshader").read_text("utf-8")
    assert "uniform float progress" in iris


def test_a_tick_a_nine_patch_would_stretch_is_said_not_drawn(tmp_path):
    made = panel.build(panels(tmp_path, HOLO + WIPES), root=str(tmp_path))
    assert made["panels"]["holo"]["normal"]["not_drawn"] == ["tick"]


def test_a_wipe_of_no_known_kind_is_refused(tmp_path):
    body = HOLO + '\n[wipe.fade]\nkind = "dissolve"\n'
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert set(refused.value.as_dict()["allowed"]) == {"sweep", "iris"}


def test_the_engine_films_each_state_and_each_wipe_step(tmp_path):
    import os

    from polyweave import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    source = panels(tmp_path, HOLO + WIPES)
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="panel"\n', encoding="utf-8")
    taken = panel.capture(source, out="ui", steps=3, root=str(tmp_path))["stills"]
    assert set(taken["holo"]) == {"normal", "focus", "disabled"}
    assert list(taken["sweep"]) == ["00", "01", "02"]

    def at(name, x, y):
        with Image.open(tmp_path / name) as opened:
            return opened.convert("RGB").getpixel((x, y))

    # The panel sits centred on grey; its focused edge is white where normal is cyan.
    edge_x, edge_y = (320 - 96 * 2) // 2 + 1, 180 // 2
    assert at(taken["holo"]["focus"], edge_x, edge_y) == (255, 255, 255)
    assert at(taken["holo"]["normal"], edge_x, edge_y) != (255, 255, 255)
    # The sweep covers nothing at the start and everything at the end.
    assert at(taken["sweep"]["00"], 160, 90) != (5, 7, 12)
    assert at(taken["sweep"]["02"], 160, 90) == (5, 7, 12)
    record = provenance.read(str(tmp_path / taken["sweep"]["02"]), root=tmp_path)
    assert record["params"] == {"wipe": "sweep", "progress": 1.0}
