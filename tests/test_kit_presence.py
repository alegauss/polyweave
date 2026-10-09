"""The presence kit the plugin carries, proved in its own fixture (§PW356).

Its proof is a script driven by simulated disconnects, focus changes and pad presses,
since whether the game stops ticking is something only the running game can say; it
runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_presence_kit_draws_its_prompts_from_the_prompts_kit():
    found = kits.every()["presence"]
    assert found["requires"] == ["prompts"]
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}
    assert found["declares"]["pause_on_focus"] is True


def test_the_presence_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("presence")["kits"]
    assert said["status"] == "skipped"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "presence" / "fixture", game)
    return game, kits.install("presence", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_presence_kit_lands_after_prompts_and_holds_in_its_fixture(tmp_path):
    _, said = _installed(tmp_path)
    assert said["order"] == ["prompts", "presence"]
    assert said["proved"]["passed"] is True, said["proved"]


PRESENCE = "addons/polyweave/presence/presence.gd"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("before", "after", "said"), [
    ('_hold("pad", tr(str(declared["LEFT"])) % (player_of(device) + 1))', "pass",
     "a pad leaving did not pause the game"),
    ("family = family_of(device)", 'family = "xbox"',
     "a PlayStation pad leaving drew the xbox family"),
    ('"switch": JOY_BUTTON_B}', '"switch": JOY_BUTTON_A}',
     "a Switch pad's back button resumed the game"),
    ("FOCUS_OUT and pause_on_focus and why", "FOCUS_OUT and why",
     "with PAUSE_ON_FOCUS off, losing focus paused the game"),
    ("get_tree().paused = _was_paused", "get_tree().paused = false",
     "unpaused a game its own menu had paused"),
])
def test_a_broken_presence_fails_the_proof_by_name(tmp_path, before, after, said):
    game, _ = _installed(tmp_path)
    broken = game / PRESENCE
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["presence"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
