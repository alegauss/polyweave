"""Visual effects declared as data and built into a Godot scene (§PW259).

Starship's trails were a Resource per trail, tuned by eye. The scene built here is
loaded by the engine itself where there is one, since a scene Godot cannot parse is one
the game cannot play.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from polyweave import engine, provenance, vfx
from polyweave.errors import PolyweaveError

TRAILS = """\
[effect.sparks]
amount = 64
lifetime = 0.8
speed = [2.0, 3.0]
gravity = [0, -2, 0]
spread = 15.0
size = 0.2
size_over_life = [1.0, 0.5, 0.0]
colour_over_life = ["#ffd24aff", "#ff4a1a00"]

[effect.band]
kind = "ribbon"
amount = 12
lifetime = 1.5
trail = 0.4
blend = "mix"
emission = "sphere"
radius = 0.1
colour_over_life = ["#80c0ff", "#ffffff00"]
"""


def effects(tmp_path, body: str = TRAILS) -> str:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "vfx").mkdir(exist_ok=True)
    (tmp_path / "vfx" / "trails.vfx.toml").write_text(body, encoding="utf-8")
    return "vfx/trails.vfx.toml"


def test_each_effect_is_built_as_a_scene_with_its_record(tmp_path):
    made = vfx.build(effects(tmp_path), root=str(tmp_path))["effects"]
    assert made["sparks"]["file"] == "vfx/sparks.tscn"
    text = (tmp_path / "vfx" / "sparks.tscn").read_text("utf-8")
    assert 'type="GPUParticles3D"' in text and "amount = 64" in text
    assert "billboard_mode = 3" in text
    ribbon = (tmp_path / "vfx" / "band.tscn").read_text("utf-8")
    assert "trail_enabled = true" in ribbon and 'type="RibbonTrailMesh"' in ribbon
    record = provenance.read("vfx/sparks.tscn", root=str(tmp_path))
    assert record["kind"] == "vfx"
    assert record["measurements"]["alive"] == 64


def test_what_an_effect_measures_is_worked_out_from_its_declaration(tmp_path):
    made = vfx.build(effects(tmp_path), root=str(tmp_path))["effects"]
    sparks = made["sparks"]
    # The fastest particle over its life, and the fall gravity adds to it.
    assert sparks["reach"] == pytest.approx(3.0 * 0.8 + 0.5 * 2.0 * 0.8**2)
    assert sparks["rate"] == pytest.approx(80.0)
    assert made["band"]["brightness"] == pytest.approx(
        0.2126 * 128 / 255 + 0.7152 * 192 / 255 + 0.0722, abs=1e-3)


def test_one_effect_can_be_built_alone_and_into_another_folder(tmp_path):
    made = vfx.build(effects(tmp_path), effect="band", out="game/fx",
                     root=str(tmp_path))["effects"]
    assert list(made) == ["band"]
    assert (tmp_path / "game" / "fx" / "band.tscn").is_file()


def test_a_scene_beside_a_source_under_a_gdignore_is_refused(tmp_path):
    # Spinhold's art/ carries a .gdignore, and the trails built beside their declaration
    # loaded in the editor and would not have shipped (§PW374).
    source = effects(tmp_path)
    (tmp_path / "vfx" / ".gdignore").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(source, root=str(tmp_path))
    assert refused.value.code == "vfx.unshipped"
    assert ".gdignore" in refused.value.message
    assert not (tmp_path / "vfx" / "sparks.tscn").exists()


def test_a_scene_beside_a_source_an_export_excludes_is_refused(tmp_path):
    source = effects(tmp_path)
    (tmp_path / "export_presets.cfg").write_text(
        '[preset.0]\nname="Windows"\nexport_filter="all_resources"\n'
        'exclude_filter="assets/models/*, vfx/*"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(source, root=str(tmp_path))
    assert refused.value.code == "vfx.unshipped"
    assert "Windows" in refused.value.message


def test_the_project_names_where_its_built_effects_go(tmp_path):
    source = effects(tmp_path)
    (tmp_path / "vfx" / ".gdignore").write_text("", encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text('[paths]\nvfx = "game/fx"\n',
                                             encoding="utf-8")
    made = vfx.build(source, root=str(tmp_path))["effects"]
    assert made["sparks"]["file"] == "game/fx/sparks.tscn"
    # A call's own out still wins over the project's folder.
    made = vfx.build(source, out="game/other", root=str(tmp_path))["effects"]
    assert made["band"]["file"] == "game/other/band.tscn"


def test_a_camera_clip_beside_an_unshipped_source_is_refused(tmp_path):
    from polyweave import camera

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "art").mkdir()
    (tmp_path / "art" / ".gdignore").write_text("", encoding="utf-8")
    (tmp_path / "art" / "a.camera.toml").write_text(
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\nhold = 1\n',
        encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        camera.build("art/a.camera.toml", root=str(tmp_path))
    assert refused.value.code == "clip.unshipped"
    assert camera.build("art/a.camera.toml", out="game/cinema",
                        root=str(tmp_path))["file"] == "game/cinema/a.tscn"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("[effect.a]\namount = 4\n", "vfx.bad-effect"),
        ("[effect.a]\namount = 0\nlifetime = 1.0\n", "vfx.bad-effect"),
        ("[effect.a]\namount = 4\nlifetime = 1.0\nkind = \"smoke\"\n",
         "vfx.bad-effect"),
        ("[effect.a]\namount = 4\nlifetime = 1.0\ncolour_over_life = [\"red\", "
         "\"#fff\"]\n", "vfx.bad-effect"),
        ("[effect.a]\namount = 4\nlifetime = 1.0\nsped = [1, 2]\n", "vfx.bad-effect"),
        ("[effect.a]\namount = 4\nlifetime = 1.0\nspeed = [1]\n", "vfx.bad-effect"),
        ("[effects.a]\namount = 4\n", "vfx.no-source"),
        ("[effect.a\n", "vfx.no-source"),
    ],
)
def test_an_effect_that_means_nothing_is_refused_with_a_code(tmp_path, body, code):
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == code


def test_a_misspelled_key_is_answered_with_its_nearest(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, "[effect.a]\namount = 4\nlifetime = 1.0\n"
                                    "sped = [1, 2]\n"), root=str(tmp_path))
    assert "'speed'" in refused.value.remedy


ACCEPTED = """\
[effect.confetti]
amount = 24
lifetime = 0.8
speed = [3.0, 8.0]
damping = [6.0, 10.0]
angle = [0, 360]
angular_velocity = [-240, 240]
shape = "flake"
blend = "mix"
randomness = 0.3

