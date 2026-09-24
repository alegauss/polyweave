"""Passing is not the same as passing comfortably (§PW104)."""

from __future__ import annotations

import pytest

from polyweave import search as S
from polyweave.accept import Spec, headroom


def test_headroom_is_the_room_to_the_nearer_bound():
    assert headroom(0.4, 0.3, 0.5) == pytest.approx(0.5)
    assert headroom(0.31, 0.3, 0.5) == pytest.approx(0.05)
    # The stars' gold facet: 0.0005 under a ceiling of 0.47 is a thousandth of it.
    assert headroom(0.4695, None, 0.47) == pytest.approx(0.001064, abs=1e-6)
    assert headroom(0.6, 0.3, 0.5) < 0
    assert headroom(0.6, None, None) is None


def band():
    """An evaluator holding a value in [0.3, 0.5], shaped as `accept.check` answers."""

    def evaluate(params):
        value = params["x"]
        room = headroom(value, 0.3, 0.5)
        passed = 0.3 <= value <= 0.5
        return {
            "passed": passed,
            "score": 1.0 if passed else 0.5,
            "predicates": [{"id": "tone", "value": value, "passed": passed}],
            "failed": [] if passed else ["tone"],
            "headroom": room,
            "tightest": "tone",
        }

    return evaluate


SPEC = Spec(
    asset="star", rung=None, predicates=(), search={"x": {"min": 0.0, "max": 1.0}}
)


def test_the_search_keeps_going_for_room_once_it_passes():
    found = S.search(SPEC, band(), budget=60, points=5, passes=6)
    assert found["passed"]
    assert found["best"]["x"] == pytest.approx(0.4, abs=0.02)
    assert found["headroom"] > 0.45
    assert found["tightest"] == "tone"


def test_it_stops_when_a_pass_finds_no_more_room():
    found = S.search(SPEC, band(), budget=500, points=5, passes=20)
    assert (
        found["stopped"] == "the spec passed, and a further pass found no more headroom"
    )
    assert found["spent"] < 500


def test_an_evaluator_that_measures_no_headroom_stops_at_the_first_pass():
    def plain(params):
        passed = 0.3 <= params["x"] <= 0.5
        return {"passed": passed, "score": 1.0 if passed else 0.5}

    found = S.search(SPEC, plain, budget=60, points=5)
    assert found["stopped"] == "the spec passed with nothing left to gain"
    assert found["headroom"] is None
