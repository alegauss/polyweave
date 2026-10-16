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


def test_a_rounded_corner_is_drawn_round_with_its_rim_and_brackets(tmp_path):
    """§PW472: a soft style's card is rounded, not cut."""
    panel.build(panels(tmp_path, HOLO.replace("cut = 4", "radius = 6")),
                root=str(tmp_path))
    normal = pixels(tmp_path, "ui/holo.normal.png")
    # Outside the arc at the corner, on it a pixel in, and inside it further round.
    assert normal[0, 0, 3] == 0
    assert 0 < normal[1, 1, 3] < 128
    assert normal[3, 3, 3] >= 0xCC
    # The rim runs straight down the side, past the corner's square.
    assert tuple(normal[32, 0, :3]) == (0x3F, 0xE0, 0xFF)
    # The bracket starts past the arc, not past a cut.
    assert tuple(normal[1, 7, :3]) == (0xFF, 0x4F, 0xD8)
    assert tuple(normal[1, 5, :3]) != (0xFF, 0x4F, 0xD8)


def test_a_rounded_corner_reaches_the_shader(tmp_path):
    body = HOLO.replace("cut = 4", "radius = 6")
    made = panel.build(panels(tmp_path, body), shader=True, root=str(tmp_path))
    material = (tmp_path / made["panels"]["holo"]["normal"]["material"]).read_text(
        "utf-8")
    assert "shader_parameter/radius = 6.0" in material
    assert "shader_parameter/cut = 0.0" in material
    assert "uniform float radius" in (tmp_path / "ui/holo.gdshader").read_text("utf-8")


PIPED = HOLO.replace(
    'edge = { width = 2, colour = "#3fe0ff" }',
    'piping = { width = 4, colour = "#c03060", raise = 0.5 }',
).replace('edge = { colour = "#ffffff" }', 'piping = { colour = "#3060c0" }')


def test_a_piping_is_a_tube_lit_along_its_crown_in_its_own_hue(tmp_path):
    """§PW472: the raised rim stuffed fabric is finished with."""
    panel.build(panels(tmp_path, PIPED), root=str(tmp_path))
    normal = pixels(tmp_path, "ui/holo.normal.png")
    focus = pixels(tmp_path, "ui/holo.focus.png")
    across = normal[32, 0:4, :3]
    crown, flank = across[1:3].mean(axis=0), across[0]
    # Lighter on the crown than at the flank, and the flank darker in its own hue.
    assert crown.sum() > flank.sum()
    assert flank[0] > flank[1] and flank[0] > flank[2]
    assert flank[0] < 0xC0
    # Inside the piping, the fill again; and a state recolours it key by key.
    assert tuple(normal[32, 6, :3]) != tuple(across[1])
    assert focus[32, 1, 2] > focus[32, 1, 0]


def test_a_piping_reaches_the_shader(tmp_path):
    made = panel.build(panels(tmp_path, PIPED), shader=True, root=str(tmp_path))
    material = (tmp_path / made["panels"]["holo"]["focus"]["material"]).read_text(
        "utf-8")
    assert "shader_parameter/piping_width = 4.0" in material
    assert "shader_parameter/piping_raise = 0.5" in material


BADGE = """\
[panel.badge]
size = [64, 64]
fill = "#e8a0b4"
outline = { shape = "lobed", lobes = 6, radius = 10, depth = 2 }
piping = { width = 3, colour = "#ffffff" }
"""

PILL = """\
[panel.button]
size = [96, 24]
margin = [16, 4, 16, 4]
fill = "#e8a0b4"
radius = "pill"
edge = { width = 2, colour = "#ffffff" }
"""


def test_an_outline_of_its_own_is_drawn_at_its_size_with_no_stylebox(tmp_path):
    """§PW472: a petal badge is no box, so it is no nine-patch either."""
    made = panel.build(panels(tmp_path, BADGE), root=str(tmp_path))
    normal = made["panels"]["badge"]["normal"]
    assert normal["stretch"] == "none"
    assert "stylebox" not in normal
    assert not (tmp_path / "ui/badge.normal.tres").exists()
    drawn = pixels(tmp_path, normal["file"])
    # Filled at the middle, empty at the box's corners, piped white at its rim.
    assert tuple(drawn[32, 32, :3]) == (0xE8, 0xA0, 0xB4)
    assert drawn[0, 0, 3] == 0
    assert drawn[63, 63, 3] == 0
    # The lobes reach the box's sides and dip between them.
    assert drawn[32, 1, 3] > 0
    assert drawn[:, :, 3].astype(bool).sum() < 64 * 64 * 0.9


