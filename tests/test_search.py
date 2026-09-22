"""Search the parameters rather than guessing them.

§PW13's cost is two minutes a sample, fourteen times over. What matters here is that the
loop converges on the values a spec asks for, spends no more than the budget it was
given, turns only what it was permitted to turn, and says what the winner scored against
every predicate rather than only that it won.

The evaluator is injected, so most of this runs without a renderer. The last test does
it for real.
"""

from __future__ import annotations

import pytest

from polyweave import accept, search
from polyweave.errors import PolyweaveError


def a_spec(**over):
    """A spec searching `light`, which some predicate is a function of."""
    declared = {
        "asset": "mascot",
        "predicate": [{"id": "bright", "measure": "alpha_coverage", "min": 0.5}],
        "search": {"light": {"min": 0.0, "max": 4.0}},
    }
    declared.update(over)
    return accept.parse(declared)


def peaking_at(target, *, name="light", width=4.0):
    """An evaluator whose score peaks where `name` equals `target`.

    Wide enough that a coarse grid can see the slope, which is what a real objective
    looks like: a rig number is not a needle in a haystack, it is a hill to climb.
    """
    calls = []

    def evaluate(values):
        calls.append(dict(values))
        distance = abs(values[name] - target)
        score = max(0.0, 1.0 - distance / width)
        return {
            "score": score,
            "passed": score >= 0.999,
            "predicates": [{"id": "bright", "margin": score, "passed": score >= 0.999}],
            "failed": [] if score >= 0.999 else ["bright"],
        }

    evaluate.calls = calls
    return evaluate


# -- it converges ---------------------------------------------------------------------


def test_the_search_finds_the_value_the_spec_asks_for():
    evaluate = peaking_at(3.0)
    found = search.search(a_spec(), evaluate, budget=30, points=3)
    assert found["best"]["light"] == pytest.approx(3.0, abs=0.3)
    assert found["score"] > 0.7


def test_refinement_beats_a_single_coarse_pass():
    """A coarse grid then local refinement, which is what makes the space affordable."""
    one = search.search(a_spec(), peaking_at(3.0), budget=30, points=3, passes=1)
    three = search.search(a_spec(), peaking_at(3.0), budget=30, points=3, passes=3)
    assert three["score"] > one["score"]


def test_it_reports_the_winner_against_every_predicate():
    """A spec satisfied by an ugly render is visible as that, not as a success."""
    found = search.search(a_spec(), peaking_at(3.0), budget=12)
    assert [p["id"] for p in found["predicates"]] == ["bright"]
    assert "margin" in found["predicates"][0]


def test_the_trace_holds_every_sample_it_took():
    evaluate = peaking_at(3.0)
    found = search.search(a_spec(), evaluate, budget=9, points=3)
    assert len(found["trace"]) == found["spent"]
    assert all({"params", "score", "passed"} == set(s) for s in found["trace"])


# -- the budget is the thing being managed ---------------------------------------------


def test_it_never_spends_more_than_its_budget():
    for budget in (1, 5, 17):
        evaluate = peaking_at(3.0)
        found = search.search(a_spec(), evaluate, budget=budget)
        assert found["spent"] <= budget
        assert len(evaluate.calls) == found["spent"]


def test_it_never_pays_for_the_same_sample_twice():
    evaluate = peaking_at(3.0)
    search.search(a_spec(), evaluate, budget=40, points=3)
    seen = [tuple(sorted(c.items())) for c in evaluate.calls]
    assert len(seen) == len(set(seen))


def test_a_search_that_has_its_answer_stops_paying():
    """No reason to keep rendering once the spec passes with nothing left to gain."""
    evaluate = peaking_at(2.0)  # 2.0 is on the first coarse grid of 0–4
    found = search.search(a_spec(), evaluate, budget=40, points=3)
    assert found["passed"] is True
    assert found["spent"] < 40
    assert found["stopped"] == "the spec passed with nothing left to gain"


