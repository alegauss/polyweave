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
import time
from pathlib import Path

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import driving, engine, godot

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


#: A splash that hands over to the game a few frames in, as a game's scenes do.
SPLASH = """extends Node2D

var frames := 0

func _process(_delta: float) -> void:
\tframes += 1
\tif frames == 3:
\t\tget_tree().change_scene_to_file("res://main.tscn")
"""


def test_a_scene_the_game_leaves_is_gone(tmp_path):
    # §PW297: the driver's scene is the current one, so the game's own change frees it.
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "splash.gd").write_text(SPLASH, encoding="utf-8")
    (root / "splash.tscn").write_text(
        SCENE.replace("main.gd", "splash.gd").replace('"Main"', '"Splash"'),
        encoding="utf-8",
    )
    session = Driven(root, "--scene=res://splash.tscn")
    try:
        assert session.ask("query", path="/root/Splash")["ok"]
        session.ask("step", frames=10)
        gone = session.ask("query", path="/root/Splash")
        assert (gone["ok"], gone["error"]) == (False, "driver.no-node")
        assert session.ask("query", path="/root/Main")["ok"]
        # A relative path follows the scene playing now.
        assert session.ask("query", path="UI/Press")["result"][0]["class"] == "Button"
    finally:
        session.close()


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
    # A tap presses on one frame and releases on the next, and a Button fires on the
    # release, so both frames have to pass.
    driven.ask("input", action="ui_accept")
    driven.ask("step", frames=2)
    assert presses() == 12


def test_a_click_outside_the_window_is_refused_rather_than_lost(driven):
    """Headless, a pointer off the viewport hovers nothing, and a Button never fires."""
    refused = driven.ask("input", click={"at": [900, 500]})
    assert refused["error"] == "driver.off-screen"
    assert "640 by 360" in refused["message"]


HELD = """extends Node2D

var held_frames := 0
var taps := 0

func _process(_delta: float) -> void:
\tif Input.is_action_pressed("ui_right"):
\t\theld_frames += 1
\tif Input.is_action_just_pressed("ui_left"):
\t\ttaps += 1
"""


def test_a_held_action_stays_pressed_until_released(tmp_path):
    """§PW216: a shooter polls held state, and a tap is seen as just pressed once."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "main.gd").write_text(HELD, encoding="utf-8")
    session = Driven(root)
    try:
        session.ask("input", action="ui_right", hold=True)
        session.ask("step", frames=10)
        session.ask("input", action="ui_right", release=True)
        session.ask("step", frames=5)
        session.ask("input", action="ui_left")
        session.ask("step", frames=3)
        said = session.ask("query", path=".", properties=["held_frames", "taps"])
        assert said["result"][0]["properties"] == {"held_frames": 10, "taps": 1}
    finally:
        session.close()


#: A stage editor's worth of gestures (§PW607): a tile dragged onto a slot through
#: Godot's own drag and drop, a pad that counts every other button, the wheel and the
#: modifiers held on them, and a field to type a name into.
GESTURES = """extends Node2D

var dropped := ""
var dropped_at := []
var right := 0
var middle := 0
var doubles := 0
var wheel := 0
var shift_wheel := 0
var ctrl_click := 0
var shift_held := 0
var moved := 0

class Tile extends ColorRect:
\tfunc _get_drag_data(_at: Vector2) -> Variant:
\t\treturn "tile"

class Slot extends ColorRect:
\tvar main: Node
\tfunc _can_drop_data(_at: Vector2, data: Variant) -> bool:
\t\treturn data == "tile"
\tfunc _drop_data(at: Vector2, data: Variant) -> void:
\t\tmain.dropped = data
\t\tmain.dropped_at = [at.x, at.y]

func _ready() -> void:
\tvar tile := Tile.new()
\ttile.name = "Tile"
\ttile.position = Vector2(20, 20)
\ttile.size = Vector2(80, 80)
\tadd_child(tile)
\tvar slot := Slot.new()
\tslot.name = "Slot"
\tslot.main = self
\tslot.position = Vector2(160, 20)
\tslot.size = Vector2(80, 80)
\tadd_child(slot)
\tvar pad := ColorRect.new()
\tpad.name = "Pad"
\tpad.position = Vector2(300, 20)
\tpad.size = Vector2(300, 200)
\tpad.gui_input.connect(_on_pad)
\tadd_child(pad)
\tvar field := LineEdit.new()
\tfield.name = "Field"
\tfield.position = Vector2(20, 260)
\tfield.size = Vector2(240, 40)
\tadd_child(field)

