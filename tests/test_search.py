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
    assert all(
        {"params", "score", "passed", "predicates", "render"} == set(s)
        for s in found["trace"]
    )


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


# -- a pass at a time rather than a sample at a time (§PW45) ---------------------------


def batched(target, *, name="light", width=4.0):
    """The same objective, handed a whole pass and answering with a list."""
    one = peaking_at(target, name=name, width=width)
    passes = []

    def evaluate_all(samples):
        passes.append(list(samples))
        return [one(v) for v in samples]

    evaluate_all.passes = passes
    evaluate_all.calls = one.calls
    return evaluate_all


def test_a_whole_pass_is_handed_over_at_once():
    """Four samples were meant to be four handles, not four waits."""
    every = batched(2.7)
    search.search(a_spec(), evaluate_all=every, budget=24, points=3, passes=3)
    assert every.passes, "it was called"
    assert all(len(p) > 1 for p in every.passes), "with a pass, not a sample"
    assert sum(len(p) for p in every.passes) == len(every.calls)


def test_batching_a_pass_finds_the_same_answer_as_one_at_a_time():
    """The batching is about when renders happen, never about what is searched."""
    alone = peaking_at(2.7)
    every = batched(2.7)
    one = search.search(a_spec(), alone, budget=24, points=3, passes=3)
    many = search.search(a_spec(), evaluate_all=every, budget=24, points=3, passes=3)
    assert many["best"] == one["best"]
    assert many["spent"] == one["spent"]
    assert many["trace"] == one["trace"]


def test_a_batch_never_exceeds_what_the_budget_still_affords():
    """The pass is cut before it is handed over, not after it is paid for."""
    every = batched(2.7)
    found = search.search(a_spec(), evaluate_all=every, budget=5, points=4, passes=3)
    assert found["spent"] <= 5
    assert sum(len(p) for p in every.passes) <= 5


def test_a_batch_holds_no_sample_twice():
    every = batched(2.7)
    search.search(a_spec(), evaluate_all=every, budget=24, points=3, passes=3)
    for one in every.passes:
        keys = [tuple(sorted(v.items())) for v in one]
        assert len(keys) == len(set(keys))


def test_a_search_that_has_its_answer_still_stops_between_passes():
    """Which is why a pass is batched and not the whole budget."""
    every = batched(2.0)
    found = search.search(a_spec(), evaluate_all=every, budget=24, points=3, passes=3)
    assert found["stopped"] == "the spec passed with nothing left to gain"
    assert found["spent"] < 24


def test_an_evaluator_that_loses_a_sample_is_refused():
    """Results are matched by position, so a short list scores the wrong parameters."""

    def drops_one(samples):
        return [{"score": 1.0, "passed": True}] * (len(samples) - 1)

    with pytest.raises(PolyweaveError) as caught:
        search.search(a_spec(), evaluate_all=drops_one, budget=8, points=3)
    assert caught.value.code == "search.batch-mismatch"


def test_exactly_one_evaluator_is_required():
    with pytest.raises(PolyweaveError) as caught:
        search.search(a_spec(), budget=8)
    assert caught.value.code == "search.no-evaluator"

    with pytest.raises(PolyweaveError) as caught:
        search.search(a_spec(), peaking_at(2.7), evaluate_all=batched(2.7), budget=8)
    assert caught.value.code == "search.no-evaluator"


# -- and whether it is worth it, which is measured ------------------------------------


def test_the_crossing_point_is_where_serial_and_parallel_meet():
    """Serial is lanes*one; parallel is one+start. They meet at start/(lanes-1)."""
    assert search.crossing_point(lanes=4, start_s=0.9) == pytest.approx(0.3)
    assert search.crossing_point(lanes=2, start_s=0.9) == pytest.approx(0.9)


def test_the_cheap_rung_is_not_worth_parallelising_and_the_dear_one_is():
    """Measured on Blender 5.2.1: a sphere renders in 0.24s and a final in 11.44s."""
    assert not search.worth_parallel(0.24), "four spheres: 0.95s serial, 1.09s parallel"
    assert search.worth_parallel(11.44), "four finals: 45.78s serial, 12.30s parallel"


def test_more_lanes_make_parallel_worth_it_sooner():
    assert search.crossing_point(lanes=8) < search.crossing_point(lanes=4)


# -- a name this renderer takes, meant differently elsewhere (§PW63) -------------------


def test_every_axis_comes_back_with_what_it_is_measured_in():
    """The guard refuses a name nothing takes; it cannot see a name that means else.

    Cottony calls the fraction of the frame a model fills `fill`, and here `fill` is a
    light in watts. Copying 0.92 across asks for a 0.92-watt fill light and gets a
    nearly black picture, and nothing refuses it because `fill` is a knob this really
    has. Saying the unit back is what puts that in front of whoever wrote it.
    """
    from polyweave.search import turnable

    def draw(*, fill=120.0, key=400.0, ambient=0.25, exposure=0.0, **rest):
        return {}

    found = turnable(draw, {"fill": {}, "key": {}, "ambient": {}})
    assert "fill (W)" in found
    assert "key (W)" in found
    assert any(one.startswith("ambient (") and "multiplier" in one for one in found)


def test_a_near_match_is_offered_with_its_unit_too():
    from polyweave.errors import PolyweaveError
    from polyweave.search import turnable

    def draw(*, exposure=0.0):
        return {}

    with pytest.raises(PolyweaveError) as caught:
        turnable(draw, {"exposur": {}})
    assert caught.value.code == "search.unknown-parameter"
    assert "exposure (stops)" in caught.value.remedy


def test_a_parameter_with_no_declared_unit_is_named_plainly():
    """Nothing is invented for a knob nobody measured; it comes back as its own name."""
    from polyweave.search import turnable

    def draw(*, transparent=True):
        return {}

    assert turnable(draw, {"transparent": {}}) == ["transparent"]


def test_the_three_cottony_collisions_each_read_as_a_different_thing():
    """Named together because it is the set that was measured, not one example."""
    from polyweave.render.rig import UNITS, described

    assert UNITS["fill"] == "W", "Cottony's fill is a fraction of the frame"
    assert UNITS["key"] == "W", "Cottony's key is a width, as a share of the reach"
    assert "multiplier" in UNITS["ambient"], "Cottony's ambient scales the rig's"
    assert described("fill") == "fill (W)"
