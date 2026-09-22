"""The preview ladder: which rung answers which question, and at what size.

§PW7's argument is a ratio — three seconds against two minutes — so the tests that
matter are about never climbing higher than the question needs. None of these starts a
renderer.
"""

from __future__ import annotations

import pytest

from polyweave import config as C
from polyweave import render
from polyweave.errors import PolyweaveError
from polyweave.render import ladder, rig


def project(tmp_path, text=None):
    if text is not None:
        (tmp_path / C.FILENAME).write_text(text, encoding="utf-8")
    return tmp_path


# -- which rung carries which question ---------------------------------------------


def test_a_surface_question_stops_at_the_sphere():
    assert ladder.rung_for("saturation_p99") == "sphere"
    assert ladder.rung_for("delta_e") == "sphere"
    assert ladder.rung_for("luma_mean") == "sphere"


def test_a_shape_question_needs_the_real_mesh_but_not_the_samples():
    assert ladder.rung_for("silhouette_iou") == "preview"
    assert ladder.rung_for("alpha_coverage") == "preview"


def test_a_question_about_the_render_itself_needs_all_of_it():
    assert ladder.rung_for("distance") == "final"
    assert ladder.rung_for("luma_bands") == "final"


def test_a_statistic_is_answered_where_its_measure_is():
    for suffix in ("_p1", "_p50", "_p99", "_mean", "_std"):
        assert ladder.rung_for(f"saturation{suffix}") == "sphere"


def test_an_unknown_measure_is_refused_by_the_name_the_spec_uses():
    with pytest.raises(PolyweaveError) as caught:
        ladder.rung_for("vibes")
    assert caught.value.code == "spec.unknown-measure"
    assert "saturation" in caught.value.remedy


def test_the_rung_is_the_highest_any_one_question_needs():
    assert ladder.lowest_rung(["saturation_p99", "delta_e"]) == "sphere"
    assert ladder.lowest_rung(["saturation_p99", "silhouette_iou"]) == "preview"
    assert ladder.lowest_rung(["silhouette_iou", "distance"]) == "final"


def test_an_asset_may_insist_on_more_than_its_measures_need():
    """`rung` in an acceptance spec is the lowest a verdict may be taken at."""
    assert ladder.lowest_rung(["saturation_p99"], floor="final") == "final"
    assert ladder.lowest_rung(["distance"], floor="sphere") == "final"


def test_asking_nothing_costs_the_cheapest_rung():
    assert ladder.lowest_rung([]) == "sphere"


def test_a_rung_the_ladder_has_no_meaning_for_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        ladder.check_rung("thumbnail")
    assert caught.value.code == "render.unknown-rung"


def test_a_project_chooses_which_rungs_not_what_they_mean():
    assert ladder.enabled(["final", "sphere"]) == ("sphere", "final")
    with pytest.raises(PolyweaveError) as caught:
        ladder.enabled(["flat"])
    assert caught.value.code == "render.unknown-rung"


def test_enabling_nothing_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        ladder.enabled([])
    assert caught.value.code == "render.no-rungs"


# -- the plan, which costs nothing ---------------------------------------------------


def test_a_plan_says_which_rung_and_why_before_anything_renders(tmp_path):
    found = render.plan(asking=["saturation_p99"], root=project(tmp_path))
    assert found["rung"] == "sphere"
    assert found["subject"] == "primitive"
    assert found["samples"] == 32
    assert found["size"] == 256
    assert "carries saturation_p99" in found["why"]


def test_a_named_rung_wins_over_the_question(tmp_path):
    found = render.plan("final", asking=["saturation_p99"], root=project(tmp_path))
    assert found["rung"] == "final"
    assert found["why"] == "named by the caller"
    assert found["size"] == 1024
    assert found["samples"] == 512


def test_each_rung_costs_less_than_the_one_above_it(tmp_path):
    """Pixels times samples is the lever, and it only goes one way up the ladder."""
    where = project(tmp_path)
    work = [
        render.plan(rung, root=where)["size"] ** 2
        * render.plan(rung, root=where)["samples"]
        for rung in ladder.RUNGS
    ]
    assert work == sorted(work)
    assert work[-1] > work[0] * 10  # the ratio the ladder exists for


def test_the_preview_rung_renders_a_decimated_mesh(tmp_path):
    found = render.plan("preview", root=project(tmp_path))
    assert found["subject"] == "mesh"
    assert found["decimate"] == render.PREVIEW_RATIO
    assert render.plan("final", root=project(tmp_path))["decimate"] == 1.0


