"""A fuzzy surface asked for as an intent, not as the constants that answer it.

§PW50's case: Cottony's plush look is eight shell-texturing constants found by eye, at
two minutes a sample, and a table of eight keys would be one project's look compiled in
while helping nobody who wanted fur instead. So the declaration states a depth and a
coarseness, and **the test of the design is whether a second surface, unlike cotton,
asks for itself in the same two words**.

The coarseness axis is not invented here. Its two ends are the two failures the
readings name: fibres grown straight off a smooth ball read as velvet rather than as
sherpa, and clumps alone gave hard beads. What worked is between them.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave.errors import PolyweaveError
from polyweave.geometry import solid as S
from polyweave.geometry import surface as F
from polyweave.post.mesh import check_mesh

#: What Cottony's readings settled on, as this vocabulary asks for it.
COTTON = {"depth": 3.0, "coarseness": 0.62}


# -- the axis is the two readings ------------------------------------------------------


def test_clumps_alone_are_the_hard_beads_the_readings_name():
    """Coarseness one is the far end: the fibre field is not mixed in at all."""
    made = F.construction({"depth": 3.0, "coarseness": 1.0})
    assert made["fibre_weight"] == 0.0
    assert made["clumps"] == min(F.CLUMPS)  # as few and as broad as it goes


def test_fibres_alone_are_the_velvet_rather_than_the_sherpa():
    """Coarseness nought is the other end, and a flat surface is what it leaves."""
    made = F.construction({"depth": 3.0, "coarseness": 0.0})
    assert made["fibre_weight"] == 1.0
    # Velvet is fibres on a flat surface: nothing rises under a clump that is not
    # there, and no tip leans towards a crown that is not there either.
    assert made["rise"] == 0.0
    assert made["lean"] == 0.0
    assert made["vary"] == 0.0


def test_what_worked_is_between_them_and_carries_both_fields():
    """Sherpa is the middle: clumps and fibres at once, which is the whole finding."""
    made = F.construction(COTTON)
    assert 0.0 < made["fibre_weight"] < 1.0
    assert made["rise"] > 0.0
    assert made["fibre"] > made["clumps"]  # the fibre field is the finer of the two


@pytest.mark.parametrize("coarseness", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_the_fibre_field_is_always_finer_than_its_clumps(coarseness):
    """A fibre field as coarse as its clumps is the clump field drawn twice."""
    made = F.construction({"depth": 2.0, "coarseness": coarseness})
    assert made["fibre"] > made["clumps"]


# -- the test of the design ------------------------------------------------------------


def test_a_second_surface_unlike_cotton_asks_in_the_same_two_words():
    """The design's own test. Three surfaces, six numbers, no new vocabulary."""
    velvet = F.construction({"depth": 0.6, "coarseness": 0.05})
    fur = F.construction({"depth": 9.0, "coarseness": 0.3})
    cotton = F.construction(COTTON)

    # Each asks with a depth and a coarseness and nothing else.
    assert set(F.ASKS) == {"depth", "coarseness"}

    # And each gets a construction that differs in every derived number.
    for field in ("shells", "edge", "clumps", "fibre", "fibre_weight", "vary"):
        assert len({velvet[field], fur[field], cotton[field]}) == 3, field

    # Fur stands furthest off the body and velvet barely off it at all.
    assert fur["depth"] > cotton["depth"] > velvet["depth"]
    # And the finer the surface, the more shells it takes to read as strands.
    assert velvet["shells"] > fur["shells"] > cotton["shells"]


def test_the_shell_count_is_read_off_coarseness_and_not_off_depth():
    """A strand needs the same samples along its length whether it is long or short.

    Which is also what keeps the count free of the declaration's units, since nothing
    here knows how big one of them is.
    """
    shallow = F.construction({"depth": 0.5, "coarseness": 0.4})
    deep = F.construction({"depth": 50.0, "coarseness": 0.4})
    assert shallow["shells"] == deep["shells"]


