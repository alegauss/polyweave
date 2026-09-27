"""The driver that holds a running game and moves it only when told (§PW212).

The install is checked everywhere. The driver itself runs in the engine, over its real
socket, and those tests skip without `$GODOT`.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import socket
import subprocess
from pathlib import Path

import pytest

from polyweave import engine, godot

#: A game with one button that counts its presses, a counter that moves every frame, and
#: a timer's worth of state: enough to see input, frames and holding at work.
MAIN = """extends Node2D

signal counted(times: int)

var presses := 0
var ticks := 0

func _ready() -> void:
\tvar button := Button.new()
\tbutton.name = "Press"
\tbutton.text = "PRESS"
\tbutton.position = Vector2(100, 100)
\tbutton.size = Vector2(200, 80)
\tbutton.pressed.connect(_on_pressed)
\tvar layer := CanvasLayer.new()
\tlayer.name = "UI"
\tadd_child(layer)
\tlayer.add_child(button)
\tadd_to_group("game")

func _process(_delta: float) -> void:
\tticks += 1

func _unhandled_input(event: InputEvent) -> void:
\tif event.is_action_pressed("ui_accept"):
\t\tpresses += 10

func _on_pressed() -> void:
\tpresses += 1
\tcounted.emit(presses)

func setup(start: int) -> int:
\tpresses = start
\treturn presses
"""

SCENE = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")
"""


def game(tmp_path: Path) -> Path:
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="driven"\n'
        'run/main_scene="res://main.tscn"\n\n[display]\n'
        "window/size/viewport_width=640\nwindow/size/viewport_height=360\n",
        encoding="utf-8",
    )
    (tmp_path / "main.gd").write_text(MAIN, encoding="utf-8")
    (tmp_path / "main.tscn").write_text(SCENE, encoding="utf-8")
    godot.install(tmp_path, addon="polyweave_driver")
    return tmp_path


def test_the_driver_installs_as_its_own_addon(tmp_path):
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    found = godot.install(tmp_path, addon="polyweave_driver")
    assert found["files"] == ["addons/polyweave_driver/driver.gd"]


