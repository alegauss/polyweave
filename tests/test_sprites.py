"""One authored clip, in both shapes the same motion is needed in.

§PW29's case: the same settle exists as a sprite the interface crossfades to and as
something a 3D scene would play, and keeping the two in step is manual.

The laying-out is arithmetic over pictures, so most of this needs no renderer. The tests
that bake a real clip need Blender and skip without it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image as PILImage
from tests.test_skeleton import figure

from polyweave import clip as C
from polyweave import skeleton, sprites
from polyweave.errors import PolyweaveError

SQUASH = {
    "root": {"scale": [(0.0, [1, 1, 1]), (0.2, [1.06, 0.93, 1.06]), (0.4, [1, 1, 1])]}
}


def settle():
    return C.clip("settle", 0.4, channels=SQUASH)


def frame(tmp_path, name, *, box, size=(40, 40)):
    """A rendered frame with its subject in a stated rectangle, and nothing else."""
    canvas = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    left, top, wide, tall = box
    canvas[top : top + tall, left : left + wide] = (200, 90, 60, 255)
    where = tmp_path / name
    PILImage.fromarray(canvas, "RGBA").save(where)
    return {"artefact": str(where), "at": 0.0, "frame": 0}


def project(tmp_path, body=""):
    (tmp_path / "polyweave.toml").write_text(body, encoding="utf-8")
    return tmp_path


# -- which moments become cells ------------------------------------------------------


def test_the_sheet_has_its_own_rate():
    """A clip authored at 24 and sampled at 12 is half the cells over the same span."""
    assert len(sprites.moments(settle(), fps=5)) == 3
    assert len(sprites.moments(settle(), fps=10)) == 5


def test_a_count_can_be_asked_for_instead():
    found = sprites.moments(settle(), fps=24, frames=3)
    assert found == [0.0, 0.2, 0.4]


def test_a_single_frame_is_the_first_moment():
    assert sprites.moments(settle(), fps=24, frames=1) == [0.0]


# -- the trim is one rectangle for the whole clip --------------------------------------


def test_the_cell_is_the_union_of_every_frame(tmp_path):
    """A frame trimmed to its own outline is a sprite that jitters on its own axis."""
    project(tmp_path)
    rendered = [
        frame(tmp_path, "a.png", box=(10, 10, 8, 8)),
        frame(tmp_path, "b.png", box=(14, 12, 10, 6)),
    ]
    found = sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert found["cell"] == [14, 8], "from x 10 to 24, and y 10 to 18"
    assert found["trim"]["left"] == 10
    assert found["trim"]["top"] == 10


def test_every_cell_is_the_same_size_whatever_the_frame_held(tmp_path):
    project(tmp_path)
    rendered = [
        frame(tmp_path, "a.png", box=(10, 10, 8, 8)),
        frame(tmp_path, "b.png", box=(14, 12, 10, 6)),
    ]
    found = sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert {tuple(one["rect"][2:]) for one in found["frames"]} == {(14, 8)}


def test_trimming_can_be_turned_off(tmp_path):
    project(tmp_path, "[sprites]\ntrim = false\n")
    rendered = [frame(tmp_path, "a.png", box=(10, 10, 8, 8))]
    found = sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert found["cell"] == [40, 40]
    assert found["trim"] is None


def test_a_clip_that_drew_nothing_has_nothing_to_trim_to(tmp_path):
    project(tmp_path)
    blank = np.zeros((20, 20, 4), dtype=np.uint8)
    PILImage.fromarray(blank, "RGBA").save(tmp_path / "blank.png")
    rendered = [{"artefact": str(tmp_path / "blank.png"), "at": 0.0, "frame": 0}]
    with pytest.raises(PolyweaveError) as caught:
        sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert caught.value.code == "clip.nothing-drawn"


def test_frames_of_two_sizes_are_a_sheet_nothing_can_index(tmp_path):
    project(tmp_path)
    rendered = [
        frame(tmp_path, "a.png", box=(2, 2, 6, 6), size=(40, 40)),
        frame(tmp_path, "b.png", box=(2, 2, 6, 6), size=(32, 32)),
    ]
    with pytest.raises(PolyweaveError) as caught:
        sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert caught.value.code == "clip.frames-differ"


# -- the sheet and the atlas beside it -------------------------------------------------


def test_the_sheet_holds_every_frame_in_a_grid(tmp_path):
    project(tmp_path)
    rendered = [frame(tmp_path, f"{n}.png", box=(8, 8, 10, 10)) for n in range(4)]
    found = sprites.sheet(
        settle(), rendered, out=tmp_path / "s.png", root=tmp_path, columns=2
    )
    assert found["columns"] == 2
    assert found["rows"] == 2
    assert found["size"] == [20, 20]
    assert Path(found["sheet"]).is_file()


def test_the_atlas_says_where_every_frame_is_and_when(tmp_path):
    project(tmp_path)
    rendered = [
        {**frame(tmp_path, f"{n}.png", box=(8, 8, 10, 10)), "at": n / 10, "frame": n}
        for n in range(3)
    ]
    found = sprites.sheet(
        settle(), rendered, out=tmp_path / "s.png", root=tmp_path, columns=3
    )
    written = json.loads(Path(found["atlas"]).read_text(encoding="utf-8"))
    assert [one["at"] for one in written["frames"]] == [0.0, 0.1, 0.2]
    assert [one["rect"][0] for one in written["frames"]] == [0, 10, 20]
    assert written["duration"] == 0.4


def test_the_atlas_is_json_because_a_machine_writes_and_reads_it(tmp_path):
    project(tmp_path)
    rendered = [frame(tmp_path, "a.png", box=(8, 8, 10, 10))]
    found = sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert found["atlas"].endswith(".atlas.json")


def test_a_sheet_of_no_frames_is_refused(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        sprites.sheet(settle(), [], out=tmp_path / "s.png", root=tmp_path)
    assert caught.value.code == "clip.no-frames"


# -- both outputs, from the one source -------------------------------------------------


def test_both_carry_the_digest_of_the_clip_they_came_from(tmp_path):
    project(tmp_path)
    rendered = [frame(tmp_path, "a.png", box=(8, 8, 10, 10))]
    found = sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    assert found["clip_sha256"] == C._digest(C.as_toml(settle()))


def test_the_same_clip_on_both_sides_is_a_match(tmp_path):
    atlas = {"clip": "settle", "clip_sha256": "abc"}
    found = sprites.matched({"clip_sha256": "abc"}, atlas, root=tmp_path)
    assert found["matched"] is True
    assert found["why"] == ""


def test_a_sheet_and_an_animation_from_different_clips_are_not(tmp_path):
    """The whole value: the two cannot drift apart without someone noticing."""
    found = sprites.matched(
        {"clip_sha256": "abc"}, {"clip": "settle", "clip_sha256": "def"}, root=tmp_path
    )
    assert found["matched"] is False
    assert "different motion" in found["why"]


def test_an_atlas_on_disk_can_be_compared_too(tmp_path):
    project(tmp_path)
    rendered = [frame(tmp_path, "a.png", box=(8, 8, 10, 10))]
    found = sprites.sheet(settle(), rendered, out=tmp_path / "s.png", root=tmp_path)
    against = {"clip_sha256": found["clip_sha256"]}
    assert sprites.matched(against, found["atlas"], root=tmp_path)["matched"] is True


# -- against a real render -------------------------------------------------------------


def baked(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    project(
        tmp_path,
        "[render]\npreview_size = 48\n"
        "samples = { sphere = 2, preview = 2, final = 2 }\n\n"
        "[sprites]\nfps = 5\n",
    )
    mesh = figure()
    rig = skeleton.fit(mesh, named="plush", root=tmp_path)
    bound = skeleton.weights(mesh, rig, root=tmp_path)
    return mesh, rig, bound


def test_one_clip_produces_an_animation_and_a_sheet(tmp_path):
    mesh, rig, bound = baked(tmp_path)
    found = sprites.both(
        settle(),
        mesh,
        rig,
        bound,
        out=tmp_path / "settle",
        root=tmp_path,
        rung="preview",
    )
    assert Path(found["animation"]["artefact"]).is_file()
    assert Path(found["sprites"]["sheet"]).is_file()
    assert Path(found["sprites"]["atlas"]).is_file()


def test_and_the_two_are_checkably_the_same_motion(tmp_path):
    mesh, rig, bound = baked(tmp_path)
    found = sprites.both(
        settle(),
        mesh,
        rig,
        bound,
        out=tmp_path / "settle",
        root=tmp_path,
        rung="preview",
    )
    against = sprites.matched(found["animation"], found["sprites"], root=tmp_path)
    assert against["matched"] is True


def test_the_sheet_is_cut_from_the_frames_the_rig_drew(tmp_path):
    mesh, rig, bound = baked(tmp_path)
    found = sprites.bake(
        settle(),
        mesh,
        rig,
        bound,
        out=tmp_path / "settle.png",
        root=tmp_path,
        rung="preview",
    )
    assert found["cell"][0] < 48, "trimmed in from the rendered frame"
    assert found["trim"]["of"] == [48, 48]
    assert len(found["frames"]) == 3, "0.4s at five a second"
