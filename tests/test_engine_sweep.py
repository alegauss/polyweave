"""One scene script over a grid of arguments, keeping runs that show a moment (§PW250).

The grid and the record are checked everywhere; the runs themselves need `$GODOT`.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from polyweave import engine
from polyweave.errors import PolyweaveError

SCAN = """extends SceneTree

func _initialize() -> void:
\tvar seed_value := 0
\tvar policy := ""
\tfor arg in OS.get_cmdline_user_args():
\t\tif arg.begins_with("--seed="):
\t\t\tseed_value = int(arg.get_slice("=", 1))
\t\telif arg.begins_with("--policy="):
\t\t\tpolicy = arg.get_slice("=", 1)
\tif seed_value %% 3 == 0 and policy == "greedy":
\t\tprint("EVENT tick=%%d evolution Ring Gunner" %% (seed_value * 100))
\tprint("scan: done")
\tquit()
"""


def game(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="scan"\n', encoding="utf-8"
    )
    (tmp_path / "scan.gd").write_text(SCAN % (), encoding="utf-8")
    return tmp_path


def test_the_runs_that_show_the_moment_are_the_hits(tmp_path):
    root = game(tmp_path)
    found = engine.sweep(
        "scan.gd",
        grid={"seed": [1, 2, 3, 4, 5, 6], "policy": ["greedy", "shy"]},
        pattern=r"EVENT tick=\d+ evolution .*",
        root=str(root),
    )
    assert found["combinations"] == 12
    assert found["flown"] == 12
    assert found["hits"] == [
        {
            "args": {"policy": "greedy", "seed": 3},
            "lines": ["EVENT tick=300 evolution Ring Gunner"],
        },
        {
            "args": {"policy": "greedy", "seed": 6},
            "lines": ["EVENT tick=600 evolution Ring Gunner"],
        },
    ]
    assert all(r["verdict"] in ("ok", "no-signal") for r in found["runs"])


def test_a_sweep_can_stop_at_its_first_hit(tmp_path):
    root = game(tmp_path)
    found = engine.sweep(
        "scan.gd",
        grid={"seed": list(range(1, 13)), "policy": ["greedy"]},
        pattern=r"EVENT .*",
        root=str(root),
        first=1,
        lanes=1,
    )
    assert len(found["hits"]) == 1
    assert found["flown"] < 12


def test_the_same_sweep_of_the_same_build_answers_from_its_record(tmp_path):
    root = game(tmp_path)
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "scan"]):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *command],
            cwd=root,
            check=True,
        )
    asked = {"grid": {"seed": [3], "policy": ["greedy"]}, "pattern": r"EVENT .*"}
    first = engine.sweep("scan.gd", root=str(root), **asked)
    again = engine.sweep("scan.gd", root=str(root), **asked)
    assert first["cached"] is False
    assert again["cached"] is True
    assert again["hits"] == first["hits"]
    (root / "scan.gd").write_text(SCAN.replace("Ring Gunner", "Tempest") % (), "utf-8")
    edited = engine.sweep("scan.gd", root=str(root), **asked)
    assert edited["cached"] is False
    assert edited["hits"][0]["lines"] == ["EVENT tick=300 evolution Tempest"]


def test_a_grid_without_values_is_refused(tmp_path):
    (tmp_path / "scan.gd").write_text("extends SceneTree\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        engine.sweep("scan.gd", grid={"seed": 3}, pattern="x", root=str(tmp_path))
    assert refused.value.code == "engine.bad-grid"
