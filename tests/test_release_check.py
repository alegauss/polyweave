"""A release checked for the driver that must never ship to a player (§PW215)."""

from __future__ import annotations

import pytest

from polyweave import driving
from polyweave.errors import PolyweaveError

PRESET = """[preset.0]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
export_filter="{mode}"
include_filter="{include}"
exclude_filter="{exclude}"
export_path="build/game.exe"

[preset.0.options]

binary_format/embed_pck=false
"""


def project(tmp_path, mode="all_resources", include="", exclude="", autoload=""):
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="shipped"\n'
        + (f"\n[autoload]\n\n{autoload}\n" if autoload else ""),
        encoding="utf-8",
    )
    (tmp_path / "export_presets.cfg").write_text(
        PRESET.format(mode=mode, include=include, exclude=exclude), encoding="utf-8"
    )
    return str(tmp_path)


def codes(found):
    return [one["code"] for one in found["findings"]]


def test_a_preset_that_excludes_the_addon_passes(tmp_path):
    root = project(tmp_path, exclude="addons/polyweave_driver/*, *.md")
    found = driving.release_checked(root)
    assert found["ok"] is True
    assert found["presets"] is True


def test_a_preset_exporting_everything_without_the_exclusion_is_named(tmp_path):
    found = driving.release_checked(project(tmp_path))
    assert codes(found) == ["game.driver-exported"]
    finding = found["findings"][0]
    assert finding["preset"] == "Windows Desktop"
    assert finding["at"] == "export_presets.cfg:8"
    assert "exclude_filter" in finding["fix"]


def test_a_preset_exporting_scenes_ships_the_driver_only_if_it_pulls_it_in(tmp_path):
    assert driving.release_checked(project(tmp_path, mode="scenes"))["ok"] is True
    pulled = driving.release_checked(
        project(tmp_path, mode="scenes", include="addons/*")
    )
    assert codes(pulled) == ["game.driver-exported"]


def test_an_autoload_naming_the_driver_is_named(tmp_path):
    root = project(
        tmp_path,
        exclude="addons/polyweave_driver/*",
        autoload='Driver="*res://addons/polyweave_driver/driver.gd"',
    )
    assert codes(driving.release_checked(root)) == ["game.driver-autoloaded"]


def test_a_pack_holding_the_driver_is_named(tmp_path):
    root = project(tmp_path, exclude="addons/polyweave_driver/*")
    header = b"GDPC" + (2).to_bytes(4, "little") + b"\x04\x00\x00\x00" * 3 + b"\0" * 4
    (tmp_path / "game.pck").write_bytes(
        header + b"res://addons/polyweave_driver/driver.gdc" + b"\x00" * 8
    )
    (tmp_path / "clean.pck").write_bytes(header + b"res://main.tscn")
    assert codes(driving.release_checked(root, pack="game.pck")) == [
        "game.driver-in-pack"
    ]
    clean = driving.release_checked(root, pack="clean.pck")
    assert clean["ok"] is True
    assert clean["pack"] is True


def test_an_encrypted_pack_is_said_to_be_unread_not_passed(tmp_path):
    root = project(tmp_path, exclude="addons/polyweave_driver/*")
    header = b"GDPC" + (2).to_bytes(4, "little") + b"\x04\x00\x00\x00" * 3
    (tmp_path / "locked.pck").write_bytes(
        header + (1).to_bytes(4, "little") + b"\xff" * 64
    )
    assert codes(driving.release_checked(root, pack="locked.pck")) == [
        "game.pack-unread"
    ]


def test_as_a_gate_the_first_finding_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        driving.release_checked(project(tmp_path), strict=True)
    assert refused.value.code == "game.driver-exported"


def test_a_pack_that_is_not_there_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        driving.release_checked(project(tmp_path), pack="nowhere.pck")
    assert refused.value.code == "game.no-pack"
