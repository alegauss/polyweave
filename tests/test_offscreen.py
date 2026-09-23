"""Getting real pixels out of the engine with nobody watching.

§PW23's case: headless mode draws nothing, so every visual check lands on a developer's
desk and never in a gate.

The tests that need the engine skip without `$GODOT`, and the ones that do run there are
the point of the line: a route is available only where a picture it drew was looked at.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import engine, offscreen
from polyweave.errors import PolyweaveError

#: The scene script these run, as a file rather than a literal (§PW48): real code
#: living in a Python string is code nothing highlights and nothing lints, and
#: GDScript's own tabs were two characters each in it.
CAPTURE = (Path(__file__).parent / "fixtures" / "gdscript" / "capture.gd").read_text(
    encoding="utf-8"
)


def engine_here():
    """The engine, or a skip: this machine may not have one."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine, and a route is not assumed")
    return os.environ["GODOT"]


def project(tmp_path, *, script=CAPTURE):
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="probe"\n', encoding="utf-8"
    )
    (tmp_path / "shot.gd").write_text(script, encoding="utf-8")
    return tmp_path / "shot.gd"


def kept(tmp_path, available, routes=None):
    """A probe answer already on disk, so nothing has to run to read it."""
    where = tmp_path / ".polyweave" / "offscreen" / "routes.json"
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(
        json.dumps(
            {
                "engine": "godot",
                "checked": "2026-09-22T00:00:00",
                "routes": routes
                or [{"route": name, "works": True, "why": ""} for name in available],
                "available": available,
            }
        ),
        encoding="utf-8",
    )
    return where


def picture(where, colour):
    canvas = np.zeros((16, 16, 4), dtype=np.uint8)
    canvas[:, :, :3] = colour
    canvas[:, :, 3] = 255
    PILImage.fromarray(canvas, "RGBA").save(where)
    return where


# -- the routes that exist ----------------------------------------------------------


def test_headless_is_among_them_so_it_can_be_shown_not_to_draw():
    """It is the route everyone reaches for, and the whole of §PW23 is that it lies."""
    named = [route.name for route in offscreen.ROUTES]
    assert "headless" in named
    assert named[-1] == "headless", "it is tried last, because it never works"


def test_the_virtual_display_route_names_what_it_needs():
    route = next(r for r in offscreen.ROUTES if r.name == "virtual-display")
    assert route.needs == "xvfb-run"
    assert route.through[0] == "xvfb-run"


def test_a_route_needing_a_command_that_is_absent_runs_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(offscreen.shutil, "which", lambda _name: None)
    route = next(r for r in offscreen.ROUTES if r.needs)
    found = offscreen.probe(route, root=tmp_path)
    assert found["works"] is False
    assert "not on PATH" in found["why"]
    assert found["seconds"] == 0.0


# -- what counts as having drawn -------------------------------------------------------


def test_a_picture_of_the_colour_the_probe_drew_counts(tmp_path):
    wanted = tuple(round(channel * 255) for channel in offscreen.PROVES)
    assert offscreen._drew(picture(tmp_path / "ok.png", wanted))[0] is True


def test_a_picture_of_any_other_colour_does_not(tmp_path):
    works, why = offscreen._drew(picture(tmp_path / "no.png", (0, 0, 0)))
    assert works is False
    assert "the probe drew" in why


def test_no_picture_at_all_does_not(tmp_path):
    works, why = offscreen._drew(tmp_path / "never-written.png")
    assert works is False
    assert why == "no picture was written"


# -- the answer is kept, and it is the machine's --------------------------------------


def test_a_probed_answer_is_read_back_rather_than_paid_for_twice(tmp_path):
    kept(tmp_path, ["window-offscreen"])
    found = offscreen.routes(tmp_path)
    assert found["available"] == ["window-offscreen"]


def test_rechecking_is_how_it_gets_paid_for_again(tmp_path, monkeypatch):
    kept(tmp_path, ["window-offscreen"])
    monkeypatch.setattr(
        offscreen,
        "probe",
        lambda route, **_: {"route": route.name, "works": False, "why": "probed"},
    )
    monkeypatch.setattr(engine, "find", lambda _root: "godot")
    found = offscreen.routes(tmp_path, recheck=True)
    assert found["available"] == []
    assert all(one["why"] == "probed" for one in found["routes"])


