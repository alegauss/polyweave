"""A clip bought from a Scenario video model, measured as a video (§PW692).

Scenario is stood in for by a fake answering its v1 routes, and the delivery is a real
one-second MP4 ffmpeg makes, so nothing is spent: the test is that the fields go as
the model declares them, that the clip is ledgered and recorded as a video, and that
its length and size are measured off the file.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store import footage
from polyweave.services import purchase
from polyweave.services import scenario as scenario_adapter
from polyweave.services import service as S

needs_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="needs ffmpeg"
)

MODEL = "model_kling-v2-1"

PROJECT = f"""[service.scenario]
base = "https://api.cloud.scenario.com"
key_env = "SCENARIO_TEST_KEY"
prices = {{ "{MODEL}" = 20 }}

[budget.scenario]
amount = 100
unit = "CU"
expires = "2099-12-31"
"""


class Fake:
    """Scenario's routes for one video model, answering at once."""

    def __init__(self):
        self.sent: list[tuple[str, str, dict | None]] = []
        self.quote = 20
        self.inputs = [
            {"name": "prompt", "type": "string"},
            {"name": "image", "type": "file"},
            {"name": "duration", "type": "number", "allowedValues": [5, 10]},
            {"name": "aspectRatio", "type": "string",
             "allowedValues": ["16:9", "9:16"]},
        ]

    def __call__(self, method, url, key, body=None):
        assert key == "k:s"
        path = url.split("/v1/", 1)[1]
        self.sent.append((method, path, body))
        if path == f"models/{MODEL}":
            return 200, {"model": {"id": MODEL, "inputs": self.inputs}}
        if path == f"generate/custom/{MODEL}?dryRun=true":
            return 200, {"creativeUnitsCost": self.quote}
        if path == f"generate/custom/{MODEL}":
            return 200, {"job": {"jobId": "job_v", "status": "queued"}}
        if path == "jobs/job_v":
            return 200, {"job": {"status": "success",
                                 "metadata": {"assetIds": ["asset_v"]}}}
        if path == "assets/asset_v":
            return 200, {"asset": {"url": "https://cdn.example/asset_v.mp4"}}
        return 404, {"error": path}


def clip(where) -> bytes:
    """A one-second 64x36 MP4 with no sound."""
    subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc=size=64x36:rate=10:duration=1", "-pix_fmt", "yuv420p", str(where)],
        check=True,
    )
    return where.read_bytes()


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("SCENARIO_TEST_KEY", "k:s")
    fake = Fake()
    monkeypatch.setattr(scenario_adapter, "call", fake)
    monkeypatch.setattr(scenario_adapter, "POLL_EVERY", 0.0)
    if shutil.which("ffmpeg"):
        made = clip(tmp_path / "made.mp4")
        monkeypatch.setattr(S, "download", lambda link: made)
    (tmp_path / "art").mkdir()
    Image.new("RGB", (32, 18), (90, 120, 160)).save(tmp_path / "art" / "still.png")
    return tmp_path, fake


def bought(root, **over):
    return footage.buy(**{"out": "video/intro.mp4",
                          "prompt": "a plush rocket lifts off", "model": MODEL,
                          "service": "scenario", "root": str(root), **over})


def drawn(fake) -> dict:
    return [body for method, path, body in fake.sent
            if method == "POST" and path == f"generate/custom/{MODEL}"][-1]


@needs_ffmpeg
def test_a_clip_is_bought_recorded_as_a_video_and_measured(project):
    root, fake = project
    entry = bought(root, image="art/still.png", duration=5, aspect_ratio="16x9")
    payload = drawn(fake)
    assert payload["prompt"] == "a plush rocket lifts off"
    assert payload["image"].startswith("data:image/png;base64,")
    assert payload["duration"] == 5 and payload["aspectRatio"] == "16:9"
    assert entry["bought"] == "video" and entry["credits"] == 20
    assert entry["video"]["video_width"] == 64 and entry["video"]["video_height"] == 36
    assert entry["video"]["video_seconds"] == pytest.approx(1.0, abs=0.15)
    assert entry["video"]["audio"] is False
    record = provenance.read("video/intro.mp4", root)
    assert record["bought"] == "video"
    assert record["details"]["model"] == MODEL and "image" not in record["details"]
    assert record["inputs"][0]["role"] == "image"
    assert record["measurements"]["video_width"] == 64
    assert purchase.spent(root, service="scenario") == 20


@needs_ffmpeg
def test_a_duration_the_model_does_not_make_is_refused_before_spending(project):
    root, fake = project
    with pytest.raises(PolyweaveError) as refused:
        bought(root, duration=7)
    assert refused.value.code == "fetch.bad-choice"
    assert "5, 10" in refused.value.remedy
    assert f"generate/custom/{MODEL}" not in [p for _, p, _ in fake.sent]
    assert purchase.read(root) == []


@needs_ffmpeg
def test_a_still_the_model_cannot_start_from_is_refused(project):
    root, fake = project
    fake.inputs = [{"name": "prompt", "type": "string"}]
    with pytest.raises(PolyweaveError) as refused:
        bought(root, image="art/still.png")
    assert refused.value.code == "fetch.unknown-field"
    assert purchase.read(root) == []


@needs_ffmpeg
def test_a_quote_above_the_row_is_refused_before_anything_is_spent(project):
    root, fake = project
    fake.quote = 35
    with pytest.raises(PolyweaveError) as refused:
        bought(root)
    assert refused.value.code == "picture.quoted-over-price"
    assert purchase.read(root) == []


def test_a_clip_needs_a_video_file_and_a_model(project):
    root, fake = project
    with pytest.raises(PolyweaveError) as refused:
        bought(root, out="video/intro.png")
    assert refused.value.code == "fetch.bad-choice"
    with pytest.raises(PolyweaveError) as refused:
        bought(root, model=None)
    assert refused.value.code == "fetch.missing-field"
    assert fake.sent == []


def test_the_adapter_waits_longer_on_a_video_job():
    assert scenario_adapter.VIDEO_TIMEOUT > scenario_adapter.JOB_TIMEOUT
    assert "video" in scenario_adapter.SERVICE.media
