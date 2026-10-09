"""The remap kit the plugin carries, proved in its own fixture (§PW345).

It lands with the prompts kit it draws its icons from; its script, which rebinds, swaps,
restarts and resets in the running game, runs where $GODOT is set and is said skipped
where it is not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_remap_kit_needs_the_prompts_kit():
    found = kits.every()["remap"]
    assert found["requires"] == ["prompts"]
    assert found["proves"]["script"] == "core/proof.gd"
    assert found["declares"]["conflict"] == "swap"


def test_the_remap_kit_lands_after_prompts_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    said = kits.install("remap", root=str(game))
    assert said["order"] == ["prompts", "remap"]
    assert said["proved"]["passed"] is True, said["proved"]
    expected = "held" if os.environ.get("GODOT") else "skipped"
    assert [s["status"] for s in said["proved"]["scripts"]] == [expected, expected]
    assert (game / "addons" / "polyweave" / "remap" / "bindings.gd").is_file()
    assert (game / "kits" / "remap" / "remap_menu.tscn").is_file()


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_clash_shared_instead_of_swapped_fails_the_proof(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    store = game / "addons" / "polyweave" / "remap" / "bindings.gd"
    text = store.read_text(encoding="utf-8")
    store.write_text(text.replace("\t\tout[each] = theirs\n", "\t\tpass\n"),
                     encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert "fire still shares its key with jump" in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_remap_proof_holds_in_a_game_with_none_of_its_actions(tmp_path):
    # a kit that requires remap lands it in a game of its own actions (§PW392)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "presence" / "fixture", game)
    said = kits.install("remap", root=str(game))
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_rebound_pad_binding_that_answers_pad_0_alone_fails_the_proof(tmp_path):
    # a decoded event keeps device 0 unless the store says otherwise (§PW391)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    broken = game / "addons" / "polyweave" / "remap" / "bindings.gd"
    text = broken.read_text(encoding="utf-8")
    assert "\t\t\tbutton.device = -1\n" in text
    broken.write_text(text.replace("\t\t\tbutton.device = -1\n", ""), encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert "answers pad 0 alone" in found["said"]
