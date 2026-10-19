"""A recorded track cut into a loop on its own beat grid (§PW192).

Cottony's tools/audio/loop_music.py moved here. On Cottony's own track it cut 57 bars at
124.00 BPM and measured the same as the loop the game shipped; these hold the cut on a
track whose beat and bars are known.
"""

from __future__ import annotations

import shutil
import wave

import numpy as np
import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import sound, sound_loop

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None,
                                  reason="ffmpeg absent: it decodes and encodes")

RATE = sound_loop.RATE
BPM = 120.0


def track(tmp_path, *, fade_out: bool = False):
    """A four-chord tune at 120 BPM, one chord a bar, round and round."""
    beat = 60.0 / BPM
    bars = 1 + 16
    t = np.arange(int(bars * 4 * beat * RATE)) / RATE
    out = np.zeros_like(t)
    for i in range(bars * 4):
        start = i * beat
        hz = (220.0, 277.18, 329.63, 246.94)[(i // 4) % 4]
        here = t >= start
        level = 1.0 if i % 4 == 0 else 0.5
        since = t - start
        out += here * level * np.sin(2 * np.pi * hz * since) * np.exp(-since / 0.15)
    if fade_out:
        out *= np.clip(1.0 - t / t[-1], 0.05, 1.0) ** 3
    pcm = (np.clip(out * 0.3, -1, 1) * 32767).astype("<i2")
    with wave.open(str(tmp_path / "track.wav"), "wb") as held:
        held.setnchannels(1)
        held.setsampwidth(2)
        held.setframerate(RATE)
        held.writeframes(pcm.tobytes())
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    return "track.wav"


@needs_ffmpeg
def test_a_track_is_cut_on_its_bars_and_its_wrap_does_not_click(tmp_path):
    # The step is the seam measure this sparse tune of lone notes answers cleanly.
    found = sound_loop.loop(track(tmp_path), out="loop.wav", root=str(tmp_path))
    assert found["bpm"] == pytest.approx(BPM, abs=0.05)
    assert found["seam_step"] <= sound_loop.STEP_LIMIT
    bar = 4 * 60.0 / BPM
    bars = found["seconds"] / bar
    assert bars == pytest.approx(round(bars), abs=0.05)
    heard = sound.measure(tmp_path / "loop.wav")
    assert heard["duration"] == pytest.approx(found["seconds"], abs=0.001)


@needs_ffmpeg
def test_a_loop_opens_on_the_bar_asked_and_stays_seamless(tmp_path):
    # Rotated, the loop is the same audio round the circle: the same length, a wrap
    # as quiet as the unrotated one, opening where the bar was (§PW561).
    whole = sound_loop.loop(track(tmp_path), out="whole.wav", root=str(tmp_path))
    found = sound_loop.loop("track.wav", out="loop.wav", root=str(tmp_path), start=2)
    bar = 4 * 60.0 / BPM
    assert found["starts_at"] == pytest.approx(whole["first_beat"] + 2 * bar, abs=0.01)
    assert found["seconds"] == whole["seconds"]
    assert found["seam_step"] <= sound_loop.STEP_LIMIT
    rotated, _ = sound.read(tmp_path / "loop.wav")
    plain, _ = sound.read(tmp_path / "whole.wav")
    # starts_at is to the millisecond, so the sample it names is found within 50
    near = round(found["starts_at"] * RATE)
    off = min(range(near - 50, near + 51),
              key=lambda at: np.abs(rotated[:RATE] - plain[at: at + RATE]).max())
    assert np.allclose(rotated[:RATE], plain[off: off + RATE], atol=2 / 32768)


@needs_ffmpeg
@pytest.mark.parametrize("suffix", ["wav", "ogg"])
def test_the_loop_reads_its_seam_as_a_spec_over_the_file_would(tmp_path, suffix):
    # One seam measure: the loop's numbers are sound.measure's on the file it wrote,
    # under the same names, so its passed is the spec's answer (§PW560).
    found = sound_loop.loop(track(tmp_path), out=f"loop.{suffix}", root=str(tmp_path))
    heard = sound.measure(tmp_path / f"loop.{suffix}")
    for name in ("seam_step", "seam_flux"):
        assert found[name] == heard[name]
    assert "seam_change" not in found
    assert found["passed"] == (found["seam_step"] <= sound_loop.STEP_LIMIT
                               and found["seam_flux"] <= sound_loop.FLUX_LIMIT)
    # An encoded loop also says how its seam read as cut, before the encoder.
    assert ("as_cut" in found) == (suffix == "ogg")
    if suffix == "ogg":
        assert set(found["as_cut"]) >= {"seam_step", "seam_flux"}


@needs_ffmpeg
def test_a_start_past_the_loop_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        sound_loop.loop(track(tmp_path), out="loop.wav", root=str(tmp_path), start=99)
    assert refused.value.code == "sound.start-past-loop"


@needs_ffmpeg
def test_a_track_that_never_comes_back_to_its_opening_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        sound_loop.loop(track(tmp_path, fade_out=True), out="loop.wav",
                        root=str(tmp_path))
    assert refused.value.code == "sound.no-loop-point"


def test_a_track_that_is_not_there_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[paths]\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        sound_loop.loop("gone.wav", out="loop.wav", root=str(tmp_path))
    assert refused.value.code == "spec.unreadable-sound"
