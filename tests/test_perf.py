"""A performance budget the gate holds, and a baseline a commit regresses from (§PW365).

The arithmetic runs anywhere; a measure needs $GODOT and a route that draws real pixels.
"""

from __future__ import annotations

import os

import pytest

from polyweave import offscreen, perf
from polyweave.errors import PolyweaveError

BUDGET = ('[perf.main]\nscene = "res://main.tscn"\nframes = 60\np95_ms = {p95}\n'
          "p99_ms = 1000\nload_ms = 5000\nmemory_mb = 4096\nnodes = 100\n")


def project(tmp_path, p95=1000):
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\n\nconfig/name="perf"\n', encoding="utf-8")
    (tmp_path / "main.tscn").write_text('[gd_scene format=3]\n\n[node name="Main" '
                                        'type="Node2D"]\n', encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text(BUDGET.format(p95=p95), encoding="utf-8")
    return str(tmp_path)


def test_a_measure_over_its_budget_is_named_and_a_move_is_a_share():
    found = perf.held({"p95_ms": 20.0, "nodes": 50.0}, {"p95_ms": 16.6, "nodes": 100},
                      {"p95_ms": 16.0, "nodes": 50.0})
    assert found["held"] is False
    assert found["budgets"]["p95_ms"] == {"value": 20.0, "most": 16.6, "held": False}
    assert found["budgets"]["nodes"]["held"] is True
    assert found["moved"]["p95_ms"]["change"] == 0.25
    assert perf.held({"p95_ms": 1.0}, {"p95_ms": 2}, None)["moved"] == {}


def test_a_project_with_no_budget_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        perf.perf(root=str(tmp_path))
    assert caught.value.code == "engine.no-budget"


def test_a_machine_with_nothing_that_draws_is_skipped_and_said(tmp_path, monkeypatch):
    def nothing(*_, **__):
        raise PolyweaveError("engine.no-offscreen-route",
                             "no route draws real pixels on this machine", "use one")

    monkeypatch.setattr(offscreen, "route_for", nothing)
    found = perf.perf(root=project(tmp_path))
    assert found["ok"] is None
    assert "no route draws" in found["skipped"]


def _drawn(found):
    if found.get("skipped"):
        pytest.skip(found["skipped"])
    return found


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_scene_is_measured_held_and_compared_with_its_baseline(tmp_path):
    root = project(tmp_path)
    first = _drawn(perf.perf(root=root))
    assert first["ok"] is True
    main = first["scenes"]["main"]
    assert main["baseline"] == "written"
    assert set(main["measured"]) >= set(perf.MEASURES)
    assert main["measured"]["nodes"] >= 2
    second = perf.perf(root=root)["scenes"]["main"]
    assert "baseline" not in second
    assert set(second["moved"]) >= {"p95_ms", "load_ms"}
    tight = perf.perf(root=project(tmp_path, p95=0.0001))
    assert tight["ok"] is False
    assert tight["says"] == "1 scene(s), over budget: main"
    assert perf.perf(root=root, rebase=True)["scenes"]["main"]["baseline"] == "written"
