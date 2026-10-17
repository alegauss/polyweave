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


SEWN = """\
[panel.play]
size = [128, 48]
margin = 20
radius = 16
fill = "#e0607a"

[panel.play.seam]
inset = 7
dash = 5
gap = 3
width = 1.6
thread = "#fff4f0"
seed = 2
"""


def seam_band(drawn) -> np.ndarray:
    """The rows along the top edge the seam is sewn on, past the rounded corners."""
    return drawn[5:10, 24:104, :3].astype(int)


def test_a_seam_is_sewn_along_the_outline_with_its_shadow(tmp_path):
    """§PW474: thread that reads as sewn, not as a road marking."""
    made = panel.build(panels(tmp_path, SEWN), root=str(tmp_path))
    drawn = pixels(tmp_path, made["panels"]["play"]["normal"]["file"])
    band = seam_band(drawn)
    # The thread, near its own colour, and gaps of cloth between the stitches.
    bright = band.sum(axis=2) > 0xE0 + 0x60 + 0x7A + 200
    assert bright.any(axis=0).sum() > 20
    assert (~bright.any(axis=0)).sum() > 10
    # A shadow below the thread, darker than the cloth and in its hue, not grey.
    cloth = np.array([0xE0, 0x60, 0x7A])
    below = drawn[4:12, 24:104, :3].astype(int).reshape(-1, 3)
    dark = below[below.sum(axis=1) < cloth.sum() - 40]
    assert len(dark)
    assert (dark[:, 0] > dark[:, 1]).all()
    # The middle of the panel is cloth, untouched.
    assert tuple(drawn[24, 64, :3]) == (0xE0, 0x60, 0x7A)


def test_a_seam_says_where_it_holds_and_where_it_does_not(tmp_path):
    made = panel.build(panels(tmp_path, SEWN), shader=True, root=str(tmp_path))
    normal = made["panels"]["play"]["normal"]
    # A nine-patch grows the stitches in its middle; the shader sews at any size.
    assert normal["stretched"] == ["seam"]
    assert "not_in_shader" not in normal
    material = (tmp_path / normal["material"]).read_text("utf-8")
    assert "shader_parameter/seam_width = 1.6" in material
    assert "shader_parameter/seam_thread = Color(1, 0.956863" in material


def test_a_seam_with_its_effects_off_is_a_plain_dash_and_the_seed_moves_it(tmp_path):
    plain = SEWN + "shading = 0\nshadow = 0\nholes = 0\njitter = 0\n"
    panel.build(panels(tmp_path, plain), root=str(tmp_path))
    flat = pixels(tmp_path, "ui/play.normal.png")
    colours = {tuple(p) for p in seam_band(flat).reshape(-1, 3).tolist()}
    # Thread, cloth, and the blend of the two at a stitch's soft edge: nothing darker.
    assert min(sum(c) for c in colours) >= 0xE0 + 0x60 + 0x7A
    panel.build(panels(tmp_path, SEWN), root=str(tmp_path))
    two = pixels(tmp_path, "ui/play.normal.png")
    moved = SEWN.replace("seed = 2", "seed = 5")
    panel.build(panels(tmp_path, moved), root=str(tmp_path))
    assert (pixels(tmp_path, "ui/play.normal.png") != two).any()


def prop(tmp_path) -> str:
    """A red disc on transparent paper, as a baked render comes out."""
    from PIL import ImageDraw

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    picture = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(picture).ellipse((4, 4, 59, 59), fill=(0xC0, 0x30, 0x40, 255))
    (tmp_path / "art").mkdir(exist_ok=True)
    picture.save(tmp_path / "art" / "prop.png")
    return "art/prop.png"


def test_a_pictures_silhouette_is_sewn_with_the_panels_needle(tmp_path):
    """§PW474: a baked prop and a drawn panel are sewn by one needle."""
    from polyweave import describe

    made = describe._REGISTRY["picture.sew"].fn(
        prop(tmp_path), out="art/prop.sewn.png",
        seam={"thread": "#fff4f0", "inset": 5, "dash": 4, "gap": 3, "width": 1.5},
        root=str(tmp_path))
    assert made["file"] == "art/prop.sewn.png"
    assert made["stitches"] > 15
    sewn = pixels(tmp_path, made["file"])
    plain = pixels(tmp_path, "art/prop.png")
    # Thread along a ring inside the edge, the middle and the paper untouched.
    ring = sewn[9:12, 24:40, :3].sum(axis=2)
    assert ring.max() > 0xC0 + 0x30 + 0x40 + 300
    assert (sewn[32, 32] == plain[32, 32]).all()
    assert (sewn[0, 0] == plain[0, 0]).all()
    # The shadow falls in the prop's own red.
    changed = (sewn[..., :3] != plain[..., :3]).any(axis=2)
    dark = sewn[changed & (sewn[..., :3].sum(axis=2) < 0xC0 + 0x30 + 0x40 - 30)]
    assert len(dark)
    assert (dark[:, 0] > dark[:, 1]).all()
    record = provenance.read(str(tmp_path / made["file"]), root=tmp_path)
    assert record["inputs"][0]["path"] == "art/prop.png"
    assert record["params"]["seam"]["inset"] == 5


