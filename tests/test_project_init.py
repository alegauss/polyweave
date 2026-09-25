"""A project's config proposed from its own tree (§PW218)."""

from __future__ import annotations

import tomllib

import pytest

from polyweave import config as C
from polyweave import project
from polyweave.cli import command_line
from polyweave.commands import answer_for
from polyweave.errors import PolyweaveError


@pytest.fixture
def tree(tmp_path, monkeypatch):
    for variable in ("GODOT", "MESHY_API_KEY", "IDEOGRAM_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    (tmp_path / "project.godot").write_text(
        '[application]\n\nconfig/name="Starship"\n', encoding="utf-8"
    )
    (tmp_path / "assets" / "models").mkdir(parents=True)
    (tmp_path / "docs" / "art").mkdir(parents=True)
    (tmp_path / "docs" / "art" / "mote.accept.toml").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "design" / "canon").mkdir(parents=True)
    (tmp_path / "i18n").mkdir()
    (tmp_path / "i18n" / "strings.csv").write_text("keys,en\n", encoding="utf-8")
    (tmp_path / "i18n" / "strings.csv.import").write_text(
        '[remap]\n\nimporter="csv_translation"\n', encoding="utf-8"
    )
    return tmp_path


def test_the_proposal_is_read_off_the_tree_and_nothing_is_written(tree):
    found = project.init(str(tree))
    stated = tomllib.loads(found["proposed"])
    assert stated["project"]["name"] == "Starship"
    assert stated["paths"]["meshes"] == "assets/models"
    assert stated["paths"]["specs"] == "docs/art"
    assert stated["paths"]["renders"] == "docs/renders"  # the default: none exists
    assert stated["style"] == {"canon": "docs/design/canon"}
    assert stated["words"] == {"table": "i18n/strings.csv"}
    assert "service" not in stated and "godot" not in stated["paths"]
    assert found["wrote"] is False and not (tree / C.FILENAME).exists()


def test_a_budget_is_never_proposed_and_is_named_as_a_person_s(tree):
    found = project.init(str(tree), write=True)
    assert "budget" not in tomllib.loads((tree / C.FILENAME).read_text("utf-8"))
    assert found["missing"][0]["table"] == "budget"
    assert found["missing"][0]["who"].startswith("a person")


def test_a_written_proposal_is_one_the_loader_accepts(tree):
    project.init(str(tree), write=True)
    loaded = C.load(tree)
    assert loaded.get("words.table") == "i18n/strings.csv"


def test_only_a_key_already_set_proposes_a_service_and_godot_is_a_reference(
    tree, monkeypatch
):
    monkeypatch.setenv("IDEOGRAM_API_KEY", "sk")
    monkeypatch.setenv("GODOT", "C:/godot/godot.exe")
    stated = tomllib.loads(project.init(str(tree))["proposed"])
    assert stated["service"] == {
        "base": "https://api.ideogram.ai",
        "key_env": "IDEOGRAM_API_KEY",
    }
    assert stated["paths"]["godot"] == "${GODOT}"


def test_two_keys_propose_two_named_services(tree, monkeypatch):
    monkeypatch.setenv("IDEOGRAM_API_KEY", "sk")
    monkeypatch.setenv("MESHY_API_KEY", "msy")
    stated = tomllib.loads(project.init(str(tree))["proposed"])
    assert sorted(stated["service"]) == ["ideogram", "meshy"]


def test_an_existing_file_is_refused_unless_merged(tree):
    (tree / C.FILENAME).write_text('[project]\nname = "Mine"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        project.init(str(tree), write=True)
    assert refused.value.code == "config.exists"
    merged = project.init(str(tree), write=True, merge=True)
    assert "project" not in merged["tables"] and "words" in merged["tables"]
    written = tomllib.loads((tree / C.FILENAME).read_text("utf-8"))
    assert written["project"]["name"] == "Mine"
    assert written["words"]["table"] == "i18n/strings.csv"


def test_a_file_that_already_has_a_budget_is_not_told_it_lacks_one(tree):
    (tree / C.FILENAME).write_text(
        '[budget]\ncredits = 10\nexpires = "2099-12-31"\n', encoding="utf-8"
    )
    assert project.init(str(tree), merge=True)["missing"] == []


def test_init_is_a_verb_on_the_command_line(tree):
    stated = command_line().parse_args(["init", "--root", str(tree), "--write"])
    assert answer_for(stated)["wrote"] is True
    assert (tree / C.FILENAME).is_file()
