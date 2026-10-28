"""One scene script over a grid of arguments, keeping runs that show a moment (§PW250).

The grid and the record are checked everywhere; the runs themselves need `$GODOT`.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import engine

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


def test_a_hit_keeps_the_whole_line_the_run_printed(tmp_path):
    """§PW487: the pattern matched "level:", and every number on the line was lost."""
    root = game(tmp_path)
    found = engine.sweep(
        "scan.gd",
        grid={"seed": [3], "policy": ["greedy"]},
        pattern=r"EVENT tick=",
        root=str(root),
    )
    (run,) = found["runs"]
    assert run["lines"] == ["EVENT tick=300 evolution Ring Gunner"]
    assert run["matched"] == ["EVENT tick="]


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


# -- a sweep of captures (§PW655) ------------------------------------------------------

DRAWS = """extends SceneTree

var frames := 0
var out := ""

func _initialize() -> void:
\tfor arg in OS.get_cmdline_user_args():
\t\tif arg.begins_with("--out="):
\t\t\tout = arg.get_slice("=", 1)

func _process(_delta: float) -> bool:
\tframes += 1
\tif frames < 3:
\t\treturn false
\tvar image := root.get_viewport().get_texture().get_image()
\timage.save_png(out)
\tprint("captured: %s %d x %d" % [out, image.get_width(), image.get_height()])
\treturn true
"""


def drawing(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[capture]\ndeclared = []\n",
                                             encoding="utf-8")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="draws"\n', encoding="utf-8")
    (tmp_path / "draws.gd").write_text(DRAWS, encoding="utf-8")
    return tmp_path


def test_a_headless_sweep_of_a_script_that_saves_a_picture_is_refused(tmp_path):
    # Spinhold's fifteen legibility runs each ended in save_png on null.
    root = drawing(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        engine.sweep("draws.gd", grid={"seed": [1]}, pattern="captured",
                     root=str(root))
    assert refused.value.code == "engine.headless-picture"


def test_a_drawn_sweep_flies_each_run_as_a_capture(tmp_path, monkeypatch):
    from pathlib import Path

    from polyweave.layers.engine import capture

    root = drawing(tmp_path)
    flown = []

    def taken(script, *, expect, root, frames, args):
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--out="))
        flown.append(out)
        (Path(root) / out).parent.mkdir(parents=True, exist_ok=True)
        (Path(root) / out).write_bytes(b"png")
        log = Path(root) / f"{len(flown)}.log"
        log.write_text(f"captured: {out} 8 x 8\n", encoding="utf-8")
        return {"ok": True, "verdict": "ok", "log": str(log), "seconds": 1.0,
                "artefacts": [str(Path(root) / out)]}

    monkeypatch.setattr(capture, "run", taken)
    found = engine.sweep("draws.gd", grid={"seed": ["a", "b"]}, pattern="captured",
                         args=["--out=shots/{seed}.png"], display=True,
                         root=str(root))
    assert flown == ["shots/a.png", "shots/b.png"]
    assert [r["produced"] for r in found["runs"]] == [["shots/a.png"], ["shots/b.png"]]
    assert len(found["hits"]) == 2


def test_a_sweep_of_captures_draws_every_picture_in_one_call(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = drawing(tmp_path)
    found = engine.sweep("draws.gd", grid={"seed": [1, 2]}, pattern="captured",
                         args=["--out=res://shots/{seed}.png"], display=True,
                         root=str(root))
    assert [r["verdict"] for r in found["runs"]] == ["ok", "ok"], found["runs"]
    assert (root / "shots" / "1.png").is_file() and (root / "shots" / "2.png").is_file()