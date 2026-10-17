"""The game booted and shut down, read (§PW469)."""

from __future__ import annotations

import subprocess

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import engine, testing

CLEAN = "Godot Engine v4.7.1.stable.official\n\n"
MUSIC = (CLEAN + "WARNING: 4 ObjectDB instances were leaked at exit\n"
         "     at: cleanup (core/object/object.cpp:2560)\n"
         "ERROR: 2 resources still in use at exit\n")


@pytest.fixture
def game(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text("[application]\n", encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(engine, "find", lambda root: "godot")
    said = {"output": CLEAN, "code": 0, "argv": None}

    def launch(argv, **how):
        said["argv"] = argv
        return said["output"], said["code"]

    monkeypatch.setattr(engine, "_launch", launch)
    return tmp_path, said


def test_a_clean_boot_is_clean_whatever_godot_returned(game):
    root, said = game
    said["code"] = 1
    found = testing.boot(str(root))
    assert found["clean"] is True and found["exit_code"] == 1
    assert said["argv"][1:4] == ["--headless", "--quit", "--path"]


def test_a_script_error_or_a_missing_main_scene_fails_it(game):
    root, said = game
    said["output"] = CLEAN + "SCRIPT ERROR: Parse Error: bad token\n"
    assert testing.boot(str(root))["clean"] is False
    said["output"] = CLEAN + "ERROR: Can't run project: no main scene defined.\n"
    found = testing.boot(str(root))
    assert found["clean"] is False and "no main scene" in found["says"]


def test_a_leak_fails_unless_the_project_forgives_exactly_it(game):
    root, said = game
    said["output"] = MUSIC
    found = testing.boot(str(root))
    assert found["clean"] is False and found["leaked"] == [4, 2]
    (root / "polyweave.toml").write_text("[engine]\nleaks = [4, 2]\n", "utf-8")
    assert testing.boot(str(root))["clean"] is True
    said["output"] = MUSIC.replace("4 ObjectDB", "5 ObjectDB")
    assert testing.boot(str(root))["clean"] is False


def test_anything_else_the_game_printed_fails_it_and_is_named(game):
    root, said = game
    said["output"] = CLEAN + "the save file was written twice\n"
    found = testing.boot(str(root))
    assert found["clean"] is False
    assert found["said"] == ["the save file was written twice"]


def test_a_boot_that_never_ends_is_said_so(game, monkeypatch):
    root, _ = game

    def hangs(argv, **how):
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(engine, "_launch", hangs)
    found = testing.boot(str(root))
    assert found["clean"] is False and "did not shut down" in found["says"]


def test_a_folder_with_no_game_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        testing.boot(str(tmp_path))
    assert refused.value.code == "engine.no-project"