def test_an_outline_reaches_the_shader_as_points(tmp_path):
    made = panel.build(panels(tmp_path, BADGE), shader=True, root=str(tmp_path))
    material = (tmp_path / made["panels"]["badge"]["normal"]["material"]).read_text(
        "utf-8")
    assert "shader_parameter/outline_count = 64.0" in material
    assert "shader_parameter/outline_points = PackedVector2Array(" in material


def test_a_pill_stretches_only_along_its_length(tmp_path):
    made = panel.build(panels(tmp_path, PILL), shader=True, root=str(tmp_path))
    normal = made["panels"]["button"]["normal"]
    assert normal["stretch"] == "width"
    drawn = pixels(tmp_path, normal["file"])
    # Round at both ends, a straight run between.
    assert drawn[0, 2, 3] == 0
    assert drawn[12, 0, 3] > 0
    assert tuple(drawn[0, 48, :3]) == (0xFF, 0xFF, 0xFF)
    material = (tmp_path / normal["material"]).read_text("utf-8")
    assert "shader_parameter/radius = 10000.0" in material


FELT = """\
[panel.card]
size = [96, 64]
margin = 16
radius = 12
fill = "#d04060"
[panel.card.material]
lift = 0.18
shade = 0.34
core = 0.3
grain = 0.6
grain_size = 2
seed = 3
"""


def hue_share(rgb) -> tuple[float, float]:
    """The colour's green and blue as shares of its red: equal shares, one hue."""
    r, g, b = (float(c) for c in rgb)
    return g / r, b / r


def test_a_felt_fill_is_lit_on_top_and_falls_into_its_own_hue(tmp_path):
    """§PW473: the material a soft style's body is, declared rather than coded."""
    panel.build(panels(tmp_path, FELT), root=str(tmp_path))
    drawn = pixels(tmp_path, "ui/card.normal.png")
    top = drawn[14:18, 40:56, :3].reshape(-1, 3).mean(axis=0)
    foot = drawn[52:56, 40:56, :3].reshape(-1, 3).mean(axis=0)
    assert top.sum() > foot.sum() + 60
    # Shade alone: the foot is the fill darkened channel by channel, never towards grey.
    shaded = FELT.replace("lift = 0.18", "lift = 0").replace("core = 0.3", "core = 0")
    panel.build(panels(tmp_path, shaded.replace("grain = 0.6", "grain = 0")),
                root=str(tmp_path))
    foot = pixels(tmp_path, "ui/card.normal.png")[56, 48, :3]
    assert foot.sum() < 0xD0 + 0x40 + 0x60 - 60
    assert hue_share(foot) == pytest.approx(hue_share((0xD0, 0x40, 0x60)), abs=0.03)
    panel.build(panels(tmp_path, FELT), root=str(tmp_path))
    # The grain varies pixel to pixel, and the seed decides how.
    row = drawn[32, 30:70, :3].sum(axis=1)
    assert len(set(row.tolist())) > 10
    panel.build(panels(tmp_path, FELT.replace("seed = 3", "seed = 4")),
                root=str(tmp_path))
    assert (pixels(tmp_path, "ui/card.normal.png") != drawn).any()


def test_a_candy_fill_is_lit_vivid_rather_than_pale(tmp_path):
    def lit(vivid: float):
        body = FELT.replace("grain = 0.6", "grain = 0").replace(
            "core = 0.3", f"core = 1\nvivid = {vivid}")
        panel.build(panels(tmp_path, body), root=str(tmp_path))
        r, g, b = (int(c) for c in pixels(tmp_path, "ui/card.normal.png")[19, 35, :3])
        return max(r, g, b) - min(r, g, b)

    assert lit(1) > lit(0) + 20


