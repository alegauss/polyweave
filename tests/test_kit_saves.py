"""The saves kit the plugin carries, proved in its own fixture (§PW348).

Its proof is a script that stops saves halfway, corrupts them and loads saves from older
and newer versions; it runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_saves_kit_lands_alone_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "saves" / "fixture", game)
    said = kits.install("saves", root=str(game))
    assert said["order"] == ["saves"]
    assert said["scenes"] == []
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("addons/polyweave/saves/saves.gd", 'FileAccess.open(target + ".tmp"',
     "FileAccess.open(target", "stopped once written did not load the last good one"),
    ("addons/polyweave/saves/saves.gd", "if _sum(body) != str(", "if false and str(",
     "a corrupt save did not fall back"),
    ("addons/polyweave/saves/saves.gd", 'var aside := ".bak" if _read(target) != null'
     ' else ".bad"', 'var aside := ".bak"', "pushed the last good one out"),
    ("polyweave_saves.gd", "return {1: func", "return {0: func",
     "no migration brings a version 1 save to 2"),
    ("addons/polyweave/saves/saves.gd", "if from > version:", "if false:",
     "a save from a newer build was not refused"),
])
def test_a_broken_save_fails_the_proof_by_name(tmp_path, where, before, after, said):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "saves" / "fixture", game)
    kits.install("saves", root=str(game))
    target = game / where
    text = target.read_text(encoding="utf-8")
    assert before in text
    target.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["saves"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