func _on_pad(event: InputEvent) -> void:
\tif event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_RIGHT:
\t\tmoved += 1
\tif not (event is InputEventMouseButton and event.pressed):
\t\treturn
\tif Input.is_key_pressed(KEY_SHIFT):
\t\tshift_held += 1
\tmatch event.button_index:
\t\tMOUSE_BUTTON_RIGHT:
\t\t\tright += 1
\t\tMOUSE_BUTTON_MIDDLE:
\t\t\tmiddle += 1
\t\tMOUSE_BUTTON_WHEEL_UP:
\t\t\twheel += 1
\t\t\tif event.shift_pressed:
\t\t\t\tshift_wheel += 1
\t\tMOUSE_BUTTON_WHEEL_DOWN:
\t\t\twheel -= 1
\t\tMOUSE_BUTTON_LEFT:
\t\t\tif event.ctrl_pressed:
\t\t\t\tctrl_click += 1
\tif event.double_click:
\t\tdoubles += 1
"""

SAID = ["dropped", "dropped_at", "right", "middle", "doubles", "wheel", "shift_wheel",
        "ctrl_click", "shift_held", "moved"]


def gestured(tmp_path: Path) -> Path:
    root = game(tmp_path)
    (root / "main.gd").write_text(GESTURES, encoding="utf-8")
    return root


def test_every_gesture_a_mouse_tool_takes_reaches_the_game(tmp_path):
    """§PW607: Spinhold's stage editor is gestures, and the driver could only click."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    session = Driven(gestured(tmp_path))
    try:
        dragged = session.ask("input", drag={"from": {"path": "Tile"},
                                             "to": {"path": "Slot"}, "frames": 6})
        assert dragged["result"] == {"from": [60, 60], "to": [200, 60], "lasts": 7}
        session.ask("step", frames=7)
        session.ask("input", click={"path": "Pad", "button": "right"})
        session.ask("input", click={"path": "Pad", "button": "middle"})
        session.ask("input", click={"path": "Pad", "double": True}, mods=["ctrl"])
        session.ask("input", wheel={"path": "Pad", "steps": 3}, mods=["shift"])
        session.ask("input", wheel={"at": [400, 100], "steps": -1})
        session.ask("input", drag={"from": {"at": [320, 40]}, "to": {"at": [580, 200]},
                                   "through": [[580, 40]], "frames": 4,
                                   "button": "right"})
        session.ask("step", frames=6)
        said = session.ask("query", path=".", properties=SAID)["result"][0]
        assert said["properties"] == {
            "dropped": "tile", "dropped_at": [40, 40], "right": 2, "middle": 1,
            "doubles": 1, "wheel": 2, "shift_wheel": 3, "ctrl_click": 2,
            "shift_held": 3, "moved": 4,
        }
        session.ask("input", click={"path": "Field"})
        session.ask("step")
        session.ask("input", text="Spinhold 1")
        session.ask("step")
        typed = session.ask("query", path="Field", properties=["text"])["result"][0]
        assert typed["properties"]["text"] == "Spinhold 1"
        for wrong in ({"click": {"path": "Pad", "button": "fourth"}},
                      {"click": {"path": "Pad"}, "mods": ["hyper"]},
                      {"wheel": {"path": "Pad", "steps": 0}},
                      {"drag": {"from": {"path": "Tile"}}},
                      {"text": "x", "mods": ["shift"]}):
            assert session.ask("input", **wrong)["error"] == "driver.bad-command"
        off = session.ask("input", drag={"from": {"path": "Tile"},
                                         "to": {"at": [900, 9]}})
        assert off["error"] == "driver.off-screen"
        assert "drag's end" in off["message"]
    finally:
        session.close()


