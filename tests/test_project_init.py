"""A project's config proposed from its own tree (§PW218)."""

from __future__ import annotations

import json
import tomllib

import pytest

from polyweave import __version__, project
from polyweave import config as C
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


# -- the project's agent, wired to polyweave (§PW219) --------------------------------


def test_agent_declares_the_server_and_writes_a_marked_section(tree):
    (tree / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"roadkeep": {"command": "rk"}}}), "utf-8"
    )
    (tree / ".claude").mkdir()
    (tree / ".claude" / "settings.json").write_text(
        json.dumps({"enabledMcpjsonServers": ["roadkeep"], "model": "x"}), "utf-8"
    )
    found = project.init(str(tree), write=True, agent=True)["agent"]
    assert found["changed"] == [
        ".mcp.json",
        ".claude/settings.json",
        "AGENTS.md",
        "CLAUDE.md",
    ]
    mcp = json.loads((tree / ".mcp.json").read_text("utf-8"))
    assert mcp["mcpServers"]["roadkeep"] == {"command": "rk"}
    assert mcp["mcpServers"]["polyweave"]["args"] == ["-m", "polyweave", "serve"]
    settings = json.loads((tree / ".claude" / "settings.json").read_text("utf-8"))
    assert settings == {
        "enabledMcpjsonServers": ["roadkeep", "polyweave"],
        "model": "x",
    }
    agents = (tree / "AGENTS.md").read_text("utf-8")
    assert agents.startswith("# Starship\n")
    assert project.BEGIN in agents and project.END in agents
    assert f"polyweave {__version__}" in agents
    assert "`docs/art`" in agents and "`docs/design/canon`" in agents
    assert (tree / "CLAUDE.md").read_text("utf-8") == "@AGENTS.md\n"


def test_a_second_run_changes_nothing(tree):
    project.init(str(tree), write=True, agent=True)
    again = project.init(str(tree), merge=True, write=True, agent=True)["agent"]
    assert again["changed"] == []
    assert again["server"] == "already declared in .mcp.json"


def test_only_the_text_between_the_markers_is_replaced(tree):
    (tree / "AGENTS.md").write_text(
        f"# Mine\n\nKeep this.\n\n{project.BEGIN}\nold\n{project.END}\n\nAnd this.\n",
        "utf-8",
    )
    (tree / "CLAUDE.md").write_text("Rules.\n\n@AGENTS.md\n", "utf-8")
    found = project.init(str(tree), agent=True)["agent"]
    agents = (tree / "AGENTS.md").read_text("utf-8")
    assert agents.startswith("# Mine\n\nKeep this.\n\n" + project.BEGIN)
    assert agents.endswith(project.END + "\n\nAnd this.\n")
    assert "\nold\n" not in agents
    assert "CLAUDE.md" not in found["changed"]


def test_an_enabled_plugin_is_not_declared_a_second_time(tree):
    (tree / ".claude").mkdir()
    (tree / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"polyweave@alegauss": True}}), "utf-8"
    )
    found = project.init(str(tree), agent=True)["agent"]
    assert found["server"].startswith("not declared: the plugin")
    assert not (tree / ".mcp.json").exists()


def test_the_section_names_only_operations_the_registry_has(tree, monkeypatch):
    from polyweave import describe

    monkeypatch.setattr(
        describe,
        "operations",
        lambda: ["asset.brief"],  # everything else renamed
    )
    with pytest.raises(PolyweaveError) as refused:
        project.init(str(tree), agent=True)
    assert refused.value.code == "op.unknown"


# -- what an adoption is missing (§PW220) --------------------------------------------


def _godot(tree, monkeypatch):
    """An engine binary that exists, as $GODOT names one on a desk."""
    binary = tree.parent / "godot.exe"
    binary.write_bytes(b"")
    monkeypatch.setenv("GODOT", str(binary))


def _codes(found):
    return sorted((f["code"], f["severity"]) for f in found["findings"])


def test_what_init_writes_checks_clean(tree, monkeypatch):
    _godot(tree, monkeypatch)
    project.init(str(tree), write=True, agent=True)
    found = project.check(str(tree))
    assert found["clean"] is True, found["findings"]
    assert found["findings"] == []


def test_a_hand_written_adoption_like_starship_s_checks_clean_with_a_warning(
    tree, monkeypatch
):
    _godot(tree, monkeypatch)
    monkeypatch.setenv("MESHY_API_KEY", "msy")
    (tree / C.FILENAME).write_text(
        '[paths]\nspecs = "docs/art"\nmeshes = "assets/models"\n\n'
        '[service]\nbase = "https://api.meshy.ai"\nkey_env = "MESHY_API_KEY"\n\n'
        '[budget]\ncredits = 30\nexpires = "2099-12-31"\n',
        encoding="utf-8",
    )
    (tree / ".claude").mkdir()
    (tree / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"polyweave@alegauss": True}}), "utf-8"
    )
    (tree / "AGENTS.md").write_text(
        "# Spinhold\n\nThe game's parts go through polyweave.\n", "utf-8"
    )
    found = project.check(str(tree))
    assert found["clean"] is True
    assert _codes(found) == [("adopt.no-agent-section", "warning")]


def test_every_drift_is_reported_with_its_remedy(tree, monkeypatch):
    _godot(tree, monkeypatch)
    project.init(str(tree), write=True, agent=True)
    (tree / "docs" / "art" / "mote.accept.toml").unlink()
    (tree / "docs" / "art").rmdir()
    agents = tree / "AGENTS.md"
    agents.write_text(
        agents.read_text("utf-8")
        .replace(f"polyweave {__version__}", "polyweave 0.0.1")
        .replace("`asset.brief`", "`asset.briefing`"),
        "utf-8",
    )
    (tree / C.FILENAME).write_text(
        (tree / C.FILENAME).read_text("utf-8")
        + '\n[service]\nbase = "https://x"\nkey_env = "POLYWEAVE_TEST_UNSET"\n\n'
        '[budget]\ncredits = 5\nexpires = "2001-01-01"\n',
        "utf-8",
    )
    found = project.check(str(tree))
    assert found["clean"] is False
    assert _codes(found) == [
        ("adopt.budget-lapsed", "error"),
        ("adopt.key-unset", "error"),
        ("adopt.path-missing", "error"),
        ("adopt.stale-section", "error"),
        ("adopt.stale-section", "warning"),
    ]
    assert all(f["remedy"] for f in found["findings"])


def test_a_server_declared_twice_or_not_at_all_is_an_error(tree, monkeypatch):
    _godot(tree, monkeypatch)
    project.init(str(tree), write=True, agent=True)
    (tree / ".claude").mkdir(exist_ok=True)
    (tree / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"polyweave@alegauss": True}}), "utf-8"
    )
    assert ("adopt.server-twice", "error") in _codes(project.check(str(tree)))
    (tree / ".claude" / "settings.json").write_text("{}", "utf-8")
    (tree / ".mcp.json").write_text("{}", "utf-8")
    assert ("adopt.no-server", "error") in _codes(project.check(str(tree)))


def test_a_tree_never_adopted_is_told_how(tree):
    assert _codes(project.check(str(tree))) == [("adopt.not-adopted", "error")]


def test_init_check_exits_non_zero_on_an_error(tree, capsys):
    from polyweave.commands import run

    stated = command_line().parse_args(["init", "--root", str(tree), "--check"])
    assert run(stated) == 1
    assert (tree / C.FILENAME).exists() is False
