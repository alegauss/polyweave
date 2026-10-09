"""The graphics kit the plugin carries, proved in its own fixture (§PW366).

Its proof is a script, since what a preset puts in force is read back from the running
viewport; it runs where $GODOT is set and is said skipped where not. The fallback is
seen by launching the fixture with Vulkan's drivers hidden, which needs a display.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import engine, kits, offscreen
from polyweave.errors import PolyweaveError


def test_the_graphics_kit_contributes_the_graphics_tab_after_options():
    found = kits.every()["graphics"]
    assert found["requires"] == ["options"]
    assert found["tab"] == "graphics"
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def test_the_graphics_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("graphics")["kits"]
    assert said["status"] == "skipped"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "graphics" / "fixture", game)
    return game, kits.install("graphics", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_graphics_kit_lands_after_options_and_every_preset_reads_back(tmp_path):
    _, said = _installed(tmp_path)
    assert said["order"] == ["prompts", "menus", "options", "graphics"]
    assert said["proved"]["passed"] is True, said["proved"]


GRAPHICS = "addons/polyweave/graphics/graphics.gd"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    (GRAPHICS, "2: Viewport.MSAA_2X, 4: Viewport.MSAA_4X",
     "2: Viewport.MSAA_4X, 4: Viewport.MSAA_4X", "preset declares msaa"),
    (GRAPHICS, "EFFECTS.filter(func(e: String) -> bool: return env.get(e))",
     "EFFECTS.duplicate()", "switched on an effect no environment"),
    ("project.godot", 'run/main_scene="res://main.tscn"\n',
     'run/main_scene="res://main.tscn"\n\n[rendering]\n\n'
     "rendering_device/fallback_to_opengl3=false\n", "fallback_to_opengl3 is off"),
])
def test_a_broken_preset_fails_the_proof_by_name(tmp_path, where, before, after, said):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["graphics"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_game_whose_vulkan_refuses_still_reaches_its_scene(tmp_path):
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError as refused:
        pytest.skip(refused.message)
    game, _ = _installed(tmp_path)
    (tmp_path / "driver.gd").write_text(
        "extends SceneTree\n\nvar frames := 0\n\n\nfunc _initialize() -> void:\n"
        '\tchange_scene_to_file("res://main.tscn")\n\n\n'
        "func _process(_d: float) -> bool:\n\tframes += 1\n\tif frames < 3:\n"
        "\t\treturn false\n"
        '\tprint("REACHED ", current_scene.name, " ON ", '
        "RenderingServer.get_current_rendering_driver_name())\n\treturn true\n",
        encoding="utf-8")
    hidden = {**os.environ, "VK_ICD_FILENAMES": str(tmp_path / "none.json"),
              "VK_DRIVER_FILES": str(tmp_path / "none.json")}
    output, _ = engine._launch(
        [engine.find(game), "--path", str(game), "--script",
         (tmp_path / "driver.gd").as_posix()],
        cwd=game, timeout=120, env=hidden)
    reached = [line for line in output.splitlines() if line.startswith("REACHED ")]
    assert reached, output[-800:]
    assert reached[0].startswith("REACHED Main ON ")
    assert not reached[0].endswith(" vulkan")