def test_a_budget_of_nothing_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        search.search(a_spec(), peaking_at(3.0), budget=0)
    assert caught.value.code == "search.no-budget"


def test_the_budget_decides_how_fine_the_grid_is():
    """As fine as the budget affords, and never coarser than the ends of the range."""
    wide = a_spec(search={"a": {"min": 0.0, "max": 1.0}, "b": {"min": 0.0, "max": 1.0}})
    evaluate = peaking_at(0.5, name="a")
    found = search.search(wide, evaluate, budget=4, points=5, passes=1)
    assert found["spent"] <= 4


# -- it turns only what it was permitted to turn ---------------------------------------


def test_it_searches_only_the_named_parameters():
    evaluate = peaking_at(3.0)
    found = search.search(a_spec(), evaluate, budget=9)
    assert found["searched"] == ["light"]
    assert all(set(c) == {"light"} for c in evaluate.calls)


def test_a_spec_permitting_nothing_is_refused():
    """A parameter not named in [search] is not searched, whatever it would like."""
    with pytest.raises(PolyweaveError) as caught:
        search.search(a_spec(search={}), peaking_at(3.0))
    assert caught.value.code == "search.nothing-to-search"
    assert "not searched" in caught.value.remedy


def test_every_sample_stays_inside_the_declared_range():
    evaluate = peaking_at(9.0)  # the peak is outside the range, so it pulls at the edge
    search.search(a_spec(), evaluate, budget=30)
    assert all(0.0 <= c["light"] <= 4.0 for c in evaluate.calls)


def test_two_parameters_are_searched_together():
    spec = a_spec(
        search={"light": {"min": 0.0, "max": 4.0}, "form": {"min": 0.0, "max": 4.0}}
    )

    def evaluate(values):
        score = max(
            0.0, 1.0 - (abs(values["light"] - 2.0) + abs(values["form"] - 4.0)) / 8.0
        )
        return {"score": score, "passed": False, "predicates": [], "failed": ["x"]}

    found = search.search(spec, evaluate, budget=30, points=3)
    assert found["searched"] == ["form", "light"]
    assert found["best"]["form"] > found["best"]["light"]


# -- steps -----------------------------------------------------------------------------


def test_a_step_is_respected_by_every_sample():
    spec = a_spec(search={"light": {"min": 0.0, "max": 1.0, "step": 0.25}})
    evaluate = peaking_at(0.5)
    search.search(spec, evaluate, budget=20, points=3)
    for call in evaluate.calls:
        assert abs(round(call["light"] / 0.25) * 0.25 - call["light"]) < 1e-9


def test_a_grid_lands_on_the_ends_of_its_range():
    assert search.grid(0.0, 4.0, 3) == [0.0, 2.0, 4.0]
    assert search.grid(0.0, 1.0, 5, 0.25) == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_a_grid_of_one_value_is_that_value():
    assert search.grid(2.0, 2.0, 3) == [2.0]


# -- against a real renderer -----------------------------------------------------------


def test_a_search_turns_a_real_rig_number(tmp_path):
    """The loop end to end: a spec, a renderer, and a number nobody chose by hand."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )
    spec = accept.parse(
        {
            "asset": "sphere",
            "rung": "sphere",
            # A brighter key fills more of the frame above the alpha floor.
            "predicate": [
                {
                    "id": "reads-bright",
                    "measure": "luma_p99",
                    "region": "subject",
                    "min": 0.35,
                }
            ],
            "search": {"key": {"min": 10.0, "max": 2000.0}},
        }
    )
    found = search.sweep(spec, out="probe.png", root=tmp_path, budget=6, points=3)
    assert found["spent"] <= 6
    assert found["searched"] == ["key"]
    assert found["predicates"][0]["id"] == "reads-bright"
    # Whatever it settled on, a brighter key scored no worse than the dimmest sample.
    dimmest = min(found["trace"], key=lambda s: s["params"]["key"])
    assert found["score"] >= dimmest["score"]
