"""A game's engine runs declared, not scripted (§PW467)."""

from __future__ import annotations

import pytest

from polyweave import capture, engine, runs
from polyweave.cli import command_line
from polyweave.commands import run
from polyweave.errors import PolyweaveError

DECLARED = """
[capture]
declared   = ["locale"]
locale     = "pt_BR"

[run.align]
script   = "tools/perf/align.gd"
expect   = 'aligned: \\d+ cells'

[run.beside]
script   = "tools/perf/beside.gd"
expect   = 'captured: res://(?P<wrote>\\S+)'
produces = ["wrote"]
capture  = true
settings = { locale = "en" }
args     = ["--seed=7"]
timeout  = 30
"""


@pytest.fixture
def game(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(DECLARED, encoding="utf-8")
    calls = []

    def ran(script, **how):
        calls.append(("engine", script, how))
        return {"ok": script.endswith("align.gd"), "why": "never printed its line",
                "found": {}, "seconds": 1.0, "log": "align.log"}

    def captured(script, **how):
        calls.append(("capture", script, how))
        return {"ok": True, "found": {"wrote": "shot.png"}, "seconds": 2.0,
                "log": "beside.log",
                "reproduced": {"holds": False, "why": "same settings, other bytes"}}

    monkeypatch.setattr(engine, "run", ran)
    monkeypatch.setattr(capture, "run", captured)
    return tmp_path, calls


def test_every_declared_run_is_run_the_way_its_table_says(game):
    root, calls = game
    found = runs.run_declared(root=str(root))
    assert found["passed"] is True
    assert sorted(found["runs"]) == ["align", "beside"]
    kinds = {script: (kind, how) for kind, script, how in calls}
    _, how = kinds["tools/perf/beside.gd"]
    assert how["environment"] == {"locale": "en"}
    assert how["produces"] == ("wrote",) and how["timeout"] == 30.0
    assert how["args"] == ("--", "--seed=7")
    assert kinds["tools/perf/align.gd"][0] == "engine"
    assert found["runs"]["beside"]["found"] == {"wrote": "shot.png"}
    assert found["runs"]["beside"]["reproduced"]["holds"] is False


def test_a_run_that_did_not_print_its_line_fails_the_whole(game, monkeypatch):
    root, _ = game
    monkeypatch.setattr(engine, "run", lambda script, **how: {
        "ok": False, "why": "the script never printed the line", "found": {},
        "seconds": 1.0, "log": "align.log"})
    found = runs.run_declared(["align"], root=str(root))
    assert found["passed"] is False
    assert found["runs"]["align"]["why"] == "the script never printed the line"
    assert "align did not" in found["says"]


def test_a_run_nobody_declared_is_refused_with_the_ones_that_are(game):
    root, _ = game
    with pytest.raises(PolyweaveError) as refused:
        runs.run_declared(["aligned"], root=str(root))
    assert refused.value.code == "engine.unknown-run"
    assert "align, beside" in refused.value.remedy


def test_a_run_missing_its_line_or_with_a_stray_key_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[run.x]\nscript = "a.gd"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        runs.declared(tmp_path)
    assert refused.value.code == "engine.bad-run"
    (tmp_path / "polyweave.toml").write_text(
        '[run.x]\nscript = "a.gd"\nexpect = "ok"\nwait = 3\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        runs.declared(tmp_path)
    assert "wait" in refused.value.message


def test_the_command_exits_non_zero_on_a_failed_run(game, monkeypatch, capsys):
    root, _ = game
    monkeypatch.setattr(engine, "run", lambda script, **how: {
        "ok": False, "why": "no line", "found": {}, "seconds": 1.0, "log": "x"})
    stated = command_line().parse_args(
        ["engine.run_declared", "--runs", '["align"]', "--root", str(root)])
    assert run(stated) == 1