def test_a_material_left_out_or_all_zero_is_the_flat_fill(tmp_path):
    flat = FELT.split("[panel.card.material]")[0] + "[panel.card.material]\nseed = 9\n"
    panel.build(panels(tmp_path, flat), root=str(tmp_path))
    drawn = pixels(tmp_path, "ui/card.normal.png")
    assert tuple(drawn[32, 48, :3]) == (0xD0, 0x40, 0x60)


def test_a_material_reaches_the_shader(tmp_path):
    made = panel.build(panels(tmp_path, FELT), shader=True, root=str(tmp_path))
    material = (tmp_path / made["panels"]["card"]["normal"]["material"]).read_text(
        "utf-8")
    assert "shader_parameter/shade = 0.34" in material
    assert "shader_parameter/light_at = Vector2(0.36, 0.3)" in material
    assert "shader_parameter/seed = 3.0" in material


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("shade = 0.34", "shade = 2"), "from 0 to 1"),
        (("grain_size = 2", "grain_size = 0"), "pixels from 1"),
        (("lift = 0.18", "light = 0.5"), "light = [x, y]"),
        (("lift = 0.18", "lifts = 0.18"), "did you mean 'lift'"),
    ],
)
def test_a_material_that_means_nothing_is_refused(tmp_path, change, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, FELT.replace(*change)), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert said in refused.value.message + refused.value.remedy


@pytest.mark.parametrize(
    ("body", "said"),
    [
        (BADGE.replace("outline", 'radius = 4\noutline'), "keep one of them"),
        (BADGE + 'brackets = { length = 4, colour = "#ffffff" }\n', "brackets sit"),
        (BADGE.replace('"lobed"', '"blob"'), "outline: there is no outline"),
        (BADGE.replace("lobes = 6, ", "lobes = 6, steps = 400, "), "fewer steps"),
        (PILL.replace('"pill"', '"round"'), 'or "pill"'),
        (PILL.replace("[16, 4, 16, 4]", "[8, 4, 8, 4]"), "stretching would bend it"),
    ],
)
def test_an_outline_or_a_pill_that_cannot_be_drawn_is_refused(tmp_path, body, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert said in refused.value.message + refused.value.remedy


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("cut = 4", "cut = 4\nradius = 4"), "keep one of them"),
        (("cut = 4", "cut = 4\npiping = { width = 2, colour = \"#fff\" }"),
         "not a colour"),
        (("cut = 4", "cut = 4\npiping = { width = 2, colour = \"#ffffff\", "
          "raise = 2 }"), "piping.raise"),
        (("cut = 4", "cut = 4\npiping = { width = 14, colour = \"#ffffff\" }"),
         "stretching would bend it"),
        (("cut = 4", "radius = 10"), "stretching would bend it"),
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
    source = panels(tmp_path, HOLO + WIPES + "\n" + BADGE + "\n" + FELT)
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
    # §PW472: the badge's own outline, drawn by the shader: filled at its middle, the
    # grey screen at its box's corner.
    badge_x, badge_y = (320 - 64 * 2) // 2, (180 - 64 * 2) // 2
    assert at(taken["badge"]["normal"], 160, 90) == (0xE8, 0xA0, 0xB4)
    assert at(taken["badge"]["normal"], badge_x + 2, badge_y + 2) == at(
        taken["holo"]["normal"], 2, 2)
    # §PW473: the engine lights the felt as panel.build did, top and foot alike.
    card_x, card_y = (320 - 96 * 2) // 2, (180 - 64 * 2) // 2
    built = pixels(tmp_path, "ui/card.normal.png")
    for x, y in ((48, 16), (48, 54)):
        filmed = at(taken["card"]["normal"], card_x + x * 2 + 1, card_y + y * 2 + 1)
        assert sum(filmed) == pytest.approx(int(built[y, x, :3].sum()), abs=36)
    # The sweep covers nothing at the start and everything at the end.
    assert at(taken["sweep"]["00"], 160, 90) != (5, 7, 12)
    assert at(taken["sweep"]["02"], 160, 90) == (5, 7, 12)
    record = provenance.read(str(tmp_path / taken["sweep"]["02"]), root=tmp_path)
    assert record["params"] == {"wipe": "sweep", "progress": 1.0}
