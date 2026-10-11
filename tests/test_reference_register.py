"""A reference video registered once, and kept out of what a capture runs (§PW407).

The video is made by ffmpeg from its own test source, as reference.frames' tests make
theirs; registering it, reading it by name, and changing it under its registration are
each a call this test makes.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from polyweave import capture, project, provenance, reference, reference_register
from polyweave.errors import PolyweaveError

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


@pytest.fixture
def video(tmp_path):
    where = tmp_path / "elsewhere" / "play.mp4"
    where.parent.mkdir()
    subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
         "testsrc=s=160x90:d=2:r=10", "-pix_fmt", "yuv420p", str(where)],
        check=True, capture_output=True,
    )
    game = tmp_path / "game"
    game.mkdir()
    (game / "polyweave.toml").write_text("", encoding="utf-8")
    return where, game


def test_a_registered_video_is_read_by_its_name(video):
    source, game = video
    made = reference_register.register(str(source), name="phase1", root=str(game))
    assert made["sha256"] == provenance.sha256_of(source)[0]
    if shutil.which("ffprobe"):
        assert (made["width"], made["height"], made["rate"]) == (160, 90, 10.0)
        assert made["duration"] == pytest.approx(2.0, abs=0.2)
    found = reference.frames("phase1", rate=2, root=str(game))
    listed = json.loads((game / found["manifest"]).read_text("utf-8"))
    assert found["frames"] > 0 and listed["reference"] == "phase1"


def test_a_video_changed_since_it_was_registered_is_refused(video):
    source, game = video
    reference_register.register(str(source), name="phase1", root=str(game))
    with source.open("ab") as more:
        more.write(b"\0" * 64)
    # By its name, and by its path: either way it is no longer the file registered.
    for named in ("phase1", str(source)):
        with pytest.raises(PolyweaveError) as refused:
            reference.frames(named, rate=2, root=str(game))
        assert refused.value.code == "fetch.reference-changed"
        assert "reference.register" in refused.value.remedy
    reference_register.register(str(source), name="phase1", root=str(game))
    assert reference.frames("phase1", rate=2, root=str(game))["frames"] > 0


def test_a_video_declared_at_another_size_is_refused_when_registered(video):
    if not shutil.which("ffprobe"):
        pytest.skip("no ffprobe to read the video's size")
    source, game = video
    (game / "polyweave.toml").write_text(
        "[reference.phase1]\nsize = [320, 180]\n"
        "regions = { play = [0, 0, 320, 180] }\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        reference_register.register(str(source), name="phase1", root=str(game))
    assert refused.value.code == "capture.wrong-size"


def test_a_capture_never_runs_on_internal_footage(video):
    source, game = video
    found = reference.frames(str(source), rate=2, root=str(game))
    with pytest.raises(PolyweaveError) as refused:
        capture.taken("scene.gd", expect="shot: (.*)",
                      args=[f"--plan={found['manifest']}"], root=str(game))
    assert refused.value.code == "capture.internal-input"


def test_the_project_check_names_a_tracked_file_taken_from_a_reference(video):
    source, game = video
    found = reference.frames(str(source), rate=2, root=str(game))
    subprocess.run(["git", "init", "-q"], cwd=game, check=True)
    subprocess.run(["git", "add", "-f", found["manifest"]], cwd=game, check=True)
    codes = [one["code"] for one in project.check(str(game))["findings"]]
    assert "adopt.internal-tracked" in codes
