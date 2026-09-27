"""Every frame of a shot, between two marks the script prints (§PW249).

These run the engine with a real display through the offscreen route, since a headless
run draws nothing, and skip where there is none.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from polyweave import capture, offscreen
from polyweave.errors import PolyweaveError

SHOT = """extends SceneTree

var rect: ColorRect

func _initialize() -> void:
\trect = ColorRect.new()
\trect.size = Vector2(40, 40)
\troot.add_child.call_deferred(rect)
\tvar asked := {}
\tfor arg in OS.get_cmdline_user_args():
\t\tif arg.contains("="):
\t\t\tasked[arg.get_slice("=", 0)] = arg.get_slice("=", 1)
\tprint("environment: resolution=%%dx%%d" %% [root.size.x, root.size.y])

func _process(_delta: float) -> bool:
\tvar frame := Engine.get_process_frames()
\tif rect:
\t\trect.position.x = frame * 4
\tif frame == %(start)d:
\t\tprint("movie: from %%d" %% frame)
\tif frame == %(stop)d:
\t\tprint("movie: to %%d" %% frame)
\treturn frame >= %(stop)d + 3
"""


def project(tmp_path: Path, start: int = 5, stop: int = 12) -> Path:
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError:
        pytest.skip("no route draws real pixels here")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="shot"\n\n[display]\n\n'
        "window/size/viewport_width=320\nwindow/size/viewport_height=180\n",
        encoding="utf-8",
    )
    (tmp_path / "shot.gd").write_text(
        SHOT % {"start": start, "stop": stop}, encoding="utf-8"
    )
    return tmp_path


def test_every_frame_between_the_marks_is_kept_and_recorded(tmp_path):
    root = project(tmp_path)
    found = capture.movie(
        "shot.gd",
        out="shots/slide",
        root=str(root),
        environment={"resolution": "320x180"},
    )
    assert found["ok"] is True, found["why"]
    assert found["count"] == 8
    assert found["dropped"] == []
    kept = sorted(p.name for p in (root / "shots" / "slide").glob("*.png"))
    assert kept == [f"{n:04d}.png" for n in range(1, 9)]
    sequence = json.loads((root / "shots" / "slide" / "sequence.json").read_text())
    assert [f["tick"] for f in sequence["frames"]] == list(range(5, 13))
    assert sequence["fps"] == 60
    assert len({f["sha256"] for f in sequence["frames"]}) == 8, "the square moved"
    assert Path(found["record"]).is_file()


def test_a_script_that_prints_no_marks_is_not_ok(tmp_path):
    root = project(tmp_path)
    (root / "shot.gd").write_text(
        "extends SceneTree\n\nfunc _process(_d: float) -> bool:\n"
        "\treturn Engine.get_process_frames() > 5\n",
        encoding="utf-8",
    )
    found = capture.movie(
        "shot.gd", out="shots/none", root=str(root), environment={}
    )
    assert found["ok"] is False
    assert "movie: from" in found["why"]
