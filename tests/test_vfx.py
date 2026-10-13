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


def test_describe_says_what_a_declaration_holds():
    """§PW409: writing two Quilt effects meant reading KEYS and SHAPES in vfx.py."""
    from polyweave import describe

    said = describe.describe("vfx.build")["declares"]
    assert set(said["keys"]) == set(vfx.KEYS) == set(vfx.ABOUT)
    assert said["keys"]["amount"]["required"] is True
    assert said["keys"]["blend"] == {
        "type": "str", "required": False, "default": "add",
        "choices": ["add", "mix"], "about": vfx.ABOUT["blend"]}
    assert "heart" in said["keys"]["shape"]["choices"]
    assert said["keys"]["emission"]["choices"] == list(vfx.EMISSIONS)
    assert "[effect.<name>.<part>]" in said["file"]
    # The listing of every operation stays as short as it was.
    assert all("declares" not in one for one in describe.describe())


WALL = """\
[effect.wall]
kind = "sheet"
amount = 4
lifetime = 1.0
size = 2.0
height = 6.0
gap = 0.5
across = ["#ffffffff", "#ffd24acc", "#ff4a1a00"]
behind = ["#ffffffff", "#ff4a1a66", "#ff4a1a00"]
ends = 0.25
flicker = 0.2
billboard = "y"
colour_over_life = ["#ffffffff", "#ffffff00"]
"""


def test_a_sheet_of_light_is_one_quad_with_its_own_shader(tmp_path):
    """§PW417: Spinhold's bomb walls are a QuadMesh and a shader built in bomb.gd."""
    made = vfx.build(effects(tmp_path, WALL), root=str(tmp_path))["effects"]["wall"]
    built = (tmp_path / "vfx" / "wall.tscn").read_text("utf-8")
    assert '[node name="wall" type="MeshInstance3D"]' in built
    assert '[sub_resource type="Shader" id="light"]' in built
    assert "MAIN_CAM_INV_VIEW_MATRIX" in built  # turned to the camera about y
    assert "blend_add" in built
    # Its front at the origin, its afterimage of three more copies trailing behind.
    assert "size = Vector2(3.5, 6)" in built
    assert "center_offset = Vector3(-0.75, 0, 0)" in built
    assert "shader_parameter/copies = 4" in built
    assert 'shader_parameter/behind = SubResource("behind")' in built
    assert built.startswith("[gd_scene load_steps=11 ")
    # It reaches its height's half or its afterimage, and is as bright as its core.
    assert made["reach"] == pytest.approx(3.0)
    assert made["brightness"] == pytest.approx(1.0)
    assert made["kind"] == "sheet"


def test_a_sheet_with_no_behind_mirrors_its_profile(tmp_path):
    vfx.build(effects(tmp_path, '[effect.beam]\nkind = "sheet"\namount = 1\n'
                                "lifetime = 0.5\n"), root=str(tmp_path))
    built = (tmp_path / "vfx" / "beam.tscn").read_text("utf-8")
    assert 'shader_parameter/behind = SubResource("across")' in built
    assert "MAIN_CAM_INV_VIEW_MATRIX" not in built
    assert built.startswith("[gd_scene load_steps=9 ")


def test_a_sheet_is_watched_face_on_and_whole():
    import tomllib

    wall = vfx._watched_as(vfx.declared("wall", tomllib.loads(WALL)["effect"]["wall"]))
    framed = vfx._framing(wall)
    centre = [float(v) for v in framed["centre"].split(", ")]
    eye = [float(v) for v in framed["eye"].split(", ")]
    assert centre == [-0.75, 0.0, 0.0]  # the middle of the sheet and its afterimage
    assert eye[0] == centre[0] and eye[1] == 0  # straight in front of its face
    # Far enough back that its 6 m stand inside a 75 degree view, standing still.
    assert eye[2] * 0.767 > 3.0
    assert framed["round"] == "0"


