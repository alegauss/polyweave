"""What a Godot build ships, read off its export preset (§PW455).

Spinhold's disclosure asked provenance.generated about the build, and the answer counted
meshes the preset excludes and listed 380 unrecorded files, nearly all code, where the
three brand pictures among them were the only ones a person had to look at.
"""

from __future__ import annotations

import pytest

from polyweave import provenance
from polyweave.errors import PolyweaveError

PRESETS = """[preset.0]

name="Windows Desktop"
platform="Windows Desktop"
export_filter="all_resources"
include_filter="game/waves/*.toml"
exclude_filter="assets/models/*, art/*, tools/*"

[preset.0.options]

[preset.1]

name="Web"
platform="Web"
export_filter="all_resources"
include_filter=""
exclude_filter=""
"""


def made(root, path, *, kind="fetch", service="elevenlabs"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.encode("utf-8"))
    provenance.write(provenance.build(
        kind, target, engine={"name": service},
        extra={"task_id": f"{service}:1", "service": service}, root=root), root=root)


def game(tmp_path):
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "export_presets.cfg").write_text(PRESETS, encoding="utf-8")
    made(tmp_path, "game/voice/line_01.ogg")
    made(tmp_path, "assets/models/drone.glb", service="meshy")
    made(tmp_path, "tools/art/meshy/drone.glb", service="meshy")
    for path in ("game/main.gd", "game/main.tscn", "game/ui/brand/logo.png",
                 "game/waves/one.toml", "game/notes.md", "docs/readme.md"):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("x", encoding="utf-8")
    (tmp_path / ".godot").mkdir()
    (tmp_path / ".godot" / "cache.png").write_text("x", encoding="utf-8")
    return tmp_path


def test_a_godot_project_answers_for_what_its_first_preset_ships(tmp_path):
    said = provenance.generated(root=str(game(tmp_path)))
    assert said["preset"] == "Windows Desktop"
    assert [one["path"] for one in said["generated"]] == ["game/voice/line_01.ogg"]


def test_unrecorded_pictures_are_apart_from_code(tmp_path):
    said = provenance.generated(root=str(game(tmp_path)))
    assert said["unrecorded"] == ["game/ui/brand/logo.png"]
    assert "game/main.gd" in said["unrecorded_code"]
    assert "game/waves/one.toml" in said["unrecorded_code"]  # its include_filter
    assert "game/notes.md" not in said["unrecorded_code"]  # not a resource
    assert all(not p.startswith(".godot") for p in said["unrecorded_code"])


def test_another_preset_is_named(tmp_path):
    said = provenance.generated(preset="Web", root=str(game(tmp_path)))
    assert said["preset"] == "Web"
    assert {one["path"] for one in said["generated"]} == {
        "game/voice/line_01.ogg", "assets/models/drone.glb",
        "tools/art/meshy/drone.glb"}


def test_a_preset_nothing_declares_is_refused_with_the_ones_there(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        provenance.generated(preset="Linux", root=str(game(tmp_path)))
    assert refused.value.code == "prov.no-preset"
    assert set(refused.value.allowed) == {"Windows Desktop", "Web"}


def test_paths_given_are_read_as_given(tmp_path):
    said = provenance.generated(paths=["assets"], root=str(game(tmp_path)))
    assert "preset" not in said
    assert [one["path"] for one in said["generated"]] == ["assets/models/drone.glb"]
