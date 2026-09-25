"""Reading a verdict off a scene script, rather than off an exit code.

§PW22's case: Godot exits zero after a script error and non-zero after a clean quit.
The honest signal is the line the script printed, the absence of an error in the output,
and the file it claims to have written — and these hold the runner to all three.

Nothing here needs Godot. A run's four answers are read out of its output, so the output
is what the tests supply.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from polyweave import engine
from polyweave.errors import PolyweaveError

CAPTURED = r"captured: (?P<artefact>\S+) (?P<width>\d+) x (?P<height>\d+)"
SUMMARY = r"checks ran: (?P<ran>\d+), failed: (?P<failed>\d+)"


def project(tmp_path, *, script="capture.gd", godot=True):
    """A project with a scene script in it, and an engine to point at."""
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / script).write_text("extends SceneTree\n", encoding="utf-8")
    if godot:
        binary = tmp_path / "godot.exe"
        binary.write_text("not really\n", encoding="utf-8")
        (tmp_path / "polyweave.toml").write_text(
            '[paths]\ngodot = "godot.exe"\n', encoding="utf-8"
        )
    return tmp_path / "tools" / script


def says(output, *, code=0):
    """An engine that prints this and exits with that, whatever the two have to do."""

    def launch(command, *, cwd, timeout):
        return output, code

    return launch


def hangs():
    def launch(command, *, cwd, timeout):
        raise subprocess.TimeoutExpired(command, timeout, output="half a line\n")

    return launch


# -- the exit code is not the verdict ----------------------------------------------


def test_a_clean_run_is_the_printed_line_and_not_the_exit_code(tmp_path):
    """Non-zero after a clean quit is one of the three ways the code lies."""
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        launch=says("checks ran: 12, failed: 0\n", code=1),
    )
    assert found["ok"] is True
    assert found["verdict"] == "ok"
    assert found["exit_code"] == 1
    assert found["found"] == {"ran": "12", "failed": "0"}


def test_a_script_error_is_a_failure_however_it_exited(tmp_path):
    """And zero after a script error is the other way round."""
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        launch=says(
            "SCRIPT ERROR: Invalid call. (res://tools/capture.gd:14)\n"
            "checks ran: 12, failed: 0\n",
            code=0,
        ),
    )
    assert found["ok"] is False
    assert found["verdict"] == "script-error"
    assert found["exit_code"] == 0


def test_a_run_that_printed_nothing_is_not_a_success(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script, expect=SUMMARY, root=tmp_path, launch=says("loading...\n", code=0)
    )
    assert found["verdict"] == "no-signal"
    assert "never printed" in found["why"]


# -- every spelling of a broken script ----------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "SCRIPT ERROR: Invalid call",
        "Parse Error: Unexpected identifier",
        "Compile Error: could not resolve",
        "String formatting error: not enough arguments",
    ],
)
def test_each_spelling_the_engine_has_for_a_broken_script(tmp_path, line):
    """The formatting one prints without the word SCRIPT and still aborts its block."""
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        launch=says(f"{line}\nchecks ran: 1, failed: 0\n"),
    )
    assert found["verdict"] == "script-error"


def test_an_error_names_the_line_of_the_script_it_came_from(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        launch=says("SCRIPT ERROR: Invalid call. (res://tools/capture.gd:14)\n"),
    )
    assert found["errors"][0]["at"] == "res://tools/capture.gd:14"
    assert found["errors"][0]["output_line"] == 1


def test_every_error_is_reported_and_not_only_the_first(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        launch=says("Parse Error: one\nParse Error: two\nParse Error: three\n"),
    )
    assert len(found["errors"]) == 3


def test_what_counts_as_an_error_is_the_caller_s_to_widen(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        errors=r"ASSERT FAILED",
        launch=says("ASSERT FAILED: the board was empty\n"),
    )
    assert found["verdict"] == "script-error"


# -- the file it says it wrote ---------------------------------------------------------


def test_a_file_it_claims_to_have_written_has_to_be_there(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=CAPTURED,
        root=tmp_path,
        produces=("artefact",),
        launch=says("captured: res://docs/shot.png 1920 x 1080\n"),
    )
    assert found["verdict"] == "missing-artefact"
    assert found["missing"] == [str(tmp_path / "docs" / "shot.png")]


def test_and_is_reported_as_an_artefact_when_it_is(tmp_path):
    script = project(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "shot.png").write_bytes(b"\x89PNG")
    found = engine.run(
        script,
        expect=CAPTURED,
        root=tmp_path,
        produces=("artefact",),
        launch=says("captured: res://docs/shot.png 1920 x 1080\n"),
    )
    assert found["ok"] is True
    assert found["artefacts"] == [str(tmp_path / "docs" / "shot.png")]
    assert found["found"]["width"] == "1920"


def test_a_run_that_promises_no_file_is_not_asked_for_one(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script, expect=SUMMARY, root=tmp_path, launch=says("checks ran: 3, failed: 0\n")
    )
    assert found["artefacts"] == []
    assert found["ok"] is True


# -- the bounds are part of the contract -----------------------------------------------


def test_both_bounds_are_on_the_command(tmp_path):
    """The frame budget ends a loop the engine sits in; the clock ends a hang."""
    script = project(tmp_path)
    seen = {}

    def launch(command, *, cwd, timeout):
        seen["command"], seen["timeout"] = command, timeout
        return "checks ran: 1, failed: 0\n", 0

    engine.run(script, expect=SUMMARY, root=tmp_path, launch=launch)
    assert "--quit-after" in seen["command"]
    assert seen["command"][seen["command"].index("--quit-after") + 1] == "6000"
    assert seen["timeout"] == 180.0


def test_the_bounds_are_the_project_s_to_set(tmp_path):
    script = project(tmp_path)
    (tmp_path / "polyweave.toml").write_text(
        '[paths]\ngodot = "godot.exe"\n\n[engine]\nframes = 120\ntimeout = 9\n',
        encoding="utf-8",
    )
    seen = {}

    def launch(command, *, cwd, timeout):
        seen["command"], seen["timeout"] = command, timeout
        return "checks ran: 1, failed: 0\n", 0

    engine.run(script, expect=SUMMARY, root=tmp_path, launch=launch)
    assert seen["command"][seen["command"].index("--quit-after") + 1] == "120"
    assert seen["timeout"] == 9.0


def test_a_hang_is_said_rather_than_waited_out(tmp_path):
    script = project(tmp_path)
    found = engine.run(script, expect=SUMMARY, root=tmp_path, launch=hangs())
    assert found["verdict"] == "timed-out"
    assert found["bounded"] is True
    assert found["exit_code"] is None


def test_frames_are_reported_only_where_the_script_said_them(tmp_path):
    script = project(tmp_path)
    quiet = engine.run(
        script, expect=SUMMARY, root=tmp_path, launch=says("checks ran: 1, failed: 0\n")
    )
    assert quiet["frames"] is None, "inferring it from the exit would be a guess"
    loud = engine.run(
        script,
        expect=SUMMARY,
        root=tmp_path,
        launch=says("frames: 41\nchecks ran: 1, failed: 0\n"),
    )
    assert loud["frames"] == 41
    assert loud["bounded"] is False


def test_a_script_that_ran_to_its_budget_is_bounded_out(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script, expect=SUMMARY, root=tmp_path, launch=says("frames: 6000\n")
    )
    assert found["bounded"] is True
    assert found["verdict"] == "no-signal"


# -- what the run leaves behind --------------------------------------------------------


def test_everything_the_run_printed_is_written_where_it_can_be_opened(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script, expect=SUMMARY, root=tmp_path, launch=says("Parse Error: nope\n")
    )
    assert Path(found["log"]).read_text(encoding="utf-8") == "Parse Error: nope\n"


def test_the_command_that_was_run_comes_back_with_the_result(tmp_path):
    script = project(tmp_path)
    found = engine.run(
        script, expect=SUMMARY, root=tmp_path, launch=says("checks ran: 1, failed: 0\n")
    )
    assert found["command"][0].endswith("godot.exe")
    assert "res://tools/capture.gd" in found["command"]


def test_headless_is_asked_for_rather_than_assumed(tmp_path):
    """A capture needs a real renderer, so this is never the default."""
    script = project(tmp_path)
    seen = {}

    def launch(command, *, cwd, timeout):
        seen["command"] = command
        return "checks ran: 1, failed: 0\n", 0

    engine.run(script, expect=SUMMARY, root=tmp_path, launch=launch)
    assert "--headless" not in seen["command"]
    engine.run(script, expect=SUMMARY, root=tmp_path, headless=True, launch=launch)
    assert "--headless" in seen["command"]


# -- as a gate -------------------------------------------------------------------------


def test_a_gate_stops_on_anything_but_a_clean_verdict(tmp_path):
    script = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        engine.require(
            script,
            expect=SUMMARY,
            root=tmp_path,
            launch=says("SCRIPT ERROR: Invalid call. (res://tools/capture.gd:14)\n"),
        )
    assert caught.value.code == "engine.script-error"


def test_the_refusal_carries_the_log_rather_than_a_summary(tmp_path):
    script = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        engine.require(script, expect=SUMMARY, root=tmp_path, launch=says("nothing\n"))
    assert caught.value.code == "engine.no-signal"
    assert Path(caught.value.remedy.split("read ")[1].split(",")[0]).is_file()


def test_every_verdict_has_a_code_to_close_with():
    """A gate that met a verdict it had no code for would invent one."""
    assert set(engine.REFUSALS) == {
        "timed-out",
        "script-error",
        "no-signal",
        "missing-artefact",
    }


def test_a_clean_run_passes_the_gate_through(tmp_path):
    script = project(tmp_path)
    found = engine.require(
        script, expect=SUMMARY, root=tmp_path, launch=says("checks ran: 9, failed: 0\n")
    )
    assert found["ok"] is True


# -- finding the engine, and what is missing -------------------------------------------


def test_a_script_that_is_not_there_is_refused_before_anything_runs(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        engine.run("tools/nothing.gd", expect=SUMMARY, root=tmp_path, launch=says(""))
    assert caught.value.code == "engine.no-script"


def test_a_binary_the_project_names_and_does_not_have_is_refused(tmp_path):
    project(tmp_path)
    (tmp_path / "godot.exe").unlink()
    with pytest.raises(PolyweaveError) as caught:
        engine.find(tmp_path)
    assert caught.value.code == "engine.not-found"


def test_the_project_s_own_binary_wins_over_the_path(tmp_path):
    project(tmp_path)
    assert engine.find(tmp_path) == str(tmp_path / "godot.exe")


def test_with_nothing_named_anywhere_it_says_so(tmp_path, monkeypatch):
    project(tmp_path, godot=False)
    monkeypatch.delenv("GODOT", raising=False)
    monkeypatch.setattr(engine.shutil, "which", lambda _name: None)
    with pytest.raises(PolyweaveError) as caught:
        engine.find(tmp_path)
    assert caught.value.code == "engine.not-found"
    assert "PATH" in caught.value.remedy


def test_an_anchored_expected_line_is_found_below_the_first_line(tmp_path):
    """§PW210: `^` in the line a script prints is that line's start, not the log's."""
    script = project(tmp_path)
    found = engine.run(
        script,
        expect=r"^checks ran: (?P<ran>\d+), failed: (?P<failed>\d+)$",
        root=tmp_path,
        launch=says(
            "Godot Engine v4.7\nenvironment: locale=en\nchecks ran: 3, failed: 0\n"
        ),
    )
    assert found["ok"] is True
    assert found["found"] == {"ran": "3", "failed": "0"}
