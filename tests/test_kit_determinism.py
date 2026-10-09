"""The determinism kit the plugin carries, and a recorded run kept as a flow (§PW360).

The kit's proof plays a run twice and holds the two to agree, which only the running
game can do; it runs where $GODOT is set and is said skipped where not. A record
becomes a flow anywhere.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from polyweave import driving, godot, kits
from polyweave.errors import PolyweaveError


def test_the_determinism_kit_compares_runs_by_the_state_kit():
    found = kits.every()["determinism"]
    assert found["requires"] == ["state"]
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def test_the_determinism_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("determinism")["kits"]
    assert said["status"] == "skipped"


def test_a_record_becomes_a_flow_that_steps_to_each_event(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "run.json").write_text(json.dumps({"format": 1, "seed": 9, "events": [
        {"frame": 40, "action": "right", "pressed": False},
        {"frame": 10, "action": "right", "pressed": True},
    ]}), encoding="utf-8")
    said = driving.record_flow("run.json", out="flows/run.json", proves="it moves",
                               root=str(tmp_path))
    flow = json.loads((tmp_path / "flows" / "run.json").read_text(encoding="utf-8"))
    assert flow["seed"] == 9
    assert flow["steps"] == [
        {"cmd": "step", "frames": 10},
        {"cmd": "input", "action": "right", "hold": True},
        {"cmd": "step", "frames": 30},
        {"cmd": "input", "action": "right", "release": True},
        {"cmd": "step", "frames": 1},
    ]
    assert "expects nothing yet" in said["says"]


def test_a_file_that_is_no_record_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        driving.record_flow("run.json", out="f.json", proves="x", root=str(tmp_path))
    assert caught.value.code == "game.bad-target"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "determinism" / "fixture", game)
    return game, kits.install("determinism", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_two_runs_of_the_fixture_from_one_seed_agree(tmp_path):
    _, said = _installed(tmp_path)
    assert said["order"] == ["state", "determinism"]
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after"), [
    ("main.gd", 'Random.randf("spawns") < 0.2',
     "RandomNumberGenerator.new().randf() < 0.2"),
    ("addons/polyweave/determinism/random.gd", "\t_streams.clear()\n", "\tpass\n"),
])
def test_a_draw_outside_the_seed_parts_the_two_runs(tmp_path, where, before, after):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["determinism"], kits.every(), game)
    assert found["status"] == "failed"
    assert "the two runs part at physics frame" in found["said"]


def _spawned(root: str, seed: int) -> dict:
    session = driving.opened(root, seed=seed)["session"]
    try:
        driving.stepped(session, frames=41, root=root)
        found = driving.queried(session, path="/root/Main",
                                properties=["enemies", "last_spawn"], root=root)
        return found["result"][0]["properties"]
    finally:
        driving.closed(session, root=root)


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_recorded_run_replays_as_a_flow_and_the_drivers_seed_reaches_the_streams(
        tmp_path):
    game, _ = _installed(tmp_path)
    godot.install(game, addon="polyweave_driver")
    root = str(game)
    assert _spawned(root, 11) == _spawned(root, 11)
    assert _spawned(root, 11) != _spawned(root, 7)
    driving.record_flow("record.json", out="tests/flows/right.json",
                        proves="holding right from frame 10 to 40 moves the player 60",
                        expect=[{"path": "/root/Main", "property": "player_x",
                                 "equals": 60.0}], root=root)
    replayed = driving.replayed("tests/flows/right.json", root=root)
    assert replayed["ok"] is True, replayed
