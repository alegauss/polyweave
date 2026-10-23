"""Two runs' entity traces compared, the first to part named (§PW612)."""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import traces


def written(tmp_path, name: str, lines: list[dict]) -> str:
    (tmp_path / "runs").mkdir(exist_ok=True)
    (tmp_path / "runs" / name).write_text(
        "".join(json.dumps(one) + "\n" for one in lines), encoding="utf-8")
    return f"runs/{name}"


def flight(frames: int = 4, wobble: dict | None = None, gone: int | None = None):
    """A wasp flying right and a player standing, as an editor's preview replays."""
    lines = []
    for frame in range(frames):
        x = 100.0 + 2 * frame + (wobble or {}).get(frame, 0.0)
        lines.append({"frame": frame, "id": "wasp-1", "kind": "enemy",
                      "position": [x, 40.0], "hp": 3})
        lines.append({"frame": frame, "id": "player", "kind": "player",
                      "position": [320.0 + (wobble or {}).get(frame, 0.0) * 2, 300.0]})
        if gone is None or frame < gone:
            lines.append({"frame": frame, "id": "wasp-2", "kind": "enemy",
                          "position": [200.0, 80.0], "hp": 1})
    return lines


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    return tmp_path


def test_two_runs_that_match_agree(project):
    one = written(project, "play.jsonl", flight())
    other = written(project, "editor.jsonl", flight())
    said = traces.compare_runs(one, other, root=str(project))
    assert said["agree"] is True and said["first"] is None
    assert said["compared"] == {"samples": 12, "entities": 3}


def test_the_first_entity_to_part_is_named_and_what_followed_is_a_consequence(project):
    one = written(project, "play.jsonl", flight())
    other = written(project, "editor.jsonl", flight(wobble={2: 0.25, 3: 0.25}))
    said = traces.compare_runs(one, other, root=str(project))
    assert said["agree"] is False
    assert said["first"] == {"at": 2, "id": "wasp-1", "field": "position",
                             "one": [104.0, 40.0], "other": [104.25, 40.0], "by": 0.25}
    assert [c["id"] for c in said["consequences"]] == ["player"]
    assert said["says"].startswith("wasp-1 parted first, on position at 2 by 0.25")


def test_a_declared_tolerance_lets_a_small_drift_agree(project):
    (project / "polyweave.toml").write_text("[trace]\ntolerance = { position = 0.6 }\n",
                                            encoding="utf-8")
    one = written(project, "play.jsonl", flight())
    other = written(project, "editor.jsonl", flight(wobble={2: 0.25}))
    assert traces.compare_runs(one, other, root=str(project))["agree"] is True
    tighter = traces.compare_runs(one, other, tolerance={"position": 0.1},
                                  root=str(project))
    assert tighter["first"]["id"] == "wasp-1"


def test_an_entity_one_run_lost_parts_on_exists_and_a_short_run_on_ended(project):
    one = written(project, "play.jsonl", flight())
    lost = written(project, "lost.jsonl", flight(gone=1))
    said = traces.compare_runs(one, lost, root=str(project))
    assert said["first"] == {"at": 1, "id": "wasp-2", "field": "exists", "one": True,
                             "other": False, "by": None}
    short = written(project, "short.jsonl", flight(frames=3))
    ended = traces.compare_runs(one, short, root=str(project))
    assert ended["first"]["field"] == "ended"
    assert ended["ends"] == {"one": 3, "other": 2}


def test_a_gate_holds_every_declared_pair(project):
    written(project, "a.jsonl", flight())
    written(project, "b.jsonl", flight())
    written(project, "c.jsonl", flight(wobble={1: 1.0}))
    (project / "polyweave.toml").write_text(
        '[trace]\npairs = [{one = "runs/a.jsonl", other = "runs/b.jsonl"},\n'
        '         {one = "runs/a.jsonl", other = "runs/c.jsonl"}]\n', encoding="utf-8")
    said = traces.compare_runs(root=str(project))
    assert said["passed"] is False
    assert [p["agree"] for p in said["pairs"]] == [True, False]


def test_seconds_stamp_a_trace_where_the_project_says_so(project):
    (project / "polyweave.toml").write_text('[trace]\ntime = "t"\n', encoding="utf-8")
    lines = [{"t": 0.5, "id": "a", "hp": 1}, {"t": 1.0, "id": "a", "hp": 1}]
    one = written(project, "a.jsonl", lines)
    other = written(project, "b.jsonl", [lines[0], {**lines[1], "hp": 0}])
    said = traces.compare_runs(one, other, root=str(project))
    assert said["first"]["at"] == 1.0 and said["first"]["by"] == 1.0


@pytest.mark.parametrize(("body", "code"), [
    ("not json\n", "game.bad-trace"),
    ('{"id": "a"}\n', "game.bad-trace"),
    ('{"frame": 0, "id": "a"}\n{"frame": 0, "id": "a"}\n', "game.bad-trace"),
    ("\n", "game.bad-trace"),
])
def test_a_trace_that_is_not_one_is_refused_by_its_line(project, body, code):
    (project / "runs").mkdir()
    (project / "runs" / "bad.jsonl").write_text(body, encoding="utf-8")
    good = written(project, "good.jsonl", flight())
    with pytest.raises(PolyweaveError) as refused:
        traces.compare_runs(good, "runs/bad.jsonl", root=str(project))
    assert refused.value.code == code


def test_a_missing_trace_or_pair_is_refused(project):
    with pytest.raises(PolyweaveError) as refused:
        traces.compare_runs(root=str(project))
    assert refused.value.code == "game.no-trace"
    with pytest.raises(PolyweaveError) as refused:
        traces.compare_runs("runs/a.jsonl", "runs/b.jsonl", root=str(project))
    assert refused.value.code == "game.no-trace"
    with pytest.raises(PolyweaveError) as refused:
        traces.compare_runs("runs/a.jsonl", root=str(project))
    assert refused.value.code == "game.bad-target"
