"""A verdict given through the CLI lands in the ledger (§PW332).

Each command-line call gets its own copy of the run, parsed from JSON, and the copy dies
with the call. These tests pass each call a fresh copy, as the command line does.
"""

from __future__ import annotations

import json

from polyweave import loop, verdict
from test_verdict import DARK, member


def copied(run):
    """The run as the next command-line call receives it."""
    return json.loads(json.dumps(run))


def test_an_open_run_outlives_the_call_that_opened_it(tmp_path):
    family = [member(tmp_path, "star_gold", DARK)]
    started = loop.start("star_gold", "after", root=str(tmp_path))
    said = verdict.judge(family, "accept", "reads well", root=str(tmp_path),
                         run=copied(started))
    assert said["ledger"] == "recorded in the open run"
    # The same stale JSON the caller kept, as loop.finish --run '<json>' passes it.
    done = loop.finish(copied(started), root=str(tmp_path))
    assert done["results"] == 1 and done["accepted"] is True
    assert loop.pending(str(tmp_path))["assets"][0]["judged"]


def test_a_run_named_by_its_id_alone_is_the_kept_one(tmp_path):
    started = loop.start("cloud", "after", root=str(tmp_path))
    loop.spent({"id": started["id"]}, renders=3, root=str(tmp_path))
    loop.judged({"id": started["id"]}, tool_passed=True, person_accepted=False,
                why="too flat", root=str(tmp_path))
    done = loop.finish({"id": started["id"]}, root=str(tmp_path))
    assert done["renders"] == 3 and done["results"] == 1
    assert not list((tmp_path / ".polyweave").rglob("open-runs/*.json"))


def test_a_verdict_given_in_a_conversation_lands_in_one_call(tmp_path):
    family = [member(tmp_path, "star_gold", DARK)]
    said = verdict.judge(family, "accept", "the owner said yes in chat",
                         asset="star_gold", root=str(tmp_path))
    assert said["ledger"] == "recorded in a run opened and closed for star_gold"
    [run] = loop.read(str(tmp_path))
    assert run["asset"] == "star_gold" and run["accepted"] is True
    assert run["verdicts"][0]["why"].endswith("the owner said yes in chat")


def test_finishing_with_accepted_and_no_verdict_keeps_it_as_one(tmp_path):
    started = loop.start("drone", "after", root=str(tmp_path))
    done = loop.finish(copied(started), accepted=True, root=str(tmp_path))
    assert done["verdicts"][0]["person_accepted"] is True
    assert loop.pending(str(tmp_path))["assets"][0]["judged"]
