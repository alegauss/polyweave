"""A capture that knows what the game loaded (§PW118)."""

from __future__ import annotations

import json
from pathlib import Path

from polyweave import capture
from test_capture import SHOT, project, taking

LOG = (
    "environment: locale=pt_BR\n"
    "Loading resource: res://art/star_dim.png\n"
    "loaded: res://art/star_gold.png\n"
    "Loading resource: res://art/star_dim.png\n"
    "loaded: res://art/gone.png\n"
    "captured: res://shot.png 24 x 24\n"
)


def setup(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    (tmp_path / "art").mkdir()
    for name in ("star_dim", "star_gold"):
        (tmp_path / "art" / f"{name}.png").write_bytes(name.encode())
    shot = tmp_path / "shot.png"
    return script, shot


def take(tmp_path, script, shot, picture: bytes):
    shot.write_bytes(picture)
    return capture.run(
        script,
        expect=SHOT,
        root=tmp_path,
        take=taking(LOG, artefacts=(shot,)),
    )


def test_the_log_says_what_the_game_opened():
    assert capture.loaded(LOG) == [
        "res://art/gone.png",
        "res://art/star_dim.png",
        "res://art/star_gold.png",
    ]


def test_the_record_hashes_the_script_and_every_file_loaded(tmp_path):
    script, shot = setup(tmp_path)
    found = take(tmp_path, script, shot, b"one")
    record = json.loads(Path(found["records"][0]).read_text(encoding="utf-8"))
    assert [(i["role"], i["path"]) for i in record["inputs"]] == [
        ("script", "shot.gd"),
        ("loaded", "art/star_dim.png"),
        ("loaded", "art/star_gold.png"),
    ]
    assert found["unread"] == ["res://art/gone.png"]


def test_a_picture_that_moved_because_a_sprite_did_names_the_sprite(tmp_path):
    script, shot = setup(tmp_path)
    take(tmp_path, script, shot, b"one")
    (tmp_path / "art" / "star_dim.png").write_bytes(b"a brighter star")
    found = take(tmp_path, script, shot, b"two")
    (verdict,) = found["reproduced"]["artefacts"]
    assert verdict["verdict"] == "different-work"
    assert verdict["moved"] == ["art/star_dim.png"]
    assert "art/star_dim.png changed since" in verdict["why"]
    assert found["reproduced"]["holds"] is True


def test_with_every_input_unchanged_it_still_blames_what_is_undeclared(tmp_path):
    script, shot = setup(tmp_path)
    take(tmp_path, script, shot, b"one")
    found = take(tmp_path, script, shot, b"two")
    (verdict,) = found["reproduced"]["artefacts"]
    assert verdict["verdict"] == "differs"
    assert "not declared" in verdict["why"]