def test_a_kept_drag_replays_with_no_agent(tmp_path):
    """§PW607: a mouse tool's case runs in the gate once game.keep has written it."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(gestured(tmp_path))
    session = driving.opened(root)["session"]
    try:
        lasts = driving.inputted(session, drag="Tile", to="Slot", frames=5,
                                 mods=["Shift"], root=root)["result"]["lasts"]
        driving.stepped(session, frames=lasts, root=root)
        driving.inputted(session, wheel=-2, over="Pad", root=root)
        driving.inputted(session, at=[400, 100], button="right", double=True, root=root)
        driving.stepped(session, root=root)
        seen = driving.queried(session, path=".",
                               properties=["dropped", "wheel", "right"], root=root)
        assert seen["result"][0]["properties"] == {"dropped": "tile", "wheel": -2,
                                                   "right": 2}
        kept = driving.kept(session, out="tests/flows/drag.flow.json",
                            proves="a tile dragged onto its slot lands there",
                            expect=[seen["step"]], root=root)
    finally:
        driving.closed(session, root=root)
    flow = json.loads(Path(kept["flow"]).read_text(encoding="utf-8"))
    assert flow["steps"][0]["drag"] == {"from": {"path": "Tile"},
                                        "to": {"path": "Slot"}, "frames": 5}
    assert flow["steps"][0]["mods"] == ["shift"]
    replayed = driving.replayed("tests/flows/drag.flow.json", root=root)
    assert replayed["ok"] is True, replayed["why"]


def test_an_input_that_names_two_gestures_or_none_is_refused_before_sending(tmp_path):
    for asked in ({}, {"click": "A", "drag": "B"}, {"key": "Space", "button": "right"},
                  {"drag": "A"}, {"wheel": 1}, {"wheel": 1, "over": "A", "at": [1, 1]}):
        with pytest.raises(PolyweaveError) as refused:
            driving.inputted("nobody", root=str(tmp_path), **asked)
        assert refused.value.code == "game.bad-target", asked


def test_a_kept_drag_is_rekeyed_at_both_of_its_ends():
    fields = {"drag": {"from": {"path": "@C@1"}, "to": {"path": "@C@2"}, "frames": 3},
              "mods": ["ctrl"]}
    assert driving._step_paths(fields) == ["@C@1", "@C@2"]
    keyed = driving._selected(fields, {"@C@1": {"class": "Tile"},
                                       "@C@2": {"class": "Slot"}})
    assert keyed["drag"] == {"from": {"select": {"class": "Tile"}},
                             "to": {"select": {"class": "Slot"}}, "frames": 3}
    assert fields["drag"]["from"] == {"path": "@C@1"}, "the step kept is not changed"
    clicked = driving._selected({"click": {"path": "@C@1", "button": "right"}},
                                {"@C@1": {"class": "Tile"}})
    assert clicked["click"] == {"select": {"class": "Tile"}, "button": "right"}


SEEDED = """extends Node2D

var rng := RandomNumberGenerator.new()
var drawn := 0

func draw() -> int:
\tdrawn = rng.randi_range(0, 1000000)
\treturn drawn
"""


def test_a_set_seeds_a_generator_the_game_made_itself(tmp_path):
    """§PW217: --seed covers the global functions, and a game's own generator not."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "main.gd").write_text(SEEDED, encoding="utf-8")
    drawn = []
    for _ in range(2):
        session = driving.opened(str(root))["session"]
        try:
            was = driving.set_value(
                session, path=".", prop="rng:seed", value="42", root=str(root)
            )
            assert was["result"]["now"] == 42
            drawn.append(
                driving.called(session, path=".", method="draw", root=str(root))[
                    "result"
                ]
            )
        finally:
            driving.closed(session, root=str(root))
    assert drawn[0] == drawn[1]
    session = driving.opened(str(root))["session"]
    try:
        with pytest.raises(PolyweaveError) as refused:
            driving.set_value(
                session, path=".", prop="nothing", value="1", root=str(root)
            )
        assert refused.value.code == "driver.bad-command"
    finally:
        driving.closed(session, root=str(root))


