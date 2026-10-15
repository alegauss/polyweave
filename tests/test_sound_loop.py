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

from polyweave import sound, sound_loop
from polyweave.errors import PolyweaveError

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
    # The spectral bar is the track's own 90th percentile, which a tune of lone notes
    # leaves near zero; on Cottony's dense mix the same cut read 0.61. The step is the
    # one this sparse track can answer.
    found = sound_loop.loop(track(tmp_path), out="loop.wav", root=str(tmp_path))
    assert found["bpm"] == pytest.approx(BPM, abs=0.05)
    assert found["seam_step"] <= sound_loop.STEP_LIMIT
    bar = 4 * 60.0 / BPM
    bars = found["seconds"] / bar
    assert bars == pytest.approx(round(bars), abs=0.05)
    heard = sound.measure(tmp_path / "loop.wav")
    assert heard["duration"] == pytest.approx(found["seconds"], abs=0.001)


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
