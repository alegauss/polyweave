"""A declaration composed into the mesh it describes.

§PW60's case: every piece either side of this was built and nothing composed them. The
op functions, the build order and the report that reads the result all shipped, and the
spec's own worked example could not be produced by any call in the package.

The tray is that example, copied from `docs/specs/geometry.md` into `test_geometry.py`
and imported here, so the thing being built is the thing the spec documents.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from tests.test_geometry import TRAY

from polyweave import geometry as G
from polyweave.errors import PolyweaveError
from polyweave.geometry import build as B
from polyweave.geometry import review
from polyweave.post.mesh import check_mesh


def document(tmp_path, body=TRAY, name="tray.toml"):
    (tmp_path / name).write_text(body, encoding="utf-8")
    return G.read(name, root=tmp_path)


def solving():
    from polyweave.geometry import solver

    found = solver.available()
    if not found["ready"]:
        pytest.skip(found["why"])


def one(op, **fields):
    """A one-node document, for an op that needs nothing else built first."""
    return {
        "name": "just_one",
        "version": 1,
        "params": {},
        "materials": {},
        "nodes": [{"id": "it", "op": op, **fields}],
        "output": "it",
    }


# -- the ops, each built through the table rather than called directly -----------------


@pytest.mark.parametrize(
    "node",
    [
        {"op": "primitive", "kind": "sphere", "size": 4.0},
        {"op": "primitive", "kind": "cube", "size": 2.0},
        {"op": "prism", "outline": {"shape": "circle", "radius": 3.0}, "depth": 2.0},
        {"op": "plate", "rect": [0, 0, 40, 40], "depth": 3.0, "corner": 4.0},
        {
            "op": "crowned",
            "outline": {"shape": "rounded_square", "size": 20.0},
            "depth": 2.0,
            "crown": 3.0,
        },
        {"op": "annulus", "outer": 10.0, "inner": 4.0, "depth": 2.0},
        {
            "op": "inflate",
            "outline": {"shape": "rounded_square", "size": 20.0, "corner": 4.0},
            "thickness": 6.0,
        },
    ],
)
def test_every_op_that_needs_no_solver_builds_a_mesh(tmp_path, node):
    found = B.build(one(node.pop("op"), **node), root=tmp_path)
    check_mesh(found["output"])
    assert found["report"]["nodes"][0]["faces"] > 0


def test_an_op_nothing_builds_is_refused_by_name(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        B.build(one("extrude_along_spline", depth=1.0), root=tmp_path)
    assert caught.value.code == "geom.unknown-op"
    assert "prism" in caught.value.remedy
    assert "custom" in caught.value.remedy


def test_an_op_nothing_builds_is_warned_about_before_anything_is_built(tmp_path):
    """The cheap half of the same answer, off the builder's own table (§PW60)."""
    found = review.describe(one("extrude_along_spline", depth=1.0))
    assert any("nothing builds that" in w for w in found["warnings"])


def test_the_warning_and_the_refusal_cannot_drift(tmp_path):
    """One list decides both, which is why there is a table and not an if/elif."""
    for op in B.BUILDS:
        assert B.builds(op) is True
    assert B.builds("extrude_along_spline") is False


# -- what a repeat means ---------------------------------------------------------------


def test_a_repeated_node_builds_one_mesh_for_the_whole_set(tmp_path):
    """Its id names the set, which is what makes the tray one boolean not sixty-four."""
    body = TRAY.replace('bevel  = "bevel"', "")
    found = B.build(document(tmp_path, _without_carve(body)), root=tmp_path)
    seat = found["built"]["seat"]
    assert found["report"]["nodes"][1]["instances"] == 64
    # Sixty-four prisms joined: one mesh, and its extent spans the whole board.
    points = np.asarray(seat["vertices"], dtype=float)
    assert np.ptp(points[:, 0]) > 800, "the set reaches across the tray, not one cell"


def test_at_places_each_instance_where_its_own_repeat_puts_it(tmp_path):
    found = B.build(document(tmp_path, _without_carve(TRAY)), root=tmp_path)
    points = np.asarray(found["built"]["seat"]["vertices"], dtype=float)
    # Eight distinct column centres, 112 apart, starting at pad + cell/2 = 72.
    columns = np.unique(np.round(points[:, 0] / 112.0).astype(int))
    assert len(columns) >= 8
    assert points[:, 0].min() == pytest.approx(72 - 91.84 / 2, abs=1.0)


def _without_carve(body: str) -> str:
    """The tray up to its boolean, for the checks that must run without a solver."""
    head, _, _ = body.partition('[[nodes]]\nid     = "tray"')
    return head.replace('output  = "tray"', 'output  = "seat"')


# -- the spec's own worked example ----------------------------------------------------


def test_the_tray_in_the_spec_builds_and_reports_what_came_out(tmp_path):
    solving()
    found = B.build(document(tmp_path), root=tmp_path)
    report = found["report"]
    assert report["output"] == "tray"
    assert [n["id"] for n in report["nodes"]] == ["face", "seat", "tray"]
    assert report["nodes"][1]["instances"] == 64
    assert report["warnings"] == []
    check_mesh(found["output"])


def test_the_tray_comes_out_the_size_the_spec_says(tmp_path):
    """928 by 928 by 6: eight cells of 112 with 16 of padding either side."""
    solving()
    found = B.build(document(tmp_path), root=tmp_path)
    low = [round(v, 3) for v in found["report"]["bounds"][:3]]
    high = [round(v, 3) for v in found["report"]["bounds"][3:]]
    assert low == [0.0, 0.0, 0.0]
    assert high == [928.0, 928.0, 6.0]