[effect.band]
amount = 12
lifetime = 1.0
emission = "box"
extents = [0.1, 1.0, 0.1]
damping = 2
shape = "ring"
"""


def test_particles_start_unevenly_where_randomness_says(tmp_path):
    """§PW285: every accepted Starship trail sets randomness 0.3 on its particles."""
    vfx.build(effects(tmp_path, "[effect.a]\namount = 27\nlifetime = 0.45\n"
                                "randomness = 0.3\n"), root=str(tmp_path))
    assert "randomness = 0.3" in (tmp_path / "vfx" / "a.tscn").read_text("utf-8")
    with pytest.raises(PolyweaveError):
        vfx.build(effects(tmp_path, "[effect.a]\namount = 4\nlifetime = 1.0\n"
                                    "randomness = 1.5\n"), root=str(tmp_path))


def test_the_keys_an_accepted_trail_relies_on_are_built(tmp_path):
    """§PW281: Starship's seven trails refused every one of these as vfx.bad-effect."""
    vfx.build(effects(tmp_path, ACCEPTED), root=str(tmp_path))
    confetti = (tmp_path / "vfx" / "confetti.tscn").read_text("utf-8")
    for line in ("damping_min = 6", "damping_max = 10", "angle_max = 360",
                 "angular_velocity_min = -240", 'type="GradientTexture2D" id="shape"',
                 'albedo_texture = SubResource("shape")'):
        assert line in confetti, line
    assert "fill = 1" not in confetti  # a flake is a strip, not a radial dot
    band = (tmp_path / "vfx" / "band.tscn").read_text("utf-8")
    assert "emission_shape = 3" in band
    assert "emission_box_extents = Vector3(0.1, 1, 0.1)" in band
    assert "damping_min = 2" in band and "damping_max = 2" in band
    assert "fill = 1" in band


