"""Giving a fetched mesh a skeleton, so it can be posed at all.

§PW26's case: every generative mesh arrives as a static surface, and rigging one by
hand is the step that keeps character animation out of reach. Nothing else in Block F is
reachable while every mesh is a rigid surface.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave import skeleton
from polyweave.errors import PolyweaveError


def tube(width=0.6, height=1.0, depth=0.4, *, at=(0.0, 0.0, 0.0), levels=9):
    """A closed box as a stack of rings, so its edges are short and real.

    Short edges matter: the stretch guard is a ratio of edge lengths, and a face fan
    joining vertices that are not neighbours would make every rig look torn.
    """
    rings = []
    for y in np.linspace(0.0, height, levels):
        rings.append(
            [
                [-width / 2, y, -depth / 2],
                [width / 2, y, -depth / 2],
                [width / 2, y, depth / 2],
                [-width / 2, y, depth / 2],
            ]
        )
    points = np.array([point for ring in rings for point in ring]) + np.array(at)
    faces = []
    for level in range(levels - 1):
        low, high = level * 4, (level + 1) * 4
        faces += [
            (low + i, low + (i + 1) % 4, high + (i + 1) % 4, high + i) for i in range(4)
        ]
    faces += [(0, 1, 2, 3), tuple(range((levels - 1) * 4, levels * 4))]
    return {"vertices": points, "faces": faces}


def joined(*parts):
    """Several tubes as one mesh, each part's faces moved onto its own vertices."""
    points, faces, offset = [], [], 0
    for part in parts:
        points.append(part["vertices"])
        faces += [tuple(i + offset for i in face) for face in part["faces"]]
        offset += len(part["vertices"])
    return {"vertices": np.vstack(points), "faces": faces}


def figure(height=1.0):
    """A body whose limbs are where the plush plan puts its bones: two of each."""
    return joined(
        tube(0.4, height * 0.7, 0.3, at=(0.0, height * 0.3, 0.0)),
        tube(0.1, height * 0.3, 0.1, at=(0.3, height * 0.45, 0.0)),
        tube(0.1, height * 0.3, 0.1, at=(-0.3, height * 0.45, 0.0)),
        tube(0.12, height * 0.32, 0.2, at=(0.12, 0.0, 0.0)),
        tube(0.12, height * 0.32, 0.2, at=(-0.12, 0.0, 0.0)),
    )


def blob(width=0.6, height=1.0, depth=0.4, **how):
    return tube(width, height, depth, **how)


# -- the body plans that recur ------------------------------------------------------


def test_every_plan_is_a_skeleton_and_not_a_list():
    for name in skeleton.PLANS:
        joints = skeleton.plan(name)
        assert sum(1 for _, parent, _ in joints if not parent) == 1


def test_a_plan_is_written_once_and_mirrored():
    names = {name for name, _, _ in skeleton.plan("plush")}
    assert "arm.L" in names and "arm.R" in names
    left = dict((n, a) for n, _, a in skeleton.plan("plush"))
    assert left["arm.R"][0] == -left["arm.L"][0]
    assert left["arm.R"][1] == left["arm.L"][1]


def test_a_mirrored_joint_hangs_from_its_own_side():
    parents = {name: parent for name, parent, _ in skeleton.plan("plush")}
    assert parents["hand.R"] == "arm.R"
    assert parents["leg.R"] == "root"


def test_a_plan_by_a_name_nothing_has_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        skeleton.plan("dragon")
    assert caught.value.code == "rig.unknown-plan"
    assert "plush" in caught.value.remedy


def test_a_joint_hanging_from_nothing_is_not_a_skeleton():
    with pytest.raises(PolyweaveError) as caught:
        skeleton.check_plan([("root", "", (0, 0, 0)), ("hand", "arm", (0, 1, 0))])
    assert caught.value.code == "rig.bad-plan"


def test_a_plan_with_two_roots_is_not_one_either():
    with pytest.raises(PolyweaveError) as caught:
        skeleton.check_plan([("a", "", (0, 0, 0)), ("b", "", (0, 1, 0))])
    assert caught.value.code == "rig.bad-plan"
    assert "2 joints with no parent" in caught.value.message


# -- fitted to the mesh actually there ------------------------------------------------