@pytest.mark.parametrize(
    ("seam", "said"),
    [
        ({"inset": 3}, "seam has no thread"),
        ({"thread": "#ffffff", "needle": 1}, "no key 'needle'"),
        ({"thread": "#ffffff", "inset": 40}, "too small to sew"),
    ],
)
def test_a_picture_that_cannot_be_sewn_is_refused(tmp_path, seam, said):
    from polyweave import describe

    source = prop(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        describe._REGISTRY["picture.sew"].fn(source, out="art/x.png", seam=seam,
                                             root=str(tmp_path))
    assert refused.value.code == "compose.bad-seam"
    assert said in refused.value.message + refused.value.remedy


LILAC = """\
[panel.glass]
size = [120, 80]
margin = 30
fill = "#080a21d1"
cut = 12
edge = { width = 3, colour = "#baa6ff", lit = [1.15, 0.55] }
hairline = { inset = 9, width = 1, colour = "#baa6ff", strength = 0.35 }
brackets = { length = 12, width = 3, colour = "#40e8ff", inset = 12 }
tick = { from = 30, to = 102, width = 3, colour = "#ff3dcc" }
"""


def test_a_holo_panels_bevel_hairline_and_set_in_brackets(tmp_path):
    """§PW479: what Spinhold's accepted holo shader drew, declared."""
    made = panel.build(panels(tmp_path, LILAC), shader=True, root=str(tmp_path))
    drawn = pixels(tmp_path, "ui/glass.normal.png")
    # The edge lit at the top and falling to shadow at the foot, in its own hue.
    top, foot = drawn[1, 60, :3], drawn[78, 60, :3]
    assert top.sum() > foot.sum() * 1.6
    assert top[2] > top[0] > top[1]
    assert foot[2] > foot[0] > foot[1]
    # A faint hairline nine pixels in, between the glass on either side of it.
    line, glass = drawn[40, 9, :3].sum(), drawn[40, 14, :3].sum()
    assert line > glass + 30
    # Brackets set in from the cut on both axes, not on the outer edge.
    assert tuple(drawn[13, 18, :3]) == (0x40, 0xE8, 0xFF)
    assert tuple(drawn[1, 18, :3]) != (0x40, 0xE8, 0xFF)
    material = (tmp_path / made["panels"]["glass"]["normal"]["material"]).read_text(
        "utf-8")
    for said in ("edge_top = 1.15", "edge_foot = 0.55", "hairline_inset = 9.0",
                 "hairline_strength = 0.35", "bracket_inset = 12.0", "tick_from = 30.0",
                 "tick_length = 72.0"):
        assert f"shader_parameter/{said}" in material


STATED = LILAC + """\
sweep = { colour = "#baa6ff", strength = 0.05 }

[panel.glass.states.focus]
glow = 1.9

[panel.glass.states.pressed]
glass_lift = 0.35

[panel.glass.states.disabled]
drain = 1.0
"""


def test_a_state_glows_lifts_or_drains_by_an_amount(tmp_path):
    """§PW479: focus, pressed and disabled as amounts, not only colours."""
    made = panel.build(panels(tmp_path, STATED), root=str(tmp_path))
    normal = pixels(tmp_path, "ui/glass.normal.png")
    focus = pixels(tmp_path, "ui/glass.focus.png")
    pressed = pixels(tmp_path, "ui/glass.pressed.png")
    disabled = pixels(tmp_path, "ui/glass.disabled.png")
    # Focus brightens the marks, not the glass.
    assert focus[13, 18, :3].sum() >= normal[13, 18, :3].sum()
    assert focus[40, 9, :3].sum() == normal[40, 9, :3].sum()
    assert focus[78, 60, :3].sum() > normal[78, 60, :3].sum() * 1.5
    # Pressed lifts the glass.
    assert pressed[40, 60, :3].sum() > normal[40, 60, :3].sum()
    # Disabled drains to grey and fades a little.
    r, g, b, a = disabled[13, 18]
    assert max(r, g, b) - min(r, g, b) <= 2
    assert a < normal[13, 18, 3]
    # A still cannot move the glass's sweep, and says so.
    assert made["panels"]["glass"]["normal"]["not_drawn"] == ["tick", "sweep"]


def test_a_game_sets_tint_and_cut_on_one_panel_of_many(tmp_path):
    body = STATED.replace('margin = 30', 'margin = 30\ntint = "#ff8080"')
    made = panel.build(panels(tmp_path, body), shader=True, root=str(tmp_path))
    focus = (tmp_path / made["panels"]["glass"]["focus"]["material"]).read_text("utf-8")
    # Local to its scene: each Control gets its own copy to set tint or cut on.
    assert "resource_local_to_scene = true" in focus
    for said in ("glow = 1.9", "tint = Color(1, 0.501961, 0.501961, 1)",
                 "sweep_strength = 0.05", "cut = 12.0", "bracket_length = 12.0"):
        assert f"shader_parameter/{said}" in focus
    program = (tmp_path / "ui/glass.gdshader").read_text("utf-8")
    assert "TIME * sweep_speed" in program
    drawn = pixels(tmp_path, "ui/glass.normal.png")
    assert tuple(drawn[13, 18, :3]) == (0x40, 0x74, 0x80)


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("glow = 1.9", "glow = 9"), "glow from 0 to 4"),
        (("strength = 0.05", "strength = 5"), "sweep.strength from 0 to 1"),
    ],
)
def test_an_amount_out_of_range_is_refused(tmp_path, change, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, STATED.replace(*change)), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert said in refused.value.message + refused.value.remedy


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("lit = [1.15, 0.55]", "lit = 1.15"), "lit = [top, foot]"),
        (("strength = 0.35", "strength = 3"), "hairline.strength"),
        (("from = 30, to = 102", "from = 30, to = 20"), "to past from"),
        (("inset = 12 }", "inset = 40 }"), "stretching would bend it"),
    ],
)
def test_a_holo_part_that_cannot_be_drawn_is_refused(tmp_path, change, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, LILAC.replace(*change)), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert said in refused.value.message + refused.value.remedy


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (('thread = "#fff4f0"\n', ""), "seam has no thread"),
        (("width = 1.6", "width = 0"), "pixels from 0.5"),
        (("seed = 2", "shadow = 3"), "from 0, off, to 1"),
        (("seed = 2", "needle = 1"), "no key 'needle'"),
    ],
)
def test_a_seam_that_cannot_be_sewn_is_refused(tmp_path, change, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, SEWN.replace(*change)), root=str(tmp_path))
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