def test_a_vector_given_as_a_list_is_set_as_the_propertys_own_type(tmp_path):
    """§PW599: Spinhold's camera moved to [10.8, 0.7, -1.6] landed at the origin."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    session = driving.opened(str(root))["session"]
    try:
        moved = driving.set_value(session, path=".", prop="position", value="[1, 2]",
                                  root=str(root))
        assert moved["result"]["now"] == [1.0, 2.0]
        spelt = driving.set_value(session, path=".", prop="position",
                                  value='"Vector2(3, 4)"', root=str(root))
        assert spelt["result"]["now"] == [3.0, 4.0]
        tinted = driving.set_value(session, path=".", prop="modulate",
                                   value="[1, 0, 0]", root=str(root))
        assert tinted["result"]["now"][:3] == [1.0, 0.0, 0.0]
        with pytest.raises(PolyweaveError) as refused:
            driving.set_value(session, path=".", prop="position", value="[1, 2, 3]",
                              root=str(root))
        assert "a list of 2 numbers" in refused.value.message
    finally:
        driving.closed(session, root=str(root))


SAVING = """extends Node2D

var opened := 0

func _ready() -> void:
\tvar was := FileAccess.get_file_as_string("user://count.txt")
\topened = int(was) + 1 if was != "" else 1
\tvar out := FileAccess.open("user://count.txt", FileAccess.WRITE)
\tout.store_string(str(opened))
"""


def test_every_session_starts_from_a_fresh_user_folder(tmp_path):
    """§PW217: a driven game never reads or writes the person's own save."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "main.gd").write_text(SAVING, encoding="utf-8")
    for _ in range(2):
        session = driving.opened(str(root))["session"]
        try:
            said = driving.queried(
                session, path=".", properties=["opened"], root=str(root)
            )
            assert said["result"][0]["properties"]["opened"] == 1
        finally:
            driving.closed(session, root=str(root))


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


def test_a_session_is_opened_driven_and_closed_through_the_operations(tmp_path):
    """§PW213: every call a connection of its own, the game held between them."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    opened = driving.opened(root, seed=7)
    session = opened["session"]
    try:
        assert opened["frame"] == 0
        found = driving.queried(session, path="UI/Press", root=root)
        assert found["result"][0]["properties"]["text"] == "PRESS"
        assert driving.inputted(session, click="UI/Press", root=root)["result"] == {
            "at": [200, 140]
        }
        stepped = driving.stepped(session, frames=2, root=root)
        assert stepped["frame"] == 2
        met = driving.waited(session, path=".", prop="presses", equals="1", root=root)
        assert met["result"] == {"met": True, "frames": 0}
        assert (
            driving.called(session, path=".", method="setup", args=[5], root=root)[
                "result"
            ]
            == 5
        )
        with pytest.raises(PolyweaveError) as refused:
            driving.queried(session, path="Nowhere", root=root)
        assert refused.value.code == "driver.no-node"
        with pytest.raises(PolyweaveError) as headless:
            driving.shot(session, out="shots/x.png", root=root)
        assert headless.value.code == "driver.no-picture"
    finally:
        ended = driving.closed(session, root=root)
    assert ended["closed"] is True
    with pytest.raises(PolyweaveError) as gone:
        driving.queried(session, path=".", root=root)
    assert gone.value.code == "game.no-session"


def test_the_game_s_own_arguments_reach_it_and_its_kept_flow(tmp_path):
    """Spinhold opens a run straight in a world with its own --world flag, which
    game.open could not pass (§PW553)."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "main.gd").write_text(
        MAIN.replace("var ticks := 0\n", "var ticks := 0\nvar world := \"\"\n").replace(
            "\tadd_to_group(\"game\")\n",
            "\tadd_to_group(\"game\")\n\tfor arg in OS.get_cmdline_user_args():\n"
            "\t\tif arg.begins_with(\"--world=\"):\n"
            "\t\t\tworld = arg.get_slice(\"=\", 1)\n"),
        encoding="utf-8")
    opened = driving.opened(str(root), args=["--world=quilt"])
    session = opened["session"]
    try:
        assert opened["args"] == ["--world=quilt"]
        found = driving.queried(session, path=".", properties=["world"], root=str(root))
        assert found["result"][0]["properties"]["world"] == "quilt"
        kept = driving.kept(session, out="flows/world.flow.json",
                            proves="the run opens in the world its flag names",
                            root=str(root))
    finally:
        driving.closed(session, root=str(root))
    flow = json.loads(Path(kept["flow"]).read_text(encoding="utf-8"))
    assert flow["args"] == ["--world=quilt"]


