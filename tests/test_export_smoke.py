"""Each export preset built and launched as a player would launch it (§PW363).

The export and the launch need $GODOT and its export templates for this platform; a
project with no preset is refused everywhere.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

from polyweave import driving
from polyweave.errors import PolyweaveError

PRESET = """[preset.0]

name="Desktop"
platform="{platform}"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter="{exclude}"
export_path=""
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

binary_format/embed_pck=false
"""

MAIN = """extends Node

var loaded := false


func _ready() -> void:
\tloaded = load("res://art/dot.png") != null
"""


def game(tmp_path: Path, exclude: str) -> Path:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\n\nconfig/name="smoked"\n'
        'run/main_scene="res://main.tscn"\n', encoding="utf-8")
    (tmp_path / "main.gd").write_text(MAIN, encoding="utf-8")
    (tmp_path / "main.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://main.gd" id="1"]\n\n'
        '[node name="Main" type="Node"]\nscript = ExtResource("1")\n', encoding="utf-8")
    (tmp_path / "art").mkdir(exist_ok=True)
    Image.new("RGB", (4, 4), (255, 0, 0)).save(tmp_path / "art" / "dot.png")
    platform = "Windows Desktop" if sys.platform == "win32" else "Linux"
    (tmp_path / "export_presets.cfg").write_text(
        PRESET.format(platform=platform, exclude=exclude), encoding="utf-8")
    return tmp_path


def test_a_project_with_no_preset_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        driving.export_smoke(root=str(tmp_path))
    assert caught.value.code == "game.no-preset"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_resource_the_filter_left_out_is_found_by_launching_the_build(tmp_path):
    here = game(tmp_path, exclude="art/*")
    [preset] = driving.export_smoke(root=str(here))["presets"]
    assert preset["held"] is False
    assert "res://art/dot.png" in preset["why"]
    assert preset["ran"] == "the exported debug binary"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_whole_export_launches_and_replays_a_flow_with_the_driver_outside(tmp_path):
    here = game(tmp_path, exclude="")
    flow = here / "tests" / "smoke.flow.json"
    flow.parent.mkdir()
    steps = [{"cmd": "step", "frames": 3},
             {"cmd": "expect", "path": "/root/Main", "property": "loaded",
              "equals": True}]
    flow.write_text(json.dumps({"format": 1, "proves": "the dot loads", "seed": 0,
                                "scene": "", "steps": steps}), encoding="utf-8")
    answer = driving.export_smoke(flow="tests/smoke.flow.json", root=str(here))
    [preset] = answer["presets"]
    assert preset["held"] is True, preset
    assert "the driver from outside" in preset["ran"]
    assert answer["ok"] is True
    pack = Path(preset["binary"]).with_suffix(".pck")
    assert b"polyweave_driver" not in pack.read_bytes()
    steps[1]["equals"] = False
    flow.write_text(json.dumps({"format": 1, "proves": "wrong", "seed": 0, "scene": "",
                                "steps": steps}), encoding="utf-8")
    [wrong] = driving.export_smoke(flow="tests/smoke.flow.json",
                                   root=str(here))["presets"]
    assert wrong["held"] is False
    assert "loaded" in wrong["why"]
