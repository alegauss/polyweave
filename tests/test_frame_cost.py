"""What a change costs a frame, one timing script on two builds (§PW258).

Starship's RK131 had to be measured by stashing, re-importing and timing both sides by
hand. The builds here are commits of a small git repository, and the engine is stood in
for by a run that prints a frame time per build, so the comparison itself is what is
tested; the last test times a real one where there is an engine.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from polyweave import frame_cost
from polyweave.errors import PolyweaveError

PERF = "extends SceneTree\n# the timing script, whose body is stood in for\n"


def git(where: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=where, capture_output=True, text=True,
                          check=True).stdout.strip()


def repo(tmp_path: Path) -> Path:
    """A project with two commits: the old build, then the one that costs more."""
    here = tmp_path / "game"
    (here / "dev").mkdir(parents=True)
    fake = tmp_path / "godot.exe"
    fake.write_text("", encoding="utf-8")
    (here / "polyweave.toml").write_text(
        f'[paths]\ngodot = "{fake.as_posix()}"\n', encoding="utf-8")
    (here / ".gitignore").write_text(".polyweave/\n", encoding="utf-8")
    (here / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (here / "dev" / "perf.gd").write_text(PERF, encoding="utf-8")
    (here / "sky.txt").write_text("cost=2.0\n", encoding="utf-8")
    git(here, "init", "-q")
    git(here, "config", "user.email", "t@example.com")
    git(here, "config", "user.name", "t")
    git(here, "add", ".")
    git(here, "commit", "-qm", "old")
    (here / "sky.txt").write_text("cost=3.0\n", encoding="utf-8")
    git(here, "commit", "-qam", "a sky that costs a millisecond")
    return here


@pytest.fixture
def timed(monkeypatch):
    """Every run prints `PERF avg=<its build's cost + jitter>ms frames=540`, the cost
    read off the build's own sky.txt, and the order the sides ran in is kept."""
    order = []
    jitter = iter([0.0, 0.05, -0.05, 0.02, -0.02, 0.01, -0.01, 0.03, -0.03, 0.0] * 4)

    def once(side, headless, how):
        base = float((side["root"] / "sky.txt").read_text().split("=")[1])
        order.append(side["label"])
        log = side["root"] / ".polyweave" / "perf.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("Vulkan 1.4 - Forward+ - Using Device #0: Test - GPU 1\n"
                       f"PERF preset=high avg={base + next(jitter):.2f}ms frames=540\n",
                       encoding="utf-8")
        return {"ok": True, "log": str(log), "verdict": "ok"}

    monkeypatch.setattr(frame_cost, "_once", once)
    monkeypatch.setattr(frame_cost, "_imported", lambda side, binary, timeout: None)
    return order


def test_a_change_s_cost_is_one_call_and_says_how_sure(tmp_path, timed):
    here = repo(tmp_path)
    said = frame_cost.cost("dev/perf.gd", expect=r"^PERF .*", against="HEAD~1",
                           runs=4, root=str(here))
    assert said["ok"] is True, said.get("why")
    avg = said["measures"]["avg"]
    assert avg["difference"] == pytest.approx(1.0, abs=0.05)
    assert avg["interval"][0] > 0 and avg["sure"] is True
    assert said["sure"] == ["avg"]
    # A count that did not move is not a cost, and is not sure of one.
    assert said["measures"]["frames"]["difference"] == 0
    assert said["machine"]["device"] == ["Test - GPU 1"]
    assert said["on"]["label"] == "working tree"


def test_the_sides_alternate_so_drift_lands_on_both(tmp_path, timed):
    here = repo(tmp_path)
    frame_cost.cost("dev/perf.gd", expect=r"^PERF .*", against="HEAD~1", runs=3,
                    root=str(here))
    assert timed == ["working tree", "HEAD~1", "HEAD~1", "working tree",
                     "working tree", "HEAD~1"]


def test_a_revision_is_its_own_worktree_and_the_tree_is_never_stashed(tmp_path, timed):
    here = repo(tmp_path)
    (here / "sky.txt").write_text("cost=5.0\n", encoding="utf-8")  # uncommitted work
    said = frame_cost.cost("dev/perf.gd", expect=r"^PERF .*", against="HEAD",
                           runs=2, root=str(here))
    assert (here / "sky.txt").read_text() == "cost=5.0\n"
    assert said["measures"]["avg"]["difference"] == pytest.approx(2.0, abs=0.1)
    assert "trees" in git(here, "worktree", "list")