def test_an_error_the_game_prints_is_reported_by_the_call_that_caused_it(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "main.gd").write_text(
        MAIN
        + '\nfunc broken() -> void:\n\tpush_error("SCRIPT ERROR: the vault jammed")\n',
        encoding="utf-8",
    )
    session = driving.opened(str(root))["session"]
    try:
        quiet = driving.stepped(session, root=str(root))
        assert quiet["errors"] == []
        loud = driving.called(session, path=".", method="broken", root=str(root))
        assert any("the vault jammed" in line for line in loud["errors"])
        assert driving.stepped(session, root=str(root))["errors"] == []
    finally:
        driving.closed(session, root=str(root))


def test_a_session_nobody_calls_ends_on_its_own(tmp_path):
    """A session an agent forgot never outlives the conversation (§PW213)."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "polyweave.toml").write_text("[driving]\nidle = 2\n", encoding="utf-8")
    session = driving.opened(str(root))["session"]
    record = json.loads(
        (root / ".polyweave" / "driving" / f"{session}.json").read_text()
    )
    deadline = time.monotonic() + 30
    while driving._alive(record["pid"]) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert not driving._alive(record["pid"])
    with pytest.raises(PolyweaveError) as gone:
        driving.stepped(session, root=str(root))
    assert gone.value.code == "game.gone"


def test_a_step_resets_the_idle_clock_and_a_timeout_says_it_was_one(tmp_path):
    """§PW590: a session quit as idle seconds after a step, and the refusal could not
    say whether it had timed out or crashed, nor how long it had been."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    (root / "polyweave.toml").write_text("[driving]\nidle = 3\n", encoding="utf-8")
    session = driving.opened(str(root))["session"]
    for _ in range(3):
        time.sleep(1.5)  # under the idle seconds each time, past them in all
        driving.stepped(session, frames=30, root=str(root))
    record = json.loads(
        (root / ".polyweave" / "driving" / f"{session}.json").read_text()
    )
    deadline = time.monotonic() + 30
    while driving._alive(record["pid"]) and time.monotonic() < deadline:
        time.sleep(0.5)
    with pytest.raises(PolyweaveError) as gone:
        driving.stepped(session, root=str(root))
    assert "its last answer, to step at frame 90" in gone.value.message
    assert "[driving] idle" in gone.value.remedy
    assert "since it answered step at frame 90" in gone.value.detail


def test_a_sweep_drops_only_the_user_folders_of_sessions_gone(tmp_path):
    """§PW594: Spinhold's driving folder held 5,207 folders of ended sessions."""
    folder = tmp_path / "driving"
    for name in ("g0000aaaa.user/Godot", "g1111bbbb.user", "replay.user"):
        (folder / name).mkdir(parents=True)
    (folder / "g1111bbbb.json").write_text("{}", encoding="utf-8")  # still open
    driving._sweep_users(folder)
    assert sorted(one.name for one in folder.iterdir()) == [
        "g1111bbbb.json", "g1111bbbb.user", "replay.user"]