def test_damping_and_a_box_are_counted_in_the_reach(tmp_path):
    made = vfx.build(effects(tmp_path, ACCEPTED), root=str(tmp_path))["effects"]
    # The fastest spark brakes at the least damping, and has not stopped at 0.8 s.
    assert made["confetti"]["reach"] == pytest.approx(8.0 * 0.8 - 0.5 * 6.0 * 0.8**2)
    # At 1 m/s braked by 2, stopped at 0.5 s, from the far corner of its box.
    assert made["band"]["reach"] == pytest.approx(
        (1.0 * 0.5 - 0.5 * 2 * 0.5**2) + (0.01 + 1.0 + 0.01) ** 0.5, abs=1e-4)


def test_a_picture_can_be_a_particle_s_shape(tmp_path):
    source = effects(tmp_path, '[effect.a]\namount = 4\nlifetime = 1.0\n'
                               'shape = "art/star.png"\n')
    (tmp_path / "art").mkdir()
    (tmp_path / "art" / "star.png").write_bytes(b"\x89PNG\r\n")
    vfx.build(source, root=str(tmp_path))
    built = (tmp_path / "vfx" / "a.tscn").read_text("utf-8")
    assert '[ext_resource type="Texture2D" path="res://art/star.png" id="picture"]' \
        in built
    assert 'albedo_texture = ExtResource("picture")' in built


@pytest.mark.parametrize(
    "extra",
    ["damping = -1", "damping = [1, 2, 3]", 'emission = "box"',
     'emission = "box"\nextents = [0.1, -1, 0.1]', 'shape = "star"',
     'shape = "art/missing.png"', "angle = \"wide\""],
)
def test_a_trail_key_that_means_nothing_is_refused(tmp_path, extra):
    source = effects(tmp_path, f"[effect.a]\namount = 4\nlifetime = 1.0\n{extra}\n")
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(source, root=str(tmp_path))
    assert refused.value.code == "vfx.bad-effect"


WAKE = """\
[effect.wake]
kind = "path_ribbon"
amount = 90
lifetime = 1.2
size = 0.6
size_over_life = [1.0, 0.0]
colour_over_life = ["#9fe8ffff", "#2a6cff00"]
"""


def test_a_path_ribbon_is_a_scene_that_draws_the_path_its_parent_flew(tmp_path):
    """§PW281: the tender's ribbon narrows as it ages and had no kind at all."""
    made = vfx.build(effects(tmp_path, WAKE), root=str(tmp_path))["effects"]
    built = (tmp_path / "vfx" / "wake.tscn").read_text("utf-8")
    assert '[node name="wake" type="Node3D"]' in built
    assert '[sub_resource type="GDScript" id="follows"]' in built
    for line in ("width = 0.6", "life = 1.2", "most = 90", "facing = Vector3(0, 1, 0)"):
        assert line in built, line
    assert "GPUParticles3D" not in built
    assert made["wake"]["kind"] == "path_ribbon"
    assert made["wake"]["reach"] == pytest.approx(0.3)


TRAIL = """\
[effect.sparks.ribbon]
kind = "path_ribbon"
amount = 64
lifetime = 0.35
size = 0.25
colour_over_life = ["#ffd980ff", "#ff4d1a00"]

[effect.sparks.particles]
amount = 27
lifetime = 0.45
direction = [0, 1, 0]
spread = 180.0
speed = [3.0, 8.0]
damping = [6.0, 10.0]
size = 0.09
shape = "dot"
colour_over_life = ["#ff9933ff", "#4df2ff00"]
"""


