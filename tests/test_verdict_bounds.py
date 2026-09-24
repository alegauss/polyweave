"""Every verdict is evidence about a bound (§PW108)."""

from __future__ import annotations

import pytest

from polyweave import loop
from polyweave.errors import PolyweaveError


def checked(tail, *, body=0.2, ceiling=0.37):
    """What `accept.check` says of a star, shaped as it says it."""
    return {
        "passed": tail <= ceiling,
        "predicates": [
            {"id": "body", "value": body, "passed": True, "bound": {"side": "max"}},
            {
                "id": "no-hot-facet",
                "value": tail,
                "passed": tail <= ceiling,
                "bound": {"side": "max", "origin": "margin"},
            },
        ],
    }


def judge(tmp_path, *verdicts, asset="star_dim"):
    run = loop.start(asset, "after", root=tmp_path)
    for tail, accepted, named in verdicts:
        found = checked(tail)
        loop.judged(
            run,
            tool_passed=found["passed"],
            person_accepted=accepted,
            check=found,
            named=named,
        )
    return loop.finish(run, root=tmp_path)


def test_a_verdict_keeps_every_value_it_was_given_on(tmp_path):
    done = judge(tmp_path, (0.40, True, ()))
    (verdict,) = done["verdicts"]
    assert verdict["predicates"][1] == {
        "id": "no-hot-facet",
        "value": 0.40,
        "passed": False,
        "side": "max",
    }


def test_a_verdict_without_a_check_is_what_it_always_was(tmp_path):
    run = loop.start("star", "after", root=tmp_path)
    loop.judged(run, tool_passed=True, person_accepted=True)
    assert set(run["verdicts"][0]) == {"tool_passed", "person_accepted", "why", "at"}


def test_a_bound_a_person_accepted_past_twice_is_too_tight(tmp_path):
    """The dim star: 0.37 refused a star a person accepted, and would again."""
    judge(tmp_path, (0.40, True, ()), (0.41, True, ()))
    (one,) = [b for b in loop.bounds(tmp_path) if b.get("id") == "no-hot-facet"]
    assert one["tight"] == [0.40, 0.41]
    assert one["side"] == "max"
    assert "no-hot-facet's max is too tight" in one["wrong"]
    assert "0.4, 0.41" in one["wrong"]


def test_once_is_not_a_pattern(tmp_path):
    judge(tmp_path, (0.40, True, ()))
    (one,) = loop.bounds(tmp_path)
    assert one["wrong"] is None


def test_a_rejection_counts_against_the_bound_a_person_named(tmp_path):
    judge(
        tmp_path,
        (0.30, False, ("no-hot-facet",)),
        (0.32, False, ("no-hot-facet",)),
    )
    (one,) = loop.bounds(tmp_path)
    assert one["loose"] == [0.30, 0.32]
    assert "too loose" in one["wrong"]


def test_a_rejection_naming_nothing_is_not_spread_over_every_pass(tmp_path):
    judge(tmp_path, (0.30, False, ()))
    assert loop.bounds(tmp_path) == [{"asset": "star_dim", "unattributed": 1}]


def test_the_wrong_bounds_come_first_and_one_asset_can_be_asked_for(tmp_path):
    judge(tmp_path, (0.40, True, ()), asset="star_gold")
    judge(tmp_path, (0.40, True, ()), (0.45, True, ()))
    found = loop.bounds(tmp_path)
    assert found[0]["asset"] == "star_dim"
    assert found[0]["wrong"]
    assert [b["asset"] for b in loop.bounds(tmp_path, asset="star_gold")] == [
        "star_gold"
    ]


def test_naming_a_predicate_the_check_lacks_is_refused(tmp_path):
    run = loop.start("star", "after", root=tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        loop.judged(
            run,
            tool_passed=True,
            person_accepted=False,
            check=checked(0.3),
            named=("no-hot-facets",),
        )
    assert refused.value.code == "loop.unknown-predicate"
    assert "no-hot-facet" in refused.value.remedy
