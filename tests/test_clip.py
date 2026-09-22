"""Motion as something with a name and a duration, rather than a second still.

§PW27's case: motion in Cottony is a second static render of the same mesh squashed to
93 per cent of its height. Right for one beat, with no way to say what a walk would be.

The render tests here need Blender and skip without it; everything about the clip itself
is arithmetic and does not.
"""

from __future__ import annotations

import numpy as np
import pytest
from tests.test_skeleton import figure

from polyweave import clip as C
from polyweave import skeleton
from polyweave.errors import PolyweaveError

SQUASH = {
    "root": {"scale": [(0.0, [1, 1, 1]), (0.2, [1.06, 0.93, 1.06]), (0.4, [1, 1, 1])]}
}
WAVE = {"arm.L": {"rotation": [(0.0, [0, 0, 0]), (0.5, [0, 0, 40]), (1.0, [0, 0, 0])]}}


def rigged(tmp_path):
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    return mesh, rig, skeleton.weights(mesh, rig, root=tmp_path)


# -- a clip is a thing with a name and a duration ------------------------------------


def test_the_squash_is_expressible_as_what_it_honestly_is():
    """A clip of a few poses, rather than the only thing the pipeline can say."""
    found = C.clip("settle", 0.4, channels=SQUASH)
    assert found["name"] == "settle"
    assert found["duration"] == 0.4
    assert C.keys(found) == [0.0, 0.2, 0.4]


def test_a_clip_knows_which_joints_it_moves():
    assert C.joints(C.clip("wave", 1.0, channels=WAVE)) == ["arm.L"]


def test_the_three_properties_are_the_three_the_engine_animates():
    assert C.PROPERTIES == ("rotation", "scale", "translation")


def test_a_channel_driving_something_else_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        C.clip("odd", 1.0, channels={"root": {"colour": [(0.0, [1, 0, 0])]}})
    assert caught.value.code == "clip.unknown-property"
    assert "rotation" in caught.value.remedy


def test_a_clip_that_moves_nothing_is_a_still_with_a_duration_attached():
    with pytest.raises(PolyweaveError) as caught:
        C.clip("nothing", 1.0, channels={})
    assert caught.value.code == "clip.empty"
    assert "a still with a duration attached" in caught.value.remedy


def test_a_key_past_the_end_never_plays_so_it_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        C.clip("late", 0.4, channels={"root": {"scale": [(0.9, [1, 1, 1])]}})
    assert caught.value.code == "clip.outside-duration"


def test_a_clip_with_no_frames_in_it_is_not_a_clip():
    with pytest.raises(PolyweaveError) as caught:
        C.clip("instant", 0.0, channels=SQUASH)
    assert caught.value.code == "clip.no-frames"


def test_an_easing_nothing_implements_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        C.clip("bouncy", 1.0, channels=WAVE, easing="elastic")
    assert caught.value.code == "clip.unknown-easing"


# -- what it looks like at a moment ---------------------------------------------------


def test_a_key_reads_back_exactly_at_its_own_moment():
    found = C.clip("settle", 0.4, channels=SQUASH)
    assert C.at(found, 0.2)["root"]["scale"] == pytest.approx((1.06, 0.93, 1.06))


def test_between_two_keys_it_is_between_the_two_values():
    found = C.clip("settle", 0.4, channels=SQUASH)
    middle = C.at(found, 0.1)["root"]["scale"]
    assert middle[1] == pytest.approx(0.965), "half way down"


def test_before_the_first_key_and_after_the_last_it_holds():
    found = C.clip("wave", 1.0, channels=WAVE)
    assert C.at(found, -5.0)["arm.L"]["rotation"] == pytest.approx((0, 0, 0))
    assert C.at(found, 99.0)["arm.L"]["rotation"] == pytest.approx((0, 0, 0))


def test_a_step_key_holds_until_the_next_one():
    found = C.clip(
        "blink",
        1.0,
        channels={"head": {"scale": [(0.0, [1, 1, 1], "step"), (1.0, [2, 2, 2])]}},
    )
    assert C.at(found, 0.9)["head"]["scale"] == pytest.approx((1, 1, 1))


