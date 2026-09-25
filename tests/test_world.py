"""A game's world as a declaration beside its prose (§PW196)."""

from __future__ import annotations

import pytest

from polyweave import world
from polyweave.commands import answer_for
from polyweave.errors import PolyweaveError

GOOD = """\
[entity.crew]
name = "The Crew"
kind = "faction"

[entity.ada]
code = "ada"
name = "Captain Ada"
kind = "character"
faction = "crew"
style = "portrait"
first = "act 1"

[entity.drone]
name = "Drone"
kind = "enemy"

[rules]
longest_line = 80
silent = ["drone"]
unshown = []
"""


def _project(tmp_path, text=GOOD, styles=("portrait",)):
    tables = "".join(f"[style.{s}]\n" for s in styles)
    (tmp_path / "polyweave.toml").write_text(tables, encoding="utf-8")
    where = tmp_path / "docs" / "starship.world.toml"
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(text, encoding="utf-8")
    return where


def _codes(found):
    return [(f["code"], f["line"]) for f in found["findings"]]


def test_a_sound_world_reads_back_with_its_rules(tmp_path):
    _project(tmp_path)
    read = world.read(root=str(tmp_path))
    assert read["world"] == "docs/starship.world.toml"
    assert read["entities"]["ada"]["faction"] == "crew"
    assert read["entities"]["drone"]["code"] == "drone"  # the id where unset
    assert read["rules"]["longest_line"] == 80
    assert world.validate(root=str(tmp_path))["valid"] is True


def test_one_entity_is_one_read_and_a_misspelled_one_is_named(tmp_path):
    _project(tmp_path)
    assert world.read("ada", root=str(tmp_path))["entity"]["name"] == "Captain Ada"
    with pytest.raises(PolyweaveError) as refused:
        world.read("adda", root=str(tmp_path))
    assert refused.value.code == "world.unknown-entity"
    assert "'ada'" in refused.value.remedy


def test_a_name_two_entities_share_is_reported_on_its_line(tmp_path):
    text = GOOD + '\n[entity.ada2]\nname = "captain ada"\nkind = "character"\n'
    _project(tmp_path, text)
    found = world.validate(root=str(tmp_path))
    assert found["valid"] is False
    assert _codes(found) == [("world.duplicate-name", 23)]
    assert found["findings"][0]["at"] == "starship.world.toml:23"


def test_a_faction_nobody_declared_and_a_character_as_one_are_both_reported(tmp_path):
    text = GOOD.replace('faction = "crew"', 'faction = "crw"') + (
        '\n[entity.bob]\nname = "Bob"\nkind = "character"\nfaction = "ada"\n'
    )
    _project(tmp_path, text)
    found = world.validate(root=str(tmp_path))
    assert _codes(found) == [
        ("world.unknown-faction", 9),
        ("world.unknown-faction", 25),
    ]
    assert "did you mean 'crew'" in found["findings"][0]["remedy"]
    assert "a character, not a faction" in found["findings"][1]["message"]


def test_a_style_family_polyweave_toml_lacks_is_reported(tmp_path):
    _project(tmp_path, styles=("scenery",))
    found = world.validate(root=str(tmp_path))
    assert _codes(found) == [("world.unknown-family", 10)]
    assert "[style.portrait]" in found["findings"][0]["remedy"]


def test_a_project_with_no_style_at_all_lacks_every_family(tmp_path):
    _project(tmp_path, styles=())
    assert _codes(world.validate(root=str(tmp_path))) == [("world.unknown-family", 10)]


def test_a_rule_naming_no_entity_is_reported(tmp_path):
    _project(tmp_path, GOOD.replace('silent = ["drone"]', 'silent = ["dron"]'))
    found = world.validate(root=str(tmp_path))
    assert _codes(found) == [("world.unknown-entity", 19)]


def test_faults_of_shape_are_findings_and_read_refuses_them(tmp_path):
    text = GOOD.replace('kind = "enemy"', 'kind = "monster"\nhp = 3') + "[lore]\n"
    _project(tmp_path, text)
    found = world.validate(root=str(tmp_path))
    assert sorted(_codes(found)) == [
        ("world.bad-kind", 15),
        ("world.unknown-key", 16),
        ("world.unknown-key", 22),
    ]
    with pytest.raises(PolyweaveError) as refused:
        world.read(root=str(tmp_path))
    assert refused.value.code == "world.unknown-key"


def test_a_missing_name_and_a_bad_rule_are_findings(tmp_path):
    text = GOOD.replace('name = "Drone"\n', "").replace("= 80", "= 0")
    _project(tmp_path, text)
    assert _codes(world.validate(root=str(tmp_path))) == [
        ("world.missing-field", 13),
        ("world.bad-value", 17),
    ]


def test_a_look_of_the_wrong_shape_is_reported_on_its_own_line(tmp_path):
    text = GOOD.replace(
        '[entity.drone]\nname = "Drone"',
        '[entity.drone]\nname = "Drone"\nlook = { shows = "a red eye", hue = 2 }',
    )
    _project(tmp_path, text)
    assert sorted(_codes(world.validate(root=str(tmp_path)))) == [
        ("world.bad-value", 15),
        ("world.unknown-key", 15),
    ]


def test_the_file_is_found_named_or_refused_among_several(tmp_path):
    _project(tmp_path)
    (tmp_path / "other.world.toml").write_text(GOOD, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        world.read(root=str(tmp_path))
    assert refused.value.code == "world.several"
    named = world.read(world="other.world.toml", root=str(tmp_path))
    assert named["world"] == "other.world.toml"


def test_a_project_with_no_world_is_told_where_one_goes(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        world.validate(root=str(tmp_path))
    assert refused.value.code == "world.none"


def test_broken_toml_is_refused_as_malformed(tmp_path):
    _project(tmp_path, "[entity.ada\n")
    with pytest.raises(PolyweaveError) as refused:
        world.validate(root=str(tmp_path))
    assert refused.value.code == "world.malformed"


def test_both_operations_answer_by_name_on_the_command_line(tmp_path):
    from polyweave.cli import command_line

    _project(tmp_path)
    stated = command_line().parse_args(["world.validate", "--root", str(tmp_path)])
    assert answer_for(stated)["valid"] is True
    stated = command_line().parse_args(
        ["world.read", "--entity", "ada", "--root", str(tmp_path)]
    )
    assert answer_for(stated)["entity"]["kind"] == "character"
