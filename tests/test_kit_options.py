"""The options kit the plugin carries, proved in its own fixture (§PW347).

Its proof is a script: every row read back after a change, a restart, a file an older
build wrote, and a pad walking the screen. It runs where $GODOT is set.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits
from polyweave.errors import PolyweaveError


def test_a_kit_that_contributes_a_tab_declares_it():
    found = kits.every()
    assert found["remap"]["tab"] == "controls"
    assert found["options"]["tab"] is None
    assert found["options"]["requires"] == ["menus"]


def test_a_tab_with_no_rows_and_rows_with_no_tab_are_refused(tmp_path):
    folder = tmp_path / "remap"
    shutil.copytree(kits.KITS / "remap", folder)
    toml = folder / "kit.toml"
    text = toml.read_text(encoding="utf-8")
    toml.write_text(text.replace('tab = "controls"\n', ""), encoding="utf-8")
    shutil.copytree(kits.KITS / "prompts", tmp_path / "prompts")
    with pytest.raises(PolyweaveError) as untold:
        kits.every(tmp_path)
    assert "declares no tab" in untold.value.message
    toml.write_text(text, encoding="utf-8")
    (folder / "core" / "options.gd").unlink()
    with pytest.raises(PolyweaveError) as empty:
        kits.every(tmp_path)
    assert "keeps no options.gd" in empty.value.message


def test_the_options_kit_lands_after_menus_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "options" / "fixture", game)
    said = kits.install("options", root=str(game))
    assert said["order"] == ["prompts", "menus", "options"]
    assert said["proved"]["passed"] is True, said["proved"]


def _broken(tmp_path, where, before, after):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "options" / "fixture", game)
    kits.install("options", root=str(game))
    target = game / where
    text = target.read_text(encoding="utf-8")
    assert before in text
    target.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["options"], kits.every(), game)
    return found


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("polyweave_options.gd", "Engine.set_meta(\"subtitles\", v)", "pass",
     "general/subtitles changes nothing"),
    ("addons/polyweave/options/settings.gd", "for held in [_kept, _values]:",
     "for held in [_values]:", "a key no row declares was dropped"),
    ("addons/polyweave/menus/menu.gd", '"switch": JOY_BUTTON_A}',
     '"switch": JOY_BUTTON_B}', "east button did not change language"),
])
def test_a_broken_option_fails_the_proof_by_name(tmp_path, where, before, after, said):
    found = _broken(tmp_path, where, before, after)
    assert found["status"] == "failed"
    assert said in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_remap_kit_puts_its_controls_tab_on_the_screen(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "options" / "fixture", game)
    kits.install("remap", root=str(game))
    said = kits.install("options", root=str(game))
    assert said["proved"]["passed"] is True, said["proved"]
    (game / "kits" / "remap" / "remap_menu.tscn").unlink()
    [found] = kits._scripts(["options"], kits.every(), game)
    assert "controls/remap opens res://kits/remap/remap_menu.tscn" in found["said"]


ONE_ROW = '''extends RefCounted


static func options() -> Array[Dictionary]:
	return [{"tab": "general", "key": "subtitles", "label": "subtitles",
		"default": true,
		"apply": func(v: bool) -> void: Engine.set_meta("subtitles", v),
		"read": func() -> bool: return Engine.get_meta("subtitles", true)}]
'''


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_options_proof_holds_in_a_game_with_one_value_row(tmp_path):
    # its refused value once overwrote the one value it kept (§PW393)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "options" / "fixture", game)
    (game / "polyweave_options.gd").write_text(ONE_ROW, encoding="utf-8")
    said = kits.install("options", root=str(game))
    assert said["proved"]["passed"] is True, said["proved"]
