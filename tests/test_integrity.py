"""A Godot project's references and scripts held to its files (§PW358).

Each project is written here as text, the way an agent writes one with no editor open,
so the static half runs anywhere; the parse half runs where $GODOT is set.
"""

from __future__ import annotations

import os

import pytest

from polyweave import integrity, project
from polyweave.errors import PolyweaveError

SCENE = (
    '[gd_scene load_steps=2 format=3 uid="uid://cmain"]\n\n'
    '[ext_resource type="Script" uid="uid://bplayer" path="{path}" id="1"]\n\n'
    '[node name="Main" type="Node2D"]\nscript = ExtResource("1")\n'
)


def game(tmp_path, **files):
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\n\nrun/main_scene="res://main.tscn"\n\n'
        '[autoload]\n\nMusic="*res://music.gd"\n', encoding="utf-8")
    (tmp_path / "music.gd").write_text("extends Node\n", encoding="utf-8")
    (tmp_path / "player.gd").write_text("extends Node2D\n", encoding="utf-8")
    (tmp_path / "player.gd.uid").write_text("uid://bplayer\n", encoding="utf-8")
    (tmp_path / "main.tscn").write_text(SCENE.format(path="res://player.gd"),
                                        encoding="utf-8")
    for name, text in files.items():
        where = tmp_path / name.replace("__", "/")
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text, encoding="utf-8")
    return tmp_path


def codes(found):
    return sorted(one["code"] for one in found["findings"])


def test_a_project_whose_references_all_resolve_is_clean(tmp_path):
    found = integrity.check(str(game(tmp_path)), parse=False)
    assert found["clean"] is True
    assert found["findings"] == []
    assert found["parsed"] is None


def test_a_file_moved_with_its_uid_is_repointed_by_fix(tmp_path):
    here = game(tmp_path)
    (here / "actors").mkdir()
    (here / "player.gd").rename(here / "actors" / "player.gd")
    (here / "player.gd.uid").rename(here / "actors" / "player.gd.uid")
    found = integrity.check(str(here), parse=False)
    [moved] = found["findings"]
    assert moved["code"] == "engine.moved-reference"
    assert (moved["file"], moved["line"]) == ("res://main.tscn", 3)
    assert found["clean"] is True
    fixed = integrity.check(str(here), parse=False, fix=True)
    assert fixed["findings"] == []
    assert fixed["fixed"] == ["res://main.tscn:3 now points at res://actors/player.gd"]
    assert 'path="res://actors/player.gd"' in (here / "main.tscn").read_text()


def test_a_file_moved_without_its_uid_resolves_to_nothing(tmp_path):
    here = game(tmp_path)
    (here / "actors").mkdir()
    (here / "player.gd").rename(here / "actors" / "player.gd")
    found = integrity.check(str(here), parse=False)
    assert codes(found) == ["engine.broken-reference", "engine.orphan-uid"]
    assert found["clean"] is False
    broken = next(f for f in found["findings"] if f["severity"] == "error")
    assert broken["said"].startswith("uid://bplayer resolves to nothing")
    integrity.check(str(here), parse=False, fix=True)
    assert not (here / "player.gd.uid").exists()


def test_a_uid_nothing_declares_falls_back_to_its_path(tmp_path):
    here = game(tmp_path)
    (here / "player.gd.uid").unlink()
    [stale] = integrity.check(str(here), parse=False)["findings"]
    assert stale["code"] == "engine.stale-uid"


def test_project_godot_and_an_import_are_held_to_their_files(tmp_path):
    here = game(tmp_path, **{"art__gone.png.import":
                             '[remap]\n\nuid="uid://cgone"\n\n[deps]\n\n'
                             'source_file="res://art/gone.png"\n'})
    (here / "music.gd").unlink()
    found = integrity.check(str(here), parse=False)
    assert codes(found) == ["engine.broken-reference", "engine.orphan-import"]
    assert any(f["file"] == "res://project.godot" for f in found["findings"])


def test_a_script_path_is_a_warning_and_a_prefix_or_pattern_is_none(tmp_path):
    here = game(tmp_path, **{
        "loader.gd": 'extends Node\nconst A := "res://levels/one.tres"\n'
                     'var b := "res://levels/" + "two"\n'
                     'var c := "res://x/[0-9]+"\n'
                     'func f(p): return p.begins_with("res://fx/traffic_")\n'
                     '# "res://commented.tres"\n',
        "addons__kit__k.gd": 'const P := "res://polyweave_kit.gd"\n',
    })
    [missing] = integrity.check(str(here), parse=False)["findings"]
    assert missing["code"] == "engine.missing-path"
    assert missing["severity"] == "warning"
    assert (missing["file"], missing["line"]) == ("res://loader.gd", 2)


def test_project_check_holds_a_godot_project_to_its_references(tmp_path):
    here = game(tmp_path)
    (here / "player.gd").unlink()
    (here / "player.gd.uid").unlink()
    (here / "polyweave.toml").write_text("", encoding="utf-8")
    found = project.check(str(here))
    assert any(f["code"] == "engine.broken-reference" for f in found["findings"])


def test_a_folder_with_no_project_godot_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        integrity.check(str(tmp_path), parse=False)
    assert caught.value.code == "engine.no-project"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_script_that_does_not_parse_is_named_with_its_line(tmp_path):
    here = game(tmp_path, **{
        "named.gd": "class_name Named\nextends Node\n\nfunc hi() -> int:\n\treturn 1\n",
        "uses.gd": "extends Node\n\nfunc f() -> int:\n\treturn Named.new().hi()\n",
        "broken.gd": "extends Node\n\nfunc broken(:\n\tpass\n",
    })
    found = integrity.check(str(here))
    [error] = found["findings"]
    assert error["code"] == "engine.parse-error"
    assert (error["file"], error["line"]) == ("res://broken.gd", 3)
    assert found["parsed"]["scripts"] == 5
