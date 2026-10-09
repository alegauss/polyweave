"""The state kit the plugin carries, and game.query reading it (§PW359).

Its proof is a script, since a node path and a value's type are something only the
running game can answer; it runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import driving, godot, kits
from polyweave.errors import PolyweaveError


def test_the_state_kit_is_declared_and_proved_by_script():
    found = kits.every()["state"]
    assert found["requires"] == []
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def test_the_state_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("state")["kits"]
    assert said["status"] == "skipped"


def test_a_query_of_state_and_a_node_at_once_is_refused_before_it_is_sent(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        driving.queried("any", state=["health"], path="Player", root=str(tmp_path))
    assert caught.value.code == "game.bad-target"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "state" / "fixture", game)
    return game, kits.install("state", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_state_kit_holds_every_name_in_its_fixture(tmp_path):
    _, said = _installed(tmp_path)
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("player.gd", "var health := 3", "var health := 3.5",
     "health is float, not the int declared"),
    ("polyweave_state.gd", '"position": {"node": "Player"',
     '"position": {"node": "Ghost"',
     "position reads Ghost, which is not in the running game"),
    ("polyweave_state.gd", '"method": "snapshot"', '"method": "summary"',
     "level calls summary on Level, which has no such method"),
])
def test_a_name_that_does_not_answer_fails_the_proof_by_name(tmp_path, where, before,
                                                             after, said):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["state"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_game_query_reads_a_declared_name_with_no_path(tmp_path):
    game, _ = _installed(tmp_path)
    godot.install(game, addon="polyweave_driver")
    root = str(game)
    session = driving.opened(root)["session"]
    try:
        read = driving.queried(session, state=["health"], root=root)["result"]
        [health] = read.items()
        assert health == ("health", {"ok": True, "value": 3, "type": "int", "said": ""})
        every = driving.queried(session, state=["*"], root=root)["result"]
        assert sorted(every) == ["health", "level", "position"]
        assert every["position"]["value"] == [40, 60]
        assert every["level"]["value"] == {"wave": 1, "enemies": 4}
    finally:
        driving.closed(session, root=root)
    (game / "addons" / "polyweave" / "state" / "state.gd").unlink()
    session = driving.opened(root)["session"]
    try:
        with pytest.raises(PolyweaveError) as refused:
            driving.queried(session, state=["health"], root=root)
        assert refused.value.code == "driver.no-state"
    finally:
        driving.closed(session, root=root)