@pytest.mark.parametrize(
    "extra",
    ["height = 0", "ends = 0.6", "flicker = 2", 'billboard = "x"',
     'across = ["#ffffff"]', 'behind = ["#ffffff"]', "size = 0"],
)
def test_a_sheet_that_means_nothing_is_refused(tmp_path, extra):
    source = effects(tmp_path, f'[effect.a]\nkind = "sheet"\namount = 1\n'
                               f"lifetime = 1.0\n{extra}\n")
    with pytest.raises(PolyweaveError) as refused:
        vfx.build(source, root=str(tmp_path))
    assert refused.value.code == "vfx.bad-effect"


CUTE = """\
[effect.twinkles]
amount = 8
lifetime = 0.6
shape = "twinkle"

[effect.stars]
amount = 8
lifetime = 0.6
shape = "star"

[effect.hearts]
amount = 8
lifetime = 0.6
shape = "heart"
"""


def test_a_twinkle_a_star_and_a_heart_are_drawn_inside_the_scene(tmp_path):
    """§PW408: Spinhold's Quilt twinkles shipped as flakes, its hearts as GDScript."""
    vfx.build(effects(tmp_path, CUTE), root=str(tmp_path))
    for name in ("twinkles", "stars", "hearts"):
        built = (tmp_path / "vfx" / f"{name}.tscn").read_text("utf-8")
        assert '[sub_resource type="ImageTexture" id="shape"]' in built, name
        assert '"format": "LumAlpha8"' in built
        assert 'albedo_texture = SubResource("shape")' in built
        assert "ext_resource" not in built  # nothing for the game to import
        assert built.startswith("[gd_scene load_steps=10 ")


def _at(alpha: list[int], u: float, v: float) -> int:
    side = vfx.DRAWN_SIDE
    return alpha[int((1 - v) / 2 * side) * side + int((u + 1) / 2 * side)]


def test_each_drawn_shape_is_where_its_name_says():
    twinkle, star, heart = (vfx._drawn_alpha(s)
                            for s in ("twinkle", "star", "heart"))
    # The twinkle's upright spike reaches further than its level one, and the
    # diagonals between them are empty.
    assert _at(twinkle, 0, 0.8) == 255 and _at(twinkle, 0.8, 0) == 0
    assert _at(twinkle, 0.5, 0) == 255 and _at(twinkle, 0.5, 0.5) == 0
    # The star points up, and the notch under its top point is empty.
    assert _at(star, 0, 0.7) == 255 and _at(star, 0, -0.85) == 0
    assert _at(star, 0.3, 0.6) == 0 and _at(star, 0, 0) == 255
    # The heart has two lobes over a dip, and a point below.
    assert _at(heart, -0.45, 0.55) == 255 and _at(heart, 0.45, 0.55) == 255
    assert _at(heart, 0, 0.8) == 0 and _at(heart, 0, -0.8) == 255
    # Every edge is smoothed, not stepped.
    for alpha in (twinkle, star, heart):
        assert any(0 < a < 255 for a in alpha)


