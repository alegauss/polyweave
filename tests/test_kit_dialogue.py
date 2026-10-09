"""The dialogue kit the plugin carries, proved in its own fixture (§PW353).

Its proof is a script, driven by pad events alone, since whether a line is reached,
typed and fits its box is something only the running game can say; it runs where $GODOT
is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_dialogue_kit_reads_lines_through_the_language_kit():
    found = kits.every()["dialogue"]
    assert found["requires"] == ["prompts", "language"]
    assert found["installs"]["scene"] == "scene/dialogue_box.tscn"
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def test_the_dialogue_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("dialogue")["kits"]
    assert said["status"] == "skipped"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "dialogue" / "fixture", game)
    return game, kits.install("dialogue", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_dialogue_kit_lands_with_its_box_and_holds_in_its_fixture(tmp_path):
    game, said = _installed(tmp_path)
    assert said["order"] == ["prompts", "language", "dialogue"]
    assert "kits/dialogue/dialogue_box.tscn" in said["scenes"]
    assert (game / "kits" / "dialogue" / "dialogue_box.tscn").is_file()
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("addons/polyweave/dialogue/dialogue.gd",
     "\t\t_text().visible_characters = -1\n\t\treturn\n", "\t\tpass\n",
     "moved on before it was whole"),
    ("addons/polyweave/dialogue/dialogue.gd", '"switch": JOY_BUTTON_B}',
     '"switch": JOY_BUTTON_A}', "switch's other button moved"),
    ("addons/polyweave/dialogue/dialogue.gd", "_shown += delta * rate",
     "_shown += 100000.0", "characters typed in"),
    ("i18n/strings.csv", "Go.,Vá.", "Go.,\"" + "Vá agora, depressa. " * 30 + "\"",
     "pt_BR INTRO_3"),
    ("addons/polyweave/dialogue/dialogue.gd",
     "portrait.visible = portrait.texture != null", "portrait.visible = false",
     "INTRO_1 does not show its portrait"),
])
def test_a_broken_dialogue_box_fails_the_proof_by_name(tmp_path, where, before, after,
                                                       said):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["dialogue"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
