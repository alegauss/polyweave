"""A shape's own numbers, reachable from the search that tunes everything else.

§PW32's case: the rig's parameters live in a dataclass and the geometry's live inside
Python modules, so a search can reach the lighting and never the shape it is lighting.

Nothing here renders. The build and the judgement are both injected, which is what lets
the rebuild counting be checked at all.
"""

from __future__ import annotations

import pytest

from polyweave import accept, geometry
from polyweave.errors import PolyweaveError
from polyweave.geometry import tuning
from polyweave.search import rebuilds_in, slowest_first

SHAPE = """
name   = "tray"
output = "tray"

[params]
cell  = 100.0
bevel = 2.0
pad   = 8.0

[[nodes]]
id    = "face"
op    = "plate"
rect  = ["0", "0", "cell + pad * 2", "cell + pad * 2"]
depth = 4

[[nodes]]
id     = "tray"
op     = "bevel"
of     = "face"
amount = "bevel"
"""

SPEC = """
asset = "tray"
rung  = "preview"

[[predicate]]
id      = "coverage"
measure = "alpha_coverage"
min     = 0.2
max     = 0.8

[search.bevel]
min = 1.0
max = 4.0

[search.exposure]
min = -1.0
max = 1.0
"""


def shape(tmp_path, body=SHAPE):
    (tmp_path / "tray.toml").write_text(body, encoding="utf-8")
    return geometry.read("tray.toml", root=tmp_path)


def spec(tmp_path, body=SPEC):
    (tmp_path / "tray.accept.toml").write_text(body, encoding="utf-8")
    return accept.read("tray.accept.toml", root=tmp_path)


# -- which parameters are the shape's ------------------------------------------------


def test_the_document_says_which_names_are_the_shape_s(tmp_path):
    found = tuning.split(shape(tmp_path), spec(tmp_path))
    assert found["shape"] == ["bevel"]
    assert found["rig"] == ["exposure"]


def test_what_each_shape_parameter_rebuilds_is_known(tmp_path):
    found = tuning.split(shape(tmp_path), spec(tmp_path))
    assert found["rebuilds"]["bevel"] == ["tray"]


def test_a_search_over_a_name_the_shape_lacks_is_refused(tmp_path):
    """Or a budget turns a knob attached to nothing and reports it as a finding."""
    with pytest.raises(PolyweaveError) as caught:
        tuning.addressable(shape(tmp_path), ["bevle"])
    assert caught.value.code == "geom.unknown-name"
    assert "bevel" in caught.value.remedy


def test_a_rig_parameter_is_not_asked_of_the_shape(tmp_path):
    found = tuning.split(shape(tmp_path), spec(tmp_path))
    assert "exposure" not in found["rebuilds"]


# -- the ordering, which is the whole of the cost argument -----------------------------


def test_the_expensive_axes_are_swept_slowest():
    """The product varies its last axis fastest, so the rebuilding names go first."""
    assert slowest_first(["a", "shape", "z"], ["shape"]) == ["shape", "a", "z"]


def test_with_nothing_expensive_it_is_plain_sorting():
    assert slowest_first(["b", "a"], []) == ["a", "b"]


def test_counting_rebuilds_counts_the_times_the_shape_changed():
    samples = [
        {"params": {"s": 1, "r": 0}},
        {"params": {"s": 1, "r": 1}},
        {"params": {"s": 2, "r": 0}},
        {"params": {"s": 2, "r": 1}},
    ]
    assert rebuilds_in(samples, ["s"]) == 2, "two shapes, two builds"


def test_an_unordered_sweep_would_rebuild_on_every_sample():
    scrambled = [
        {"params": {"s": 1, "r": 0}},
        {"params": {"s": 2, "r": 0}},
        {"params": {"s": 1, "r": 1}},
        {"params": {"s": 2, "r": 1}},
    ]
    assert rebuilds_in(scrambled, ["s"]) == 4, "every sample, which is what to avoid"


# -- a mixed search --------------------------------------------------------------------


def searching(tmp_path, judge=None, build=None):
    built = []

    def default_build(resolved):
        built.append(resolved["params"]["bevel"])
        return {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "faces": [(0, 1, 2)]}

    def default_judge(mesh, values):
        # A score that peaks where the bevel is two and the exposure is zero.
        score = 1.0 - abs(values["bevel"] - 2.0) / 4.0 - abs(values["exposure"]) / 4.0
        return {"passed": score > 0.95, "score": score, "predicates": [], "failed": []}

    found = tuning.tune(
        shape(tmp_path),
        spec(tmp_path),
        build or default_build,
        judge or default_judge,
        budget=9,
        passes=1,
    )
    return found, built


def test_a_mixed_search_turns_the_shape_and_the_rig_together(tmp_path):
    found, _ = searching(tmp_path)
    assert found["shape"] == ["bevel"]
    assert found["rig"] == ["exposure"]
    assert set(found["best"]) == {"bevel", "exposure"}


def test_it_builds_once_per_shape_and_not_once_per_sample(tmp_path):
    """The whole cost argument, counted rather than claimed."""
    found, built = searching(tmp_path)
    assert found["built"] < found["naive_builds"]
    assert found["built"] == len(set(built))
    assert len(built) == found["built"], "no shape was built twice"


def test_the_answer_says_how_many_rebuilds_it_paid_for(tmp_path):
    found, _ = searching(tmp_path)
    assert found["rebuilds"] == found["built"]
    assert found["rebuilding"] == ["bevel"]


def test_the_rig_is_swept_over_each_shape_before_the_next(tmp_path):
    _, built = searching(tmp_path)
    assert built == sorted(built), "one pass through the shapes, in order"


# -- a value that makes an invalid mesh ------------------------------------------------


def test_a_build_that_refuses_is_a_failed_sample_and_not_a_dead_search(tmp_path):
    """A wall thickness that goes negative gives an invalid mesh, not a poor render."""

    def build(resolved):
        if resolved["params"]["bevel"] > 3.0:
            raise PolyweaveError(
                "post.mesh-empty",
                "the bevel ate the plate",
                "keep the bevel under half the wall",
            )
        return {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "faces": [(0, 1, 2)]}

    def judge(mesh, values):
        return {"passed": False, "score": 0.5, "predicates": [], "failed": []}

    found = tuning.tune(
        shape(tmp_path), spec(tmp_path), build, judge, budget=9, passes=1
    )
    assert found["refused"], "the invalid combinations are reported"
    assert found["spent"] > len(found["refused"]), "and the valid ones still ran"
    assert found["score"] == 0.5, "a search that died would have no score at all"


def test_the_refusal_says_which_values_it_was(tmp_path):
    def build(resolved):
        raise PolyweaveError("post.mesh-empty", "nothing came out", "try smaller")

    def judge(mesh, values):  # pragma: no cover - never reached
        return {"passed": True, "score": 1.0, "predicates": [], "failed": []}

    found = tuning.tune(
        shape(tmp_path), spec(tmp_path), build, judge, budget=4, passes=1
    )
    assert all("bevel" in one["params"] for one in found["refused"])
    assert found["passed"] is False