def test_the_boolean_really_removed_something(tmp_path):
    """A cut that silently returned nothing is the failure the report exists for."""
    solving()
    found = B.build(document(tmp_path), root=tmp_path)
    assert found["report"]["nodes"][2]["faces"] > found["report"]["nodes"][0]["faces"]


def test_a_parameter_given_at_build_time_reaches_the_shape(tmp_path):
    """The search turns these, so a build has to take them."""
    solving()
    found = B.build(document(tmp_path), root=tmp_path, board=2)
    assert found["report"]["nodes"][1]["instances"] == 4
    assert found["report"]["params"]["board"] == 2


# -- the escape hatch, through the same walker ----------------------------------------


def test_a_custom_node_builds_where_the_vocabulary_stops(tmp_path):
    (tmp_path / "mine.py").write_text(
        "def build(along=None, thickness=1.0):\n"
        "    return {\n"
        "        'vertices': [[0,0,0],[thickness,0,0],[0,thickness,0]],\n"
        "        'faces': [(0,1,2)],\n"
        "    }\n",
        encoding="utf-8",
    )
    found = B.build(
        one("custom", fn="mine.py:build", args={"thickness": 2.0}), root=tmp_path
    )
    assert len(found["output"]["faces"]) == 1
    assert np.asarray(found["output"]["vertices"], dtype=float).max() == 2.0


def test_a_custom_node_is_handed_its_inputs_as_meshes(tmp_path):
    (tmp_path / "mine.py").write_text(
        "def build(along=None, **how):\n"
        "    return {'vertices': along['vertices'], 'faces': along['faces']}\n",
        encoding="utf-8",
    )
    stated = {
        "name": "two",
        "version": 1,
        "params": {},
        "materials": {},
        "nodes": [
            {"id": "base", "op": "primitive", "kind": "cube", "size": 2.0},
            {
                "id": "it",
                "op": "custom",
                "fn": "mine.py:build",
                "inputs": {"along": "base"},
            },
        ],
        "output": "it",
    }
    found = B.build(stated, root=tmp_path)
    assert len(found["output"]["faces"]) == 6, "it was handed the cube, not its id"


# -- composing what was already built ------------------------------------------------


def test_a_union_joins_the_nodes_it_names(tmp_path):
    stated = {
        "name": "pair",
        "version": 1,
        "params": {},
        "materials": {},
        "nodes": [
            {"id": "a", "op": "primitive", "kind": "cube", "size": 2.0},
            {
                "id": "b",
                "op": "primitive",
                "kind": "cube",
                "size": 2.0,
                "at": [10, 0, 0],
            },
            {"id": "it", "op": "union", "inputs": ["a", "b"]},
        ],
        "output": "it",
    }
    found = B.build(stated, root=tmp_path)
    assert len(found["output"]["faces"]) == 12, "two cubes, six faces each"
    points = np.asarray(found["output"]["vertices"], dtype=float)
    assert np.ptp(points[:, 0]) == pytest.approx(12.0), "and the second one moved"


def test_a_transform_moves_what_it_was_given(tmp_path):
    stated = {
        "name": "moved",
        "version": 1,
        "params": {},
        "materials": {},
        "nodes": [
            {"id": "a", "op": "primitive", "kind": "cube", "size": 2.0},
            {
                "id": "it",
                "op": "transform",
                "of": "a",
                "at": [5, 0, 0],
                "scale": [2, 1, 1],
            },
        ],
        "output": "it",
    }
    found = B.build(stated, root=tmp_path)
    points = np.asarray(found["output"]["vertices"], dtype=float)
    assert np.ptp(points[:, 0]) == pytest.approx(4.0), "scaled on x and not on y"
    assert np.ptp(points[:, 1]) == pytest.approx(2.0)
    assert points[:, 0].mean() == pytest.approx(5.0), "and placed where `at` says"


# -- a model a game has, as a declaration (§PW64) --------------------------------------

COTTONY = Path(__file__).parent / "fixtures" / "cottony"


def test_cottonys_star_builds_from_a_declaration():
    """The shape the whole concave-cap finding came from, stated rather than programmed.

    `star_model.py` is 124 lines around one `crowned` call. The numbers here are its
    own — REACH 0.47, CROWN 0.13, a depth of a tenth of the canvas, an inner radius of
    half the outer — and they are parameters, so a search reaches them.
    """
    found = B.build(G.read("star.toml", root=COTTONY), root=COTTONY)
    check_mesh(found["output"])
    assert found["report"]["nodes"][0]["op"] == "crowned"
    assert found["report"]["warnings"] == []


def test_the_read_and_the_build_now_agree_about_that_star(tmp_path):
    """They did not: the review said the shape was fine and the build refused it."""
    document = G.read("star.toml", root=COTTONY)
    said = review.describe(document)["reads"][0]
    assert "a star of" in said
    assert "points 5" in said
    assert "domed face" in said
    B.build(document, root=COTTONY)  # and it builds, which is the half that did not


def test_the_star_keeps_its_five_even_points(tmp_path):
    """The one shape whose silhouette has to stay exactly five even points."""
    from polyweave.geometry import outline as O

    document = G.read("star.toml", root=COTTONY)
    resolved = G.expand(document)["nodes"][0]["instances"][0]
    ring = O.resolve(resolved["outline"], root=COTTONY)
    assert len(ring) == 10
    # Alternating radii, five of each, and every arm the same length as its siblings.
    radii = np.round(np.linalg.norm(ring, axis=1), 6)
    assert len(set(radii.tolist())) == 2, "two radii, not five arms of different sizes"
    assert sorted(radii)[-5:] == [max(radii)] * 5
