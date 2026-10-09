"""The launch kit the plugin carries, proved in its own fixture (§PW349).

Its proof times the run from launch to the first scene and the frames of a change to a
large scene, so it runs on the wall clock where $GODOT is set.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_launch_kit_lands_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "launch" / "fixture", game)
    said = kits.install("launch", root=str(game))
    assert said["order"] == ["launch"]
    assert said["scenes"] == ["kits/launch/splash.tscn"]
    assert said["proved"]["passed"] is True, said["proved"]


def test_a_proof_script_runs_on_the_wall_clock(tmp_path, monkeypatch):
    from polyweave import engine

    seen = {}

    def run(script, **given):
        seen.update(given)
        return {"ok": True}

    monkeypatch.setenv("GODOT", "godot")
    monkeypatch.setattr(engine, "run", run)
    kits._scripts(["launch"], kits.every(), tmp_path)
    assert seen["fixed_fps"] == 0
    assert seen["frames"] >= 1_000_000


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("addons/polyweave/launch/splash.gd", " or event is InputEventJoypadButton:", ":",
     "InputEventJoypadButton press did not skip the splash"),
    ("polyweave_launch.gd", "LAUNCH_MS := 3000", "LAUNCH_MS := 1",
     "over the budget of 1 ms"),
    ("polyweave_launch.gd", "FRAME_MS := 100.0", "FRAME_MS := 0.0001",
     "at the 95th percentile, over 0.0"),
])
def test_a_broken_launch_fails_the_proof_by_name(tmp_path, where, before, after, said):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "launch" / "fixture", game)
    kits.install("launch", root=str(game))
    target = game / where
    text = target.read_text(encoding="utf-8")
    assert before in text
    target.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["launch"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
