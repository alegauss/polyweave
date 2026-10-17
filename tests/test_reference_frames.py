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

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.reference import reference

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


# -- another game's footage stays internal (§PW384) ------------------------------------


def _git(project, *args):
    subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)


def test_frames_are_marked_internal_and_so_is_what_is_made_from_them(video):
    from polyweave.layers.reference import reference_objects

    source, project = video
    found = reference.frames(str(source), rate=2, root=str(project))
    assert provenance.read(found["manifest"], root=project)["internal"] is True
    made = reference_objects.objects(
        found["folder"], {"grey": {"colour": "#808080", "size": [1, 100000]}},
        root=str(project))
    # Two steps down, with no mark of its own, it is internal through its input.
    assert "internal" not in provenance.read(made["objects"], root=project)
    assert provenance.internal(made["objects"], project) is True


def test_frames_written_outside_the_work_area_are_refused(video):
    source, project = video
    with pytest.raises(PolyweaveError) as refused:
        reference.frames(str(source), out="../docs/frames", root=str(project))
    assert refused.value.code in ("fetch.no-reference", "config.path-outside")
    with pytest.raises(PolyweaveError) as refused:
        reference.frames(str(source), out="docs/frames", root=str(project))
    assert refused.value.code == "fetch.no-reference"


def test_a_tracked_file_taken_from_a_reference_is_named_by_verify(video):
    source, project = video
    found = reference.frames(str(source), rate=2, root=str(project))
    assert provenance.verify(str(project))["leaked"] == []
    _git(project, "init", "-q")
    _git(project, "add", "-f", found["manifest"])
    leaked = provenance.verify(str(project))["leaked"]
    assert [one["artefact"] for one in leaked] == [found["manifest"]]
    assert provenance.verify(str(project))["sound"] is False


def test_a_store_page_is_never_cut_from_internal_footage(video):
    from polyweave.layers.store import store

    source, project = video
    found = reference.frames(str(source), rate=2, root=str(project))
    frame = f"{found['folder']}/t00000000.png"
    provenance.write(provenance.build(
        "picture", frame, inputs=[provenance.source("frames", found["manifest"],
                                                    root=project)],
        root=project), project)
    with pytest.raises(PolyweaveError) as refused:
        store.capsules(frame, frame, out="store", root=str(project))
    assert refused.value.code == "store.internal-input"
