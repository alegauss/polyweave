"""A run past the project's frame budget, sized by the caller (§PW251). Needs $GODOT."""

from __future__ import annotations

import os

import pytest

from polyweave import engine

LATE = """extends SceneTree

func _process(_delta: float) -> bool:
\tif Engine.get_process_frames() == 6713:
\t\tprint("mason: broken at 6713")
\t\treturn true
\treturn false
"""


@pytest.fixture
def late(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "late.gd").write_text(LATE, encoding="utf-8")
    return tmp_path


def test_a_late_moment_is_reached_with_the_budget_passed(late):
    found = engine.run(
        "late.gd", expect=r"mason: broken", root=late, headless=True, frames=8000
    )
    assert found["ok"] is True, found["why"]


def test_the_project_budget_cuts_it_and_the_answer_names_the_budget(late):
    found = engine.run("late.gd", expect=r"mason: broken", root=late, headless=True)
    assert found["ok"] is False
    assert "frame budget of 6000" in found["why"]
