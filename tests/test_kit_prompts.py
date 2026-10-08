"""The prompts kit the plugin carries, proved in its own fixture (§PW344).

Its picture proof runs anywhere; its script, which asks the running game whether every
bound action has an icon in every family, runs where $GODOT is set and is said skipped
where it is not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_prompts_kit_keeps_the_contract():
    found = kits.every()["prompts"]
    assert found["proves"]["script"] == "core/proof.gd"
    assert set(found["declares"]["families"]) == {
        "xbox", "playstation", "switch", "keyboard"}


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
