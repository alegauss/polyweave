"""Text read off a held screen for whether it fits (§PW336).

A small game lays out a menu panel 240 pixels wide in a 640 by 360 window: a label that
fits, one cut short by clipping, two lying over each other, and one placed outside the
panel. Godot grows an unwrapped label to its text, so a label too long for its menu
shows as a box leaving its panel; a clipped one, as text wider than its box. A pt_BR
translation makes the short one long, so the same screen fails in the other language.
The tests skip without `$GODOT`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from polyweave.layers.engine import driving, godot

LABELS = """extends Node2D

func _ready() -> void:
\tvar pt := Translation.new()
\tpt.locale = "pt_BR"
\tpt.add_message("START", "COMEÇAR UMA NOVA PARTIDA AGORA")
\tTranslationServer.add_translation(pt)
\tTranslationServer.set_locale("en")
\tvar layer := CanvasLayer.new()
\tlayer.name = "UI"
\tadd_child(layer)
\tvar menu := Panel.new()
\tmenu.name = "Menu"
\tmenu.position = Vector2(20, 20)
\tmenu.size = Vector2(240, 300)
\tlayer.add_child(menu)
\tmenu.add_child(_label("Start", "START", Vector2(10, 10), Vector2(160, 30)))
\tvar long_line := "A LINE FAR TOO LONG"
\tmenu.add_child(_label("Wide", long_line, Vector2(10, 60), Vector2(60, 30), true))
\tmenu.add_child(_label("Left", "OPTIONS", Vector2(10, 120), Vector2(100, 30)))
\tmenu.add_child(_label("Right", "HELP", Vector2(80, 125), Vector2(100, 30)))
\tmenu.add_child(_label("Out", "BACK", Vector2(200, 280), Vector2(100, 30)))
\t# A tag drawn as a texture: in its own viewport it sits where Start sits on screen.
\tvar card := SubViewport.new()
\tcard.name = "Card"
\tcard.size = Vector2i(320, 120)
\tadd_child(card)
\tcard.add_child(_label("Tag", "NORTH", Vector2(30, 30), Vector2(160, 30)))
\t# A list scrolled to its top: its last row is clipped away, not lying over anything.
\tvar scroll := ScrollContainer.new()
\tscroll.name = "Scroll"
\tscroll.position = Vector2(300, 20)
\tscroll.size = Vector2(200, 100)
\tadd_child(scroll)
\tvar rows := Control.new()
\trows.name = "Rows"
\trows.custom_minimum_size = Vector2(180, 400)
\tscroll.add_child(rows)
\trows.add_child(_label("Shown", "FIRST", Vector2(0, 10), Vector2(160, 30)))
\trows.add_child(_label("Hidden", "LAST", Vector2(0, 300), Vector2(160, 30)))
\t# A panel scaled down whole: its label fits its own box at any scale.
\tvar small := Control.new()
\tsmall.name = "Small"
\tsmall.position = Vector2(300, 150)
\tsmall.scale = Vector2(0.64, 0.64)
\tadd_child(small)
\tsmall.add_child(_label("Scaled", "SCALED TEXT HERE", Vector2(0, 0), Vector2(200, 30)))
\t# Drawn small through label_settings: the theme's font would not fit it.
\tvar tiny := _label("Tiny", "TINY PRINT ON A LINE", Vector2(300, 200),
\t\tVector2(100, 30))
\ttiny.label_settings = LabelSettings.new()
\ttiny.label_settings.font_size = 8
\tadd_child(tiny)
\t# Past the right edge of a 640-wide screen.
\tadd_child(_label("Edge", "EDGE", Vector2(600, 260), Vector2(100, 30)))
\t# A modal over the menu covers it, on a layer of its own.
\tvar modal := CanvasLayer.new()
\tmodal.name = "Modal"
\tmodal.layer = 5
\tadd_child(modal)
\tmodal.add_child(_label("Over", "OK", Vector2(30, 140), Vector2(100, 30)))
\tvar gone := CanvasLayer.new()
\tgone.name = "Gone"
\tgone.visible = false
\tadd_child(gone)
\tgone.add_child(_label("Ghost", "UNSEEN", Vector2(30, 30), Vector2(100, 30)))

func _label(named: String, said: String, at: Vector2, size: Vector2,
\t\tclip := false) -> Label:
\tvar label := Label.new()
\tlabel.clip_text = clip
\tlabel.name = named
\tlabel.text = said
\tlabel.position = at
\tlabel.size = size
\treturn label
"""

SCENE = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")
"""


@pytest.fixture
def screen(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="labels"\n'
        'run/main_scene="res://main.tscn"\n\n[display]\n'
        "window/size/viewport_width=640\nwindow/size/viewport_height=360\n",
        encoding="utf-8",
    )
    (tmp_path / "main.gd").write_text(LABELS, encoding="utf-8")
    (tmp_path / "main.tscn").write_text(SCENE, encoding="utf-8")
    godot.install(tmp_path, addon="polyweave_driver")
    root = str(tmp_path)
    session = driving.opened(root, seed=1)["session"]
    yield session, root
    driving.closed(session, root=root)


def unfit(found) -> dict[str, list[str]]:
    return {Path(one["path"]).name: one["findings"] for one in found["unfit"]}


def test_each_text_that_does_not_fit_is_named_with_why(screen):
    session, root = screen
    found = driving.text_fit(session, root=root)
    bad = unfit(found)
    assert "Start" not in bad
    assert any("px wide" in one for one in bad["Wide"])
    assert any("lies over" in one and "Right" in one for one in bad["Left"])
    assert any("leaves its container" in one for one in bad["Out"])
    assert found["passed"] is False


def test_a_label_in_a_subviewport_is_held_to_its_own_viewport(screen):
    """§PW589: a map tag's label read as lying over the screen's, in other units."""
    session, root = screen
    found = driving.text_fit(session, root=root)
    tag = next(one for one in found["nodes"] if one["path"].endswith("Tag"))
    assert tag["viewport"].endswith("Card")
    assert "Tag" not in unfit(found)
    assert not any("Tag" in one for one in unfit(found).get("Start", ()))
    start = next(one for one in found["nodes"] if one["path"].endswith("Start"))
    assert "viewport" not in start


def test_a_longer_translation_is_caught_in_its_own_language(screen):
    session, root = screen
    assert "Start" not in unfit(driving.text_fit(session, root=root))
    found = driving.text_fit(session, locale="pt_BR", root=root)
    start = next(one for one in found["nodes"] if one["path"].endswith("Start"))
    assert start["key"] == "START"
    assert start["text"].startswith("COMEÇAR")
    assert any("leaves its container" in one for one in unfit(found)["Start"])


def node(found, name: str) -> dict:
    return next(one for one in found["nodes"] if Path(one["path"]).name == name)


def test_text_is_judged_as_it_is_drawn(screen):
    # Spinhold, in pt-BR (§PW647): scrolled rows, a scaled kit, label_settings and a
    # modal over the HUD each read as unfit, and a row off the screen read as nothing.
    session, root = screen
    found = driving.text_fit(session, root=root)
    bad = unfit(found)
    hidden = node(found, "Hidden")
    assert hidden["clipped"] is True and hidden["findings"] == []
    assert "Shown" not in bad
    assert "Scaled" not in bad, bad.get("Scaled")
    assert "Tiny" not in bad, bad.get("Tiny")
    assert any("past the screen's edge" in one for one in bad["Edge"])
    assert "Over" not in bad
    assert not any("Over" in one for one in bad.get("Left", ()))
    assert not any(Path(one["path"]).name == "Ghost" for one in found["nodes"])