def test_a_closed_session_takes_its_user_folder_with_it(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    session = driving.opened(str(root))["session"]
    folder = root / ".polyweave" / "driving"
    assert (folder / f"{session}.user").is_dir()
    said = driving.closed(session, root=str(root))
    assert said["user_removed"] is True
    assert not (folder / f"{session}.user").exists()
    assert (folder / f"{session}.log").is_file()


def test_a_session_kept_as_a_flow_replays_with_no_agent(tmp_path):
    """§PW214: what a session proved becomes a file the runner replays alone."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    session = driving.opened(root, seed=3)["session"]
    try:
        driving.stepped(session, root=root)
        # A wrong turn, left out of the flow.
        wrong = driving.called(session, path=".", method="setup", args=[100], root=root)
        driving.called(session, path=".", method="setup", args=[0], root=root)
        driving.inputted(session, click="UI/Press", root=root)
        driving.stepped(session, frames=3, root=root)
        seen = driving.queried(session, path=".", properties=["presses"], root=root)
        assert seen["result"][0]["properties"]["presses"] == 1
        kept = driving.kept(
            session,
            out="tests/flows/press.flow.json",
            proves="a click on PRESS counts one press",
            expect=[seen["step"]],
            drop=[wrong["step"]],
            root=root,
        )
    finally:
        driving.closed(session, root=root)
    assert kept["expectations"] == 1
    flow = json.loads(Path(kept["flow"]).read_text(encoding="utf-8"))
    assert [one["cmd"] for one in flow["steps"]] == [
        "step",
        "call",
        "input",
        "step",
        "expect",
    ]
    assert flow["seed"] == 3
    assert flow["engine"]

    passed = driving.replayed("tests/flows/press.flow.json", root=root)
    assert passed["ok"] is True, passed["why"]
    assert passed["frame"] == 4
    assert passed["differs"] == {}

    flow["steps"][-1]["equals"] = 7
    Path(kept["flow"]).write_text(json.dumps(flow), encoding="utf-8")
    broke = driving.replayed("tests/flows/press.flow.json", root=root)
    assert broke["ok"] is False
    assert broke["failed_step"] == 5
    assert "presses was 1, not 7" in broke["why"]


#: A game that names none of its nodes, as Cottony builds its screens, and adds one more
#: ahead of them where `res://extra.txt` exists: what renumbers every generated name.
UNNAMED = """extends Node2D

var presses := 0
var label: Label

func _ready() -> void:
\tif FileAccess.file_exists("res://extra.txt"):
\t\tadd_child(Node2D.new())
\tvar button := Button.new()
\tbutton.text = "GO"
\tbutton.position = Vector2(100, 100)
\tbutton.size = Vector2(200, 80)
\tbutton.pressed.connect(_on_pressed)
\tadd_child(button)
\tlabel = Label.new()
\tlabel.text = "READY"
\tadd_child(label)

func _on_pressed() -> void:
\tpresses += 1
\tlabel.text = "PRESSED %d" % presses
"""


def test_a_flow_kept_at_generated_names_survives_a_node_added_ahead(tmp_path):
    """§PW270: Cottony's flows clicked at @Node2D@14-style paths, which renumber."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    (tmp_path / "main.gd").write_text(UNNAMED, encoding="utf-8")
    session = driving.opened(root, seed=1)["session"]
    try:
        driving.stepped(session, root=root)
        button = driving.queried(session, of_class="Button", root=root)["result"][0]
        assert "@" in button["path"], "an unnamed node's path is a generated one"
        driving.inputted(session, click=button["path"], root=root)
        driving.stepped(session, frames=3, root=root)
        seen = driving.queried(session, of_class="Label", properties=["text"],
                               root=root)
        assert seen["result"][0]["properties"]["text"] == "PRESSED 1"
        kept = driving.kept(session, out="tests/flows/go.flow.json",
                            proves="a click on GO says so", expect=[seen["step"]],
                            root=root)
    finally:
        driving.closed(session, root=root)
    assert kept["fragile"] == []
    flow = json.loads(Path(kept["flow"]).read_text(encoding="utf-8"))
    clicked = next(one for one in flow["steps"] if one["cmd"] == "input")
    assert clicked["click"] == {"select": {"class": "Button"}}
    assert flow["steps"][-1]["select"] == {"class": "Label"}
    (tmp_path / "extra.txt").write_text("renumber", encoding="utf-8")
    again = driving.replayed("tests/flows/go.flow.json", root=root)
    assert again["ok"] is True, again["why"]
    # The same flow at the generated path breaks, which is what the selector saved.
    clicked["click"] = {"path": button["path"]}
    Path(kept["flow"]).write_text(json.dumps(flow), encoding="utf-8")
    assert driving.replayed("tests/flows/go.flow.json", root=root)["ok"] is False


#: Two screens the game names, each holding an unnamed button of the same text: no
#: class or property tells the buttons apart, only the screen each sits in.
SCREENS = """extends Node2D

var title := 0
var menu := 0

func _ready() -> void:
\tif FileAccess.file_exists("res://extra.txt"):
\t\tadd_child(Node2D.new())
\tfor screen_name in ["Title", "Menu"]:
\t\tvar screen := Node2D.new()
\t\tscreen.name = screen_name
\t\tadd_child(screen)
\t\tvar button := Button.new()
\t\tbutton.text = "GO"
\t\tbutton.position = Vector2(100 if screen_name == "Title" else 400, 100)
\t\tbutton.size = Vector2(120, 60)
\t\tbutton.pressed.connect(_pressed.bind(screen_name))
\t\tscreen.add_child(button)

func _pressed(screen_name: String) -> void:
\tif screen_name == "Menu":
\t\tmenu += 1
\telse:
\t\ttitle += 1
"""


def test_an_unnamed_button_is_picked_out_under_the_screen_it_sits_in(tmp_path):
    """§PW277: Cottony's play buttons stayed fragile, each alone under a screen."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    (tmp_path / "main.gd").write_text(SCREENS, encoding="utf-8")
    session = driving.opened(root, seed=1)["session"]
    try:
        driving.stepped(session, root=root)
        found = driving.queried(session, of_class="Button", root=root)["result"]
        menu = next(one for one in found if "/Menu/" in one["path"])
        driving.inputted(session, click=menu["path"], root=root)
        driving.stepped(session, frames=3, root=root)
        seen = driving.queried(session, path=".", properties=["title", "menu"],
                               root=root)
        assert seen["result"][0]["properties"] == {"title": 0, "menu": 1}
        kept = driving.kept(session, out="tests/flows/menu.flow.json",
                            proves="the menu's GO counts the menu", root=root,
                            expect=[seen["step"]])
    finally:
        driving.closed(session, root=root)
    assert kept["fragile"] == []
    flow = json.loads(Path(kept["flow"]).read_text(encoding="utf-8"))
    clicked = next(one for one in flow["steps"] if one["cmd"] == "input")
    assert clicked["click"]["select"]["under"] == {"class": "Node2D", "name": "Menu"}
    (tmp_path / "extra.txt").write_text("renumber", encoding="utf-8")
    assert driving.replayed("tests/flows/menu.flow.json", root=root)["ok"] is True


#: A game counting in a Dictionary, which a query answers and a flow expects whole.
COUNTED = MAIN.replace("var presses := 0", "var presses := 0\nvar tally := {}").replace(
    "\tpresses += 1\n\tcounted.emit(presses)",
    '\tpresses += 1\n\ttally = {"Menu": presses, "Title": 0, "seen": [presses, 2]}'
    "\n\tcounted.emit(presses)",
)


def test_an_expectation_on_a_dictionary_of_numbers_holds_as_numbers(tmp_path):
    """§PW278: {"Menu": 1} was compared with {"Menu": 1.0} as text, and failed."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    (tmp_path / "main.gd").write_text(COUNTED, encoding="utf-8")
    session = driving.opened(root, seed=1)["session"]
    try:
        driving.stepped(session, root=root)
        driving.inputted(session, click="UI/Press", root=root)
        driving.stepped(session, frames=3, root=root)
        seen = driving.queried(session, path=".", properties=["tally"], root=root)
        assert seen["result"][0]["properties"]["tally"]["Menu"] == 1
        kept = driving.kept(session, out="tests/flows/tally.flow.json",
                            proves="a press counts in the tally", root=root,
                            expect=[seen["step"]])
    finally:
        driving.closed(session, root=root)
    assert driving.replayed("tests/flows/tally.flow.json", root=root)["ok"] is True
    flow = json.loads(Path(kept["flow"]).read_text(encoding="utf-8"))
    flow["steps"][-1]["equals"]["Menu"] = 2
    Path(kept["flow"]).write_text(json.dumps(flow), encoding="utf-8")
    broke = driving.replayed("tests/flows/tally.flow.json", root=root)
    assert broke["ok"] is False and '"Menu":1' in broke["why"]


def test_a_flow_kept_before_selectors_is_rekeyed_in_one_call(tmp_path):
    """§PW276: Cottony's older flows still reach their nodes by generated names."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    (tmp_path / "main.gd").write_text(UNNAMED, encoding="utf-8")
    session = driving.opened(root, seed=1)["session"]
    try:
        driving.stepped(session, root=root)
        button = driving.queried(session, of_class="Button", root=root)["result"][0]
        label = driving.queried(session, of_class="Label", root=root)["result"][0]
    finally:
        driving.closed(session, root=root)
    older = {"format": 1, "proves": "a click on GO says so", "seed": 1, "scene": "",
             "engine": "", "driver": "", "steps": [
                 {"cmd": "step", "frames": 1},
                 {"cmd": "input", "click": {"path": button["path"]}},
                 {"cmd": "step", "frames": 3},
                 {"cmd": "expect", "path": label["path"], "property": "text",
                  "equals": "PRESSED 1"},
             ]}
    where = tmp_path / "tests" / "flows" / "old.flow.json"
    where.parent.mkdir(parents=True)
    where.write_text(json.dumps(older), encoding="utf-8")
    said = driving.rekeyed("tests/flows/old.flow.json", root=root)
    assert said["rekeyed"] == 2 and said["fragile"] == []
    flow = json.loads(where.read_text(encoding="utf-8"))
    assert flow["steps"][1]["click"] == {"select": {"class": "Button"}}
    (tmp_path / "extra.txt").write_text("renumber", encoding="utf-8")
    assert driving.replayed("tests/flows/old.flow.json", root=root)["ok"] is True


def test_a_batch_of_commands_is_one_call_and_is_kept_like_any_other(tmp_path):
    """§PW271: a level of thirty moves cost hundreds of processes from the terminal."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    session = driving.opened(root, seed=2)["session"]
    try:
        said = driving.batched(session, [
            {"cmd": "step"},
            *[{"cmd": "input", "click": {"path": "UI/Press"}}, {"cmd": "step",
              "frames": 2}] * 3,
            {"cmd": "query", "path": ".", "properties": ["presses"]},
            {"cmd": "call", "path": ".", "method": "nope"},
            {"cmd": "step"},
        ], root=root)
        assert said["stopped"] == 8 and said["sent"] == 9
        assert said["answers"][7]["result"][0]["properties"]["presses"] == 3
        assert said["answers"][8]["refused"]["code"] == "driver.no-method"
        kept = driving.kept(session, out="tests/flows/three.flow.json",
                            proves="three clicks count three",
                            expect=[said["answers"][7]["step"]], root=root)
    finally:
        driving.closed(session, root=root)
    assert kept["expectations"] == 1
    assert driving.replayed("tests/flows/three.flow.json", root=root)["ok"] is True


def test_a_batch_command_that_is_not_one_is_refused_before_any_is_sent(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        driving.batched("nobody", [{"cmd": "launch"}], root=str(tmp_path))
    assert refused.value.code == "game.bad-target"


def test_a_query_step_is_all_an_expectation_can_be_made_of(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = str(game(tmp_path))
    session = driving.opened(root)["session"]
    try:
        step = driving.stepped(session, root=root)["step"]
        with pytest.raises(PolyweaveError) as refused:
            driving.kept(
                session, out="x.flow.json", proves="x", expect=[step], root=root
            )
        assert refused.value.code == "game.bad-target"
    finally:
        driving.closed(session, root=root)


def test_a_project_that_installed_nothing_is_driven_by_the_carried_driver(tmp_path):
    """§PW216: driving a game writes nothing into its tree."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = game(tmp_path)
    import shutil

    shutil.rmtree(root / "addons")
    session = driving.opened(str(root))["session"]
    try:
        driving.inputted(session, click="UI/Press", root=str(root))
        driving.stepped(session, root=str(root))
        seen = driving.queried(
            session, path=".", properties=["presses"], root=str(root)
        )
        driving.kept(
            session,
            out=".polyweave/flows/press.flow.json",
            proves="one press, with nothing installed",
            expect=[seen["step"]],
            root=str(root),
        )
    finally:
        driving.closed(session, root=str(root))
    assert not (root / "addons").exists()
    replayed = driving.replayed(".polyweave/flows/press.flow.json", root=str(root))
    assert replayed["ok"] is True, replayed["why"]


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
