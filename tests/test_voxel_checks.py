"""What a voxel build is checked for before anything renders it (§PW97).

Each model is drawn with `cells`, so the defect it carries is visible in the test itself
and the cells a finding names can be checked against the drawing.
"""

from __future__ import annotations

import pytest

from polyweave import post
from polyweave.errors import PolyweaveError
from polyweave.geometry import voxels as V

LIMITS = {"parts": 1, "thread": 3, "budget": 0, "extent": [], "near_symmetry": 0.9}


def drawn(*layers, voxels=None):
    return {
        "name": "ship",
        "version": 1,
        "params": {},
        "materials": {"hull": {}},
        "nodes": [
            {
                "id": "art",
                "op": "cells",
                "legend": {"#": "hull"},
                "layers": list(layers),
            }
        ],
        "output": "art",
        "voxels": voxels or {"cell": 1.0},
    }


def found(document, root=None, **limits):
    made = V.voxelize(document, root=root or ".")
    if limits:
        return post.check("voxels", made, **{**LIMITS, **limits})
    return made["checks"]


def kinds(checks):
    return [one["check"] for one in checks["findings"]]


def test_a_clean_block_has_nothing_to_say():
    checks = found(drawn(["####", "####"]))
    assert checks["findings"] == []
    assert checks["parts"] == 1
    assert checks["symmetry"] == 1.0


def test_a_cell_floating_free_is_named():
    checks = found(drawn(["###..#", "###..."]))
    assert kinds(checks) == ["floating"]
    assert checks["findings"][0]["cells"] == [[5, 1, 0]]


def test_separate_parts_are_not_floating_when_the_document_says_so():
    document = drawn(["###..#", "###..."], voxels={"cell": 1.0, "parts": 2})
    assert "floating" not in kinds(found(document))


def test_a_piece_held_on_by_a_corner_reads_as_broken_off():
    checks = found(drawn(["...#", "###.", "###."]))
    assert kinds(checks) == ["diagonal"]
    assert checks["findings"][0]["cells"] == [[3, 2, 0]]


def test_a_thread_longer_than_the_project_allows_is_named():
    checks = found(drawn(["##......", "########", "##......"]))
    threads = [one for one in checks["findings"] if one["check"] == "thread"]
    assert len(threads) == 1
    assert threads[0]["count"] == 6
    assert (
        found(drawn(["##......", "########", "##......"]), thread=6)["findings"] == []
    )


def test_a_sheet_one_cell_thick_is_not_a_thread():
    checks = found(drawn(["#####", "#####", "#####"]))
    assert "thread" not in kinds(checks)


def test_a_model_over_the_budget_is_reported():
    checks = found(drawn(["####", "####"]), budget=6)
    assert kinds(checks) == ["budget"]
    assert "8 cells, over the 6" in checks["findings"][0]["says"]


def ball(**voxels):
    return {
        "name": "saucer",
        "version": 1,
        "params": {"skin": 2},
        "materials": {},
        "nodes": [{"id": "ball", "op": "primitive", "kind": "sphere", "size": 20.0}],
        "output": "ball",
        "voxels": {"cell": 1.0, **voxels},
    }


def test_a_budget_finding_says_how_many_cells_are_buried():
    """§PW234: a model over on its inside is told to hollow, not to shrink."""
    checks = found(ball(), budget=3000)
    over = checks["findings"][0]
    assert over["check"] == "budget"
    assert over["buried"] > over["count"] / 2
    assert "[voxels] hollow = 1" in over["says"]


def test_a_hollowed_model_keeps_its_skin_and_nothing_under_it():
    whole = V.voxelize(ball())
    hollow = V.voxelize(ball(hollow=1))
    assert hollow["size"] == whole["size"]
    assert hollow["count"] < whole["count"] / 2
    assert found(ball(hollow=1), budget=3000)["findings"] == []
    cells = set(
        zip(*(hollow["cells"][a] for a in "xyz"), strict=True)
    )
    assert (10, 10, 10) not in cells
    assert (10, 10, 0) in cells


