"""A verdict is not a way of making the asset (§PW388).

`verdict.judge(asset=)` opens a run to land a person's word in. Read as an `after` run,
it refused that asset's baseline for good, which is how five of Spinhold's six assets
were closed to measurement by one yes each.
"""

from __future__ import annotations

import json

import pytest

from polyweave import loop, verdict
from polyweave.errors import PolyweaveError
from test_verdict import DARK, member


def judged_in_chat(tmp_path, name="star_gold"):
    verdict.judge([member(tmp_path, name, DARK)], "accept", "the owner said yes",
                  asset=name, root=str(tmp_path))


def made(tmp_path, way, *, seconds, renders=0, verdicts=((True, True),)):
    run = loop.start("star_gold", way, root=str(tmp_path))
    loop.spent(run, seconds=seconds, renders=renders, root=str(tmp_path))
    for passed, accepted in verdicts:
        loop.judged(run, tool_passed=passed, person_accepted=accepted,
                    root=str(tmp_path))
    return loop.finish(run, root=str(tmp_path))


def test_a_verdict_given_in_a_conversation_leaves_the_baseline_open(tmp_path):
    judged_in_chat(tmp_path)
    [run] = loop.read(str(tmp_path))
    assert run["made"] is False and not loop.was_made(run)
    started = loop.start("star_gold", "before", root=str(tmp_path))
    assert started["way"] == "before"


def test_a_verdict_run_from_an_older_ledger_is_read_the_same_way(tmp_path):
    judged_in_chat(tmp_path)
    ledger = next(tmp_path.rglob("polyweave.loop.json"))
    runs = json.loads(ledger.read_text(encoding="utf-8"))["runs"]
    del runs[0]["made"]
    ledger.write_text(json.dumps({"runs": runs}), encoding="utf-8")
    assert loop.start("star_gold", "before", root=str(tmp_path))["way"] == "before"


def test_a_real_port_still_refuses_a_late_baseline(tmp_path):
    made(tmp_path, "after", seconds=8.6, renders=28)
    with pytest.raises(PolyweaveError) as refused:
        loop.start("star_gold", "before", root=str(tmp_path))
    assert refused.value.code == "loop.baseline-too-late"


def test_a_verdict_is_not_an_after_side_to_wait_on(tmp_path):
    judged_in_chat(tmp_path)
    [row] = loop.pending(str(tmp_path))["assets"]
    assert row["after"] is False and row["judged"]


def test_a_verdict_alone_is_not_a_side_to_compare(tmp_path):
    made(tmp_path, "before", seconds=3.3, renders=4)
    judged_in_chat(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        loop.compare("star_gold", root=str(tmp_path))
    assert refused.value.code == "loop.nothing-to-compare"


def test_a_verdict_run_brings_its_overruling_and_no_cost(tmp_path):
    made(tmp_path, "before", seconds=3.3, renders=4)
    made(tmp_path, "after", seconds=8.6, renders=28)
    verdict.judge([member(tmp_path, "star_gold", DARK)], "look", "too flat",
                  asset="star_gold", root=str(tmp_path))
    after = loop.compare("star_gold", root=str(tmp_path))["after"]
    assert after["seconds"] == 8.6 and after["renders"] == 28
    assert after["judged_only"] == 1 and after["results"] == 2