def test_a_trail_is_one_effect_of_two_parts_in_one_scene(tmp_path):
    """§PW284: Starship's trail is a ribbon and its particles, accepted as one look."""
    made = vfx.build(effects(tmp_path, TRAIL), root=str(tmp_path))["effects"]
    assert list(made) == ["sparks"]
    assert made["sparks"]["kind"] == "parts"
    parts = made["sparks"]["parts"]
    assert parts == {"ribbon": "path_ribbon", "particles": "particles"}
    built = (tmp_path / "vfx" / "sparks.tscn").read_text("utf-8")
    assert '[node name="sparks" type="Node3D"]' in built
    assert '[node name="ribbon" type="Node3D" parent="."]' in built
    assert '[node name="particles" type="GPUParticles3D" parent="."]' in built
    # Each part keeps its own look, renamed so the two never collide.
    assert 'id="ribbon_look"' in built and 'id="particles_look"' in built
    assert 'look = SubResource("ribbon_look")' in built


def test_a_whole_measures_every_part(tmp_path):
    made = vfx.build(effects(tmp_path, TRAIL), root=str(tmp_path))["effects"]["sparks"]
    assert made["alive"] == 64 + 27
    assert made["lifetime"] == pytest.approx(0.45)
    assert made["reach"] == pytest.approx(8.0 * 0.45 - 0.5 * 6.0 * 0.45**2, abs=1e-3)


def test_an_effect_that_mixes_keys_and_parts_is_refused(tmp_path):
    body = "[effect.a]\namount = 4\n\n[effect.a.ribbon]\nkind = \"path_ribbon\"\n"
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, body), root=str(tmp_path))
    assert "mixes keys" in refused.value.message


def test_a_part_s_refusal_names_its_part(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, TRAIL.replace("damping = [6.0, 10.0]",
                                                  "damping = -1")),
                  root=str(tmp_path))
    assert "sparks.particles" in refused.value.message


def test_a_path_ribbon_too_small_for_its_life_is_refused(tmp_path):
    """§PW286: paced every 1/60 s, a 1.2 s ribbon holds 73 points."""
    source = effects(tmp_path, WAKE.replace("amount = 90", "amount = 40"))
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(source, root=str(tmp_path))
    assert "needs 73" in refused.value.message
    vfx.build(effects(tmp_path, WAKE + "step = 0.05\n"), root=str(tmp_path))
    built = (tmp_path / "vfx" / "wake.tscn").read_text("utf-8")
    assert "step = 0.05" in built and "gap = 0.3" in built


def test_a_path_ribbon_with_no_width_to_face_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(effects(tmp_path, WAKE + "facing = [0, 0, 0]\n"), root=str(tmp_path))
    assert refused.value.code == "vfx.bad-effect"


def test_a_burst_is_watched_standing_still_and_a_trail_moving():
    burst = vfx.checked("b", {"amount": 8, "lifetime": 0.5, "one_shot": True})
    trail = vfx.checked("t", {"amount": 8, "lifetime": 0.5})
    assert vfx._framing(burst)["round"] == "0"
    assert float(vfx._framing(trail)["round"]) > 0


def test_an_acceptance_spec_bounds_what_a_built_effect_measures(tmp_path):
    from polyweave import accept

    vfx.build(effects(tmp_path), root=str(tmp_path))
    where = tmp_path / "vfx" / "sparks.accept.toml"
    where.write_text(
        'asset = "sparks"\n'
        '[[predicate]]\nid = "budget"\nmeasure = "alive"\nmax = 48\n'
        '[[predicate]]\nid = "reach"\nmeasure = "reach"\nmin = 2.0\nmax = 4.0\n',
        encoding="utf-8",
    )
    found = accept.checked("vfx/sparks.accept.toml", "vfx/sparks.tscn",
                           root=str(tmp_path))
    assert found["failed"] == ["budget"]
    values = {r["id"]: r["value"] for r in found["predicates"]}
    assert values["budget"] == 64
    assert values["reach"] == pytest.approx(3.04)


