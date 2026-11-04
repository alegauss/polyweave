"""A game's level files held to the project's own schema and its world (§PW203)."""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import level_schema

SCHEMA = {
    "type": "object",
    "required": ["stage"],
    "additionalProperties": False,
    "properties": {
        "line": {"type": "object"},
        "stage": {"type": "array", "minItems": 1, "items": {
            "type": "object", "properties": {"wave": {"type": "array", "items": {
                "type": "object", "required": ["time_limit"],
                "properties": {
                    "time_limit": {"type": "number", "minimum": 1},
                    "group": {"type": "array", "items": {
                        "type": "object", "required": ["enemy", "count"],
                        "properties": {
                            "enemy": {"type": "string", "x-entity": True},
                            "count": {"type": "integer", "minimum": 1, "maximum": 40},
                            "side": {"enum": ["left", "right"]},
                        }}},
                }}}}}},
    },
}

WAVES = """
[line]
speed = 24.0

[[stage]]
[[stage.wave]]
time_limit = 12.0
[[stage.wave.group]]
enemy = "drone"
count = 10
"""

WORLD = ('[entity.drone]\nname = "Drone"\nkind = "enemy"\n\n'
         '[entity.lancer]\nname = "Lancer"\nkind = "enemy"\n')


def _project(tmp_path, waves=WAVES, schema=SCHEMA, world=True):
    (tmp_path / "polyweave.toml").write_text(
        '[levels]\nschema = "data/level.schema.json"\n'
        'files = ["waves/*.waves.toml"]\n', encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "level.schema.json").write_text(json.dumps(schema),
                                                         encoding="utf-8")
    (tmp_path / "waves").mkdir()
    (tmp_path / "waves" / "one.waves.toml").write_text(waves, encoding="utf-8")
    if world:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "game.world.toml").write_text(WORLD, encoding="utf-8")
    return tmp_path


def test_a_level_that_holds_its_schema_and_world_passes(tmp_path):
    said = level_schema.validate(root=str(_project(tmp_path)))
    assert said["ok"] is True and said["files"] == 1 and said["findings"] == []


def test_each_place_a_level_breaks_its_schema_is_named(tmp_path):
    waves = WAVES.replace('enemy = "drone"', 'enemy = "lancr"\nside = "up"') \
        .replace("count = 10", "count = 0") \
        .replace("time_limit = 12.0", 'time_limit = "long"')
    waves = "bonus = 1\n" + waves  # at the top, before any table opens
    said = level_schema.validate(root=str(_project(tmp_path, waves)))
    found = {(one["at"], one["said"]) for one in said["findings"]}
    assert ("stage[0].wave[0].time_limit", '"long" is no number') in found
    assert ("stage[0].wave[0].group[0].count", "0 is under its least, 1") in found
    assert ("stage[0].wave[0].group[0].enemy",
            "'lancr' is no entity the world declares; did you mean 'lancer'?") in found
    assert ("stage[0].wave[0].group[0].side",
            "'up' is none of ['left', 'right']") in found
    assert ("bonus", "bonus is no key the schema declares") in found
    assert all(one["file"] == "waves/one.waves.toml" for one in said["findings"])
    assert said["ok"] is False


def test_a_required_key_missing_is_said_where_it_was_wanted(tmp_path):
    waves = WAVES.replace("count = 10\n", "")
    said = level_schema.validate(root=str(_project(tmp_path, waves)))
    assert said["findings"] == [{"file": "waves/one.waves.toml",
                                 "at": "stage[0].wave[0].group[0]",
                                 "said": "count is required and missing"}]


@pytest.mark.parametrize("schema", [
    {"type": "object", "oneOf": []},
    {"type": "object", "properties": {"a": {"$ref": "#/x"}}},
    {"type": "tuple"},
    {"additionalProperties": {"type": "string"}},
])
def test_a_schema_this_cannot_read_whole_is_refused(tmp_path, schema):
    with pytest.raises(PolyweaveError) as refused:
        level_schema.validate(root=str(_project(tmp_path, schema=schema)))
    assert refused.value.code == "level.no-schema"


