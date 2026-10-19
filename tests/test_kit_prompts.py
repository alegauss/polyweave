"""The prompts kit the plugin carries, proved in its own fixture (§PW344).

Its picture proof runs anywhere; its script, which asks the running game whether every
bound action has an icon in every family, runs where $GODOT is set and is said skipped
where it is not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave.layers import kits


def test_the_prompts_kit_keeps_the_contract():
    found = kits.every()["prompts"]
    assert found["proves"]["script"] == "core/proof.gd"
    assert set(found["declares"]["families"]) == {
        "xbox", "playstation", "switch", "generic", "keyboard"}


def test_every_family_draws_every_position_a_pad_has():
    icons = kits.KITS / "prompts" / "core" / "icons"
    positions = {p.name for p in (icons / "xbox").glob("*_64.png")}
    assert {"south_64.png", "east_64.png", "rt_64.png", "dpad_left_64.png"} <= positions
    for family in ("playstation", "switch"):
        assert {p.name for p in (icons / family).glob("*_64.png")} == positions


def test_the_prompts_kit_lands_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "prompts" / "fixture", game)
    said = kits.install("prompts", root=str(game))
    assert said["proved"]["passed"] is True, said["proved"]
    [script] = said["proved"]["scripts"]
    expected = "held" if os.environ.get("GODOT") else "skipped"
    assert script["status"] == expected
    assert said["game"]["actions"] == ["fire", "jump", "move_left", "pause"]


#: A game of its own words, in the machine's language, as Spinhold is on a pt-BR desk.
WORDS = """extends Node
## The game's own key and pad names, in Portuguese, and its language set before
## anything is read, as a game's language code does at start (§PW485).

func _init() -> void:
\tvar table := Translation.new()
\ttable.locale = "pt_BR"
\tvar rows := {"KEYNAME_SPACE": "ESPAÇO", "PAD_SOUTH": "SUL",
\t\t\t"KEYNAME_ENTER": "ENTRA"}
\tfor row in rows:
\t\ttable.add_message(row, rows[row])
\tTranslationServer.add_translation(table)
\tTranslationServer.set_locale("pt_BR")
"""


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_proof_holds_in_a_game_running_in_another_language(tmp_path):
    """§PW485: a pt-BR game turned correct lookups into a red proof about the table."""
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "prompts" / "fixture", game)
    (game / "words.gd").write_text(WORDS, encoding="utf-8")
    project = game / "project.godot"
    project.write_text(project.read_text("utf-8")
                       + '\n[autoload]\n\ngame_words="*res://words.gd"\n',
                       encoding="utf-8")
    said = kits.install("prompts", root=str(game))
    assert said["proved"]["passed"] is True, said["proved"]


def test_the_kits_records_name_where_their_files_landed(tmp_path, monkeypatch):
    """Spinhold's verify called 128 kit icons missing: each copied record named the file
    where polyweave built it (§PW550). An update puts an older core's records right."""
    import json

    from polyweave.kernel import provenance

    monkeypatch.delenv("GODOT", raising=False)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    checked = provenance.verify(root=str(game))
    landed = [one for one in checked["ok"] if one.startswith("addons/polyweave/")]
    assert landed and not [one for one in checked["missing"]
                           if one["artefact"].startswith(("core/", "src/"))]
    assert checked["missing"] == []
    icon = next((game / "addons" / "polyweave" / "prompts").rglob("*.png.prov.json"))
    record = json.loads(icon.read_text("utf-8"))
    assert record["kit"]["name"] == "prompts"
    assert record["kit"]["from"].startswith("core/")
    # an older install's record, as Spinhold has them
    record["artefact"]["path"] = record["kit"]["from"]
    del record["kit"]
    icon.write_text(json.dumps(record), encoding="utf-8")
    assert provenance.verify(root=str(game))["missing"]
    said = kits.update("prompts", root=str(game))
    assert "records now name" in said["says"]
    assert provenance.verify(root=str(game))["missing"] == []


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_missing_icon_fails_the_proof_by_name(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "prompts" / "fixture", game)
    kits.install("prompts", root=str(game))
    icons = game / "addons" / "polyweave" / "prompts" / "icons"
    (icons / "switch" / "rt_64.png").unlink()
    [found] = kits._scripts(["prompts"], kits.every(), game)
    assert found["status"] == "failed"
    assert "fire has no icon in switch" in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("before", "after", "said"), [
    ("\tif _touched or connected.is_empty():\n\t\treturn family\n",
     "\treturn family\n", "started on keyboard"),
    ("\t_touched = true\n", "", "found after a key was pressed"),
    # Spinhold bridged its help lines into icons by hand (§PW551)
    ("\tvar path := icon_path(action_of(action, player), wanted)\n",
     "\tvar path := icon_path(action, wanted)\n", "not their own binding's"),
    ("\tif sticks[0] != \"\" and", "\tif false and", "four moves on one stick"),
])
def test_prompts_that_ignore_the_pad_in_hand_fail_the_proof(
        tmp_path, before, after, said):
    # Spinhold set the family itself at boot to name the plugged-in pad (§PW545)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "prompts" / "fixture", game)
    kits.install("prompts", root=str(game))
    script = game / "addons" / "polyweave" / "prompts" / "prompts.gd"
    text = script.read_text(encoding="utf-8")
    assert before in text
    script.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["prompts"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