def test_an_eased_key_moves_slowly_at_the_ends_and_fast_in_the_middle():
    eased = C.clip(
        "e",
        1.0,
        channels={"head": {"scale": [(0.0, [0, 0, 0], "ease"), (1.0, [1, 1, 1])]}},
    )
    straight = C.clip(
        "l", 1.0, channels={"head": {"scale": [(0.0, [0, 0, 0]), (1.0, [1, 1, 1])]}}
    )
    assert (
        C.at(eased, 0.1)["head"]["scale"][0] < C.at(straight, 0.1)["head"]["scale"][0]
    )
    assert C.at(eased, 0.5)["head"]["scale"][0] == pytest.approx(0.5)


# -- the frames it has -----------------------------------------------------------------


def test_the_frame_rate_decides_how_many_frames_there_are():
    assert len(C.times(C.clip("settle", 0.5, fps=24, channels=SQUASH))) == 13
    assert len(C.times(C.clip("settle", 0.5, fps=12, channels=SQUASH))) == 7


def test_the_first_frame_is_the_start_and_the_last_is_the_end():
    found = C.times(C.clip("settle", 0.5, fps=10, channels=SQUASH))
    assert found[0] == 0.0
    assert found[-1] == pytest.approx(0.5)


def test_the_keys_are_what_somebody_stated_and_not_every_frame():
    found = C.clip("settle", 0.4, fps=60, channels=SQUASH)
    assert len(C.keys(found)) == 3
    assert len(C.times(found)) == 25


# -- what it does to a mesh ------------------------------------------------------------


def test_the_squash_makes_the_mesh_shorter_and_wider(tmp_path):
    """Which is the whole of what Cottony's settle does, now said as a clip."""
    mesh, rig, bound = rigged(tmp_path)
    found = C.clip("settle", 0.4, channels=SQUASH)
    rest = C.apply(mesh, rig, bound, C.at(found, 0.0))
    bottom = C.apply(mesh, rig, bound, C.at(found, 0.2))
    assert np.ptp(bottom[:, 1]) < np.ptp(rest[:, 1]), "shorter"
    assert np.ptp(bottom[:, 0]) > np.ptp(rest[:, 0]), "and wider"


def test_and_comes_back_to_where_it_started(tmp_path):
    mesh, rig, bound = rigged(tmp_path)
    found = C.clip("settle", 0.4, channels=SQUASH)
    assert np.allclose(
        C.apply(mesh, rig, bound, C.at(found, 0.0)),
        C.apply(mesh, rig, bound, C.at(found, 0.4)),
    )


def test_a_rotation_channel_goes_through_the_skinning(tmp_path):
    mesh, rig, bound = rigged(tmp_path)
    found = C.clip("wave", 1.0, channels=WAVE)
    rest = C.apply(mesh, rig, bound, C.at(found, 0.0))
    up = C.apply(mesh, rig, bound, C.at(found, 0.5))
    assert np.abs(up - rest).max() > 0.02


def test_a_joint_carries_everything_below_it_and_the_root_carries_all(tmp_path):
    """glTF propagates a node's transform down the tree, and this is that in weights."""
    mesh, rig, bound = rigged(tmp_path)
    assert np.allclose(C.carried(rig, bound, "root"), 1.0)
    arm = C.carried(rig, bound, "arm.L")
    assert arm.max() > 0.9, "the arm carries the arm"
    assert arm.min() < 0.1, "and not the far leg"


def test_a_translation_channel_moves_what_that_joint_carries(tmp_path):
    mesh, rig, bound = rigged(tmp_path)
    found = C.clip(
        "hop",
        1.0,
        channels={"root": {"translation": [(0.0, [0, 0, 0]), (1.0, [0, 0.5, 0])]}},
    )
    moved = C.apply(mesh, rig, bound, C.at(found, 1.0))
    assert moved[:, 1].mean() > np.asarray(mesh["vertices"])[:, 1].mean()


