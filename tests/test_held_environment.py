"""A held game runs in the environment [capture] declares, and its shot says so (§PW339).

Starship's [capture] declared 1920x1080 and en, and every held shot came back 1280x720
in the machine's locale with nothing in the answer to show it. These tests open a game
with a display, so they skip without `$GODOT` or a route that draws real pixels.
"""

from __future__ import annotations

import os

import pytest

from polyweave import driving, godot, offscreen

MAIN = """extends Node2D
"""

SCENE = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")
"""


@pytest.fixture
def game(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    if not offscreen.routes(tmp_path)["available"]:
        pytest.skip("no route draws real pixels here")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="held"\n'
        'run/main_scene="res://main.tscn"\n\n[display]\n'
        "window/size/viewport_width=640\nwindow/size/viewport_height=360\n"
        "window/size/window_width_override=1280\n"
        "window/size/window_height_override=720\n",
        encoding="utf-8",
    )
    (tmp_path / "polyweave.toml").write_text(
        '[capture]\nresolution = [400, 240]\nlocale = "pt_BR"\n', encoding="utf-8"
    )
    (tmp_path / "main.gd").write_text(MAIN, encoding="utf-8")
    (tmp_path / "main.tscn").write_text(SCENE, encoding="utf-8")
    godot.install(tmp_path, addon="polyweave_driver")
    return str(tmp_path)


def test_a_held_shot_is_taken_in_the_declared_environment(game):
    opened = driving.opened(game, display=True)
    session = opened["session"]
    try:
        assert opened["environment"] == {"resolution": "400x240", "locale": "pt_BR"}
        shot = driving.shot(session, out="shots/held.png", root=game)
        # The declared size beats the project's 1280x720 window override.
        assert shot["environment"]["resolution"] == "400x240"
        assert shot["environment"]["locale"].startswith("pt")
        assert shot["differs"] == []
    finally:
        driving.closed(session, root=game)


def test_a_call_may_name_its_own_environment(game):
    opened = driving.opened(game, display=True, resolution=[320, 200], locale="en")
    session = opened["session"]
    try:
        shot = driving.shot(session, out="shots/own.png", root=game)
        assert shot["environment"]["resolution"] == "320x200"
        assert shot["asked"] == {"resolution": "320x200", "locale": "en"}
    finally:
        driving.closed(session, root=game)
