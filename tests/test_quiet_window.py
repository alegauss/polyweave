"""An engine that runs out of sight (§PW296).

A gate run flashed dozens of Godot windows: the offscreen route opened a normal window
and only the script moved it away. A run now starts minimised and unfocused through the
override.cfg polyweave writes for it, merged into its own and never into a project's.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from polyweave import offscreen


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "shot.gd").write_text("extends SceneTree\n", encoding="utf-8")
    seen = {}

    def run(script, **how):
        target = Path(tmp_path) / "override.cfg"
        seen["override"] = target.read_text("utf-8") if target.exists() else None
        return {"ok": True, "log": "", "verdict": "ok"}

    monkeypatch.setattr(offscreen.engine, "run", run)
    monkeypatch.setattr(offscreen, "route_for",
                        lambda root, named="": offscreen.ROUTES[0])
    return tmp_path, seen


def test_a_capture_runs_minimised_and_unfocused_and_leaves_nothing(project):
    here, seen = project
    said = offscreen.capture("shot.gd", root=str(here), expect="x")
    assert said["quiet"] is True
    assert "window/size/mode=1" in seen["override"]
    assert "window/size/no_focus=true" in seen["override"]
    # Godot draws nothing while minimised, so this draws each frame in its place.
    assert "[autoload]" in seen["override"]
    assert offscreen.DRAWS.as_posix() in seen["override"]
    assert offscreen.DRAWS.is_file()
    assert not (here / "override.cfg").exists()


def test_it_merges_into_the_override_polyweave_wrote_for_the_run(project):
    here, seen = project
    ours = offscreen.OURS + "[display]\n\nwindow/size/borderless=true\n"
    (here / "override.cfg").write_text(ours, encoding="utf-8")
    offscreen.capture("shot.gd", root=str(here), expect="x")
    assert "window/size/borderless=true" in seen["override"]
    assert "window/size/mode=1" in seen["override"]
    assert (here / "override.cfg").read_text("utf-8") == ours


def test_a_project_s_own_override_is_never_touched(project):
    here, seen = project
    (here / "override.cfg").write_text("[display]\n\nwindow/vsync=false\n", "utf-8")
    said = offscreen.capture("shot.gd", root=str(here), expect="x")
    assert said["quiet"] is False
    assert seen["override"] == "[display]\n\nwindow/vsync=false\n"


def test_a_person_who_wants_to_watch_turns_it_off(project):
    here, seen = project
    (here / "polyweave.toml").write_text("[engine]\nquiet = false\n", encoding="utf-8")
    assert offscreen.capture("shot.gd", root=str(here), expect="x")["quiet"] is False
    assert seen["override"] is None


AWAITS = """extends SceneTree

func _initialize() -> void:
\tvar patch := ColorRect.new()
\tpatch.size = Vector2(64, 64)
\troot.add_child(patch)
\tfor colour in [Color.RED, Color.GREEN, Color.BLUE]:
\t\tpatch.color = colour
\t\tawait process_frame
\t\tawait RenderingServer.frame_post_draw
\t\tprint("drew %s" % root.get_texture().get_image().get_pixel(8, 8).to_html(false))
\tprint("awaited: done")
\tquit()
"""


def test_a_script_awaiting_each_draw_still_draws_while_minimised(tmp_path):
    # Cottony's capture scripts await frame_post_draw, which a minimised window never
    # emits; the autoload quiet() adds draws each frame in its place.
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    try:
        offscreen.route_for(tmp_path)
    except offscreen.PolyweaveError:
        pytest.skip("no route draws real pixels here")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="awaits"\n', encoding="utf-8")
    (tmp_path / "awaits.gd").write_text(AWAITS, encoding="utf-8")
    found = offscreen.capture("awaits.gd", root=str(tmp_path), timeout=60,
                              expect=re.compile(r"^awaited: done", re.MULTILINE))
    assert found["ok"] is True, found.get("why")
    log = Path(found["log"]).read_text(encoding="utf-8", errors="replace")
    drew = re.findall(r"^drew (\w+)", log, re.MULTILINE)
    assert drew == ["ff0000", "00ff00", "0000ff"]