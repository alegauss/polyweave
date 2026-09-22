"""Reading a shape before building it, because building it is the expensive place.

§PW33's case: two wrong constructions of Cottony's tray seats were built before the
right one, and both looked entirely reasonable while being written. Neither was visible
until rendered.
"""

from __future__ import annotations

import pytest
from tests.test_geometry import TRAY

from polyweave import geometry as G
from polyweave.errors import PolyweaveError
from polyweave.geometry import review
from polyweave.geometry import solid as S


def tray(tmp_path, body=TRAY):
    (tmp_path / "tray.toml").write_text(body, encoding="utf-8")
    return G.read("tray.toml", root=tmp_path)


def read(found, node):
    return next(one["says"] for one in found["nodes"] if one["id"] == node)


# -- the structural read, which costs nothing ----------------------------------------


def test_the_tray_reads_as_what_it_is(tmp_path):
    """A sentence somebody can disagree with, before anything is built."""
    found = review.describe(tray(tmp_path))
    assert "64 of them" in read(found, "seat")
    assert "8 by 8 grid" in read(found, "seat")
    assert "face with seat cut out of it" in read(found, "tray")


def test_a_plate_says_its_own_size(tmp_path):
    found = review.describe(tray(tmp_path))
    assert "928 by 928" in read(found, "face")


def test_an_extruded_outline_says_which_outline(tmp_path):
    found = review.describe(tray(tmp_path))
    assert "rounded_square" in read(found, "seat")
    assert "extruded" in read(found, "seat")


def test_a_material_is_named_where_a_node_wears_one(tmp_path):
    assert "in cushion" in read(review.describe(tray(tmp_path)), "face")


def test_the_nodes_read_in_the_order_they_build(tmp_path):
    found = review.describe(tray(tmp_path))
    ids = [one["id"] for one in found["nodes"]]
    assert ids.index("face") < ids.index("tray")
    assert ids.index("seat") < ids.index("tray")


def test_a_traced_outline_says_which_drawing_it_came_from(tmp_path):
    body = TRAY.replace(
        'outline = { shape = "rounded_square", size = "cell * 0.82", corner = 18 }',
        'outline = { image = "art/star.png", size = "cell * 0.82" }',
    )
    assert "traced from art/star.png" in read(
        review.describe(tray(tmp_path, body)), "seat"
    )


def test_the_read_carries_the_resolved_parameters(tmp_path):
    found = review.describe(tray(tmp_path))
    assert found["params"]["cell"] == 112.0
    assert found["output"] == "tray"


def test_a_parameter_given_at_the_call_changes_what_it_says(tmp_path):
    found = review.describe(tray(tmp_path), board=2)
    assert "4 of them" in read(found, "seat")


def test_one_instance_says_nothing_about_a_count(tmp_path):
    assert "of them" not in read(review.describe(tray(tmp_path)), "face")


# -- what is odd, found without building -----------------------------------------------


def test_a_node_nothing_uses_is_named(tmp_path):
    """It builds, it costs, and it is not in the output."""
    spare = 'id     = "spare"\nop     = "primitive"\nkind   = "cube"\n'
    body = TRAY.replace('id     = "tray"', f'{spare}\n[[nodes]]\nid     = "tray"')
    found = review.describe(tray(tmp_path, body))
    assert any("spare is built and nothing uses it" in one for one in found["warnings"])


def test_a_parameter_nothing_reads_is_named(tmp_path):
    body = TRAY.replace("bevel      = 2.0", "bevel      = 2.0\nunused     = 9.0")
    found = review.describe(tray(tmp_path, body))
    assert any(
        "unused is declared and no node reads it" in one for one in found["warnings"]
    )


def test_a_repeat_bigger_than_a_document_usually_means_is_named(tmp_path):
    body = TRAY.replace("board      = 8", "board      = 40")
    found = review.describe(tray(tmp_path, body))
    assert any("repeats 1600 times" in one for one in found["warnings"])


