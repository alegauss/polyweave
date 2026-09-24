"""One rig searched against every member of a family (§PW105)."""

from __future__ import annotations

import pytest

from polyweave import search as S
from polyweave.accept import Spec, headroom, margin

AXES = {"x": {"min": 0.0, "max": 1.0}}


def member(name, predicate, low, high):
    """A member holding x inside [low, high], answering as `accept.check` does."""

    def evaluate(values):
        x = values["x"]
        passed = (low is None or x >= low) and (high is None or x <= high)
        room = headroom(x, low, high)
        return {
            "passed": passed,
            "score": 1.0 if passed else margin(x, low, high),
            "predicates": [
                {
                    "id": predicate,
                    "value": x,
                    "passed": passed,
                    "margin": margin(x, low, high),
                }
            ],
            "failed": [] if passed else [predicate],
            "headroom": room,
            "tightest": predicate,
        }

    spec = Spec(asset=name, rung=None, predicates=(), search=AXES)
    return {"name": name, "spec": spec, "evaluate": evaluate}


def test_the_rig_that_holds_on_every_member_is_found_directly():
    found = S.family(
        [
            member("gold", "tone", 0.3, 0.5),
            member("dim", "facet", 0.4, 0.7),
        ],
        budget=80,
        points=5,
        passes=6,
    )
    assert found["passed"]
    assert 0.4 <= found["best"]["x"] <= 0.5
    assert found["members"]["gold"]["passed"] and found["members"]["dim"]["passed"]
    assert found["tightest"] in ("gold:tone", "dim:facet")
    assert "conflict" not in found


def test_a_member_that_fails_fails_the_sample():
    found = S.family(
        [member("gold", "tone", 0.0, 1.0), member("dim", "facet", 0.9, 1.0)],
        budget=40,
        points=5,
    )
    assert found["best"]["x"] >= 0.9


def test_where_nothing_holds_the_answer_is_the_conflict():
    found = S.family(
        [
            member("gold", "tone", None, 0.4),
            member("dim", "facet", 0.6, None),
        ],
        budget=40,
        points=5,
    )
    assert not found["passed"]
    conflict = found["conflict"]
    assert conflict["between"] == ["dim:facet", "gold:tone"]
    # The sample nearest each side: the one holding it that comes closest to the other.
    assert conflict["closest_to"]["gold:tone"]["x"] <= 0.4
    assert conflict["closest_to"]["dim:facet"]["x"] >= 0.6
    assert conflict["closest_to"]["gold:tone"]["x"] == pytest.approx(0.4, abs=0.13)
    assert conflict["never"] == []


def test_a_predicate_no_sample_ever_held_is_named():
    found = S.family(
        [member("gold", "tone", 0.3, 0.5), member("dim", "facet", 2.0, 3.0)],
        budget=20,
        points=5,
    )
    assert found["conflict"] == {
        "between": None,
        "closest_to": {},
        "never": ["dim:facet"],
    }
