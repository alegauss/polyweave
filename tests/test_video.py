"""A teaser cut from captured runs, scored, encoded and measured (§PW429)."""

from __future__ import annotations

import json
import shutil
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from polyweave import accept, video
from polyweave.errors import PolyweaveError

needs_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="needs ffmpeg"
)


def _run(
    folder: Path,
    *,
    seconds: float,
    fps: int = 30,
    still: float = 0.0,
    colour=(200, 60, 40),
    audio: bool = False,
) -> Path:
    """A folder as capture.movie writes one: numbered frames, sequence.json, audio.wav.
    The square stands for `still` seconds, then moves across."""
    folder.mkdir(parents=True)
    frames = []
    for n in range(int(seconds * fps)):
        image = Image.new("RGB", (320, 180), (20, 22, 28))
        moving = max(0.0, n / fps - still)
        x = int(20 + moving * 120) % 260
        image.paste(colour, (x, 60, x + 50, 110))
        name = f"{n + 1:04d}.png"
        image.save(folder / name)
        frames.append({"file": name, "tick": n, "sha256": ""})
    if audio:
        _tone(folder / "audio.wav", seconds, 330.0)
    (folder / "sequence.json").write_text(
        json.dumps(
            {
                "format": 1,
                "fps": fps,
                "count": len(frames),
                "dropped": [],
                "audio": audio,
                "frames": frames,
            }
        ),
        encoding="utf-8",
    )
    return folder


def _tone(path: Path, seconds: float, pitch: float) -> None:
    rate = 48000
    t = np.arange(int(seconds * rate)) / rate
    samples = (0.3 * np.sin(2 * np.pi * pitch * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(samples.tobytes())


def _project(tmp_path: Path) -> Path:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    return tmp_path


@needs_ffmpeg
def test_two_runs_crossfade_under_music_into_an_mp4_that_measures_what_it_is(tmp_path):
    here = _project(tmp_path)
    _run(here / "caps" / "a", seconds=3, still=1.0)
    _run(here / "caps" / "b", seconds=3, colour=(40, 160, 220), audio=True)
    _tone(here / "theme.wav", 8, 220.0)
    (here / "teaser.cut.toml").write_text(
        '[video]\nout = "store/teaser.mp4"\nsize = [640, 360]\nfps = 30\n'
        'music = "theme.wav"\nclip_audio = true\nfade_out = 0.5\n\n'
        '[[clip]]\nfrom = "caps/a"\nstart = 0.5\nlength = 2.0\n\n'
        '[[clip]]\nfrom = "caps/b"\nstart = 0.0\nlength = 2.0\nfade_in = 0.5\n',
        encoding="utf-8",
    )
    said = video.cut("teaser.cut.toml", root=str(here))
    assert said["file"] == "store/teaser.mp4"
    assert (said["video_width"], said["video_height"]) == (640, 360)
    assert said["video_seconds"] == pytest.approx(3.5, abs=0.1)
    assert said["video_fps"] == pytest.approx(30)
    # the first clip starts half a second in, and its run holds still for a second
    assert said["first_motion"] == pytest.approx(0.5, abs=0.1)
    assert said["audio"] is True
    assert (here / said["sheet"]).is_file()
    record = json.loads((here / "store" / "teaser.mp4.prov.json").read_text("utf-8"))
    assert {one["path"] for one in record["inputs"]} >= {
        "caps/a/sequence.json",
        "caps/b/sequence.json",
        "theme.wav",
    }

    (here / "teaser.accept.toml").write_text(
        'asset = "teaser"\n\n[[predicate]]\nid = "short"\nmeasure = "video_seconds"\n'
        'max = 30\n\n[[predicate]]\nid = "plays-soon"\nmeasure = "first_motion"\n'
        'max = 3\n\n[[predicate]]\nid = "full-hd"\nmeasure = "video_width"\n'
        "min = 1920\n",
        encoding="utf-8",
    )
    checked = accept.checked("teaser.accept.toml", "store/teaser.mp4", root=str(here))
    assert checked["failed"] == ["full-hd"]


@needs_ffmpeg
def test_a_clip_asking_more_than_its_run_holds_is_refused_before_ffmpeg_runs(tmp_path):
    here = _project(tmp_path)
    _run(here / "caps" / "a", seconds=1)
    (here / "t.cut.toml").write_text(
        '[[clip]]\nfrom = "caps/a"\nstart = 0.5\nlength = 1.0\n', encoding="utf-8"
    )
    with pytest.raises(PolyweaveError) as refused:
        video.cut("t.cut.toml", root=str(here))
    assert refused.value.code == "video.short-sequence"


def test_a_cut_is_refused_on_what_it_cannot_hold(tmp_path):
    here = _project(tmp_path)
    _run(here / "caps" / "a", seconds=2)
    for body, code in [
        (
            '[video]\nsize = [1921, 1080]\n[[clip]]\nfrom = "caps/a"\nlength = 1\n',
            "video.bad-cut",
        ),
        (
            '[video]\nspeed = 2\n[[clip]]\nfrom = "caps/a"\nlength = 1\n',
            "video.bad-cut",
        ),
        ('[[clip]]\nfrom = "caps/a"\nlength = 1\nfade_in = 0.5\n', "video.bad-cut"),
        ('[[clip]]\nfrom = "caps/none"\nlength = 1\n', "video.no-sequence"),
        ("[video]\nfps = 30\n", "video.bad-cut"),
    ]:
        (here / "t.cut.toml").write_text(body, encoding="utf-8")
        with pytest.raises(PolyweaveError) as refused:
            video.read(here / "t.cut.toml", here)
        assert refused.value.code == code, body