def test_the_skeleton_spans_the_mesh_it_was_fitted_to(tmp_path):
    found = skeleton.fit(blob(height=2.0), named="plush", root=tmp_path)
    ys = [joint["at"][1] for joint in found["joints"]]
    assert min(ys) == pytest.approx(0.0, abs=0.05), "it stands on the ground"
    assert max(ys) == pytest.approx(2.0, abs=0.1), "and reaches the top"


def test_a_taller_mesh_gets_a_taller_skeleton(tmp_path):
    short = skeleton.fit(blob(height=1.0), named="plush", root=tmp_path)
    tall = skeleton.fit(blob(height=3.0), named="plush", root=tmp_path)
    assert max(j["at"][1] for j in tall["joints"]) > 2.5
    assert max(j["at"][1] for j in short["joints"]) < 1.2


def test_a_joint_is_pulled_onto_the_volume_rather_than_the_box(tmp_path):
    """A plan placed in a box puts an arm bone in the air beside a narrower mesh."""
    narrow = figure()
    boxed = skeleton.fit(narrow, named="plush", root=tmp_path, pull=0.0)
    pulled = skeleton.fit(narrow, named="plush", root=tmp_path, pull=1.0)
    hand = {j["name"]: j["at"] for j in boxed["joints"]}["hand.L"]
    onto = {j["name"]: j["at"] for j in pulled["joints"]}["hand.L"]
    assert abs(onto[0]) < abs(hand[0]), "it moved in, onto the arm that is there"


def test_the_same_mesh_and_plan_give_the_same_skeleton(tmp_path):
    """Re-runnable: a mesh refetched at better quality should not cost its animation."""
    once = skeleton.fit(figure(), named="plush", root=tmp_path)
    again = skeleton.fit(figure(), named="plush", root=tmp_path)
    assert once == again


def test_the_project_names_the_plan_where_the_call_does_not(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[rig]\nplan = "biped"\n', encoding="utf-8"
    )
    assert skeleton.fit(figure(), root=tmp_path)["plan"] == "biped"


