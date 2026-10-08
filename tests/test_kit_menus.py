"""The menus kit the plugin carries, proved in its own fixture (§PW346).

Its proof is a script alone, since whether a pad reaches every control is something only
the running game can say; it runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_menus_kit_is_proved_by_its_script_alone():
    found = kits.every()["menus"]
    assert found["requires"] == ["prompts"]
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}
    assert found["declares"]["back"] == {"main": "quit", "pause": "resume",
                                         "confirm": "no"}


def test_the_menus_kit_lands_after_prompts_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "menus" / "fixture", game)
    said = kits.install("menus", root=str(game))
    assert said["order"] == ["prompts", "menus"]
    assert said["proved"]["passed"] is True, said["proved"]
    expected = "held" if os.environ.get("GODOT") else "skipped"
    assert [s["status"] for s in said["proved"]["scripts"]] == [expected, expected]
    assert list(game.rglob("menus/proof.accept.toml")) == []
    assert list(game.rglob("prompts/proof.accept.toml")) != []


def test_a_kit_proved_by_a_script_alone_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("menus")["kits"]
    assert said["status"] == "skipped"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("script", "before", "after", "said"), [
    ("menu.gd", '"switch": JOY_BUTTON_A}', '"switch": JOY_BUTTON_B}',
     "a Switch pad's south then east chose"),
    ("menu.gd", "all[(i + 1) % all.size()]", "all[mini(i + 1, all.size() - 1)]",
     "did not come back round to play"),
    ("pause.gd", "get_tree().paused = true", "pass", "ticked"),
])
def test_a_broken_menu_fails_the_proof_by_name(tmp_path, script, before, after, said):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "menus" / "fixture", game)
    kits.install("menus", root=str(game))
    broken = game / "addons" / "polyweave" / "menus" / script
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["menus"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