@pytest.mark.parametrize(
    "extra",
    ["damping = -1", "damping = [1, 2, 3]", 'emission = "box"',
     'emission = "box"\nextents = [0.1, -1, 0.1]', 'shape = "comet"',
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


def test_an_effect_the_export_leaves_out_is_watched_in_a_sitting_under_art(tmp_path):
    """§PW424: spinhold's bomb, declared under art/, could not be previewed into
    art/review/ beside the day's other sittings."""
    from polyweave import offscreen

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    source = effects(tmp_path)
    (tmp_path / "vfx" / ".gdignore").write_text("", encoding="utf-8")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    laid = vfx.preview(source, out="art/review/fx", effect="sparks", stills=4,
                       root=str(tmp_path))
    assert laid["sitting"] == "art/review/fx/sitting.json"
    # Filmed from a scene built where nothing ships, never beside the declaration.
    assert laid["effects"]["sparks"]["scene"].startswith(".polyweave/vfx/scenes/")
    assert not (tmp_path / "vfx" / "sparks.tscn").exists()
    assert laid["effects"]["sparks"]["frames"] > 60


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


LOADS_CUTE = """extends SceneTree

func _initialize() -> void:
\tfor name in ["twinkles", "stars", "hearts"]:
\t\tvar node: GPUParticles3D = load("res://vfx/%s.tscn" % name).instantiate()
\t\tvar look: StandardMaterial3D = node.draw_pass_1.material
\t\tvar image: Image = look.albedo_texture.get_image()
\t\tprint("vfx: %s shape=%s size=%dx%d middle=%.2f corner=%.2f" % [
\t\t\tname, look.albedo_texture.get_class(), image.get_width(), image.get_height(),
\t\t\timage.get_pixel(32, 32).a, image.get_pixel(0, 0).a])
\t\tnode.free()
\tprint("vfx: loaded")
\tquit()
"""


def test_the_engine_draws_a_twinkle_a_star_and_a_heart(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, CUTE), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "loads.gd").write_text(LOADS_CUTE, encoding="utf-8")
    ran = engine.run("loads.gd", expect=r"^vfx: loaded", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    for name in ("twinkles", "stars", "hearts"):
        assert f"vfx: {name} shape=ImageTexture size=64x64 middle=1.00 corner=0.00" \
            in said, said


LIGHTS = """extends SceneTree

var frames := 0
var wall: MeshInstance3D

func _initialize() -> void:
\tvar camera := Camera3D.new()
\tcamera.position = Vector3(0, 0, 4)
\troot.add_child(camera)
\twall = load("res://vfx/wall.tscn").instantiate()
\troot.add_child(wall)

func _shown() -> String:
\tvar seen := root.get_texture().get_image()
\tvar middle := seen.get_pixel(seen.get_width() / 2, seen.get_height() / 2)
\tvar corner := seen.get_pixel(2, 2)
\treturn "middle=%.2f corner=%.2f" % [middle.get_luminance(), corner.get_luminance()]

func _process(_delta: float) -> bool:
\tframes += 1
\tif frames == 4:
\t\tprint("vfx: lit " + _shown())
\t\twall.set_instance_shader_parameter("fade", 0.0)
\tif frames == 8:
\t\tprint("vfx: faded " + _shown())
\t\treturn true
\treturn false
"""


def test_the_engine_draws_a_sheet_of_light_and_fades_one(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, WALL.replace("flicker = 0.2", "flicker = 0.0")
                      .replace('"#ffffff00"]\n', '"#ffffffff"]\n')),
              root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "lights.gd").write_text(LIGHTS, encoding="utf-8")
    ran = engine.run("lights.gd", expect=r"^vfx: faded", root=tmp_path)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    lit = re.search(r"vfx: lit middle=([\d.]+) corner=([\d.]+)", said)
    faded = re.search(r"vfx: faded middle=([\d.]+) corner=([\d.]+)", said)
    assert lit and faded, said
    assert float(lit[1]) > 0.8 > float(lit[2])  # its white core, over the backdrop
    # The game faded this one out: its middle is the backdrop again.
    assert float(faded[1]) == pytest.approx(float(faded[2]), abs=0.02)


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


FREED = """extends SceneTree

func _initialize() -> void:
\tvar before := Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)
\tfor i in 7:
\t\tvar wake: Node3D = load("res://vfx/wake.tscn").instantiate()
\t\twake.free()
\tvar after := Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)
\tprint("vfx: orphans=%d" % int(after - before))
\tquit()
"""


def test_a_path_ribbon_freed_outside_the_tree_leaves_nothing_behind(tmp_path):
    """§PW421: spinhold's check built seven trails and left seven mesh nodes at exit."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    vfx.build(effects(tmp_path, WAKE), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="vfx"\n', encoding="utf-8")
    (tmp_path / "freed.gd").write_text(FREED, encoding="utf-8")
    ran = engine.run("freed.gd", expect=r"^vfx: orphans", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    assert re.search(r"vfx: orphans=0\b", said), said


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