def test_a_mesh_with_nothing_in_it_has_nothing_to_fit(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        skeleton.fit({"vertices": np.zeros((0, 3)), "faces": []}, root=tmp_path)
    assert caught.value.code == "rig.unbound-vertices"


# -- weights, solved from proximity ----------------------------------------------------


def test_every_vertex_is_carried_by_something(tmp_path):
    mesh = figure()
    bound = skeleton.weights(mesh, skeleton.fit(mesh, root=tmp_path), root=tmp_path)
    assert np.allclose(bound["weights"].sum(axis=1), 1.0, atol=1e-4)


def test_a_vertex_takes_only_a_few_bones(tmp_path):
    mesh = figure()
    bound = skeleton.weights(
        mesh, skeleton.fit(mesh, root=tmp_path), root=tmp_path, influences=2
    )
    assert int((bound["weights"] > 0).sum(axis=1).max()) <= 2


def test_a_vertex_belongs_most_to_the_bone_it_is_nearest(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    points = np.asarray(mesh["vertices"])
    highest = int(np.argmax(points[:, 1]))
    best = bound["names"][int(np.argmax(bound["weights"][highest]))]
    assert best in ("head", "crown"), "the topmost vertex belongs to the head"


def test_the_falloff_is_how_hard_a_vertex_snaps_to_one_bone(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    sharp = skeleton.weights(mesh, rig, root=tmp_path, falloff=12.0)
    soft = skeleton.weights(mesh, rig, root=tmp_path, falloff=1.0)
    assert sharp["weights"].max(axis=1).mean() > soft["weights"].max(axis=1).mean()


# -- the pose, which is how a rig gets looked at ---------------------------------------


def test_a_pose_of_nothing_leaves_the_mesh_where_it_was(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    assert np.allclose(skeleton.pose(mesh, rig, bound, {}), mesh["vertices"], atol=1e-9)


def test_turning_a_joint_moves_what_hangs_below_it(tmp_path):
    """A shoulder carries the hand, which is what a hierarchy is for."""
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    points = np.asarray(mesh["vertices"])
    reach = int(np.argmax(points[:, 0]))  # out at the end of the left arm
    moved = skeleton.pose(mesh, rig, bound, {"spine": (0, 0, 40)})
    assert np.linalg.norm(moved[reach] - points[reach]) > 0.05


def test_turning_a_joint_leaves_what_is_not_below_it_alone(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path, influences=1, falloff=12.0)
    points = np.asarray(mesh["vertices"])
    lowest = int(np.argmin(points[:, 1]))
    moved = skeleton.pose(mesh, rig, bound, {"head": (0, 0, 40)})
    assert np.linalg.norm(moved[lowest] - points[lowest]) < 0.02


# -- the two guards --------------------------------------------------------------------


def test_a_rig_that_holds_says_what_it_checked(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    found = skeleton.check(mesh, rig, bound, root=tmp_path)
    assert found["holds"] is True
    assert found["bones"] == len(bound["names"])
    assert found["stretch"]["edges"] > 0


def test_tearing_is_a_number_rather_than_a_judgement_about_a_picture(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    found = skeleton.stretch(mesh, rig, bound)
    assert found["worst"] > 0
    assert len(found["at"]) == 2, "and it names the edge"


def test_one_bone_per_vertex_tears_at_every_boundary_and_is_caught(tmp_path):
    """The worst setting there is, and the clearest statement of what a tear is."""
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path, influences=1)
    with pytest.raises(PolyweaveError) as caught:
        skeleton.check(mesh, rig, bound, root=tmp_path)
    assert caught.value.code == "rig.tearing"
    assert "vertices [" in caught.value.message, "and it names the edge that tore"
    assert skeleton.stretch(mesh, rig, bound)["worst"] > 4.0


def test_both_ends_of_the_falloff_are_worse_than_the_middle(tmp_path):
    """Measured, because it is not what anyone would guess from the name."""
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)

    def torn(falloff):
        return skeleton.stretch(
            mesh, rig, skeleton.weights(mesh, rig, root=tmp_path, falloff=falloff)
        )["worst"]

    assert torn(1.0) > torn(4.0), "too low spreads a vertex onto bones nowhere near it"
    assert torn(16.0) > torn(4.0), "too high snaps it to one, and the boundary tears"


def test_the_defaults_sit_in_that_trough(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    assert skeleton.stretch(mesh, rig, bound)["worst"] < 2.0
    assert skeleton.check(mesh, rig, bound, root=tmp_path)["holds"] is True


def test_the_bar_for_tearing_is_the_project_s_to_set(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        "[rig]\ntear_ratio = 1000.0\n", encoding="utf-8"
    )
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    assert skeleton.check(mesh, rig, bound, root=tmp_path)["tear_ratio"] == 1000.0


# -- one clip, more than one skeleton --------------------------------------------------


def test_a_pose_plays_on_any_skeleton_that_spells_its_joints_the_same(tmp_path):
    mesh = figure()
    plush = skeleton.fit(mesh, named="plush", root=tmp_path)
    biped = skeleton.fit(mesh, named="biped", root=tmp_path)
    wave = {"head": (0, 0, 10), "spine": (0, 5, 0)}
    assert skeleton.retarget(wave, plush) == skeleton.retarget(wave, biped)


def test_a_joint_the_skeleton_does_not_have_is_named_rather_than_dropped(tmp_path):
    """A silently ignored channel is a limb that does not move and nobody knows why."""
    plush = skeleton.fit(figure(), named="plush", root=tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        skeleton.retarget({"tail": (0, 0, 20)}, plush)
    assert caught.value.code == "rig.unmatched-joints"
    assert "a near miss is not a match" in caught.value.remedy


def test_which_joints_two_plans_share_is_a_read():
    both = skeleton.shared("plush", "biped")
    assert "head" in both
    assert "spine" in both
    assert "crown" not in both, "the plush has one and the biped does not"


# -- what gets written down ------------------------------------------------------------


def test_the_record_holds_enough_to_fit_it_again(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    record = skeleton.as_record(
        rig, bound, skeleton.check(mesh, rig, bound, root=tmp_path)
    )
    assert record["plan"] == "plush"
    assert record["pull"] == rig["pull"]
    assert record["falloff"] == bound["falloff"]
    assert len(record["joints"]) == len(rig["joints"])


def test_the_weights_are_not_in_it(tmp_path):
    """One number per vertex per bone is a record nobody reads."""
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    record = skeleton.as_record(
        rig, bound, skeleton.check(mesh, rig, bound, root=tmp_path)
    )
    assert "weights" not in record


def test_the_record_says_what_the_guards_found(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    record = skeleton.as_record(
        rig, bound, skeleton.check(mesh, rig, bound, root=tmp_path)
    )
    assert record["checked"]["worst_stretch"] > 0
    assert record["checked"]["bones"] == len(bound["names"])