def test_no_schema_or_no_level_is_refused(tmp_path):
    root = _project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        level_schema.validate("waves/none.waves.toml", root=str(root))
    assert refused.value.code == "level.no-level"
    (root / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        level_schema.validate(root=str(root))
    assert refused.value.code == "level.no-schema"


#: A compiler of the project's own: the TOML source to the JSON the game loads.
COMPILER = """import json, sys, tomllib
from pathlib import Path
source, out = sys.argv[1], sys.argv[2]
data = tomllib.loads(Path(source).read_text(encoding="utf-8"))
if data.get("line", {}).get("speed") == 0:
    sys.exit("speed 0 is no level")
Path(out).write_text(json.dumps(data), encoding="utf-8")
"""


def _compiling(tmp_path):
    root = _project(tmp_path)
    (root / "tools").mkdir()
    (root / "tools" / "compile_level.py").write_text(COMPILER, encoding="utf-8")
    with (root / "polyweave.toml").open("a", encoding="utf-8") as table:
        table.write('compile = ["python", "tools/compile_level.py", "{source}", '
                    '"{out}"]\nout = "{dir}/{stem}.json"\n')
    return root


def test_a_source_compiles_to_the_file_the_game_loads_and_is_recorded(tmp_path):
    import sys

    from polyweave.kernel import provenance

    root = _compiling(tmp_path)
    text = (root / "polyweave.toml").read_text(encoding="utf-8")
    (root / "polyweave.toml").write_text(text.replace('"python"',
                                                      json.dumps(sys.executable)),
                                         encoding="utf-8")
    made = level_schema.compile_level("waves/one.waves.toml", root=str(root))
    assert made["compiled"] == "waves/one.waves.json"
    loaded = json.loads((root / "waves" / "one.waves.json").read_text("utf-8"))
    assert loaded["stage"][0]["wave"][0]["group"][0]["enemy"] == "drone"
    record = provenance.read("waves/one.waves.json", root=str(root))
    assert record["kind"] == "level"
    assert {one["role"]: one["path"] for one in record["inputs"]} == {
        "level": "waves/one.waves.toml", "schema": "data/level.schema.json",
        "compiler": "tools/compile_level.py"}


def test_an_invalid_source_or_a_failing_command_is_refused(tmp_path):
    import sys

    root = _compiling(tmp_path)
    text = (root / "polyweave.toml").read_text(encoding="utf-8")
    (root / "polyweave.toml").write_text(text.replace('"python"',
                                                      json.dumps(sys.executable)),
                                         encoding="utf-8")
    source = root / "waves" / "one.waves.toml"
    source.write_text(WAVES.replace("count = 10", "count = 0"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        level_schema.compile_level("waves/one.waves.toml", root=str(root))
    assert refused.value.code == "level.invalid"
    assert "group[0].count" in refused.value.message
    source.write_text(WAVES.replace("speed = 24.0", "speed = 0"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        level_schema.compile_level("waves/one.waves.toml", root=str(root))
    assert refused.value.code == "level.compile-failed"
    assert not (root / "waves" / "one.waves.json").exists()


def test_with_no_command_the_source_is_what_the_game_loads(tmp_path):
    from polyweave.kernel import provenance

    root = _project(tmp_path)
    made = level_schema.compile_level("waves/one.waves.toml", root=str(root))
    assert made["compiled"] == "waves/one.waves.toml"
    record = provenance.read("waves/one.waves.toml", root=str(root))
    assert [one["role"] for one in record["inputs"]] == ["schema"]


def test_each_field_says_what_a_game_s_editor_needs_of_it(tmp_path):
    from polyweave.kernel import provenance

    schema = json.loads(json.dumps(SCHEMA))
    group = schema["properties"]["stage"]["items"]["properties"]["wave"]["items"][
        "properties"]["group"]["items"]["properties"]
    group["count"].update({"x-step": 1, "x-unit": "enemies", "default": 6,
                           "description": "how many fly in"})
    root = _project(tmp_path, schema=schema)
    said = level_schema.fields(out="tools/fields.json", root=str(root))
    by = {one["path"]: one for one in said["fields"]}
    assert by["stage[].wave[].group[].count"] == {
        "path": "stage[].wave[].group[].count", "required": True, "type": "integer",
        "min": 1, "max": 40, "step": 1, "unit": "enemies", "default": 6,
        "help": "how many fly in", "help_key": "LEVEL_STAGE_WAVE_GROUP_COUNT_HELP"}
    assert by["stage[].wave[].group[].enemy"]["entity"] is True
    assert by["stage[].wave[].group[].side"]["choices"] == ["left", "right"]
    assert by["stage"]["required"] is True and by["line"]["required"] is False
    assert list(by)[:3] == ["line", "stage", "stage[]"]
    written = json.loads((root / "tools" / "fields.json").read_text("utf-8"))
    assert written["fields"] == said["fields"]
    record = provenance.read("tools/fields.json", root=str(root))
    assert record["kind"] == "level"


def test_each_help_goes_to_the_string_table_by_its_key_untranslated(tmp_path):
    """§PW683: the editor's help read in the schema's language in every locale."""
    import csv

    schema = json.loads(json.dumps(SCHEMA))
    group = schema["properties"]["stage"]["items"]["properties"]["wave"]["items"][
        "properties"]["group"]["items"]["properties"]
    group["count"]["description"] = "how many fly in"
    group["enemy"]["description"] = "which enemy, by the world's name"
    root = _project(tmp_path, schema=schema)
    with (root / "polyweave.toml").open("a", encoding="utf-8") as table:
        table.write('\n[words]\ntable = "strings.csv"\n')
    (root / "strings.csv").write_text(
        "keys,en,pt_BR\nLEVEL_STAGE_WAVE_GROUP_ENEMY_HELP,which foe,qual inimigo\n",
        encoding="utf-8")
    said = level_schema.fields(strings=True, root=str(root))
    by = {one["path"]: one for one in said["fields"]}
    assert by["stage[].wave[].group[].count"]["help_key"] == (
        "LEVEL_STAGE_WAVE_GROUP_COUNT_HELP")
    assert said["strings"]["added"] == ["LEVEL_STAGE_WAVE_GROUP_COUNT_HELP"]
    (changed,) = said["strings"]["changed"]
    assert changed["key"] == "LEVEL_STAGE_WAVE_GROUP_ENEMY_HELP"
    assert changed["stale"] == ["pt_BR"]
    rows = list(csv.reader((root / "strings.csv").read_text("utf-8").splitlines()))
    assert rows[-1] == ["LEVEL_STAGE_WAVE_GROUP_COUNT_HELP", "how many fly in", ""]
    assert rows[1][1] == "which foe", "a changed help is named, never rewritten"
    again = level_schema.fields(strings=True, root=str(root))
    assert again["strings"]["added"] == []


def test_the_reader_has_a_typed_class_for_each_object(tmp_path):
    root = _project(tmp_path)
    made = level_schema.reader("levels/level_reader.gd", root=str(root))
    text = (root / "levels" / "level_reader.gd").read_text(encoding="utf-8")
    assert made["written"] is True
    for name in ("class _Level:", "class _Stage:", "class _StageWave:",
                 "class _StageWaveGroup:", "\tvar count: int",
                 "\tvar time_limit: float",
                 "static func read(data: Dictionary) -> Dictionary:"):
        assert name in text
    again = level_schema.reader("levels/level_reader.gd", root=str(root))
    assert again["written"] is False


READS = """extends SceneTree

func _initialize() -> void:
\tvar reader = load("res://levels/level_reader.gd")
\tvar good: Dictionary = JSON.parse_string(%s)
\tvar read: Dictionary = reader.read(good)
\tprint("good: %%d %%d %%s" %% [read["errors"].size(),
\t\tread["level"].stage[0].wave[0].group[0].count,
\t\tread["level"].stage[0].wave[0].group[0].enemy])
\tvar bad: Dictionary = JSON.parse_string(%s)
\tprint("bad: " + " | ".join(reader.read(bad)["errors"]))
\tquit()
"""


def test_godot_reads_a_level_through_the_generated_reader(tmp_path):
    import os

    from polyweave.layers.engine import engine

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = _project(tmp_path)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    level_schema.reader("levels/level_reader.gd", root=str(root))
    good = {"stage": [{"wave": [{"time_limit": 12.0,
                                 "group": [{"enemy": "drone", "count": 10}]}]}]}
    bad = {"stage": [{"wave": [{"time_limit": "long",
                                "group": [{"count": 0, "side": "up"}]}]}],
           "bonus": 1}
    (root / "reads.gd").write_text(READS % (json.dumps(json.dumps(good)),
                                            json.dumps(json.dumps(bad))),
                                   encoding="utf-8")
    ran = engine.run("reads.gd", root=root, headless=True, expect=r"^bad: ")
    assert ran["ok"] is True, ran["why"]
    log = (root / ".polyweave" / "engine" / "reads.log").read_text("utf-8")
    assert "good: 0 10 drone" in log
    said = log.split("bad: ", 1)[1].splitlines()[0]
    for place in ("bonus is no key the schema declares",
                  "stage[0].wave[0].time_limit is no number",
                  "stage[0].wave[0].group[0].enemy is required and missing",
                  "stage[0].wave[0].group[0].count is past its least, 1",
                  "stage[0].wave[0].group[0].side is none of its choices"):
        assert place in said, said


def test_a_json_level_is_read_as_json(tmp_path):
    root = _project(tmp_path)
    (root / "waves" / "one.waves.toml").unlink()
    (root / "polyweave.toml").write_text(
        '[levels]\nschema = "data/level.schema.json"\nfiles = ["waves/*.json"]\n',
        encoding="utf-8")
    (root / "waves" / "two.json").write_text(json.dumps({"stage": []}),
                                             encoding="utf-8")
    said = level_schema.validate(root=str(root))
    assert said["findings"] == [{"file": "waves/two.json", "at": "stage",
                                 "said": "0 item(s), under its least, 1"}]
