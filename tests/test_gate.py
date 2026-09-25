"""One gate that keeps its log and stamps what ran (§PW134)."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "tools" / "gate.py"


@pytest.fixture
def gate(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HERE", tmp_path / "gate")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


REPORT = """<testsuites><testsuite>
<testcase name="a"/>
<testcase name="b"><failure message="boom"/></testcase>
<testcase name="c"><skipped message="Blender is not importable here"/></testcase>
<testcase name="d"><skipped message="could not import 'bpy'"/></testcase>
<testcase name="e"><skipped message="no $GODOT on this machine"/></testcase>
<testcase name="f"><skipped message="not on this platform"/></testcase>
</testsuite></testsuites>"""


def test_the_counts_say_which_engine_each_skip_was_for(gate, tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(REPORT, encoding="utf-8")
    found = gate.counts(report)
    assert (found["passed"], found["failed"], found["skipped"]) == (1, 1, 4)
    assert found["skipped_for"] == {"Blender": 2, "Godot": 1}


def test_the_summary_says_an_absent_engine_plainly(gate):
    stamp = {
        "exit": 0,
        "commit": "abc",
        "passed": 10,
        "failed": 0,
        "skipped": 41,
        "present": {"Blender": False, "Godot": True},
        "skipped_for": {"Blender": 41, "Godot": 0},
        "log": "x.log",
    }
    said = gate.summary(stamp)
    assert "Blender: absent, 41 tests skipped for it" in said
    assert said.startswith("gate green")


def test_a_live_lock_refuses_and_a_dead_one_is_taken_over(gate):
    gate.HERE.mkdir(parents=True)
    (gate.HERE / "lock").write_text(str(os.getpid()), encoding="utf-8")
    with pytest.raises(gate.Held):
        gate.lock()
    (gate.HERE / "lock").write_text("999999", encoding="utf-8")
    assert gate.lock().read_text(encoding="utf-8") == str(os.getpid())


def test_a_log_at_the_root_and_the_gates_own_files_are_never_staged():
    """§PW135: the commit tool stages the whole tree, so a redirected run must not."""
    import subprocess

    root = SCRIPT.parents[1]
    for path in ("pytest.log", ".polyweave/gate/stamp.json"):
        done = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", path],
            cwd=root,
            check=False,
        )
        assert done.returncode == 0, f"{path} is not ignored"


def test_a_red_run_keeps_its_log_aside_and_its_exit_code(gate, tmp_path):
    (tmp_path / "test_red.py").write_text(
        "def test_red():\n    assert False\n", encoding="utf-8"
    )
    code = gate.main(["-q", "-p", "no:cacheprovider", str(tmp_path / "test_red.py")])
    assert code == 1
    stamp = json.loads((gate.HERE / "stamp.json").read_text(encoding="utf-8"))
    assert stamp["exit"] == 1
    assert stamp["failed"] == 1
    assert (tmp_path / stamp["red_log"]).is_file()
    assert not (gate.HERE / "lock").exists()