def test_the_clip_as_geometry_is_one_mesh_per_frame(tmp_path):
    mesh, rig, bound = rigged(tmp_path)
    found = C.clip("settle", 0.4, fps=10, channels=SQUASH)
    every = C.poses(found, rig, bound, mesh)
    assert len(every) == len(C.times(found))
    assert every[0].shape == np.asarray(mesh["vertices"]).shape


# -- a frame of a clip is a still ------------------------------------------------------


def test_every_frame_goes_through_the_same_call_a_still_does(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    (tmp_path / "polyweave.toml").write_text(
        "[render]\npreview_size = 32\nsamples = { sphere = 2, preview = 2 }\n",
        encoding="utf-8",
    )
    mesh, rig, bound = rigged(tmp_path)
    seen = []

    def bake(report, **how):
        seen.append(how)
        return {
            "artefact": how["out"],
            "measurements": [{"measure": "alpha_coverage", "value": 0.4}],
            "rung": "preview",
        }

    found = C.clip("settle", 0.4, fps=5, channels=SQUASH)
    rendered = C.frames(found, mesh, rig, bound, out="shots", root=tmp_path, bake=bake)
    assert len(rendered) == len(C.times(found))
    assert all(how["model"].endswith(".glb") for how in seen)
    assert rendered[0]["frame"] == 0
    assert rendered[-1]["at"] == pytest.approx(0.4)


def test_only_the_moments_asked_for_are_rendered(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    mesh, rig, bound = rigged(tmp_path)
    found = C.clip("settle", 0.4, channels=SQUASH)

    def bake(report, **how):
        return {"artefact": how["out"], "measurements": [], "rung": "preview"}

    rendered = C.frames(
        found,
        mesh,
        rig,
        bound,
        out="shots",
        root=tmp_path,
        when=C.keys(found),
        bake=bake,
    )
    assert [one["at"] for one in rendered] == [0.0, 0.2, 0.4]


# -- the measurement a still cannot make -----------------------------------------------


def test_a_measurement_across_a_clip_reports_its_worst_frame():
    """A silhouette that fits at rest and not mid-stride is one nobody measured."""
    rendered = [
        {
            "frame": n,
            "at": n / 10,
            "measurements": [{"measure": "alpha_coverage", "value": v}],
        }
        for n, v in enumerate([0.30, 0.34, 0.51, 0.33])
    ]
    found = C.across(rendered, "alpha_coverage")
    assert found["worst"] == 0.51
    assert found["frame"] == 2
    assert found["at"] == pytest.approx(0.2)
    assert found["rest"] == 0.30, "and what it was at rest, to compare against"


def test_the_worst_can_be_the_smallest_where_that_is_the_question():
    rendered = [
        {
            "frame": n,
            "at": 0.0,
            "measurements": [{"measure": "alpha_coverage", "value": v}],
        }
        for n, v in enumerate([0.4, 0.1, 0.5])
    ]
    assert C.across(rendered, "alpha_coverage", worst="min")["worst"] == 0.1


def test_a_measure_no_frame_carries_is_said_so():
    rendered = [
        {
            "frame": 0,
            "at": 0.0,
            "measurements": [{"measure": "alpha_coverage", "value": 0.4}],
        }
    ]
    with pytest.raises(PolyweaveError) as caught:
        C.across(rendered, "hue_spread")
    assert caught.value.code == "spec.unknown-measure"
    assert "alpha_coverage" in caught.value.remedy


# -- what gets written down ------------------------------------------------------------


def test_the_record_says_what_the_clip_is_without_every_key_in_it():
    found = C.as_record(C.clip("settle", 0.4, channels=SQUASH))
    assert found["name"] == "settle"
    assert found["channels"] == ["root.scale"]
    assert found["frames"] == len(C.times(C.clip("settle", 0.4, channels=SQUASH)))
    assert found["keys"] == [0.0, 0.2, 0.4]
