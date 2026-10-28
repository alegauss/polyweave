"""A recorded run flown back at several frame rates, tick held to tick (§PW640).

Spinhold's replays drifted from play counted in frames, which a proof at one tick a
frame never shows. Flying the run needs the engine and runs where $GODOT is set; the
refusals run anywhere.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers import kits
from polyweave.layers.engine import traces

ENGINE = pytest.mark.skipif(not os.environ.get("GODOT"),
                            reason="no $GODOT on this machine")


def test_a_game_without_the_determinism_kit_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        traces.replay_rates(root=str(tmp_path))
    assert refused.value.code == "game.no-determinism"


@pytest.mark.parametrize("rates", [[60], [60, 60], [60, 0], [60, 24.5], [60, True]])
def test_rates_that_cannot_be_held_against_each_other_are_refused(tmp_path, rates):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    proof = tmp_path / traces.PROOF
    proof.parent.mkdir(parents=True)
    proof.write_text("extends SceneTree\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        traces.replay_rates(rates, root=str(tmp_path))
    assert refused.value.code == "game.bad-rates"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "determinism" / "fixture", game)
    kits.install("determinism", root=str(game))
    return game


@ENGINE
def test_play_counted_in_ticks_agrees_at_every_frame_rate(tmp_path):
    game = _installed(tmp_path)
    found = traces.replay_rates(root=str(game))
    assert found["passed"] is True, found
    by_rate = {one["fps"]: one for one in found["rates"]}
    # The same ninety ticks, in more frames than ticks at 144 and fewer at 24.
    assert {one["ticks"] for one in by_rate.values()} == {90}
    assert by_rate[24]["frames"] < 90 < by_rate[144]["frames"]


@ENGINE
def test_play_counted_in_frames_parts_and_is_named(tmp_path):
    game = _installed(tmp_path)
    main = game / "main.gd"
    main.write_text(main.read_text(encoding="utf-8") + (
        "\n\nvar steps := 0\n\n\nfunc _process(_delta: float) -> void:\n"
        "\tsteps += 1\n"), encoding="utf-8")
    state = game / "polyweave_state.gd"
    counted = '"steps": {"node": ".", "property": "steps", "type": "int"},\n'
    state.write_text(state.read_text(encoding="utf-8").replace(
        '"last_spawn": {', counted + '\t"last_spawn": {'), encoding="utf-8")
    found = traces.replay_rates([60, 24], root=str(game))
    assert found["passed"] is False
    [parted] = found["compared"]
    assert parted["first"]["id"] == "steps"
    assert "at 24 fps against 60" in found["says"]
