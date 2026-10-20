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

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import driving

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


def _app_zip(where: Path, pack: bytes = b"GDPC") -> Path:
    import zipfile

    with zipfile.ZipFile(where, "w") as made:
        binary = zipfile.ZipInfo("Smoked.app/Contents/MacOS/Smoked")
        binary.external_attr = 0o100755 << 16
        made.writestr(binary, b"\xcf\xfa\xed\xfe")
        made.writestr("Smoked.app/Contents/Resources/Smoked.pck", pack)
        made.writestr("Smoked.app/Contents/Info.plist", "<plist/>")
    return where


def test_a_macos_preset_is_exported_as_a_bundle_and_its_binary_launched(tmp_path,
                                                                       monkeypatch):
    """§PW577: on a Mac every preset was skipped, and the export looked for a .exe."""
    here = game(tmp_path, exclude="")
    (here / "export_presets.cfg").write_text(
        PRESET.format(platform="macOS", exclude=""), encoding="utf-8")
    monkeypatch.setattr(driving.sys, "platform", "darwin")
    monkeypatch.setenv("GODOT", "godot")
    launched = []

    def launch(command, *, cwd, timeout, env=None):
        launched.append(command)
        if "--export-debug" in command:
            assert command[-1].endswith(".zip")
            _app_zip(Path(command[-1]))
        return "", 0

    monkeypatch.setattr(driving.engine, "_launch", launch)
    [preset] = driving.export_smoke(presets=["Desktop"], root=str(here))["presets"]
    assert preset["held"] is True, preset
    binary = preset["binary"].replace("\\", "/")
    assert binary.endswith("Smoked.app/Contents/MacOS/Smoked")
    assert preset["pack"].endswith("Smoked.pck")
    assert preset["bundle"].endswith(".app")
    assert launched[-1][0] == preset["binary"]
    assert "--headless" in launched[-1]
    if sys.platform != "win32":
        assert os.access(preset["binary"], os.X_OK), "the execute bit kept from the zip"


def test_a_release_check_reads_the_pack_inside_a_macos_bundle(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    shipped = _app_zip(tmp_path / "Smoked.zip", b"pack " + driving.ADDON.encode())
    found = driving.release_checked(root=str(tmp_path), pack=str(shipped))
    assert [one["code"] for one in found["findings"]] == ["game.driver-in-pack"]
    assert found["pack"] is True


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
