"""A reference video sampled into frames and sheets an agent can read (§PW328).

The video is made by ffmpeg from its own test sources: two still seconds of grey, then
two of a moving pattern, so a change bound has something to drop.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from PIL import Image

from polyweave import provenance, reference
from polyweave.errors import PolyweaveError

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


@pytest.fixture
def video(tmp_path):
    where = tmp_path / "elsewhere" / "play.mp4"
    where.parent.mkdir()
    subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
         "color=c=gray:s=160x90:d=2:r=10", "-f", "lavfi", "-i",
         "testsrc=s=160x90:d=2:r=10", "-filter_complex",
         "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p",
         str(where)],
        check=True, capture_output=True,
    )
    project = tmp_path / "game"
    project.mkdir()
    return where, project


def test_frames_are_named_by_time_and_recorded_against_the_video(video):
    source, project = video
    found = reference.frames(str(source), rate=2, root=str(project))
    folder = project / found["folder"]
    names = sorted(one.name for one in folder.glob("t*.png"))
    assert names[:3] == ["t00000000.png", "t00000500.png", "t00001000.png"]
    assert found["frames"] == 8
    assert not list(project.rglob("*.mp4"))
    record = provenance.read(found["manifest"], root=project)
    assert record["inputs"][0]["sha256"] == provenance.sha256_of(source)[0]
    assert record["params"]["rate"] == 2.0


def test_a_range_is_sampled_denser_and_a_sheet_holds_sixteen(video):
    source, project = video
    found = reference.frames(str(source), rate=1, ranges=[[2.0, 3.0, 10]],
                             root=str(project))
    listed = json.loads((project / found["manifest"]).read_text("utf-8"))
    times = [one["ms"] for one in listed["frames"]]
    assert 2100 in times and 2900 in times and 1000 in times
    assert len(found["sheets"]) == -(-found["frames"] // 16)
    with Image.open(project / found["sheets"][0]) as sheet:
        assert sheet.width == 4 * reference.TILE


def test_a_change_bound_drops_the_still_stretch(video):
    source, project = video
    every = reference.frames(str(source), rate=5, root=str(project))
    moving = reference.frames(str(source), rate=5, changed=0.02, root=str(project))
    # Ten still frames are one: what is kept is where the picture changed.
    assert every["frames"] - moving["frames"] >= 9
    assert moving["frames"] >= 2


def test_a_crop_gets_its_own_sheet(video):
    source, project = video
    found = reference.frames(str(source), rate=2, crop=[0, 0, 160, 20],
                             root=str(project))
    with Image.open(project / found["crops"][0]) as strip:
        assert strip.height < 4 * 60


def test_a_video_that_is_not_there_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        reference.frames(str(tmp_path / "none.mp4"), root=str(tmp_path))
    assert refused.value.code == "fetch.no-reference"
