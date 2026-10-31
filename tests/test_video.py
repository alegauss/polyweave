"""A teaser cut from captured runs, scored, encoded and measured (§PW429)."""

from __future__ import annotations

import json
import shutil
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store import video
from polyweave.loop import accept

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


@needs_ffmpeg
def test_a_still_is_held_and_moved_and_a_video_file_is_cut_in(tmp_path):
    """§PW671: Dumont held its cards and cut its B-roll with ffmpeg calls of its own."""
    import subprocess

    here = _project(tmp_path)
    card = Image.new("RGB", (640, 360), (30, 30, 36))
    card.paste((230, 200, 40), (80, 80, 560, 280))
    card.save(here / "card.png")
    _run(here / "caps" / "a", seconds=2, still=0.0)
    subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-y", "-framerate", "30", "-i",
         str(here / "caps" / "a" / "%04d.png"), "-pix_fmt", "yuv420p",
         str(here / "broll.mp4")], check=True)
    (here / "story.cut.toml").write_text(
        '[video]\nsize = [640, 360]\nfps = 30\n\n'
        '[[clip]]\nstill = "card.png"\nlength = 1.0\n\n'
        '[[clip]]\nstill = "card.png"\nlength = 1.0\n'
        'motion = { zoom = [1.0, 1.3], pan = "left" }\n\n'
        '[[clip]]\nvideo = "broll.mp4"\nstart = 0.5\nlength = 1.0\nfade_in = 0.25\n',
        encoding="utf-8",
    )
    said = video.cut("story.cut.toml", root=str(here))
    assert said["video_seconds"] == pytest.approx(2.75, abs=0.1)
    # The held card does not move; the zoom does, from its first second on.
    assert said["first_motion"] == pytest.approx(1.0, abs=0.15)
    record = json.loads((here / "story.mp4.prov.json").read_text("utf-8"))
    assert {one["role"] for one in record["inputs"]} == {"still", "video"}


def test_a_file_clip_is_refused_on_what_it_cannot_hold(tmp_path):
    here = _project(tmp_path)
    Image.new("RGB", (64, 36)).save(here / "card.png")
    for body in (
        '[[clip]]\nstill = "card.png"\nfrom = "caps/a"\nlength = 1\n',
        '[[clip]]\nstill = "card.png"\nlength = 1\nmotion = { zoom = [0.5, 1.0] }\n',
        '[[clip]]\nstill = "card.png"\nlength = 1\nmotion = { pan = "sideways" }\n',
    ):
        (here / "t.cut.toml").write_text(body, encoding="utf-8")
        with pytest.raises(PolyweaveError) as refused:
            video.read(here / "t.cut.toml", here)
        assert refused.value.code == "video.bad-cut", body
    (here / "t.cut.toml").write_text('[[clip]]\nstill = "gone.png"\nlength = 1\n',
                                     encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        video.read(here / "t.cut.toml", here)
    assert refused.value.code == "video.no-source"


@needs_ffmpeg
def test_each_language_is_a_track_of_its_voices_over_the_music_with_subtitles(tmp_path):
    """§PW671: Dumont laid each language's narration over a looped bed by hand."""
    here = _project(tmp_path)
    Image.new("RGB", (640, 360), (30, 30, 36)).save(here / "card.png")
    _tone(here / "bed.wav", 1.0, 110.0)
    _tone(here / "en.wav", 0.8, 440.0)
    _tone(here / "pt.wav", 0.8, 550.0)
    (here / "en.srt").write_text(
        "1\n00:00:00,500 --> 00:00:01,500\nWelcome\n", encoding="utf-8")
    (here / "story.cut.toml").write_text(
        '[video]\nsize = [640, 360]\nfps = 30\nmusic = "bed.wav"\nmusic_loop = true\n'
        "music_gain = -12\n\n"
        '[[clip]]\nstill = "card.png"\nlength = 2.5\n\n'
        '[[track]]\nlanguage = "eng"\n\n[[track]]\nlanguage = "por"\n\n'
        '[[voice]]\nfile = "en.wav"\nat = 0.5\ntrack = "eng"\n\n'
        '[[voice]]\nfile = "pt.wav"\nat = 0.5\ntrack = "por"\n\n'
        '[[subtitles]]\nfile = "en.srt"\nlanguage = "eng"\n',
        encoding="utf-8",
    )
    said = video.cut("story.cut.toml", root=str(here))
    assert said["tracks"] == ["eng", "por"]
    assert (said["audio_tracks"], said["subtitle_tracks"]) == (2, 1)
    # The one-second bed loops under the whole cut.
    assert said["video_seconds"] == pytest.approx(2.5, abs=0.1)
    record = json.loads((here / "story.mp4.prov.json").read_text("utf-8"))
    assert {"voice", "subtitles", "music"} <= {one["role"] for one in record["inputs"]}


def test_a_voice_on_no_declared_track_is_refused(tmp_path):
    here = _project(tmp_path)
    Image.new("RGB", (64, 36)).save(here / "card.png")
    _tone(here / "en.wav", 0.5, 440.0)
    (here / "t.cut.toml").write_text(
        '[[clip]]\nstill = "card.png"\nlength = 1\n\n'
        '[[voice]]\nfile = "en.wav"\nat = 0\ntrack = "eng"\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        video.read(here / "t.cut.toml", here)
    assert refused.value.code == "video.bad-cut"
    assert "no [[track]] declares" in refused.value.message
