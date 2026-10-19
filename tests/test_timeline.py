"""A scene's own properties keyed in a declared timeline and built (§PW554).

Spinhold's title logo reveal kept its curves as constants in the game's code, where the
design asked them declared as the cutscenes are. The scene built here is played by the
engine itself where there is one.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import engine
from polyweave.layers.motion import timeline

REVEAL = """\
name = "logo_reveal"
easing = "linear"

[[track]]
target = "Halo:modulate"
keys = [
  { at = 0.0, value = [1, 1, 1, 0] },
  { at = 0.8, value = "#ffffff" },
]

[[track]]
target = "Halo:position"
keys = [{ at = 0.0, value = [0, 40], ease = "out" }, { at = 1.0, value = [0, 0] }]

[[track]]
target = "Halo:visible"
keys = [{ at = 0.0, value = false }, { at = 0.1, value = true }]

[[mark]]
at = 1.2
name = "hit"
"""


def reveal(tmp_path, body: str = REVEAL) -> str:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "ui").mkdir(exist_ok=True)
    (tmp_path / "ui" / "logo.timeline.toml").write_text(body, encoding="utf-8")
    return "ui/logo.timeline.toml"


def test_a_timeline_is_built_as_a_scene_with_its_record(tmp_path):
    made = timeline.build(reveal(tmp_path), root=str(tmp_path))
    assert made["file"] == "ui/logo_reveal.tscn"
    assert made["tracks"] == 3 and made["keys"] == 6 and made["marks"] == 1
    assert made["duration"] == pytest.approx(1.2)
    text = (tmp_path / "ui" / "logo_reveal.tscn").read_text("utf-8")
    assert '[node name="logo_reveal" type="AnimationPlayer"]' in text
    assert 'NodePath("Halo:modulate")' in text and "Color(1, 1, 1, 1)" in text
    record = provenance.read("ui/logo_reveal.tscn", root=str(tmp_path))
    assert record["kind"] == "timeline"
    assert record["inputs"][0]["path"] == "ui/logo.timeline.toml"


@pytest.mark.parametrize(("body", "said"), [
    (REVEAL.replace('target = "Halo:position"', 'target = "Halo"'), "targets"),
    (REVEAL.replace("{ at = 1.0, value = [0, 0] }", "{ at = 0.0, value = [0, 0] }"),
     "not after the key before it"),
    (REVEAL.replace("value = false", "value = 0.0"), "mixes values"),
    (REVEAL.replace('ease = "out"', 'ease = "bounce"'), "easing"),
    (REVEAL.replace("name = \"hit\"", "name = \"hit\"\nwhen = 3"), "has no key"),
])
def test_a_timeline_no_animation_can_play_is_refused_by_name(tmp_path, body, said):
    with pytest.raises(PolyweaveError) as refused:
        timeline.build(reveal(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == "clip.bad-timeline"
    assert said in refused.value.message


PLAYS = """extends SceneTree

var parent := Node2D.new()
var player: AnimationPlayer
var marks := []

func _initialize() -> void:
\tvar halo := Sprite2D.new()
\thalo.name = "Halo"
\tparent.add_child(halo)
\troot.add_child(parent)
\tplayer = load("res://ui/logo_reveal.tscn").instantiate()
\tparent.add_child(player)

func _process(_delta: float) -> bool:
\tvar halo: Sprite2D = parent.get_node("Halo")
\tplayer.mark.connect(func(name: String) -> void: marks.append(name))
\tplayer.play("logo_reveal")
\tplayer.seek(0.4, true)
\tprint("timeline: alpha=%.3f y=%.3f visible=%s" % [halo.modulate.a, halo.position.y,
\t\thalo.visible])
\tplayer.advance(1.0)
\tprint("timeline: marks=%s end_alpha=%.3f" % [",".join(marks), halo.modulate.a])
\treturn true
"""


def test_the_engine_plays_the_timeline_as_declared(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    timeline.build(reveal(tmp_path), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="timeline"\n', encoding="utf-8")
    (tmp_path / "plays.gd").write_text(PLAYS, encoding="utf-8")
    ran = engine.run("plays.gd", expect=r"^timeline: marks", root=tmp_path,
                     headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    # halfway through the fade; the move eases out from its first key, so it is past
    # the 24 a linear move would be at
    assert "alpha=0.500" in said, said
    assert "visible=true" in said
    y = float(said.split(" y=")[1].split()[0])
    assert 0 < y < 40 * 0.6
    assert "marks=hit end_alpha=1.000" in said