def test_an_effect_bound_on_something_vfx_build_did_not_make_is_refused(tmp_path):
    from polyweave import accept

    effects(tmp_path)
    (tmp_path / "plain.tscn").write_text("[gd_scene format=3]\n", encoding="utf-8")
    where = tmp_path / "plain.accept.toml"
    where.write_text('asset = "plain"\n[[predicate]]\nid = "r"\nmeasure = "reach"\n'
                     "max = 4.0\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        accept.checked("plain.accept.toml", "plain.tscn", root=str(tmp_path))
    assert refused.value.code == "spec.not-effect"


def test_an_effect_is_watched_over_its_life_as_a_sitting(tmp_path):
    import json

    from polyweave import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    source = effects(tmp_path)
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    laid = vfx.preview(source, out="review/fx", effect="sparks", stills=4,
                       root=str(tmp_path))
    assert laid["effects"]["sparks"]["frames"] > 60
    manifest = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))
    assert set(manifest["choices"]) == set(vfx.VFX_CHOICES)
    # Each choice says what it is and what it leads to (§PW287).
    assert all({"label", "means", "then"} <= set(one)
               for one in manifest["choices"].values())
    # And the effect plays as a film the page loops, beside today's where one is named.
    films = manifest["families"]["sparks"]["members"][0]["films"]
    assert [film["label"] for film in films] == ["Built by polyweave"]
    assert (tmp_path / films[0]["path"]).is_file()
    from PIL import Image

    with Image.open(tmp_path / "review" / "fx" / "sparks.png") as sheet:
        assert sheet.width == 8 + 4 * (vfx.FRAME[0] + 8)
        # Something lit the grey: the sparks are drawn, not only the backdrop.
        import numpy as np

        drawn = np.asarray(sheet.convert("RGB"))[8:8 + vfx.FRAME[1], 8:]
        assert drawn.max() > 120


LOADS = """extends SceneTree

func _initialize() -> void:
\tfor name in ["sparks", "band"]:
\t\tvar packed: PackedScene = load("res://vfx/%s.tscn" % name)
\t\tvar node: GPUParticles3D = packed.instantiate()
\t\tvar process: ParticleProcessMaterial = node.process_material
\t\tprint("vfx: %s amount=%d trail=%s ramp=%s mesh=%s" % [name, node.amount,
\t\t\tnode.trail_enabled, process.color_ramp != null, node.draw_pass_1.get_class()])
\t\tnode.free()
\tprint("vfx: loaded")
\tquit()
"""


