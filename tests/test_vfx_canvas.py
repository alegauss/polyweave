"""Effects declared for a 2D canvas (§PW623).

Cottony's board screen is 2D, and its star drift between the panels was written by hand
as a script: four rectangles, a seed, a preprocess, two sizes and a ramp, which is a
declaration's worth of numbers.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import engine
from polyweave.layers.vfx import vfx
from test_vfx import effects

DRIFT = """\
[effect.drift]
canvas = true
amount = 40
lifetime = 6.0
rects = [[0, 0, 300, 100], [0, 400, 100, 100]]
direction = [0, -1]
gravity = [0, 4]
speed = [8, 14]
size = 24
shape = "star"
angular_velocity = [-30, 30]
colour_over_life = ["#ffe08000", "#ffe080ff", "#ffe08000"]
seed = 7
preprocess = 6.0
"""


def test_a_canvas_effect_is_a_cpu_particles_2d_in_pixels(tmp_path):
    vfx.build(effects(tmp_path, DRIFT), root=str(tmp_path))
    text = (tmp_path / "vfx" / "drift.tscn").read_text("utf-8")
    assert '[node name="drift" type="Node2D"]' in text
    emitters = re.findall(
        r'\[node name="(drift_\d)" type="CPUParticles2D" parent="."\]', text)
    assert emitters == ["drift_0", "drift_1"]
    # The amount is shared by area: 30,000 px and 10,000 px of 40 particles.
    assert re.findall(r"^amount = (\d+)$", text, re.MULTILINE) == ["30", "10"]
    assert "position = Vector2(150, 50)" in text
    assert "emission_rect_extents = Vector2(150, 50)" in text
    assert "direction = Vector2(0, -1)" in text and "gravity = Vector2(0, 4)" in text
    # A star drawn 64 px across, at 24 px: a scale of 0.375.
    assert "scale_amount_min = 0.375" in text
    assert "use_fixed_seed = true\nseed = 7" in text and "seed = 8" in text
    assert "preprocess = 6" in text
    assert "GPUParticles3D" not in text


def test_one_emitter_with_no_rects_is_the_scene_s_own_node(tmp_path):
    body = ('[effect.dust]\ncanvas = true\namount = 8\nlifetime = 2.0\n'
            'emission = "box"\nextents = [40, 10]\nsize = 4\n')
    vfx.build(effects(tmp_path, body), root=str(tmp_path))
    text = (tmp_path / "vfx" / "dust.tscn").read_text("utf-8")
    assert '[node name="dust" type="CPUParticles2D"]' in text
    assert "emission_shape = 3" in text and "Vector2(40, 10)" in text
    # A plain square is a white texture of its own, 8 px across.
    assert "scale_amount_min = 0.5" in text and 'type="ImageTexture"' in text
    assert "use_fixed_seed" not in text and "preprocess" not in text


def test_a_seed_and_preprocess_reach_a_3d_effect_too(tmp_path):
    body = "[effect.a]\namount = 4\nlifetime = 1.0\nseed = 3\npreprocess = 0.5\n"
    vfx.build(effects(tmp_path, body), root=str(tmp_path))
    text = (tmp_path / "vfx" / "a.tscn").read_text("utf-8")
    assert "use_fixed_seed = true\nseed = 3" in text and "preprocess = 0.5" in text


@pytest.mark.parametrize(
    ("body", "said"),
    [
        ('kind = "ribbon"\ncanvas = true\n', "on a canvas"),
        ('mesh = "sphere"\ncanvas = true\n', "on a canvas"),
        ("rects = [[0, 0, 10, 10]]\n", "is not on a canvas"),
        ("canvas = true\nrects = [[0, 0, 0, 10]]\n", "sets rects"),
        ('canvas = true\nrects = [[0, 0, 10, 10]]\nemission = "box"\n',
         "an emission or extents"),
        ("seed = -4\n", "sets seed"),
        ("preprocess = -1\n", "sets preprocess"),
    ],
)
def test_a_canvas_effect_that_means_nothing_is_refused(tmp_path, body, said):
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, f"[effect.a]\namount = 4\nlifetime = 1.0\n{body}"),
                  root=str(tmp_path))
    assert refused.value.code == "vfx.bad-effect"
    assert said in refused.value.message


def test_parts_on_a_canvas_are_held_by_a_node_2d_and_never_mixed(tmp_path):
    body = ("[effect.glow.near]\ncanvas = true\namount = 4\nlifetime = 1.0\n"
            "[effect.glow.far]\ncanvas = true\namount = 2\nlifetime = 2.0\n")
    vfx.build(effects(tmp_path, body), root=str(tmp_path))
    text = (tmp_path / "vfx" / "glow.tscn").read_text("utf-8")
    assert '[node name="glow" type="Node2D"]' in text
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, body.replace("canvas = true\namount = 2",
                                                 "amount = 2")), root=str(tmp_path))
    assert "mixes parts on a canvas" in refused.value.message


def test_a_canvas_effect_is_framed_on_what_it_emits_from(tmp_path):
    """§PW636: watched still and in pixels, the rectangles grown by the reach."""
    vfx.build(effects(tmp_path, DRIFT), root=str(tmp_path))
    effect = vfx.declared("drift", vfx.tomllib.loads(DRIFT)["effect"]["drift"],
                          tmp_path)
    x0, y0, x1, y1 = vfx._canvas_bounds(effect)
    reach = vfx.measured(effect)["reach"]
    assert (x0, y0) == (pytest.approx(-reach), pytest.approx(-reach))
    assert (x1, y1) == (pytest.approx(300 + reach), pytest.approx(500 + reach))
    framed = vfx._framing_canvas(effect)
    zoom = float(framed["zoom"])
    assert zoom * (x1 - x0) <= vfx.FRAME[0] + 1e-6
    assert zoom * (y1 - y0) <= vfx.FRAME[1] + 1e-6


def test_a_canvas_effect_is_watched_on_its_own(tmp_path):
    """§PW636: a drift between panels has a sitting of its own, on the neutral grey."""
    import json

    import numpy as np
    from PIL import Image

    from polyweave.layers.engine import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    source = effects(tmp_path, DRIFT.replace('shape = "star"', 'shape = "dot"'))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    laid = vfx.preview(source, out="review/fx", stills=4, root=str(tmp_path))
    assert laid["effects"]["drift"]["frames"] > 60
    manifest = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))
    assert "drift" in manifest["families"]
    with Image.open(tmp_path / "review" / "fx" / "drift.png") as sheet:
        drawn = np.asarray(sheet.convert("RGB"))[32:32 + vfx.FRAME[1], 8:]
        assert drawn.max() > 120, "the stars are drawn on the grey"


LOADS = """extends SceneTree

func _initialize() -> void:
\tvar root: Node2D = load("res://vfx/drift.tscn").instantiate()
\tvar one: CPUParticles2D = root.get_child(0)
\tprint("vfx: emitters=%d amount=%d seed=%d fixed=%s pre=%s extents=%s texture=%s" % [
\t\troot.get_child_count(), one.amount, one.seed, one.use_fixed_seed,
\t\tone.preprocess, one.emission_rect_extents, one.texture.get_class()])
\troot.free()
\tquit()
"""


def test_the_engine_loads_a_canvas_effect_as_declared(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, DRIFT), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "loads.gd").write_text(LOADS, encoding="utf-8")
    ran = engine.run("loads.gd", expect=r"^vfx: emitters", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    assert ("vfx: emitters=2 amount=30 seed=7 fixed=true pre=6.0 "
            "extents=(150.0, 50.0) texture=ImageTexture") in said
