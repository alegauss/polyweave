"""The players kit the plugin carries, proved in its own fixture (§PW357).

Its proof is a script with simulated pads, since which pad presses which player's action
is something only the running game's InputMap can say; it runs where $GODOT is set and
is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_players_kit_seats_players_through_the_remap_kit():
    found = kits.every()["players"]
    assert found["requires"] == ["remap"]
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}
    assert found["declares"]["max_players"] == 2


def test_the_players_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("players")["kits"]
    assert said["status"] == "skipped"


def _installed(tmp_path, *more):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "players" / "fixture", game)
    said = kits.install("players", root=str(game))
    for one in more:
        kits.install(one, root=str(game))
    return game, said


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_players_kit_lands_after_remap_and_holds_with_presence_beside_it(tmp_path):
    game, said = _installed(tmp_path, "presence")
    assert said["order"] == ["prompts", "remap", "players"]
    assert said["proved"]["passed"] is True, said["proved"]
    [found] = kits._scripts(["players"], kits.every(), game)
    assert found["status"] == "held", found


PLAYERS = "addons/polyweave/players/players.gd"
PRESENCE = "addons/polyweave/presence/presence.gd"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    (PLAYERS, "event.device = device if device >= 0 else -1", "pass",
     "player 1's pad presses p2_fire"),
    (PLAYERS, "var device: int = pads[0] if count() > 1 else -1", "var device := -1",
     "player 2's pad presses player 1's fire"),
    (PLAYERS, ' or count() >= int(declared["MAX_PLAYERS"])', "",
     "a pad past MAX_PLAYERS joined"),
    (PLAYERS, "\t\t\tInputMap.erase_action(action(name, player))\n", "\t\t\tpass\n",
     "kept their pad or their actions"),
    (PLAYERS, "_apply(action(each, player), _pad_half(after[each]), pads[player])",
     "_apply(each, _pad_half(after[each]), pads[player])", "changed player 1's"),
    (PRESENCE, "\t\t\treturn seated\n", "\t\t\treturn device\n",
     "with the presence kit, pad 3 is named as player 4"),
])
def test_a_broken_seating_fails_the_proof_by_name(tmp_path, where, before, after, said):
    game, _ = _installed(tmp_path, "presence")
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["players"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
