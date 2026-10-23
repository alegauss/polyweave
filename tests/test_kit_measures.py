"""The measures kit: measure.pressure in the engine, held to the Python one (§PW613).

The comparison is polyweave's, over what the proof wrote, so it is checked everywhere;
the engine's half runs where $GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from polyweave.layers import kits
from polyweave.layers.engine import pressure

CASE = {"events": [{"second": 0, "weight": 1, "until": 4},
                   {"second": 6.25, "weight": 3, "until": 9.5}],
        "warp": 0.5, "window": 1.5}


def test_the_measures_kit_is_declared_and_proved_by_script():
    found = kits.every()["measures"]
    assert found["requires"] == []
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def printed(tmp_path, answer: dict, measure: str = "pressure") -> str:
    (tmp_path / "out").mkdir(exist_ok=True)
    (tmp_path / "out" / "a.inputs.json").write_text(json.dumps(CASE), "utf-8")
    (tmp_path / "out" / "a.answer.json").write_text(json.dumps(answer), "utf-8")
    return f"KIT STEP x\nKIT MEASURE {measure} out/a.inputs.json out/a.answer.json\n"


def ours() -> dict:
    events, _ = pressure._read(CASE["events"], None)
    return pressure._curves(events, CASE["warp"], CASE["window"])


def test_an_engine_answer_polyweave_agrees_with_holds(tmp_path):
    answer = ours()
    answer["alive_slow"] = [v + 0.0004 for v in answer["alive_slow"]]
    [said] = kits._measures(printed(tmp_path, answer), tmp_path)
    assert said == {"measure": "pressure", "inputs": "out/a.inputs.json", "held": True}


@pytest.mark.parametrize(("change", "where"), [
    (lambda a: a["alive_fast"].__setitem__(1, a["alive_fast"][1] + 0.5),
     "alive_fast[1] is"),
    (lambda a: a["gaps"].pop(), "gaps holds 0 in the engine and 1 in polyweave"),
    (lambda a: a.pop("longest_gap"), "longest_gap is in only one of the two answers"),
])
def test_the_first_value_the_engine_drifted_on_fails_the_proof(tmp_path, change, where):
    answer = ours()
    change(answer)
    [said] = kits._measures(printed(tmp_path, answer), tmp_path)
    assert said["held"] is False
    assert where in said["said"]


def test_a_measure_polyweave_does_not_carry_fails(tmp_path):
    [said] = kits._measures(printed(tmp_path, ours(), "threat"), tmp_path)
    assert said["held"] is False and "no measure threat" in said["said"]


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "measures" / "fixture", game)
    return game, kits.install("measures", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_engine_copy_answers_as_polyweave_over_the_cases_and_the_games_waves(
        tmp_path):
    _, said = _installed(tmp_path)
    assert said["proved"]["passed"] is True, said["proved"]
    [script] = said["proved"]["scripts"]
    measured = script["measures"]
    assert len(measured) == 4 and all(one["held"] for one in measured)
    assert measured[-1]["inputs"].endswith("pressure-phase1.inputs.json")


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_an_engine_copy_that_drifted_fails_the_proof_by_its_value(tmp_path):
    game, _ = _installed(tmp_path)
    copy = game / "addons" / "polyweave" / "measures" / "pressure.gd"
    text = copy.read_text(encoding="utf-8")
    drifted = "[[fast, e[\"second\"] + warp], [slow, e[\"until\"]]]"
    assert drifted in text
    copy.write_text(text.replace(drifted, drifted.replace("+ warp", "+ warp * 2")),
                    encoding="utf-8")
    [found] = kits._scripts(["measures"], kits.every(), game)
    assert found["status"] == "failed"
    assert "alive_fast" in found["said"]