class Driven:
    """One launched game and its socket, for a test to speak the protocol to."""

    def __init__(self, root: Path, *args: str) -> None:
        self.process = subprocess.Popen(
            [
                engine.find(root),
                "--headless",
                "--path",
                str(root),
                "--fixed-fps",
                "60",
                "--script",
                "res://addons/polyweave_driver/driver.gd",
                "--",
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.said = []
        for line in self.process.stdout:
            self.said.append(line)
            found = re.search(r"polyweave_driver: port=(\d+) token=(\w+)", line)
            if found:
                self.port, self.token = int(found[1]), found[2]
                break
        else:
            said = "".join(self.said)
            raise AssertionError(f"the driver never said where it listens:\n{said}")
        self.socket = socket.create_connection(("127.0.0.1", self.port), timeout=60)
        self.reader = self.socket.makefile("r", encoding="utf-8")
        self.next = 0

    def ask(self, cmd: str, token: str | None = None, **fields) -> dict:
        self.next += 1
        request = {"token": token or self.token, "id": self.next, "cmd": cmd, **fields}
        self.socket.sendall((json.dumps(request) + "\n").encode("utf-8"))
        answer = json.loads(self.reader.readline())
        assert answer["id"] == self.next
        return answer

    def close(self) -> None:
        with contextlib.suppress(OSError, json.JSONDecodeError):
            self.ask("close")
        self.socket.close()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()


@pytest.fixture
def driven(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    session = Driven(game(tmp_path), "--seed=7")
    yield session
    session.close()


def ticks(session) -> int:
    return session.ask("query", path=".", properties=["ticks"])["result"][0][
        "properties"
    ]["ticks"]


def test_a_held_game_does_not_move_until_it_is_stepped(driven):
    first = ticks(driven)
    assert ticks(driven) == first, "held, the game's own _process never ran"
    answer = driven.ask("step", frames=5)
    assert answer["ok"] and answer["result"] == {"frames": 5}
    assert ticks(driven) == first + 5
    assert answer["frame"] == 5


def test_a_query_finds_nodes_by_path_group_and_class(driven):
    by_path = driven.ask("query", path="UI/Press")["result"][0]
    assert by_path["class"] == "Button"
    assert by_path["properties"]["text"] == "PRESS"
    assert by_path["properties"]["position"] == [100, 100]
    assert driven.ask("query", group="game")["result"][0]["path"] == "/root/Main"
    assert driven.ask("query", **{"class": "Button"})["result"][0]["path"].endswith(
        "/Press"
    )
    missing = driven.ask("query", path="Nowhere")
    assert (missing["ok"], missing["error"]) == (False, "driver.no-node")


def test_a_click_on_a_button_presses_it_and_an_action_reaches_the_game(driven):
    def presses() -> int:
        answer = driven.ask("query", path=".", properties=["presses"])
        return answer["result"][0]["properties"]["presses"]

    driven.ask("step")
    landed = driven.ask("input", click={"path": "UI/Press"})
    assert landed["result"]["at"] == [200, 140]
    assert presses() == 0, "input lands when the next frame passes, not before"
    driven.ask("step")
    assert presses() == 1
    # The click left the button focused, so accept presses it too, besides the game's.
    driven.ask("input", action="ui_accept")
    driven.ask("step")
    assert presses() == 12


def test_a_click_outside_the_window_is_refused_rather_than_lost(driven):
    """Headless, a pointer off the viewport hovers nothing, and a Button never fires."""
    refused = driven.ask("input", click={"at": [900, 500]})
    assert refused["error"] == "driver.off-screen"
    assert "640 by 360" in refused["message"]


def test_a_wait_spends_frames_until_its_condition_holds(driven):
    at = ticks(driven)
    met = driven.ask("wait", path=".", property="ticks", equals=at + 12, frames=60)
    assert met["result"] == {"met": True, "frames": 12}
    unmet = driven.ask("wait", path=".", property="ticks", equals=-1, frames=3)
    assert unmet["ok"] and unmet["result"] == {"met": False, "frames": 3}


def test_a_wait_for_a_signal_ends_on_the_frame_it_fires(driven):
    driven.ask("step")
    driven.ask("input", click={"path": "UI/Press"})
    fired = driven.ask("wait", path=".", signal="counted", frames=10)
    assert fired["result"]["met"] is True


def test_a_call_runs_a_method_the_game_exposes(driven):
    assert driven.ask("call", path=".", method="setup", args=[40])["result"] == 40
    refused = driven.ask("call", path=".", method="nothing")
    assert refused["error"] == "driver.no-method"


def test_a_shot_in_a_headless_run_is_refused_not_saved_blank(driven):
    assert driven.ask("shot", out="user://x.png")["error"] == "driver.no-picture"


def test_an_unknown_command_is_refused_and_the_game_stays_held(driven):
    first = ticks(driven)
    assert driven.ask("fly")["error"] == "driver.bad-command"
    assert ticks(driven) == first


def test_a_wrong_token_is_refused_and_the_driver_quits(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    session = Driven(game(tmp_path))
    answer = session.ask("query", token="nope", path=".")
    assert answer["error"] == "driver.bad-token"
    assert session.process.wait(timeout=30) == 1
    session.socket.close()


def test_the_same_commands_give_the_same_game(tmp_path):
    """§PW211's finding, held here: the game is the same however long it was held."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    seen = []
    for _ in range(2):
        session = Driven(game(tmp_path), "--seed=7")
        session.ask("step", frames=3)
        session.ask("input", click={"path": "UI/Press"})
        session.ask("step", frames=7)
        pressed = session.ask("query", path=".", properties=["presses"])
        seen.append((ticks(session), pressed))
        session.close()
    assert seen[0][0] == seen[1][0] == 10
    assert seen[0][1]["result"] == seen[1][1]["result"]
