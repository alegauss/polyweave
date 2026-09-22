"""The acceptance spec: judgement turned into a gate.

§PW12's case is Cottony's repository, where nothing states that the face should read
the drawing's own colour or that the silhouette should match the drawn outline. The
knowledge existed; it was not written anywhere a later change could be checked against.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import accept, measure
from polyweave.errors import PolyweaveError


def png(tmp_path, name, *, size=(32, 32), colour=(232, 213, 196), coverage=1.0):
    rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    rows = max(1, int(round(size[1] * coverage)))
    rgba[:rows, :, :3] = colour
    rgba[:rows, :, 3] = 255
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def spec_file(tmp_path, text, name="mascot.accept.toml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# -- the spec is a file ---------------------------------------------------------------


def test_a_spec_states_its_predicates(tmp_path):
    found = accept.read(
        spec_file(
            tmp_path,
            'asset = "mascot"\nrung = "final"\n\n'
            "[[predicate]]\n"
            'id = "face-reads-cream"\n'
            'measure = "delta_e"\n'
            "region = [1, 1, 20, 20]\n"
            'target = "#E8D5C4"\n'
            "max = 2.0\n",
        )
    )
    assert found.asset == "mascot"
    assert found.rung == "final"
    assert len(found.predicates) == 1
    one = found.predicates[0]
    assert one.id == "face-reads-cream"
    assert one.measure == "delta_e"
    assert one.maximum == 2.0
    assert one.arguments == {"target": "#E8D5C4"}


def test_a_spec_with_no_predicates_checks_nothing_and_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(spec_file(tmp_path, 'asset = "mascot"\n'))
    assert caught.value.code == "spec.no-predicates"


def test_an_anonymous_predicate_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(
            spec_file(
                tmp_path,
                '[[predicate]]\nmeasure = "alpha_coverage"\nmin = 0.1\n',
            )
        )
    assert caught.value.code == "spec.anonymous-predicate"
    assert "cannot be discussed" in caught.value.remedy


def test_two_predicates_cannot_share_an_id(tmp_path):
    body = '[[predicate]]\nid = "a"\nmeasure = "alpha_coverage"\nmin = 0.1\n'
    with pytest.raises(PolyweaveError) as caught:
        accept.read(spec_file(tmp_path, body * 2))
    assert caught.value.code == "spec.duplicate-id"


def test_an_unknown_measure_is_refused_where_it_is_written(tmp_path):
    """The vocabulary is closed: a spec accepting any string silently checks nothing."""
    with pytest.raises(PolyweaveError) as caught:
        accept.read(
            spec_file(tmp_path, '[[predicate]]\nid = "a"\nmeasure = "vibes"\nmin = 1\n')
        )
    assert caught.value.code == "spec.unknown-measure"


def test_a_predicate_with_no_bound_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(
            spec_file(tmp_path, '[[predicate]]\nid = "a"\nmeasure = "alpha_coverage"\n')
        )
    assert caught.value.code == "spec.no-bound"
    assert "nothing can fail it" in caught.value.message


def test_a_bound_that_is_not_a_number_is_refused(tmp_path):
    """A predicate states a bound, not an expression."""
    with pytest.raises(PolyweaveError) as caught:
        accept.read(
            spec_file(
                tmp_path,
                '[[predicate]]\nid = "a"\nmeasure = "alpha_coverage"\nmin = "lots"\n',
            )
        )
    assert caught.value.code == "spec.bad-bound"


def test_a_field_the_spec_does_not_carry_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(
            spec_file(
                tmp_path,
                '[[predicate]]\nid = "a"\nmeasure = "alpha_coverage"\n'
                "min = 0.1\nteolerance = 3\n",
            )
        )
    assert caught.value.code == "spec.unknown-field"


def test_a_malformed_spec_says_where(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(spec_file(tmp_path, "[[predicate\n"))
    assert caught.value.code == "spec.malformed"
    assert caught.value.detail


def test_a_spec_that_is_not_there_says_so(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(tmp_path / "nobody.accept.toml")
    assert caught.value.code == "spec.missing"


# -- the search permission ------------------------------------------------------------


def test_the_search_ranges_are_the_whole_permission(tmp_path):
    found = accept.read(
        spec_file(
            tmp_path,
            '[[predicate]]\nid = "a"\nmeasure = "alpha_coverage"\nmin = 0.1\n\n'
            "[search.light]\nmin = 0.5\nmax = 4.0\n\n"
            "[search.form]\nmin = 1.0\nmax = 4.0\nstep = 0.1\n",
        )
    )
    assert set(found.search) == {"light", "form"}
    assert found.search["form"]["step"] == 0.1


def test_a_range_open_at_one_end_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        accept.read(
            spec_file(
                tmp_path,
                '[[predicate]]\nid = "a"\nmeasure = "alpha_coverage"\nmin = 0.1\n\n'
                "[search.light]\nmin = 0.5\n",
            )
        )
    assert caught.value.code == "spec.no-bound"


# -- the rung a verdict may be taken at ------------------------------------------------


def test_the_spec_needs_the_rung_its_measures_need(tmp_path):
    found = accept.read(
        spec_file(
            tmp_path,
            '[[predicate]]\nid = "a"\nmeasure = "saturation_p99"\nmin = 0.5\n\n'
            '[[predicate]]\nid = "b"\nmeasure = "alpha_coverage"\nmin = 0.1\n',
        )
    )
    assert found.needs_rung() == "preview"  # alpha_coverage needs the real mesh


def test_the_specs_own_rung_raises_the_floor_and_never_lowers_it(tmp_path):
    one = [{"id": "a", "measure": "saturation_p99", "min": 0.5}]
    assert accept.parse({"rung": "final", "predicate": one}).needs_rung() == "final"
    assert accept.parse({"rung": "sphere", "predicate": one}).needs_rung() == "sphere"


def test_a_verdict_below_the_specs_floor_is_refused(tmp_path):
    found = accept.parse(
        {
            "rung": "final",
            "predicate": [{"id": "a", "measure": "alpha_coverage", "min": 0.1}],
        }
    )
    with pytest.raises(PolyweaveError) as caught:
        accept.check(found, png(tmp_path, "r.png"), rung="sphere")
    assert caught.value.code == "spec.rung-too-low"


# -- checking --------------------------------------------------------------------------


def a_spec(**over):
    predicate = {
        "id": "covered",
        "measure": "alpha_coverage",
        "region": "frame",
        "min": 0.5,
    }
    predicate.update(over)
    return accept.parse({"asset": "mascot", "predicate": [predicate]})


def test_a_predicate_that_holds_passes(tmp_path):
    found = accept.check(a_spec(), png(tmp_path, "r.png"), rung="final")
    assert found["passed"] is True
    assert found["failed"] == []
    assert found["predicates"][0]["value"] == 1.0
    assert found["predicates"][0]["margin"] == 1.0


def test_a_predicate_that_does_not_hold_fails_by_name(tmp_path):
    spec = a_spec(min=0.9)
    found = accept.check(spec, png(tmp_path, "r.png", coverage=0.25))
    assert found["passed"] is False
    assert found["failed"] == ["covered"]


def test_a_failing_predicate_still_reports_how_close_it_came(tmp_path):
    """A pure boolean gives a search a cliff and nothing to climb."""
    near = accept.check(a_spec(min=1.0), png(tmp_path, "a.png", coverage=0.9))
    far = accept.check(a_spec(min=1.0), png(tmp_path, "b.png", coverage=0.2))
    assert near["predicates"][0]["passed"] is False
    assert far["predicates"][0]["passed"] is False
    assert near["predicates"][0]["margin"] > far["predicates"][0]["margin"]


def test_the_score_is_the_weighted_mean_of_the_margins(tmp_path):
    spec = accept.parse(
        {
            "predicate": [
                {"id": "a", "measure": "alpha_coverage", "min": 1.0, "weight": 3.0},
                {"id": "b", "measure": "alpha_coverage", "min": 1.0, "weight": 1.0},
            ]
        }
    )
    found = accept.check(spec, png(tmp_path, "r.png", coverage=1.0))
    assert found["score"] == 1.0
    assert [p["weight"] for p in found["predicates"]] == [3.0, 1.0]


def test_weight_defaults_to_one():
    assert a_spec().predicates[0].weight == 1.0


def test_the_rung_a_verdict_was_taken_at_is_reported(tmp_path):
    found = accept.check(a_spec(), png(tmp_path, "r.png"), rung="final")
    assert found["rung"] == "final"
    assert found["predicates"][0]["rung"] == "final"


def test_a_measure_a_bound_cannot_hold_is_refused(tmp_path):
    spec = accept.parse(
        {"predicate": [{"id": "c", "measure": "region_colour", "max": 50.0}]}
    )
    with pytest.raises(PolyweaveError) as caught:
        accept.check(spec, png(tmp_path, "r.png"))
    assert caught.value.code == "spec.unbounded-measure"
    assert "region_colour_p99" in caught.value.remedy


# -- the margin itself -----------------------------------------------------------------


def test_a_margin_is_one_inside_the_bound_and_climbs_towards_it():
    assert accept.margin(0.9, 0.5, None) == 1.0
    assert accept.margin(0.25, 0.5, None) == 0.5
    assert accept.margin(0.0, 0.5, None) == 0.0
    assert accept.margin(1.0, None, 2.0) == 1.0
    assert accept.margin(4.0, None, 2.0) == 0.5


def test_a_margin_between_two_bounds_takes_the_worse_of_them():
    assert accept.margin(0.5, 0.4, 0.6) == 1.0
    assert accept.margin(0.2, 0.4, 0.6) == 0.5


# -- the predicates Cottony would have written -----------------------------------------


def test_a_face_reads_the_drawings_own_colour(tmp_path):
    """delta_e against a hex target, which is the predicate that was never written."""
    cream = png(tmp_path, "cream.png", colour=(232, 213, 196))
    spec = accept.parse(
        {
            "predicate": [
                {
                    "id": "face-reads-cream",
                    "measure": "delta_e",
                    "target": "#E8D5C4",
                    "max": 2.0,
                }
            ]
        }
    )
    assert accept.check(spec, cream)["passed"] is True

    wrong = png(tmp_path, "blue.png", colour=(120, 150, 220))
    assert accept.check(spec, wrong)["passed"] is False


def test_a_silhouette_holds_against_a_reference(tmp_path):
    same = png(tmp_path, "a.png", coverage=0.5)
    spec = accept.parse(
        {
            "predicate": [
                {
                    "id": "silhouette-holds",
                    "measure": "silhouette_iou",
                    "against": str(same),
                    "region": "frame",
                    "min": 0.97,
                }
            ]
        }
    )
    assert accept.check(spec, same)["passed"] is True

    different = png(tmp_path, "b.png", coverage=0.2)
    found = accept.check(spec, different)
    assert found["passed"] is False
    assert 0.0 < found["predicates"][0]["margin"] < 1.0


def test_the_tall_dome_against_the_wide_low_cap(tmp_path):
    """The measure that would have caught it before the credits were spent."""
    wide = np.zeros((64, 64, 4), dtype=np.uint8)
    wide[40:, 8:56, 3] = 255
    tall = np.zeros((64, 64, 4), dtype=np.uint8)
    tall[8:, 24:40, 3] = 255
    for name, data in (("wide.png", wide), ("tall.png", tall)):
        PILImage.fromarray(data, "RGBA").save(tmp_path / name)

    iou = measure.measure(
        tmp_path / "tall.png",
        ["silhouette_iou"],
        against=tmp_path / "wide.png",
        region="frame",
    )[0]["value"]
    # Nowhere near the 0.97 a silhouette predicate would have asked for.
    assert iou < 0.3


def test_a_reference_of_another_size_still_compares(tmp_path):
    """A render and a drawing of different sizes are normalised before comparing."""
    big = png(tmp_path, "big.png", size=(64, 64), coverage=0.5)
    small = png(tmp_path, "small.png", size=(16, 16), coverage=0.5)
    iou = measure.measure(big, ["silhouette_iou"], against=small, region="frame")[0][
        "value"
    ]
    assert iou > 0.95
