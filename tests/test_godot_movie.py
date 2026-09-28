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


def test_a_movie_comes_out_at_the_size_asked_whatever_the_project_window(tmp_path):
    """§PW273: asked 320x240, a 1152x648 project's Movie Maker recorded 1152x648."""
    root = project(tmp_path)
    # The project's own window, Godot's default, and not the size asked.
    (root / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="shot"\n', encoding="utf-8")
    found = capture.movie("shot.gd", out="shots/sized", root=str(root),
                          environment={"resolution": "320x240"})
    assert found["ok"] is True, found["why"]
    from PIL import Image

    with Image.open(root / "shots" / "sized" / "0001.png") as first:
        assert first.size == (320, 240)
    assert not (root / "override.cfg").exists(), "the run's override is removed after"


def test_a_project_with_its_own_override_is_refused_before_it_runs(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "override.cfg").write_text("[display]\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        capture.movie("shot.gd", out="shots/x", root=str(tmp_path),
                      environment={"resolution": "320x240"})
    assert refused.value.code == "capture.override-held"
    assert (tmp_path / "override.cfg").read_text(encoding="utf-8") == "[display]\n"


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