def test_the_last_answer_is_named_stale_once_a_build_moves(tmp_path, timed):
    here = repo(tmp_path)
    ask = {"expect": r"^PERF .*", "against": "HEAD~1", "runs": 2, "root": str(here)}
    assert frame_cost.cost("dev/perf.gd", **ask)["previous"] is None
    assert frame_cost.cost("dev/perf.gd", **ask)["previous"]["stale"] is False
    (here / "sky.txt").write_text("cost=4.0\n", encoding="utf-8")
    again = frame_cost.cost("dev/perf.gd", **ask)
    assert again["previous"]["stale"] is True
    kept = json.loads(Path(again["record"]).read_text(encoding="utf-8"))
    assert kept["measures"]["avg"]["on"]["mean"] > 3.5


def test_a_revision_without_the_script_borrows_the_working_tree_s(tmp_path, timed):
    here = repo(tmp_path)
    (here / "dev" / "new.gd").write_text(PERF, encoding="utf-8")
    said = frame_cost.cost("dev/new.gd", expect=r"^PERF .*", against="HEAD",
                           runs=2, root=str(here))
    assert said["against"]["script"] == "the working tree's"
    assert "script" not in said["on"]


def test_two_runs_that_never_printed_their_line_are_nothing_to_compare(tmp_path,
                                                                        monkeypatch):
    here = repo(tmp_path)
    log = tmp_path / "silent.log"
    log.write_text("nothing\n", encoding="utf-8")
    monkeypatch.setattr(frame_cost, "_once", lambda side, headless, how: {
        "ok": False, "log": str(log), "verdict": "no-signal", "why": "silent"})
    monkeypatch.setattr(frame_cost, "_imported", lambda side, binary, timeout: None)
    said = frame_cost.cost("dev/perf.gd", expect=r"^PERF .*", against="HEAD~1",
                           runs=2, root=str(here))
    assert said["ok"] is False
    assert len(said["failed"]) == 4
    assert "fewer than two runs" in said["why"]


@pytest.mark.parametrize(
    ("ask", "code"),
    [({"against": "HEAD", "on": "HEAD"}, "engine.cost-same"),
     ({"against": "no-such-branch"}, "engine.cost-no-revision")],
)
def test_a_comparison_that_cannot_be_made_is_refused(tmp_path, timed, ask, code):
    here = repo(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        frame_cost.cost("dev/perf.gd", expect=r"^PERF .*", root=str(here), **ask)
    assert refused.value.code == code


def test_a_timing_run_is_left_on_the_wall_clock(tmp_path):
    from polyweave import engine

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "t.gd").write_text(PERF, encoding="utf-8")
    seen = {}

    def launch(command, *, cwd, timeout, **extra):
        seen["command"] = command
        return "PERF avg=1ms\n", 0

    engine.run("t.gd", expect=r"^PERF", root=tmp_path, fixed_fps=0, binary="godot",
               launch=launch)
    assert "--fixed-fps" not in seen["command"]


TIMES = """extends SceneTree

func _process(_delta: float) -> bool:
\tif Engine.get_process_frames() < 3:
\t\treturn false
\tprint("PERF avg=%.2fms" % float(FileAccess.get_file_as_string("res://sky.txt").split("=")[1]))
\treturn true
"""


def test_a_real_engine_times_both_builds(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    here = repo(tmp_path)
    godot = Path(os.environ["GODOT"]).as_posix()
    (here / "polyweave.toml").write_text(f'[paths]\ngodot = "{godot}"\n', "utf-8")
    (here / "dev" / "perf.gd").write_text(TIMES, encoding="utf-8")
    git(here, "commit", "-qam", "a script that reads its build")
    (here / "sky.txt").write_text("cost=6.0\n", encoding="utf-8")
    said = frame_cost.cost("dev/perf.gd", expect=r"^PERF .*", against="HEAD",
                           runs=2, headless=True, root=str(here))
    assert said["ok"] is True, said
    assert said["measures"]["avg"]["difference"] == pytest.approx(3.0)
