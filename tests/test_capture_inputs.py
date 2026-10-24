"""A capture that knows what the game loaded (§PW118)."""

from __future__ import annotations

import json
from pathlib import Path

from polyweave.layers.engine import capture
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


def test_godot_4s_own_spelling_is_read_and_its_imported_copies_left_out():
    """§PW488: Godot 4 adds where it remapped a load to, and the pattern refused it."""
    log = (
        "Loading resource: res://shot.gd remapped: res://shot.gd\n"
        "Loading resource: res://art/star_dim.png remapped: res://art/star_dim.png\n"
        "Loading resource: res://.godot/imported/star_dim.png-2086.ctex remapped: "
        "res://.godot/imported/star_dim.png-2086.ctex\n"
    )
    assert capture.loaded(log) == ["res://art/star_dim.png", "res://shot.gd"]


def test_a_recorded_capture_asks_the_engine_to_name_what_it_loads(tmp_path):
    script, shot = setup(tmp_path)
    seen = {}
    taken = taking(LOG, artefacts=(shot,))

    def watching(script_, **how):
        seen["args"] = how.get("args")
        return taken(script_, **how)

    shot.write_bytes(b"one")
    capture.run(script, expect=SHOT, root=tmp_path, take=watching)
    assert seen["args"][0] == "--verbose"
    assert seen["args"].index("--verbose") < seen["args"].index("--")


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


def classes(tmp_path):
    """Cottony's shape: the shot builds a board, the board a tray, by class alone."""
    (tmp_path / "scripts").mkdir()
    for name, said in {
        "board3d": "class_name Board3D\nfunc _ready():\n\tTrayMesh.build()\n",
        "tray_mesh": "class_name TrayMesh\nstatic func build():\n\treturn Bevel.new()",
        "bevel": "class_name Bevel\n",
        "unused": "class_name Unused\n",
    }.items():
        (tmp_path / "scripts" / f"{name}.gd").write_text(said, encoding="utf-8")
    shot_gd = tmp_path / "shot.gd"
    shot_gd.write_text(shot_gd.read_text("utf-8") + "\nvar board = Board3D.new()\n",
                       encoding="utf-8")


def test_a_script_reached_by_class_name_alone_is_an_input(tmp_path):
    """§PW622: the log never names a class loaded by its name, never by a path."""
    script, shot = setup(tmp_path)
    classes(tmp_path)
    found = take(tmp_path, script, shot, b"one")
    record = json.loads(Path(found["records"][0]).read_text(encoding="utf-8"))
    assert [i["path"] for i in record["inputs"] if i["role"] == "class"] == [
        "scripts/bevel.gd", "scripts/board3d.gd", "scripts/tray_mesh.gd"]


def test_a_picture_that_moved_because_a_class_did_names_the_class(tmp_path):
    script, shot = setup(tmp_path)
    classes(tmp_path)
    take(tmp_path, script, shot, b"one")
    (tmp_path / "scripts" / "tray_mesh.gd").write_text(
        "class_name TrayMesh\nstatic func build():\n\treturn Bevel.new(2)",
        encoding="utf-8")
    found = take(tmp_path, script, shot, b"two")
    (verdict,) = found["reproduced"]["artefacts"]
    assert verdict["verdict"] == "different-work"
    assert verdict["moved"] == ["scripts/tray_mesh.gd"]


def test_with_every_input_unchanged_it_still_blames_what_is_undeclared(tmp_path):
    script, shot = setup(tmp_path)
    take(tmp_path, script, shot, b"one")
    found = take(tmp_path, script, shot, b"two")
    (verdict,) = found["reproduced"]["artefacts"]
    assert verdict["verdict"] == "differs"
    assert "not declared" in verdict["why"]
