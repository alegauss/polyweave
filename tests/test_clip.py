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


# -- the authored form is text ---------------------------------------------------------


def test_a_clip_writes_as_toml_a_person_can_read(tmp_path):
    where = C.write(C.clip("settle", 0.4, channels=SQUASH), tmp_path / "settle.toml")
    text = where.read_text(encoding="utf-8")
    assert 'name = "settle"' in text
    assert "duration = 0.4" in text
    assert "[[channel]]" in text
    assert 'joint = "root"' in text


def test_every_key_gets_its_own_line_so_a_diff_can_point_at_one(tmp_path):
    """A key sharing a line with three others says nothing in a review."""
    text = C.as_toml(C.clip("settle", 0.4, channels=SQUASH))
    keyed = [line for line in text.splitlines() if line.strip().startswith("{ at")]
    assert len(keyed) == 3


def test_a_timing_change_shows_up_as_one_changed_line(tmp_path):
    """The difference between collaborating on an animation and replacing it."""
    before = C.clip("settle", 0.4, channels=SQUASH)
    after = C.set_key(before, "root", "scale", 0.2, [1.06, 0.80, 1.06])
    one, two = C.as_toml(before).splitlines(), C.as_toml(after).splitlines()
    differing = [n for n, (a, b) in enumerate(zip(one, two, strict=True)) if a != b]
    assert len(differing) == 1
    assert "0.8" in two[differing[0]]


def test_an_ease_that_changed_is_visible_in_the_text(tmp_path):
    before = C.clip("settle", 0.4, channels=SQUASH)
    after = C.set_key(before, "root", "scale", 0.2, [1.06, 0.93, 1.06], "ease")
    assert 'ease = "ease"' not in C.as_toml(before)
    assert 'ease = "ease"' in C.as_toml(after)


def test_what_was_written_reads_back_as_the_same_clip(tmp_path):
    original = C.clip("settle", 0.4, fps=30, easing="ease", channels=SQUASH)
    assert C.read(C.write(original, tmp_path / "settle.toml")) == original


def test_a_clip_with_several_channels_round_trips_too(tmp_path):
    original = C.clip("both", 1.0, channels={**SQUASH, **WAVE})
    assert C.read(C.write(original, tmp_path / "both.toml")) == original


def test_a_file_a_hand_edit_broke_says_where(tmp_path):
    where = tmp_path / "broken.toml"
    where.write_text('name = "settle\nduration = 0.4\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        C.read(where)
    assert caught.value.code == "clip.unreadable"
    assert caught.value.detail


def test_a_file_that_is_toml_and_is_not_a_clip_is_refused(tmp_path):
    where = tmp_path / "other.toml"
    where.write_text('title = "not a clip"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        C.read(where)
    assert caught.value.code == "clip.malformed"


def test_a_clip_that_is_not_there_is_not_a_traceback(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.read(tmp_path / "nothing.toml")
    assert caught.value.code == "clip.unreadable"


# -- changing a curve ------------------------------------------------------------------


def test_a_key_can_be_added_where_there_was_none():
    found = C.set_key(
        C.clip("settle", 0.4, channels=SQUASH), "root", "scale", 0.3, [1.02, 0.98, 1.02]
    )
    assert C.keys(found) == [0.0, 0.2, 0.3, 0.4]


def test_setting_a_key_that_exists_replaces_it():
    found = C.set_key(
        C.clip("settle", 0.4, channels=SQUASH), "root", "scale", 0.2, [2, 2, 2]
    )
    assert C.at(found, 0.2)["root"]["scale"] == pytest.approx((2, 2, 2))
    assert len(C.keys(found)) == 3


def test_changing_a_key_leaves_the_original_alone():
    before = C.clip("settle", 0.4, channels=SQUASH)
    C.set_key(before, "root", "scale", 0.2, [9, 9, 9])
    assert C.at(before, 0.2)["root"]["scale"] == pytest.approx((1.06, 0.93, 1.06))


def test_retiming_keeps_the_shape_over_a_different_span():
    """The change that gets made most, and the one a binary track makes hardest."""
    slower = C.retime(C.clip("settle", 0.4, channels=SQUASH), 0.8)
    assert slower["duration"] == 0.8
    assert C.keys(slower) == [0.0, 0.4, 0.8]
    assert C.at(slower, 0.4)["root"]["scale"] == pytest.approx((1.06, 0.93, 1.06))


# -- the export is a compile step with a cache -----------------------------------------


def compiled_clip(tmp_path, subject, name="out.glb", **how):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    mesh, rig, bound = rigged(tmp_path)
    return C.compile(
        subject, mesh, rig, bound, out=tmp_path / name, root=tmp_path, **how
    )


def test_the_clip_lands_in_the_file_under_its_own_name(tmp_path):
    found = compiled_clip(tmp_path, C.clip("settle", 0.4, channels=SQUASH))
    assert C.compiled(found["artefact"])["clips"][0]["name"] == "settle"


def test_and_over_the_frames_its_duration_gives(tmp_path):
    found = compiled_clip(tmp_path, C.clip("wave", 1.0, fps=24, channels=WAVE))
    assert C.compiled(found["artefact"])["clips"][0]["frames"] == [0.0, 24.0]


def test_the_joint_the_clip_drives_is_in_the_file(tmp_path):
    found = compiled_clip(tmp_path, C.clip("wave", 1.0, channels=WAVE))
    assert "arm.L" in C.compiled(found["artefact"])["clips"][0]["joints"]


def test_compiling_the_same_clip_again_is_a_copy_and_not_an_export(tmp_path):
    subject = C.clip("settle", 0.4, channels=SQUASH)
    first = compiled_clip(tmp_path, subject, name="a.glb")
    again = compiled_clip(tmp_path, subject, name="b.glb")
    assert first["cached"] is False
    assert again["cached"] is True
    assert again["cache_key"] == first["cache_key"]


def test_a_clip_that_changed_is_a_different_key(tmp_path):
    first = compiled_clip(
        tmp_path, C.clip("settle", 0.4, channels=SQUASH), name="a.glb"
    )
    changed = C.set_key(
        C.clip("settle", 0.4, channels=SQUASH), "root", "scale", 0.2, [1.2, 0.8, 1.2]
    )
    again = compiled_clip(tmp_path, changed, name="b.glb")
    assert again["cache_key"] != first["cache_key"]
    assert again["cached"] is False


def test_a_clip_driving_a_joint_the_skeleton_lacks_is_named(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    mesh, rig, bound = rigged(tmp_path)
    subject = C.clip(
        "swish",
        1.0,
        channels={"tail": {"rotation": [(0.0, [0, 0, 0]), (1.0, [0, 0, 30])]}},
    )
    with pytest.raises(PolyweaveError) as caught:
        C.compile(subject, mesh, rig, bound, out=tmp_path / "x.glb", root=tmp_path)
    assert caught.value.code == "rig.unmatched-joints"
