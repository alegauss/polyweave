"""A recording drafted as an editable score, heard into MIDI first (§PW559).

The recordings are synthesised here, tones with harmonics and drums from noise, so what
was played is known to the step. Demucs is optional and heavy; the four-stem case
stands a fake in its place that hands back the parts the mix was made of.
"""

from __future__ import annotations

import shutil
import wave

import numpy as np
import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import music, music_heard, sound_stems

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None,
                                  reason="ffmpeg absent: it decodes the recording")

RATE = music_heard.RATE
BEAT = 0.5  # 120 bpm


def tone(pitch: int, start: float, length: float, seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    hz = 440.0 * 2 ** ((pitch - 69) / 12)
    inside = (t >= start) & (t < start + length)
    since = np.where(inside, t - start, 0.0)
    attack = np.minimum(1.0, since / 0.005)
    envelope = np.where(inside, attack * np.exp(-2.5 * since), 0)
    return envelope * sum(np.sin(2 * np.pi * hz * h * t) / h for h in range(1, 5))


def hit(kind: str, start: float, seconds: float, seed: int) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    since = t - start
    on = (since >= 0) & (since < 0.15)
    if kind == "bd":
        body = np.sin(2 * np.pi * 55.0 * since) * np.exp(-25 * np.maximum(since, 0))
    else:
        noise = np.random.default_rng(seed).standard_normal(len(t))
        if kind == "hh":
            noise = np.diff(np.diff(noise, prepend=0), prepend=0)  # tilted up
        body = noise * np.exp(-40 * np.maximum(since, 0)) * 0.3
        if kind == "sd":
            body = body + 0.5 * np.sin(2 * np.pi * 200 * since) * np.exp(
                -30 * np.maximum(since, 0))
    return np.where(on, body, 0.0)


MELODY = (60, 64, 67, 72)
BASS = (36, 43)


def melody(bars: int, lead: float = 0.0) -> np.ndarray:
    seconds = lead + bars * 4 * BEAT + 1.0
    return sum(tone(MELODY[i % 4], lead + i * BEAT, 0.45, seconds)
               for i in range(bars * 4)) * 0.2


def stereo(signal: np.ndarray) -> np.ndarray:
    return np.stack([signal, signal], axis=1) * 32767.0


def write(tmp_path, name: str, signal: np.ndarray) -> str:
    with wave.open(str(tmp_path / name), "wb") as held:
        held.setnchannels(1)
        held.setsampwidth(2)
        held.setframerate(RATE)
        held.writeframes((np.clip(signal, -1, 1) * 32767).astype("<i2").tobytes())
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    return name


def heard(tmp_path, found: dict) -> list[tuple[str, int, int]]:
    text = (tmp_path / found["score"]).read_text(encoding="utf-8")
    model, problems = music.compile_source(text)
    assert problems == []
    return sorted((n["part"], n["start"], n["pitch"]) for n in model["notes"])


@needs_ffmpeg
def test_a_played_melody_drafts_to_its_notes_on_the_grid(tmp_path):
    track = write(tmp_path, "tune.wav", melody(4))
    found = music_heard.from_audio(track, split="none", bpm=120, root=str(tmp_path))
    assert found["valid"] is True and found["problems"] == []
    assert found["score"] == "tune.music.toml"
    assert (tmp_path / "tune.heard.mid").is_file()
    notes = heard(tmp_path, found)
    assert [p for _, _, p in notes] == list(MELODY) * 4
    quarter = 480
    starts = [s for _, s, _ in notes]
    assert [b - a for a, b in zip(starts, starts[1:], strict=False)] == [quarter] * 15
    assert found["tracks"]["mix"]["on_grid"] == 1.0
    assert found["form"] == ["A"]
    text = (tmp_path / found["score"]).read_text(encoding="utf-8")
    assert 'reference = "tune.wav"' in text


@needs_ffmpeg
def test_the_tempo_is_found_when_none_is_given(tmp_path):
    track = write(tmp_path, "tune.wav", melody(6, lead=0.2))
    found = music_heard.from_audio(track, split="none", root=str(tmp_path))
    assert found["bpm_given"] is False
    assert found["bpm"] == pytest.approx(120, abs=1)
    assert [p for _, _, p in heard(tmp_path, found)] == list(MELODY) * 6


@needs_ffmpeg
def test_the_answer_ends_in_the_sitting_beside_the_original(tmp_path):
    track = write(tmp_path, "tune.wav", melody(2))
    found = music_heard.from_audio(track, split="none", bpm=120, root=str(tmp_path))
    render, sitting = found["next"]
    assert render["operation"] == "music.render"
    assert render["args"]["source"] == "tune.music.toml"
    assert sitting["operation"] == "sound.sitting"
    (member,) = sitting["args"]["members"]
    assert member == {"name": "tune", "new": "tune.ogg", "old": "tune.wav"}


@needs_ffmpeg
def test_four_stems_are_each_a_track_and_the_drums_by_name(tmp_path, monkeypatch):
    seconds = 4 * 4 * BEAT + 1.0
    bass = sum(tone(BASS[(i // 4) % 2], i * BEAT, 0.45, seconds)
               for i in range(16)) * 0.3
    kit = sum(hit("bd" if i % 2 == 0 else "sd", i * BEAT, seconds, i)
              for i in range(16)) * 0.6
    kit = kit + sum(hit("hh", i * BEAT + BEAT / 2, seconds, 100 + i)
                    for i in range(16)) * 0.5
    lead = melody(4)
    parts = {"drums": stereo(kit), "bass": stereo(bass), "other": stereo(lead),
             "vocals": stereo(np.zeros_like(lead))}
    track = write(tmp_path, "song.wav", (bass + kit + lead) * 0.5)
    monkeypatch.setattr(sound_stems, "_separate", lambda frames: (
        parts, {"name": "demucs", "version": "test", "model": sound_stems.MODEL}))
    found = music_heard.from_audio(track, bpm=120, root=str(tmp_path))
    assert found["valid"] is True
    assert set(found["tracks"]) == {"drums", "bass", "other"}
    assert found["silent"] == ["vocals"]
    assert found["tracks"]["drums"]["instrument"] == "drums:0"
    assert found["tracks"]["bass"]["instrument"] == "gm:33"
    notes = heard(tmp_path, found)
    assert [p for part, _, p in notes if part == "bass"] == [36] * 4 + [43] * 4 + [
        36] * 4 + [43] * 4
    drums = [(s % 1920, p) for part, s, p in notes if part == "drums"]
    assert drums.count((0, 36)) == 4 and drums.count((480, 38)) == 4
    assert drums.count((240, 42)) == 4


@needs_ffmpeg
def test_silence_is_refused_as_nothing_heard(tmp_path):
    track = write(tmp_path, "quiet.wav", np.zeros(RATE * 3))
    with pytest.raises(PolyweaveError) as refused:
        music_heard.from_audio(track, split="none", bpm=120, root=str(tmp_path))
    assert refused.value.code == "music.nothing-heard"


def test_a_track_that_is_not_there_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        music_heard.from_audio("gone.wav", root=str(tmp_path))
    assert refused.value.code == "spec.unreadable-sound"


@needs_ffmpeg
def test_a_draft_never_writes_over_a_score_unless_told(tmp_path):
    track = write(tmp_path, "tune.wav", melody(2))
    (tmp_path / "tune.music.toml").write_text("# edited\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        music_heard.from_audio(track, split="none", bpm=120, root=str(tmp_path))
    assert refused.value.code == "music.draft-exists"
