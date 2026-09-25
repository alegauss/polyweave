"""The text a player reads, held to the world it is set in (§PW197)."""

from __future__ import annotations

import pytest

from polyweave import words
from polyweave.errors import PolyweaveError

WORLD = """\
[entity.lattice]
code = "keepers"
name = "The Lattice"
kind = "faction"

[entity.ada]
name = "Captain Ada"
kind = "character"
faction = "lattice"

[entity.pilot]
name = "Rook Vale"
kind = "character"

[entity.drone]
name = "Drone"
kind = "enemy"

[rules]
longest_line = 30
silent = ["drone"]
unshown = ["pilot"]
"""


def _project(tmp_path, rows, ordinary=()):
    listed = ", ".join(f'"{w}"' for w in ordinary)
    (tmp_path / "polyweave.toml").write_text(
        f'[words]\ntable = "i18n/strings.csv"\nordinary = [{listed}]\n',
        encoding="utf-8",
    )
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    (tmp_path / "i18n").mkdir()
    (tmp_path / "i18n" / "strings.csv").write_text(
        "keys,en,pt_BR,_speaker\n" + "".join(r + "\n" for r in rows),
        encoding="utf-8",
    )


def _found(tmp_path):
    return [
        (f["code"], f["key"], f["locale"], f["rule"])
        for f in words.check(root=str(tmp_path))["findings"]
    ]


def test_text_that_keeps_to_the_world_passes_in_every_locale(tmp_path):
    _project(
        tmp_path,
        [
            "GREET,Hi. Captain Ada waits.,Oi. Captain Ada espera.,ada",
            "TITLE,PRESS START,APERTE START,",
        ],
        ordinary=["PRESS", "APERTE", "START"],
    )
    checked = words.check(root=str(tmp_path))
    assert checked["passed"] is True
    assert checked["locales"] == ["en", "pt_BR"]
    assert checked["rows"] == 2


def test_an_old_name_on_screen_is_reported_with_its_key_and_locale(tmp_path):
    _project(tmp_path, ["HUD,Beware the Syndicate,Cuidado com The Lattice,"])
    assert _found(tmp_path) == [("words.unknown-name", "HUD", "en", "names")]


def test_a_code_name_on_screen_is_reported_and_not_twice(tmp_path):
    _project(tmp_path, ["HUD,The KEEPERS are near,Os Lattice,"])
    assert _found(tmp_path) == [("words.code-name", "HUD", "en", "code_names")]


def test_a_line_longer_than_the_world_allows_is_counted_per_locale(tmp_path):
    _project(tmp_path, ["LONG,Short.,Uma frase bem mais longa do que trinta,"])
    assert _found(tmp_path) == [("words.too-long", "LONG", "pt_BR", "longest_line")]


def test_an_escaped_newline_breaks_a_line_before_it_is_measured(tmp_path):
    _project(tmp_path, [r"LONG,Twenty characters\nand twenty more here,Curta.,"])
    assert _found(tmp_path) == []


def test_a_silent_speaker_and_an_unknown_one_are_both_reported(tmp_path):
    _project(tmp_path, ["BEEP,Beep.,Bip.,drone", "HI,Hello.,Oi.,bob"])
    assert _found(tmp_path) == [
        ("words.silent-speaks", "BEEP", None, "silent"),
        ("words.unknown-speaker", "HI", None, "speaker"),
    ]


def test_a_name_the_world_keeps_unshown_is_reported_even_in_part(tmp_path):
    _project(tmp_path, ["PILOT,Rook is here.,O piloto chegou.,"])
    assert _found(tmp_path) == [("words.hidden-name", "PILOT", "en", "unshown")]


def test_placeholders_and_markup_are_not_read_as_names(tmp_path):
    _project(tmp_path, ["HP,You have {Health} [b]left[/b].,Resta {Health}.,"])
    assert _found(tmp_path) == []


def test_a_project_with_no_table_is_told_to_make_one(tmp_path):
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        words.check(root=str(tmp_path))
    assert refused.value.code == "words.no-table"


def test_scene_literals_not_in_the_table_are_counted(tmp_path):
    _project(tmp_path, ["GREET,Welcome.,Bem-vindo.,"])
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "hud.tscn").write_text(
        '[gd_scene format=3]\n\n[node name="HUD" type="Control"]\n\n'
        '[node name="Title" type="Label" parent="."]\ntext = "KEEPERS"\n\n'
        '[node name="Greeting" type="Label" parent="."]\ntext = "GREET"\n\n'
        '[node name="Empty" type="Label" parent="."]\ntext = ""\n',
        encoding="utf-8",
    )
    found = words.unlisted(root=str(tmp_path))
    assert found["scenes"] == 1
    assert found["count"] == 1
    assert found["literals"] == [
        {"scene": "ui/hud.tscn", "line": 6, "node": "Title", "text": "KEEPERS"}
    ]