def test_a_panel_whose_shader_will_not_compile_is_refused_not_filmed(tmp_path,
                                                                    monkeypatch):
    """§PW489: a broken shader was filmed as white stills, and the answer said ok."""
    import os

    from polyweave import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    monkeypatch.setattr(panel, "_PANEL_SHADER", panel._PANEL_SHADER.replace(
        "uniform float glow = 1.0;", "uniform float glow = 1.0;\nuniform float glow;"))
    source = panels(tmp_path, HOLO)
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="panel"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        panel.capture(source, out="ui", root=str(tmp_path))
    assert refused.value.code == "compose.unfilmed"
    assert "error" in refused.value.message


def test_the_engine_films_each_state_and_each_wipe_step(tmp_path):
    import os

    from polyweave import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    source = panels(tmp_path, HOLO + WIPES + "\n" + BADGE + "\n" + FELT + "\n" + SEWN
                    + "\n" + STATED)
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
    # §PW474: the engine sews the top edge with as many stitches as panel.build did.
    def stitches(picture) -> int:
        """Stitches across the top edge: bright runs along the band's brightest row."""
        band = picture[5:10, 24:104, :3].sum(axis=2)
        row = band[int(np.argmax(band.mean(axis=1)))]
        bright = row > np.median(row) + (row.max() - np.median(row)) / 2
        return int(np.sum(bright[1:] & ~bright[:-1]) + bright[0])

    sewn = pixels(tmp_path, "ui/play.normal.png")
    play_x, play_y = (320 - 128 * 2) // 2, (180 - 48 * 2) // 2
    built_count = stitches(sewn)
    with Image.open(tmp_path / taken["play"]["normal"]) as opened:
        # Brought down to the panel's own pixels, as the build is, so the thread's
        # plies at twice the size do not split a stitch in two.
        crop = opened.convert("RGB").crop((play_x, play_y, play_x + 256, play_y + 96))
        still = np.asarray(crop.resize((128, 48), Image.Resampling.BOX)).astype(int)
    filmed_count = stitches(still)
    # 80 pixels of edge at a dash of 5 and a gap of 3 is ten stitches; the build's
    # finer ones blur at one pixel to the panel's, so it is held more loosely.
    assert abs(filmed_count - 10) <= 1
    assert built_count >= 8
    # The sweep covers nothing at the start and everything at the end.
    assert at(taken["sweep"]["00"], 160, 90) != (5, 7, 12)
    assert at(taken["sweep"]["02"], 160, 90) == (5, 7, 12)
    record = provenance.read(str(tmp_path / taken["sweep"]["02"]), root=tmp_path)
    assert record["params"] == {"wipe": "sweep", "progress": 1.0}
