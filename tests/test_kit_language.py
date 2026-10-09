"""The language kit the plugin carries, proved in its own fixture (§PW352).

Its proof is a script, since whether a line is drawn and fits is something only the
laid-out game can say; it runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_language_kit_contributes_the_language_row_and_proves_by_script():
    found = kits.every()["language"]
    assert found["requires"] == []
    assert found["tab"] == "general"
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}
    assert found["declares"]["fallback"] == "en"


def test_the_language_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("language")["kits"]
    assert said["status"] == "skipped"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "language" / "fixture", game)
    return game, kits.install("language", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_language_kit_holds_its_fixture_in_every_locale(tmp_path):
    _, said = _installed(tmp_path)
    assert said["proved"]["passed"] is True, said["proved"]
    assert said["proved"]["scripts"][0]["status"] == "held"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("polyweave_language.gd",
     'const FONTS := [{"script": "Jpan", "path": "res://fonts/kana.ttf"}]',
     "const FONTS := []", "ja TITLE needs"),
    ("main.tscn", "autowrap_mode = 3", "clip_text = true", "pt_BR HINT is"),
    ("i18n/strings.csv", "CREDITS,Credits,", "CREDITS,,",
     "en shows the raw key CREDITS"),
    ("main.tscn", 'text = "TITLE"', 'text = "Star Garden"',
     "shows Star Garden, which is no key of the table"),
    ("addons/polyweave/language/language.gd", 'if one.split("_")[0] == language:',
     "if false:", "not a locale of its language"),
])
def test_a_broken_language_runtime_fails_the_proof_by_name(tmp_path, where, before,
                                                         after, said):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["language"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
