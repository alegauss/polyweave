"""What one asset cost to make, each way, so the claim can be falsified.

§PW35's case: every line in this backlog is a claim that something will be faster or
more certain, and not one of them is measured. The risk is that the work gets rearranged
rather than reduced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polyweave import loop
from polyweave.errors import PolyweaveError


def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    return tmp_path


def run(tmp_path, way, *, seconds, renders=0, calls=0, credits=0, verdicts=((1, 1),)):
    one = loop.start("tray", way, root=tmp_path)
    loop.spent(one, seconds=seconds, renders=renders, calls=calls, credits=credits)
    for passed, accepted in verdicts:
        loop.judged(one, tool_passed=bool(passed), person_accepted=bool(accepted))
    return loop.finish(one, root=tmp_path)


# -- what a run records ---------------------------------------------------------------


def test_a_run_records_the_five_numbers(tmp_path):
    project(tmp_path)
    found = run(tmp_path, "before", seconds=900, renders=40, calls=12, credits=30)
    assert found["seconds"] == 900
    assert found["renders"] == 40
    assert found["calls"] == 12
    assert found["credits"] == 30
    assert found["results"] == 1


def test_a_run_carries_the_commit_it_was_taken_at(tmp_path):
    """So its place in the order is checkable by somebody who was not there."""
    project(tmp_path)
    found = run(tmp_path, "before", seconds=10)
    assert len(found["commit"]) in (0, 40), "a sha, or nothing where there is no git"


def test_the_ledger_is_append_only(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=10)
    run(tmp_path, "after", seconds=5)
    assert len(loop.read(tmp_path)) == 2


def test_the_ledger_is_json_because_a_machine_writes_it(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=10)
    written = json.loads((tmp_path / "polyweave.loop.json").read_text(encoding="utf-8"))
    assert len(written["runs"]) == 1


def test_a_way_that_is_neither_is_refused(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        loop.start("tray", "sideways", root=tmp_path)
    assert caught.value.code == "loop.unknown-way"


def test_a_run_nobody_judged_says_nothing(tmp_path):
    project(tmp_path)
    one = loop.start("tray", "after", root=tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        loop.finish(one, root=tmp_path)
    assert caught.value.code == "loop.unfinished"
    assert "did not finish being made" in caught.value.remedy


# -- the baseline cannot be written afterwards -----------------------------------------


def test_a_baseline_taken_after_the_port_is_refused(tmp_path):
    """A baseline written once the answer is known is a justification."""
    project(tmp_path)
    run(tmp_path, "after", seconds=100)
    with pytest.raises(PolyweaveError) as caught:
        loop.start("tray", "before", root=tmp_path)
    assert caught.value.code == "loop.baseline-too-late"
    assert "is a justification" in caught.value.remedy


def test_a_baseline_for_an_asset_nobody_ported_is_fine(tmp_path):
    project(tmp_path)
    run(tmp_path, "after", seconds=100)
    assert loop.start("mascot", "before", root=tmp_path)["way"] == "before"


def test_a_second_run_of_the_new_way_is_always_allowed(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=900)
    run(tmp_path, "after", seconds=100)
    assert loop.start("tray", "after", root=tmp_path)["way"] == "after"


# -- the measure of assertiveness ------------------------------------------------------


def test_a_result_the_tool_passed_and_a_person_rejected_is_counted(tmp_path):
    """The honest measure: approving work that gets rejected is worse, not faster."""
    project(tmp_path)
    found = run(tmp_path, "after", seconds=10, verdicts=((1, 0), (1, 0), (1, 1)))
    assert found["overruled"] == 2
    assert found["results"] == 3


def test_a_result_the_tool_failed_and_a_person_also_rejected_is_not_overruling(
    tmp_path,
):
    project(tmp_path)
    found = run(tmp_path, "after", seconds=10, verdicts=((0, 0), (1, 1)))
    assert found["overruled"] == 0


def test_the_run_is_accepted_by_the_last_verdict_a_person_gave(tmp_path):
    project(tmp_path)
    assert run(tmp_path, "after", seconds=10, verdicts=((1, 0), (1, 1)))["accepted"]
    assert not run(tmp_path, "after", seconds=10, verdicts=((1, 1), (1, 0)))["accepted"]


# -- comparing the two -----------------------------------------------------------------


def test_the_two_ways_come_back_side_by_side(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=900, renders=40, calls=12)
    run(tmp_path, "after", seconds=120, renders=18, calls=5)
    found = loop.compare("tray", root=tmp_path)
    assert found["before"]["seconds"] == 900
    assert found["after"]["seconds"] == 120
    assert found["changed"]["seconds"]["delta"] == -780


def test_it_says_how_many_times_over_and_not_only_the_difference(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=1000)
    run(tmp_path, "after", seconds=250)
    found = loop.compare("tray", root=tmp_path)
    assert found["changed"]["seconds"]["times"] == 0.25


def test_a_faster_loop_that_renders_more_is_said_to_have_moved_the_cost(tmp_path):
    """Not reduced. Which is the specific risk this line exists for."""
    project(tmp_path)
    run(tmp_path, "before", seconds=900, renders=20)
    run(tmp_path, "after", seconds=300, renders=200)
    found = loop.compare("tray", root=tmp_path)
    assert "renders went up" in found["verdict"]
    assert "may have moved rather than gone" in found["verdict"]


def test_a_loop_that_got_slower_is_said_so(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=100)
    run(tmp_path, "after", seconds=400)
    assert "not reduced" in loop.compare("tray", root=tmp_path)["verdict"]


def test_overruling_beats_every_other_number(tmp_path):
    """However fast it was. A tool approving rejected work has made things worse."""
    project(tmp_path)
    run(tmp_path, "before", seconds=9000, verdicts=((1, 1),))
    run(tmp_path, "after", seconds=1, verdicts=((1, 0), (1, 0), (1, 1)))
    found = loop.compare("tray", root=tmp_path)
    assert "overruled the tool 2 times" in found["verdict"]
    assert "faster or not" in found["verdict"]


def test_a_loop_that_is_faster_and_cheaper_everywhere_says_that(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=900, renders=40, calls=12, credits=30)
    run(tmp_path, "after", seconds=120, renders=18, calls=5, credits=0)
    assert "nothing else higher" in loop.compare("tray", root=tmp_path)["verdict"]


def test_one_side_alone_is_not_a_measurement(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=900)
    with pytest.raises(PolyweaveError) as caught:
        loop.compare("tray", root=tmp_path)
    assert caught.value.code == "loop.nothing-to-compare"
    assert "measured on one side is not measured" in caught.value.remedy


def test_what_has_been_recorded_is_a_read(tmp_path):
    project(tmp_path)
    run(tmp_path, "before", seconds=10)
    one = loop.start("mascot", "after", root=tmp_path)
    loop.judged(one, tool_passed=True, person_accepted=True)
    loop.finish(one, root=tmp_path)
    assert loop.assets(tmp_path) == ["mascot", "tray"]


def test_a_ledger_a_hand_edit_broke_says_where(tmp_path):
    project(tmp_path)
    (tmp_path / "polyweave.loop.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        loop.read(tmp_path)
    assert caught.value.code == "loop.malformed"
    assert caught.value.detail


def test_nothing_recorded_yet_is_an_empty_list_and_not_a_failure(tmp_path):
    project(tmp_path)
    assert loop.read(tmp_path) == []
    assert not Path(tmp_path / "polyweave.loop.json").exists()
