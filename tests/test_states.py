"""The state machines a game wrote, held to reach every state and leave it (§PW368).

Read off the code as written, so nothing here runs an engine.
"""

from __future__ import annotations

import pytest

from polyweave import states
from polyweave.errors import PolyweaveError

SEEKER = """extends Node
enum State { HOVER, LOCK, DIVE }
var state := State.HOVER


func _physics_process(_d: float) -> void:
\tmatch state:
\t\tState.HOVER:
\t\t\tpass
\t\tState.LOCK:
\t\t\tif true:
\t\t\t\tstate = State.DIVE
\t\tState.DIVE:
\t\t\tstate = State.HOVER


func lock() -> void:
\tstate = State.LOCK
"""


def test_a_machine_is_read_with_its_start_and_every_move_from_its_arm():
    [machine] = states.machines(SEEKER)
    assert (machine["enum"], machine["var"], machine["first"]) == ("State", "state",
                                                                   "HOVER")
    assert machine["states"] == ["HOVER", "LOCK", "DIVE"]
    moves = [(m["from"], m["to"]) for m in machine["moves"]]
    assert moves == [(["LOCK"], "DIVE"), (["DIVE"], "HOVER"), (None, "LOCK")]
    assert states.held(machine, "res://seeker.gd") == []


def test_a_state_nothing_assigns_is_unreachable():
    text = SEEKER.replace("enum State { HOVER, LOCK, DIVE }",
                          "enum State { HOVER, LOCK, DIVE, STUNNED }")
    [machine] = states.machines(text)
    [found] = states.held(machine, "res://seeker.gd")
    assert (found["state"], found["code"], found["severity"]) == (
        "STUNNED", "engine.unreachable-state", "error")


def test_a_state_nothing_leaves_is_stuck_unless_marked_final():
    text = SEEKER.replace("\t\t\tstate = State.HOVER\n", "\t\t\tpass\n").replace(
        "func lock() -> void:\n\tstate = State.LOCK\n",
        "func lock() -> void:\n\tmatch state:\n\t\tState.HOVER:\n"
        "\t\t\tstate = State.LOCK\n")
    [machine] = states.machines(text)
    [found] = states.held(machine, "res://seeker.gd")
    assert (found["state"], found["code"]) == ("DIVE", "engine.stuck-state")
    marked = text.replace("enum State { HOVER, LOCK, DIVE }",
                          "enum State {\n\tHOVER,\n\tLOCK,\n\tDIVE, # final\n}")
    [machine] = states.machines(marked)
    assert machine["final"] == ["DIVE"]
    assert states.held(machine, "res://seeker.gd") == []


def test_a_variable_declared_without_a_value_starts_at_the_first_member():
    [machine] = states.machines(
        "enum Phase { INTRO, PLAY }\nvar phase: Phase\n\nfunc go():\n"
        "\tphase = Phase.PLAY\n")
    assert machine["first"] == "INTRO"
    assert states.held(machine, "res://flow.gd")[0]["state"] == "PLAY"


def test_the_project_is_read_outside_its_addons(tmp_path):
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "seeker.gd").write_text(SEEKER, encoding="utf-8")
    (tmp_path / "addons" / "kit").mkdir(parents=True)
    (tmp_path / "addons" / "kit" / "x.gd").write_text(
        "enum State { A, B }\nvar state := State.A\n", encoding="utf-8")
    found = states.states(root=str(tmp_path))
    assert found["clean"] is True
    assert [one["script"] for one in found["machines"]] == ["res://seeker.gd"]


def test_a_folder_with_no_project_godot_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        states.states(root=str(tmp_path))
    assert caught.value.code == "engine.no-project"