def test_a_document_with_nothing_odd_in_it_warns_about_nothing(tmp_path):
    assert review.describe(tray(tmp_path))["warnings"] == []


# -- the one that costs a build --------------------------------------------------------


def built_tray(tmp_path, **how):
    from polyweave.geometry import outline as O

    return {
        "face": S.plate([0, 0, 928, 928], 6, 28),
        "seat": S.prism(O.rounded_square(92, 18), 4),
        "tray": S.plate([0, 0, 928, 928], 6, 28),
        **how,
    }


def test_the_report_says_what_every_node_came_out_as(tmp_path):
    found = review.report(tray(tmp_path), built_tray(tmp_path))
    faces = {one["id"]: one["faces"] for one in found["nodes"]}
    assert faces["face"] > 0
    assert faces["seat"] > 0
    assert found["output"] == "tray"


def test_the_report_carries_the_instance_count_beside_the_faces(tmp_path):
    found = review.report(tray(tmp_path), built_tray(tmp_path))
    seat = next(one for one in found["nodes"] if one["id"] == "seat")
    assert seat["instances"] == 64


def test_the_report_says_where_the_output_ended_up(tmp_path):
    found = review.report(tray(tmp_path), built_tray(tmp_path))
    assert len(found["bounds"]) == 6
    assert found["bounds"][3] == pytest.approx(928.0)


def test_a_node_that_was_declared_and_not_built_is_named(tmp_path):
    built = built_tray(tmp_path)
    del built["seat"]
    found = review.report(tray(tmp_path), built)
    assert any("seat was declared and not built" in one for one in found["warnings"])


def test_a_boolean_that_returned_nothing_is_visible_in_the_face_count(tmp_path):
    """Which is the whole point of the per-node count."""
    with pytest.raises(PolyweaveError) as caught:
        review.report(
            tray(tmp_path),
            {**built_tray(tmp_path), "tray": {"vertices": [], "faces": []}},
        )
    assert caught.value.code == "post.mesh-empty"


def test_the_manifold_check_is_opt_in_because_it_walks_every_edge(tmp_path):
    plain = review.report(tray(tmp_path), built_tray(tmp_path))
    assert "manifold" not in plain["nodes"][0]
    checked = review.report(tray(tmp_path), built_tray(tmp_path), manifold=True)
    assert "manifold" in checked["nodes"][0]


def test_a_mesh_that_is_not_manifold_is_said_so_rather_than_raised(tmp_path):
    torn = {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "faces": [(0, 1, 2)]}
    found = review.report(
        tray(tmp_path), {**built_tray(tmp_path), "seat": torn}, manifold=True
    )
    seat = next(one for one in found["nodes"] if one["id"] == "seat")
    assert seat["manifold"] is False
    assert any("seat:" in one for one in found["warnings"])


def test_a_path_is_not_arithmetic_and_is_not_warned_about(tmp_path):
    """`art/star.png` parses as a division; evaluating it would break the file."""
    body = TRAY.replace(
        'outline = { shape = "rounded_square", size = "cell * 0.82", corner = 18 }',
        'outline = { image = "art/star.png", size = "cell * 0.82" }',
    )
    found = review.describe(tray(tmp_path, body))
    assert found["warnings"] == []


def test_a_typo_inside_an_expression_is_warned_about(tmp_path):
    """It reads as arithmetic and names something nothing declares, so it stays text."""
    body = TRAY.replace('depth    = "face_depth"', 'depth    = "face_depth + cel"')
    found = review.describe(tray(tmp_path, body))
    assert any(
        "face.depth reads as arithmetic over cel" in one for one in found["warnings"]
    )


def test_a_repeat_variable_is_in_scope_on_its_own_node(tmp_path):
    """`col` is fine on the seat and would be a typo anywhere else."""
    assert review.describe(tray(tmp_path))["warnings"] == []
