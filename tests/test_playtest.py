"""What players met in a level, read off the events their runs wrote (§PW327)."""

from __future__ import annotations

import json

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import playtest


def _run(root, name, events):
    (root / "runs").mkdir(exist_ok=True)
    (root / "runs" / name).write_text(
        "".join(json.dumps(one) + "\n" for one in events), encoding="utf-8")
    return f"runs/{name}"


ONE = [
    {"t": 0.5, "event": "spawn", "id": "a", "weight": 1.0},
    {"t": 0.9, "event": "spawn", "id": "b", "weight": 3.0},
    {"t": 1.2, "event": "hit"},
    {"t": 2.5, "event": "kill", "id": "a"},
    {"t": 3.1, "event": "life_lost"},
]
TWO = [
    {"t": 0.2, "event": "spawn", "id": "a"},
    {"t": 1.5, "event": "kill", "id": "a"},
]


def test_a_run_s_events_are_read_per_second_and_in_all(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    said = playtest.trace([_run(tmp_path, "one.jsonl", ONE)], root=str(tmp_path))
    assert said["seconds"] == 4
    assert said["events"]["spawn"] == [4.0, 0.0, 0.0, 0.0]
    assert said["totals"] == {"hit": 1.0, "kill": 1.0, "life_lost": 1.0, "spawn": 4.0}
    # a alive from 0 to its kill at 2.5, b never killed
    assert said["alive"] == [2.0, 2.0, 2.0, 1.0]
    assert said["peak_alive"] == 2.0


def test_many_runs_are_averaged_and_written_recorded(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    runs = [_run(tmp_path, "one.jsonl", ONE), _run(tmp_path, "two.jsonl", TWO)]
    said = playtest.trace(runs, out="work/trace.json", root=str(tmp_path))
    assert said["runs"] == 2
    assert said["alive"] == [1.5, 1.5, 1.0, 0.5]
    assert said["totals"]["kill"] == 1.0
    record = provenance.read("work/trace.json", root=str(tmp_path))
    assert [one["path"] for one in record["inputs"]] == runs


@pytest.mark.parametrize("line", ['{"event": "spawn"}', '{"t": -1, "event": "x"}',
                                  '{"t": 1}', "not json",
                                  '{"t": 1, "event": "x", "weight": "a lot"}'])
def test_a_line_that_is_no_event_is_refused_with_its_place(tmp_path, line):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "bad.jsonl").write_text('{"t": 0, "event": "spawn"}\n' + line + "\n",
                                        encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        playtest.trace(["bad.jsonl"], root=str(tmp_path))
    assert refused.value.code == "game.bad-trace"
    assert "line 2" in refused.value.message


def test_no_trace_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        playtest.trace(["none.jsonl"], root=str(tmp_path))
    assert refused.value.code == "game.no-trace"
