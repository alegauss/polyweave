"""A game's data tables held to a row's schema, and the kit that loads them (§PW364).

Holding the rows to the schema runs anywhere; loading them typed and reading a changed
file again needs $GODOT.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from polyweave import kits, tables
from polyweave.errors import PolyweaveError

SCHEMA = """[enemies]
file = "data/enemies.{suffix}"
key = "id"

[enemies.columns]
id = {{ type = "string", required = true }}
hp = {{ type = "int", required = true, min = 1 }}
speed = {{ type = "float" }}
kind = {{ type = "string", choices = ["walker", "flyer"] }}
"""


def project(tmp_path, body, suffix="csv"):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "tables.toml").write_text(SCHEMA.format(suffix=suffix),
                                                   encoding="utf-8")
    (tmp_path / "data" / f"enemies.{suffix}").write_text(body, encoding="utf-8")
    return str(tmp_path)


def said(found):
    return [(f["row"], f["column"], f["said"]) for f in found["findings"]
            if f["file"].startswith("data/")]


def test_a_table_as_declared_is_clean_once_its_script_is_written(tmp_path):
    root = project(tmp_path, "id,hp,speed,kind\ngrunt,3,1.5,walker\n")
    first = tables.check(root)
    assert [f["said"] for f in first["findings"]][0].startswith(
        "the enemies script does not match")
    assert tables.check(root, write=True)["wrote"] == ["tables/enemies.gd"]
    assert tables.check(root)["clean"] is True


def test_each_wrong_row_is_named_by_its_line_and_column(tmp_path):
    root = project(tmp_path, "id,hp,speed,kind,armour\n"
                   "grunt,ten,1.5,walker,2\n"
                   "wasp,0,fast,swimmer,\n"
                   ",3,1,walker,\n"
                   "grunt,4,1,flyer,\n")
    found = said(tables.check(root, write=True))
    assert (2, "armour", "armour is no column [enemies] declares") in found
    assert (2, "hp", "'ten' is no int") in found
    assert (3, "hp", "0 is under its least, 1") in found
    assert (3, "speed", "'fast' is no float") in found
    assert (3, "kind", "'swimmer' is none of ['walker', 'flyer']") in found
    assert (4, "id", "id is required and missing") in found
    assert (5, "id", "'grunt' is the key of row 2 too") in found


def test_a_number_typed_as_a_string_in_json_is_found(tmp_path):
    root = project(tmp_path, json.dumps([{"id": "grunt", "hp": "10", "speed": 1}]),
                   suffix="json")
    [(row, column, words)] = said(tables.check(root, write=True))
    assert (row, column) == (1, "hp")
    assert words == "'10' is a str, not the int declared"


def test_a_project_with_no_schema_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        tables.check(str(tmp_path))
    assert caught.value.code == "tables.no-schema"


def test_the_fixtures_generated_script_matches_its_schema():
    fixture = kits.KITS / "tables" / "fixture"
    rows = tables.check_table("enemies", tables.schema(fixture)["enemies"], fixture)
    assert rows == []
    written = (fixture / "tables" / "enemies.gd").read_text(encoding="utf-8")
    assert written == tables.generated("enemies", tables.schema(fixture)["enemies"])


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "tables" / "fixture", game)
    return game, kits.install("tables", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_tables_kit_loads_typed_rows_and_reads_a_changed_file_again(tmp_path):
    _, said_ = _installed(tmp_path)
    assert said_["proved"]["passed"] is True, said_["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("before", "after", "words"), [
    ('\t\t"int":\n\t\t\treturn int(value)\n', '\t\t"int":\n\t\t\treturn str(value)\n',
     "enemies row 1 hp reads 3 (String), not a int"),
    ("\tif not OS.is_debug_build():\n\t\treturn\n", "\treturn\n",
     "changed on disk and the game did not read it again"),
])
def test_a_broken_loader_fails_the_proof_by_name(tmp_path, before, after, words):
    game, _ = _installed(tmp_path)
    broken = game / "addons" / "polyweave" / "tables" / "tables.gd"
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["tables"], kits.every(), game)
    assert found["status"] == "failed"
    assert words in found["said"]