def test_a_thicker_skin_is_an_expression_over_the_parameters():
    one = V.voxelize(ball(hollow=1))["count"]
    two = V.voxelize(ball(hollow="skin"))["count"]
    assert one < two < V.voxelize(ball())["count"]


@pytest.mark.parametrize("depth", [-1, 1.5])
def test_a_skin_that_is_not_whole_cells_is_refused(depth):
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(ball(hollow=depth))
    assert refused.value.code == "geom.bad-voxels"


def test_a_model_off_its_extent_says_by_how_much():
    checks = found(drawn(["####", "####"]), extent=[8, 2, 1])
    assert kinds(checks) == ["extent"]
    assert "more than a cell off in x" in checks["findings"][0]["says"]
    assert found(drawn(["####", "####"]), extent=[4.5, 2, 1])["findings"] == []


def test_a_model_nearly_symmetric_names_the_cells_without_a_partner():
    wing = "##########"
    checks = found(drawn([wing, wing, "#########."]))
    assert kinds(checks) == ["symmetry"]
    assert checks["symmetry"] == pytest.approx(28 / 29, abs=1e-4)
    assert checks["findings"][0]["cells"] == [[0, 0, 0]]


WAVE = ["##########", "##########", "#########."]


def test_the_symmetry_finding_names_its_model():
    """§PW241: a family's build prints several models, so the finding says which."""
    checks = found(drawn(*[WAVE]))
    assert checks["findings"][0]["says"].startswith("ship: ")


@pytest.mark.parametrize(
    "voxels", [{"near_symmetry": 0.99}, {"asymmetric": True}], ids=["bar", "meant"]
)
def test_a_declaration_may_say_its_asymmetry_is_meant(voxels):
    checks = found(drawn(WAVE, voxels={"cell": 1.0, **voxels}))
    assert "symmetry" not in kinds(checks)


def test_asymmetric_is_true_or_false():
    with pytest.raises(PolyweaveError) as refused:
        found(drawn(WAVE, voxels={"cell": 1.0, "asymmetric": "yes"}))
    assert refused.value.code == "geom.bad-voxels"


def test_one_variant_may_be_one_sided_while_its_base_is_checked():
    from polyweave import geometry as G

    document = drawn(WAVE)
    document["variants"] = {"wave": {"voxels": {"asymmetric": True}}}
    base = found(document)
    member = found(G.variant(document, "wave"))
    assert "symmetry" in kinds(base)
    assert "symmetry" not in kinds(member)


def test_a_variant_may_not_change_the_rest_of_voxels():
    from polyweave import geometry as G

    document = drawn(WAVE)
    document["variants"] = {"big": {"voxels": {"cell": 2.0}}}
    with pytest.raises(PolyweaveError) as refused:
        G.variant(document, "big")
    assert refused.value.code == "geom.unknown-field"
    assert refused.value.at == "variants.big.voxels.cell"


def test_a_model_far_from_symmetric_is_not_nagged_about_it():
    checks = found(drawn(["#...", "##..", "###.", "####"]))
    assert "symmetry" not in kinds(checks)


def test_the_project_config_sets_the_limits(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[voxels]\nbudget = 4\n", encoding="utf-8")
    checks = found(drawn(["####", "####"]), root=tmp_path)
    assert kinds(checks) == ["budget"]


def test_a_model_with_no_cells_is_refused():
    with pytest.raises(PolyweaveError) as refused:
        post.check("voxels", {"name": "none", "count": 0}, **LIMITS)
    assert refused.value.code == "post.voxels-empty"


def test_a_limit_left_unstated_is_refused_rather_than_invented():
    made = V.voxelize(drawn(["#"]))
    with pytest.raises(PolyweaveError) as refused:
        post.check("voxels", made, parts=1)
    assert refused.value.code == "post.tolerance-unstated"