def test_the_lengths_a_fuzz_derives_are_all_fractions_of_its_depth():
    """Rise and lean are distances, so doubling the depth doubles them."""
    one = F.construction({"depth": 2.0, "coarseness": 0.8})
    two = F.construction({"depth": 4.0, "coarseness": 0.8})
    assert two["rise"] == pytest.approx(one["rise"] * 2)
    assert two["lean"] == pytest.approx(one["lean"] * 2)
    # The wander is a fraction and stays one, so it does not scale.
    assert two["vary"] == one["vary"]


# -- the shells ------------------------------------------------------------------------


def test_the_outermost_shell_sits_exactly_at_the_declared_depth():
    made = F.layers(COTTON)
    assert len(made) == F.construction(COTTON)["shells"]
    assert made[-1]["at"] == pytest.approx(COTTON["depth"])
    assert made[0]["at"] < made[-1]["at"]


def test_each_shell_keeps_less_than_the_one_under_it():
    """The threshold only rises, or an outer shell would draw what an inner one cut."""
    keeps = [shell["keeps"] for shell in F.layers(COTTON)]
    assert keeps == sorted(keeps)
    assert keeps[-1] == pytest.approx(1.0)


def test_a_sharper_cut_lifts_the_threshold_earlier_than_a_soft_one():
    """Which is what leaves thin strands rather than the broad tufts of a clump."""
    fine = F.layers({"depth": 3.0, "coarseness": 0.0})
    coarse = F.layers({"depth": 3.0, "coarseness": 1.0})
    assert F.construction({"depth": 3.0, "coarseness": 0.0})["edge"] > F.construction(
        {"depth": 3.0, "coarseness": 1.0}
    )["edge"]
    # Halfway up its own stack, the fine surface has already cut more away.
    assert fine[len(fine) // 2]["keeps"] > coarse[len(coarse) // 2]["keeps"]


def test_a_tip_leans_and_a_root_does_not():
    made = F.layers(COTTON)
    assert made[0]["lean"] < made[-1]["lean"]
    assert made[-1]["lean"] == pytest.approx(F.construction(COTTON)["lean"])


def test_the_spacing_is_the_depth_over_the_shells():
    assert F.spacing(COTTON) == pytest.approx(
        COTTON["depth"] / F.construction(COTTON)["shells"]
    )
    # A deeper fuzz at the same coarseness spreads the same shells further apart.
    assert F.spacing({"depth": 6.0, "coarseness": 0.62}) > F.spacing(COTTON)


# -- the stack, as meshes --------------------------------------------------------------


def test_the_stack_is_the_body_and_then_one_copy_per_shell():
    body = S.primitive("sphere", 10.0)
    built = F.stack(body, COTTON)
    assert len(built) == F.construction(COTTON)["shells"] + 1
    for one in built:
        check_mesh(one)


def test_the_body_comes_first_and_unchanged():
    """The shells are drawn over a surface that is still there."""
    body = S.primitive("sphere", 10.0)
    built = F.stack(body, COTTON)
    assert np.allclose(built[0]["vertices"], body["vertices"])


def test_every_shell_keeps_the_body_s_own_topology():
    """One surface drawn many times: the same faces, moved, and never re-stitched."""
    body = S.primitive("cube", 4.0)
    for one in F.stack(body, COTTON):
        assert one["faces"] == body["faces"]
        assert len(one["vertices"]) == len(body["vertices"])


def test_the_outermost_shell_stands_the_declared_depth_off_the_body():
    """On a sphere the normal is the radius, so the growth is readable exactly."""
    body = S.primitive("sphere", 10.0)
    built = F.stack(body, {"depth": 2.0, "coarseness": 0.5})
    was = np.linalg.norm(body["vertices"], axis=1).max()
    now = np.linalg.norm(built[-1]["vertices"], axis=1).max()
    assert now - was == pytest.approx(2.0, abs=1e-6)


def test_a_normal_on_a_sphere_points_away_from_its_centre():
    body = S.primitive("sphere", 10.0)
    along = F.normals(body)
    out = body["vertices"] / np.linalg.norm(body["vertices"], axis=1, keepdims=True)
    # The poles are where the ring degenerates, so they are left out of the reading.
    middle = np.abs(body["vertices"][:, 1]) < 4.0
    assert np.all(np.sum(along[middle] * out[middle], axis=1) > 0.9)


def test_a_body_with_nothing_in_it_is_refused_rather_than_shelled():
    with pytest.raises(PolyweaveError) as caught:
        F.stack({"vertices": [], "faces": []}, COTTON)
    assert caught.value.code == "geom.bad-surface"
    assert "surface on something" in caught.value.remedy


# -- what a material asks for ----------------------------------------------------------


def test_a_material_with_no_fuzz_asks_for_none():
    assert F.fuzz({"colour": "#F2E4D0", "roughness": 0.62}) is None
    assert F.fuzz(None) is None
    assert F.fuzz({}) is None


def test_a_material_carries_its_fuzz_beside_its_colour():
    coat = F.fuzz({"colour": "#F2E4D0", "fuzz": dict(COTTON)})
    assert coat == COTTON


def test_reaching_for_a_derived_constant_is_told_what_to_state_instead():
    """The point of the line: the constants are the answer, not the way to ask."""
    with pytest.raises(PolyweaveError) as caught:
        F.fuzz({"fuzz": {"depth": 3.0, "coarseness": 0.6, "shells": 20, "lean": 0.4}})
    assert caught.value.code == "geom.bad-surface"
    assert "lean, shells" in caught.value.message
    assert "derived from those two" in caught.value.remedy


@pytest.mark.parametrize(
    ("stated", "says"),
    [
        ({"depth": 3.0}, "no coarseness"),
        ({"coarseness": 0.5}, "no depth"),
        ({}, "no depth and no coarseness"),
    ],
)
def test_a_fuzz_missing_half_of_the_ask_names_the_half(stated, says):
    with pytest.raises(PolyweaveError) as caught:
        F.fuzz({"fuzz": stated})
    assert caught.value.code == "geom.bad-surface"
    assert says in caught.value.message


def test_a_fuzz_that_stands_nowhere_off_the_body_is_not_a_fuzz():
    with pytest.raises(PolyweaveError) as caught:
        F.fuzz({"fuzz": {"depth": 0.0, "coarseness": 0.5}})
    assert caught.value.code == "geom.bad-surface"
    assert "take the fuzz off the material" in caught.value.remedy


@pytest.mark.parametrize("coarseness", [-0.1, 1.4])
def test_a_coarseness_off_the_axis_is_refused_with_both_of_its_ends(coarseness):
    with pytest.raises(PolyweaveError) as caught:
        F.fuzz({"fuzz": {"depth": 3.0, "coarseness": coarseness}})
    assert caught.value.code == "geom.bad-surface"
    assert "velvet" in caught.value.remedy
    assert "beads" in caught.value.remedy


@pytest.mark.parametrize("stated", ["deep", True, None, [3.0]])
def test_a_depth_that_is_not_a_number_is_refused_where_it_is_read(stated):
    with pytest.raises(PolyweaveError) as caught:
        F.fuzz({"fuzz": {"depth": stated, "coarseness": 0.5}})
    assert caught.value.code == "geom.bad-surface"


def test_a_fuzz_that_is_not_a_table_says_how_one_is_written():
    with pytest.raises(PolyweaveError) as caught:
        F.fuzz({"fuzz": 3.0})
    assert caught.value.code == "geom.bad-surface"
    assert "coarseness = 0.62" in caught.value.remedy


# -- read back in words ----------------------------------------------------------------


def test_a_surface_reads_back_as_a_sentence_somebody_can_disagree_with():
    assert F.says(COTTON) == "fuzzy 3 deep, clumped"
    assert F.says({"depth": 0.6, "coarseness": 0.05}) == "fuzzy 0.6 deep, fine"
    assert F.says({"depth": 9.0, "coarseness": 0.3}) == "fuzzy 9 deep, fibrous"


def test_the_top_of_the_axis_reads_back_as_what_it_measured_there():
    """A declaration that says `beaded` has been told what it asked for."""
    assert F.band(1.0) == "beaded"
    assert F.band(0.0) == "fine"