def test_an_unreadable_answer_is_probed_again_rather_than_trusted(
    tmp_path, monkeypatch
):
    where = kept(tmp_path, ["window-offscreen"])
    where.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(
        offscreen,
        "probe",
        lambda route, **_: {"route": route.name, "works": True, "why": ""},
    )
    monkeypatch.setattr(engine, "find", lambda _root: "godot")
    assert offscreen.routes(tmp_path)["available"][0] == offscreen.ROUTES[0].name


# -- which route a capture takes -------------------------------------------------------


def test_the_first_route_that_draws_here_is_the_one_taken(tmp_path):
    kept(tmp_path, ["window-minimised", "window-offscreen"])
    assert offscreen.route_for(tmp_path).name == "window-minimised"


def test_a_caller_that_wants_one_route_may_name_it(tmp_path):
    assert offscreen.route_for(tmp_path, named="headless").name == "headless"


def test_a_route_by_a_name_nothing_has_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        offscreen.route_for(tmp_path, named="xvfb")
    assert caught.value.code == "engine.no-offscreen-route"
    assert "virtual-display" in caught.value.remedy


def test_a_machine_where_nothing_draws_is_said_so_with_what_was_tried(tmp_path):
    kept(
        tmp_path,
        [],
        routes=[
            {"route": "headless", "works": False, "why": "the renderer drew nothing"},
            {"route": "virtual-display", "works": False, "why": "no xvfb-run"},
        ],
    )
    with pytest.raises(PolyweaveError) as caught:
        offscreen.route_for(tmp_path)
    assert caught.value.code == "engine.no-offscreen-route"
    assert "the renderer drew nothing" in caught.value.detail
    assert "no xvfb-run" in caught.value.detail


def test_the_caller_never_has_to_know_which_route_it_got(tmp_path):
    kept(tmp_path, ["window-offscreen"])
    project(tmp_path)
    seen = {}

    def launch(command, *, cwd, timeout):
        seen["command"] = command
        return "captured: res://shot.png 32 x 32\n", 0

    found = offscreen.capture(
        tmp_path / "shot.gd",
        expect=offscreen.CAPTURED,
        root=tmp_path,
        binary="godot",
        launch=launch,
    )
    assert found["route"] == "window-offscreen"
    assert seen["command"][-2:] == ["--", "offscreen"]
    assert "--headless" not in seen["command"]


def test_the_headless_route_puts_its_flag_on_the_command(tmp_path):
    project(tmp_path)
    seen = {}

    def launch(command, *, cwd, timeout):
        seen["command"] = command
        return "captured: res://shot.png 32 x 32\n", 0

    offscreen.capture(
        tmp_path / "shot.gd",
        expect=offscreen.CAPTURED,
        root=tmp_path,
        route="headless",
        binary="godot",
        launch=launch,
    )
    assert "--headless" in seen["command"]


# -- against the engine itself ---------------------------------------------------------


def test_the_engine_s_headless_mode_really_does_draw_nothing(tmp_path):
    """Not folklore: the probe runs it and reads back what it got."""
    binary = engine_here()
    (tmp_path / "polyweave.toml").write_text(
        f'[paths]\ngodot = "{Path(binary).as_posix()}"\n', encoding="utf-8"
    )
    route = next(r for r in offscreen.ROUTES if r.name == "headless")
    found = offscreen.probe(route, root=tmp_path)
    assert found["works"] is False
    assert "no image" in found["why"] or "no texture" in found["why"]


def test_a_real_display_driver_with_the_window_out_of_the_way_does(tmp_path):
    binary = engine_here()
    (tmp_path / "polyweave.toml").write_text(
        f'[paths]\ngodot = "{Path(binary).as_posix()}"\n', encoding="utf-8"
    )
    route = next(r for r in offscreen.ROUTES if r.name == "window-offscreen")
    found = offscreen.probe(route, root=tmp_path)
    assert found["works"] is True, found["why"]


def test_a_capture_script_comes_back_with_a_picture_that_has_pixels_in_it(tmp_path):
    binary = engine_here()
    (tmp_path / "polyweave.toml").write_text(
        f'[paths]\ngodot = "{Path(binary).as_posix()}"\n', encoding="utf-8"
    )
    project(tmp_path)
    found = offscreen.capture(
        tmp_path / "shot.gd",
        expect=offscreen.CAPTURED,
        produces=("artefact",),
        root=tmp_path,
    )
    assert found["ok"] is True, found["why"]
    assert found["route"] != "headless"
    drawn = np.asarray(PILImage.open(tmp_path / "shot.png").convert("RGBA"))
    assert tuple(drawn[16, 16, :3]) == (0, 0, 255), "the blue it was told to draw"