def test_the_engine_loads_what_was_built(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "loads.gd").write_text(LOADS, encoding="utf-8")
    ran = engine.run("loads.gd", expect=r"^vfx: loaded", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    assert "vfx: sparks amount=64 trail=false ramp=true mesh=QuadMesh" in said
    assert "vfx: band amount=12 trail=true ramp=true mesh=RibbonTrailMesh" in said


LOADS_ACCEPTED = """extends SceneTree

func _initialize() -> void:
\tfor name in ["confetti", "band"]:
\t\tvar node: GPUParticles3D = load("res://vfx/%s.tscn" % name).instantiate()
\t\tvar process: ParticleProcessMaterial = node.process_material
\t\tvar look: StandardMaterial3D = node.draw_pass_1.material
\t\tprint("vfx: %s damping=%s..%s spin=%s emits=%d box=%s shape=%s random=%s" % [
\t\t\tname, process.damping_min, process.damping_max, process.angular_velocity_max,
\t\t\tprocess.emission_shape, process.emission_box_extents,
\t\t\tlook.albedo_texture.get_class(), node.randomness])
\t\tnode.free()
\tprint("vfx: loaded")
\tquit()
"""


def test_the_engine_loads_an_accepted_trail_s_keys(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, ACCEPTED), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "loads.gd").write_text(LOADS_ACCEPTED, encoding="utf-8")
    ran = engine.run("loads.gd", expect=r"^vfx: loaded", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    assert "vfx: confetti damping=6.0..10.0 spin=240.0 emits=0" in said, said
    assert "shape=GradientTexture2D random=0.3" in said
    assert "vfx: band damping=2.0..2.0 spin=0.0 emits=3 box=(0.1, 1.0, 0.1)" in said


FLIES = """extends SceneTree

var engine := Node3D.new()
var frames := 0

func _initialize() -> void:
\troot.add_child(engine)
\tengine.add_child(load("res://vfx/wake.tscn").instantiate())

func _process(_delta: float) -> bool:
\tframes += 1
\tengine.position = Vector3(frames * 0.1, 0, 0)
\tif frames < 20:
\t\treturn false
\tvar wake: Node3D = engine.get_child(0)
\tvar strip: ImmediateMesh = wake.strip
\tvar box := strip.get_aabb()
\tprint("vfx: points=%d surfaces=%d long=%.1f wide=%.2f" % [wake.points.size(),
\t\tstrip.get_surface_count(), box.size.x, box.size.y])
\treturn true
"""


def test_a_path_ribbon_draws_a_strip_along_where_its_parent_went(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, WAKE), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "flies.gd").write_text(FLIES, encoding="utf-8")
    ran = engine.run("flies.gd", expect=r"^vfx: points", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    found = re.search(r"points=(\d+) surfaces=(\d+) long=([\d.]+) wide=([\d.]+)", said)
    assert found, said
    points, surfaces, long, wide = (float(v) for v in found.groups())
    assert points >= 19 and surfaces == 1
    # It lies behind the path flown, 0.1 a frame, and is at most its width across.
    assert long == pytest.approx(1.8, abs=0.2)
    assert 0.3 < wide <= 0.6


WHOLE = """extends SceneTree

var engine := Node3D.new()
var clock := 0.0

func _initialize() -> void:
\troot.add_child(engine)
\tengine.add_child(load("res://vfx/sparks.tscn").instantiate())

func _process(delta: float) -> bool:
\tclock += delta
\tengine.position = Vector3(clock * 6.0, 0, 0)
\tif clock < 0.5:
\t\treturn false
\tvar whole: Node3D = engine.get_child(0)
\tvar ribbon := whole.get_node("ribbon")
\tvar bits: GPUParticles3D = whole.get_node("particles")
\tprint("vfx: parts=%d points=%d amount=%d emitting=%s" % [whole.get_child_count(),
\t\tribbon.points.size(), bits.amount, bits.emitting])
\treturn true
"""


def test_the_engine_plays_a_whole_made_of_parts(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, TRAIL), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "whole.gd").write_text(WHOLE, encoding="utf-8")
    ran = engine.run("whole.gd", expect=r"^vfx: parts", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    found = re.search(r"parts=(\d+) points=(\d+) amount=(\d+) emitting=(\w+)", said)
    assert found, said
    assert found.group(1) == "2" and int(found.group(2)) > 10
    assert found.group(3) == "27" and found.group(4) == "true"


PACED = """extends SceneTree

var engine := Node3D.new()
var clock := 0.0

func _initialize() -> void:
\troot.add_child(engine)
\tengine.add_child(load("res://vfx/wake.tscn").instantiate())

func _process(delta: float) -> bool:
\tclock += delta
\tengine.position = Vector3(clock * 6.0, 0, 0)
\tif clock < 2.0:
\t\treturn false
\tvar strip: ImmediateMesh = engine.get_child(0).strip
\tprint("vfx: long=%.2f" % strip.get_aabb().size.x)
\treturn true
"""


@pytest.mark.parametrize("fps", [60, 600])
def test_a_path_ribbon_is_as_long_at_600_frames_a_second_as_at_60(tmp_path, fps):
    """§PW286: at 6 m/s and a 1.2 s life it trails 7.2 m, whatever the frame rate."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, WAKE), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "paced.gd").write_text(PACED, encoding="utf-8")
    ran = engine.run("paced.gd", expect=r"^vfx: long", root=tmp_path, headless=True,
                     fixed_fps=fps, frames=5000)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    long = float(re.search(r"long=([\d.]+)", said).group(1))
    assert long == pytest.approx(7.2, abs=0.25)


def test_a_path_ribbon_is_watched_moving_as_a_sitting(tmp_path):
    from polyweave import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    source = effects(tmp_path, WAKE)
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    vfx.preview(source, out="review/fx", stills=4, root=str(tmp_path))
    import numpy as np
    from PIL import Image

    with Image.open(tmp_path / "review" / "fx" / "wake.png") as sheet:
        # The last still: the ribbon has been drawn behind a moving emitter.
        last = np.asarray(sheet.convert("RGB"))[
            8:8 + vfx.FRAME[1], 8 + 3 * (vfx.FRAME[0] + 8):8 + 4 * vfx.FRAME[0] + 24]
        assert last[..., 2].max() > 120