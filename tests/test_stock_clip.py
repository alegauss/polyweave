"""An excerpt of a public video, taken only under a reuse licence (§PW701).

yt-dlp is stood in for: its metadata answer is the test's, and a download writes a
one-second MP4 ffmpeg makes, so nothing reaches the network.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import stock

needs_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="needs ffmpeg"
)

URL = "https://www.youtube.com/watch?v=FC9wfK1_F8c"
CC = "Creative Commons Attribution license (reuse allowed)"


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    calls = []
    said = {"id": "FC9wfK1_F8c", "title": "WordPress at 20", "channel": "WordPress",
            "license": CC, "duration": 300, "webpage_url": URL,
            "channel_url": "https://www.youtube.com/@WordPress"}

    def run(argv):
        calls.append(argv)
        if "-J" in argv:
            return json.dumps(said)
        target = argv[argv.index("-o") + 1]
        subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc=size=64x36:rate=10:duration=1", "-pix_fmt",
                        "yuv420p", target], check=True)
        return ""

    monkeypatch.setattr(stock, "_run", run)
    return tmp_path, said, calls


@needs_ffmpeg
def test_a_cc_excerpt_is_fetched_bounded_and_owes_its_credit(project):
    root, _, calls = project
    said = stock.clip(URL, "footage/wp.mp4", start=12, end=20, root=str(root))
    assert said["licence"] == CC and said["channel"] == "WordPress"
    assert "*12-20" in calls[1]
    record = provenance.read("footage/wp.mp4", root)
    assert record["params"]["start"] == 12 and record["params"]["end"] == 20
    assert record["source_page"] == URL
    owed = provenance.credits(root=str(root))["owed"]
    assert owed[0]["files"] == ["footage/wp.mp4"]
    assert "WordPress at 20" in owed[0]["credit"]


@pytest.mark.parametrize("licence", ["", "Standard YouTube License"])
def test_a_video_without_a_reuse_licence_is_refused_before_downloading(
    project, licence
):
    root, said, calls = project
    said["license"] = licence
    with pytest.raises(PolyweaveError) as refused:
        stock.clip(URL, "footage/x.mp4", end=5, root=str(root))
    assert refused.value.code == "stock.licence-refused"
    assert len(calls) == 1
    assert not (root / "footage" / "x.mp4").exists()


def test_a_project_s_own_list_decides_which_licences_it_takes(project):
    root, _, calls = project
    (root / "polyweave.toml").write_text(
        '[service.youtube]\nlicences = ["Creative Commons Attribution-ShareAlike"]\n',
        encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        stock.clip(URL, "footage/x.mp4", end=5, root=str(root))
    assert refused.value.code == "stock.licence-refused"


def test_an_excerpt_past_the_video_or_backwards_is_refused(project):
    root, _, _ = project
    with pytest.raises(PolyweaveError) as refused:
        stock.clip(URL, "footage/x.mp4", start=10, end=5, root=str(root))
    assert refused.value.code == "stock.bad-excerpt"
    with pytest.raises(PolyweaveError) as refused:
        stock.clip(URL, "footage/x.mp4", start=10, end=500, root=str(root))
    assert refused.value.code == "stock.bad-excerpt"