def test_a_question_needing_a_rung_the_project_disabled_is_refused(tmp_path):
    where = project(tmp_path, '[render]\nrungs = ["sphere"]\n')
    with pytest.raises(PolyweaveError) as caught:
        render.plan(asking=["silhouette_iou"], root=where)
    assert caught.value.code == "render.rung-disabled"
    assert "sphere" in caught.value.remedy


def test_a_rung_with_no_sample_count_is_refused(tmp_path):
    where = project(
        tmp_path,
        '[render]\nrungs = ["sphere", "final"]\nsamples = { sphere = 8 }\n',
    )
    with pytest.raises(PolyweaveError) as caught:
        render.plan("final", root=where)
    assert caught.value.code == "render.no-samples"


def test_the_project_sets_the_sizes_and_the_seed(tmp_path):
    where = project(
        tmp_path,
        "[render]\npreview_size = 64\nfinal_size = 2048\nseed = 7\n",
    )
    assert render.plan("sphere", root=where)["size"] == 64
    assert render.plan("final", root=where)["size"] == 2048
    assert render.plan("sphere", root=where)["seed"] == 7


# -- the rig is arithmetic before it is a renderer -------------------------------------


def test_the_camera_distance_follows_the_subject_and_the_lens():
    small = rig.camera_for(rig.Rig(), (-1, -1, -1), (1, 1, 1))
    large = rig.camera_for(rig.Rig(), (-10, -10, -10), (10, 10, 10))
    assert large["distance"] == pytest.approx(small["distance"] * 10)
    long_lens = rig.camera_for(rig.Rig(focal_mm=200.0), (-1, -1, -1), (1, 1, 1))
    assert long_lens["distance"] > small["distance"]


def test_a_wider_margin_stands_further_back():
    close = rig.camera_for(rig.Rig(margin=1.0), (-1, -1, -1), (1, 1, 1))
    far = rig.camera_for(rig.Rig(margin=2.0), (-1, -1, -1), (1, 1, 1))
    assert far["distance"] == pytest.approx(close["distance"] * 2)


def test_the_camera_looks_at_the_middle_of_the_subject():
    found = rig.camera_for(rig.Rig(), (0, 0, 0), (2, 4, 6))
    assert found["look_at"] == (1.0, 2.0, 3.0)


def test_elevation_lifts_the_camera_on_the_up_axis():
    """§6 fixes Y as up, so elevation moves Y and nothing else lifts."""
    level = rig.camera_for(rig.Rig(elevation=0.0), (-1, -1, -1), (1, 1, 1))
    above = rig.camera_for(rig.Rig(elevation=60.0), (-1, -1, -1), (1, 1, 1))
    assert level["location"][1] == pytest.approx(0.0, abs=1e-9)
    assert above["location"][1] > level["location"][1]


def test_the_three_lights_are_placed_around_the_subject():
    lights = rig.lights_for(rig.Rig(), (-1, -1, -1), (1, 1, 1))
    assert [light["role"] for light in lights] == ["key", "fill", "rim"]
    assert lights[0]["energy"] > lights[1]["energy"]


def test_a_flat_subject_still_has_a_camera_position():
    """A plane has zero thickness, and dividing by its radius must not explode."""
    found = rig.camera_for(rig.Rig(), (0, 0, 0), (0, 0, 0))
    assert all(isinstance(v, float) for v in found["location"])


def test_the_rig_a_record_carries_is_every_number_that_moved_it():
    params = rig.as_params(rig.Rig(key=900.0))
    assert params["key"] == 900.0
    assert set(params) == {
        "azimuth",
        "elevation",
        "margin",
        "focal_mm",
        "key",
        "fill",
        "rim",
        "light_distance",
        "ambient",
        "exposure",
        "transparent",
    }


# -- the surface describes itself ------------------------------------------------------


def test_the_bake_operation_describes_every_rig_field():
    from polyweave.describe import describe

    found = describe("render.bake")
    names = {p["name"] for p in found["parameters"]}
    assert {"azimuth", "elevation", "focal_mm", "key", "fill", "rim"} <= names
    assert "report" not in names
    assert found["asynchronous"] is True
    assert found["produces"] == "render"
    azimuth = next(p for p in found["parameters"] if p["name"] == "azimuth")
    assert azimuth["range"] == [-360, 360]
    assert azimuth["unit"] == "deg"
