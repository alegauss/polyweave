"""Every kit proved in its own fixture, before any project receives it (§PW342).

The kits are built here, as test_kit_install builds them: each with a fixture, a
project.godot, that it is installed into fresh and proved in.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from polyweave import kits
from test_kit_install import kit


@pytest.fixture
def shelf(tmp_path, monkeypatch):
    folder = tmp_path / "kits"
    folder.mkdir()
    monkeypatch.setattr(kits, "KITS", folder)
    return folder


def test_each_kit_is_installed_into_its_own_fixture_and_proved(shelf):
    kit(shelf, "input")
    kit(shelf, "settings", requires=["input"])
    said = kits.prove()
    assert [(one["kit"], one["status"]) for one in said["kits"]] == [
        ("input", "held"), ("settings", "held")]
    assert said["passed"] is True and said["held"] == 2
    # The fixture is copied, never written into.
    assert sorted(p.name for p in (shelf / "input" / "fixture").iterdir()) == [
        "project.godot"]


def test_a_kit_whose_proof_fails_fails_the_proof_by_name(shelf):
    kit(shelf, "input", low=0.99)
    said = kits.prove()
    assert said["failed"] == 1 and said["passed"] is False
    assert said["kits"][0]["status"] == "failed"


def test_a_proof_that_needs_a_running_game_is_skipped_without_an_engine(
    shelf, monkeypatch
):
    kit(shelf, "input")
    proof = shelf / "input" / "proof.accept.toml"
    on_screen = 'screen = { capture = "captures/menu.png", region = "frame" }\n\n'
    proof.write_text(proof.read_text("utf-8").replace(
        "[[predicate]]", on_screen + "[[predicate]]", 1), encoding="utf-8")
    monkeypatch.delenv("GODOT", raising=False)
    said = kits.prove("input")
    assert said["kits"][0]["status"] == "skipped"
    assert said["passed"] is True


def gate_module():
    where = Path(__file__).resolve().parent.parent / "tools" / "gate.py"
    spec = importlib.util.spec_from_file_location("gate_for_kits", where)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_gate_says_how_the_kits_went():
    gate = gate_module()
    stamp = {"exit": 1, "commit": "abc", "passed": 1, "failed": 0, "skipped": 0,
             "present": {e: True for e in gate.ENGINES},
             "skipped_for": {e: 0 for e in gate.ENGINES}, "log": "x.log",
             "kits": {"held": 2, "failed": 1, "skipped": 0, "red": ["save"]}}
    said = gate.summary(stamp)
    assert "kits: 2 held, 1 failed, 0 skipped for want of an engine (save)" in said
