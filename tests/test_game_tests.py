"""One way to run a game's tests, and the tests kit's base for writing them (§PW362).

Reading a run's output is checked everywhere; running the fixture's tests needs $GODOT.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from polyweave import kits, testing
from polyweave.errors import PolyweaveError

OWN = testing.DEFAULTS


def test_a_run_that_prints_its_summary_and_no_failure_passed():
    said = testing.read("checks ran: 4, failed: 0\n", "res://tests/a_test.gd", OWN)
    assert said["passed"] is True
    assert (said["checks"], said["failed"], said["failures"]) == (4, 0, [])


def test_a_failure_names_the_place_it_gives():
    output = ("  FAIL: two and three -- got 6, wanted 5 (res://tests/sums_test.gd:12)\n"
              "checks ran: 2, failed: 1\n")
    said = testing.read(output, "res://tests/sums_test.gd", OWN)
    assert said["passed"] is False
    [failure] = said["failures"]
    assert (failure["file"], failure["line"]) == ("res://tests/sums_test.gd", 12)
    assert failure["said"] == "two and three -- got 6, wanted 5"


def test_a_script_error_is_a_failure_at_the_line_the_engine_names():
    output = ("SCRIPT ERROR: Invalid call. Nonexistent function 'x' in base 'Nil'.\n"
              "   at: go (res://tests/boom_test.gd:7)\n"
              "checks ran: 3, failed: 0\n")
    said = testing.read(output, "res://tests/boom_test.gd", OWN)
    assert said["passed"] is False
    [failure] = said["failures"]
    assert (failure["file"], failure["line"]) == ("res://tests/boom_test.gd", 7)


def test_a_run_with_no_summary_never_passes():
    said = testing.read("", "res://tests/silent_test.gd", OWN)
    assert said["passed"] is False
    assert said["failures"][0]["said"] == "the script never printed its summary line"


def test_a_project_declares_a_convention_of_its_own():
    spinhold = {**OWN, "summary": r"^CHECK (?:OK|FAILED (?P<failed>\d+))$",
                "failure": r"^FAIL (?P<said>.+)$"}
    said = testing.read("FAIL scores: a run kept twice\nCHECK FAILED 1\n",
                        "res://dev/check.gd", spinhold)
    assert said["passed"] is False
    assert said["failures"][0]["said"] == "scores: a run kept twice"
    assert testing.read("CHECK OK\n", "res://dev/check.gd", spinhold)["passed"]


def test_kit_tests_in_the_config_is_the_convention_read(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[kit.tests]\nscripts = ["dev/check.gd"]\ntimeout = 60\n', encoding="utf-8")
    found = testing.declared(tmp_path)
    assert found["scripts"] == ["dev/check.gd"]
    assert found["timeout"] == 60
    assert found["summary"] == OWN["summary"]


def test_a_project_with_no_test_is_refused_by_name(tmp_path):
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        testing.test(root=str(tmp_path))
    assert caught.value.code == "engine.no-tests"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "tests" / "fixture", game)
    return game, kits.install("tests", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_tests_kit_holds_and_its_fixture_passes(tmp_path):
    game, said = _installed(tmp_path)
    assert said["proved"]["passed"] is True, said["proved"]
    ran = testing.test(root=str(game))
    assert (ran["passed"], ran["scripts"], ran["checks"]) == (True, 2, 3)


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_failure_a_parse_error_and_a_hang_are_each_named(tmp_path):
    game, _ = _installed(tmp_path)
    tests = game / "tests"
    (tests / "wrong_test.gd").write_text(
        'extends "res://addons/polyweave/tests/test.gd"\n\n\n'
        "func test_wrong() -> void:\n\tequal(1 + 1, 3, \"one and one\")\n",
        encoding="utf-8")
    (tests / "broken_test.gd").write_text(
        "extends SceneTree\n\nfunc _initialize(:\n\tquit()\n", encoding="utf-8")
    (tests / "stuck_test.gd").write_text(
        "extends SceneTree\n\nfunc _initialize() -> void:\n\twhile true:\n\t\tpass\n",
        encoding="utf-8")
    config = game / "polyweave.toml"
    text = config.read_text(encoding="utf-8")
    assert "timeout = 300" in text
    config.write_text(text.replace("timeout = 300", "timeout = 20"), encoding="utf-8")
    ran = testing.test(root=str(game))
    assert ran["passed"] is False
    by_file = {(f["file"], f["line"]): f["said"] for f in ran["failures"]}
    assert ("res://tests/wrong_test.gd", 5) in by_file
    assert any(file == "res://tests/broken_test.gd" and line == 3
               for file, line in by_file)
    assert any("so it hangs" in said for said in by_file.values())
    exit_code = subprocess.run(
        [sys.executable, "-m", "polyweave", "game.test", "--root", str(game)],
        capture_output=True, check=False, timeout=600).returncode
    assert exit_code == 1
