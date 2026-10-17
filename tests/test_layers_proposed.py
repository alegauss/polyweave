"""project.init proposes the layers a tree shows it using (§PW509)."""

from __future__ import annotations

from polyweave.kernel import config as C
from polyweave.kernel.layer import layers, on
from polyweave.surface.project import init


def _tree(root, files):
    for name, body in files.items():
        where = root / name
        where.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            where.write_bytes(body)
        else:
            where.write_text(body, encoding="utf-8")
    return root


def test_a_godot_game_with_pictures_and_sound_is_proposed_those_layers(tmp_path):
    _tree(tmp_path, {
        "project.godot": 'config/name="Bubbles"\n',
        "art/bubble.png": b"\x89PNG",
        "audio/pop.wav": b"RIFF",
        "fx/burst.vfx.toml": "[effect.burst]\n",
    })
    said = init(str(tmp_path))
    assert said["layers"]["on"] == ["engine", "kits", "picture", "sound", "vfx"]
    assert said["layers"]["because"]["engine"] == "a project.godot"
    assert "geometry" in said["layers"]["left_off"]
    assert '[layers]\non = ["engine", "kits", "picture", "sound", "vfx"]' in said[
        "proposed"]


def test_the_proposal_written_is_a_file_the_project_runs_on(tmp_path):
    _tree(tmp_path, {"project.godot": "", "box.toml": '[[nodes]]\nop = "box"\n'})
    init(str(tmp_path), write=True)
    assert sorted(on(tmp_path)) == ["engine", "geometry", "kits"]
    C.load(tmp_path)  # every table it wrote belongs to a layer it turned on


def test_a_tree_that_shows_nothing_turns_no_layer_off(tmp_path):
    said = init(str(tmp_path))
    assert "layers" not in said and "[layers]" not in said["proposed"]


def test_a_merge_into_a_file_a_project_runs_on_adds_no_switch(tmp_path):
    _tree(tmp_path, {"project.godot": "", C.FILENAME: '[project]\nname = "x"\n'})
    said = init(str(tmp_path), write=True, merge=True)
    assert "layers" not in said["tables"]
    assert on(tmp_path) == frozenset(layers())
