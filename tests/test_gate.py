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
    monkeypatch.setattr(module, "GUI", tmp_path / "gui")
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
    assert found["skipped_for"] == {"Blender": 2, "Godot": 1, "Audio": 0}


def test_the_tests_skipped_for_godot_are_named_to_run_again_alone(gate, tmp_path):
    """The VMware guest crashed with two Godot windows drawing at once, so its gate
    runs them one at a time after the rest (tools/gate-guest.cmd)."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_vfx.py").write_text("", encoding="utf-8")
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="tests.test_vfx" name="test_a[x]">'
        '<skipped message="no $GODOT on this machine"/></testcase>'
        '<testcase classname="tests.test_vfx.TestFilm" name="test_b">'
        '<skipped message="no $GODOT on this machine"/></testcase>'
        '<testcase classname="tests.test_vfx" name="test_c">'
        '<skipped message="could not import bpy"/></testcase>'
        '<testcase classname="tests.test_vfx" name="test_d"/>'
        '</testsuite></testsuites>', encoding="utf-8")
    assert gate.skipped_for_godot(report) == [
        "tests/test_vfx.py::test_a[x]", "tests/test_vfx.py::TestFilm::test_b"]


#: What xdist printed on 2026-10-17, the one crash in the kept red logs (§PW524).
CRASH = (
    "[gw5] node down: Not properly terminated\n"
    "worker 'gw5' crashed while running "
    "'tests/test_render.py::test_a_blend_bakes_like_any_other_mesh'\n"
    "worker 'gw12' crashed while running "
    "'tests/test_render.py::test_a_render_that_is_black_to_any_observer_is_refused'\n"
)


def test_a_crashed_worker_is_named_with_the_crash_log_it_left(gate, tmp_path,
                                                              monkeypatch):
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(gate.tempfile, "gettempdir", lambda: str(temp))
    stale = temp / "old.crash.txt"
    stale.write_text("before the run", encoding="utf-8")
    os.utime(stale, (1, 1))
    (temp / "blender.crash.txt").write_text("# Blender 4.5, Crash report",
                                            encoding="utf-8")
    log = tmp_path / "pytest.log"
    log.write_text(CRASH, encoding="utf-8")
    keep = tmp_path / "gate"
    keep.mkdir()
    found = gate.crashed(log, since=100.0, keep=keep)
    assert found["tests"] == [
        "tests/test_render.py::test_a_blend_bakes_like_any_other_mesh",
        "tests/test_render.py::test_a_render_that_is_black_to_any_observer_is_refused",
    ]
    [kept] = found["logs"]
    assert kept.endswith("blender.crash.txt")
    assert (tmp_path / kept).read_text(encoding="utf-8").startswith("# Blender")
    said = gate._crashed_said(found)
    assert "2 worker(s) crashed" in said and "crash log kept at" in said


def test_a_run_with_no_crash_names_none_and_copies_nothing(gate, tmp_path, monkeypatch):
    monkeypatch.setattr(gate.tempfile, "gettempdir", lambda: str(tmp_path))
    (tmp_path / "blender.crash.txt").write_text("from another day", encoding="utf-8")
    log = tmp_path / "pytest.log"
    log.write_text("3 passed in 1.0s\n", encoding="utf-8")
    assert gate.crashed(log, since=0.0, keep=tmp_path) == {"tests": [], "logs": []}
    assert gate._crashed_said({"tests": [], "logs": []}) == ""


def test_the_summary_says_an_absent_engine_plainly(gate):
    stamp = {
        "exit": 0,
        "commit": "abc",
        "passed": 10,
        "failed": 0,
        "skipped": 41,
        "present": {"Blender": False, "Godot": True, "Audio": True},
        "skipped_for": {"Blender": 41, "Godot": 0, "Audio": 0},
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
    code = gate.main(["-q", "-n", "0", "-p", "no:cacheprovider",
                      str(tmp_path / "test_red.py")])
    assert code == 1
    stamp = json.loads((gate.HERE / "stamp.json").read_text(encoding="utf-8"))
    assert stamp["exit"] == 1
    assert stamp["failed"] == 1
    assert (tmp_path / stamp["red_log"]).is_file()
    assert not (gate.HERE / "lock").exists()


def test_pytest_runs_on_every_core_and_the_timed_tests_alone(gate, monkeypatch):
    """Half an hour on one core was most of every task's wait, and a frame budget read
    beside 28 workers measured the load."""
    monkeypatch.setattr(gate.importlib.util, "find_spec",
                        lambda name: object() if name == "xdist" else None)
    assert gate.runs(["-q"]) == [["-n", "auto", "-m", "not serial", "-q"],
                                 ["-m", "serial", "-q"]]
    assert gate.runs(["-n", "4"]) == [["-n", "4"]]
    assert gate.runs(["-m", "serial"]) == [["-m", "serial"]]
    assert gate.runs(["-p", "no:xdist"]) == [["-p", "no:xdist"]]
    monkeypatch.setattr(gate.importlib.util, "find_spec", lambda name: None)
    assert gate.runs(["-q"]) == [["-q"]]


def test_two_runs_are_counted_as_one(gate):
    one = {"passed": 3, "failed": 1, "skipped": 2,
           "skipped_for": {engine: 1 for engine in gate.ENGINES}}
    total = gate.summed([one, one])
    assert (total["passed"], total["failed"], total["skipped"]) == (6, 2, 4)
    assert set(total["skipped_for"].values()) == {2}


def test_the_window_is_said_skipped_with_the_reason_where_it_cannot_run(gate, tmp_path):
    # §PW303: one gate covers both halves, and a half it could not run is said.
    assert gate.window(tmp_path / "gui.log") == {"ran": False, "why": "no gui/ here"}
    (tmp_path / "gui").mkdir()
    (tmp_path / "gui" / "package.json").write_text("{}", encoding="utf-8")
    if gate.shutil.which("npm"):
        found = gate.window(tmp_path / "gui.log")
        assert found["why"] == "not installed: run npm ci in gui/"


def test_the_summary_says_how_the_window_went(gate):
    stamp = {
        "exit": 1,
        "commit": "abc",
        "passed": 10,
        "failed": 0,
        "skipped": 0,
        "present": {"Blender": True, "Godot": True, "Audio": True},
        "skipped_for": {"Blender": 0, "Godot": 0, "Audio": 0},
        "log": "x.log",
        "gui": {"ran": True, "exit": 1, "failed": "test"},
    }
    assert "gui: test RED" in gate.summary(stamp)
