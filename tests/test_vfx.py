"""Visual effects declared as data and built into a Godot scene (§PW259).

Starship's trails were a Resource per trail, tuned by eye. The scene built here is
loaded by the engine itself where there is one, since a scene Godot cannot parse is one
the game cannot play.
"""

from __future__ import annotations

import os
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
    assert manifest["choices"] == vfx.VFX_CHOICES
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