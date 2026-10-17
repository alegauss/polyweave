"""A recorded track cut into the loop a game plays, and its seam proved (§PW192).

Cottony's music is recorded, generated from a prompt, and a generated track arrives with
an ending: the one its RK134 started from faded into a second of silence, so every
repeat was a fade, a gap and a hard start. `tools/audio/loop_music.py` cut it into a
loop, and this is that script moved here, since any game with a recorded track needs
the same cut.

How the cut is chosen, in order:

1. **The beat grid.** Spectral flux, and the tempo and phase whose beats land on the
   most of it. A generated track is sample-locked to its tempo: on Cottony's track the
   waveform correlation peaked within two samples of where 124.000 BPM put the bar.
2. **The bar.** Every bar line in the second half whose first two beats are about as
   loud as the track's first two is a candidate, and the one that sounds most like them
   wins, by the correlation of their log spectra. The level is not optional: on
   Cottony's track the best spectral match alone was bar 41, in the loud middle, which
   would have dropped the intro's quiet into the seam and a third of the music with it.
   Matched on level too it is bar 57, in the outro. The length is then refined by
   waveform correlation.
3. **The seam.** What followed the cut is crossfaded into the head over one beat, equal
   power, so the last sample is followed by the sample that followed it the first time.

Then the file written is decoded and its wrap measured, so the answer carries the seam
the player hears, and a seam that stands out is said, not hidden.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import numpy as np

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

RATE = 44100

#: Vorbis quality: 5 is about 160 kbit/s, where a marimba's attack still reads as one.
QUALITY = 5

#: The tempos searched. A generated casual track sits well inside this, and a floor
#: above half of the ceiling keeps the search from answering half the real tempo.
TEMPOS = (90.0, 170.0)

#: A bar line is a candidate while its first two beats are within this factor of the
#: opening's level, either way. It also keeps the cut out of the ending's fade.
LEVEL = 1.5

#: The seam stands out above these: the wrap's step over the track's 99th-percentile
#: step, and its largest spectral change over the track's 90th-percentile change,
#: Cottony's own bars. A seam may sound like any ordinary moment of the music, a note
#: starting included.
STEP_LIMIT = 1.0
FLUX_LIMIT = 1.0


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found is None:
        raise PolyweaveError(
            "sound.no-ffmpeg",
            "cutting a loop decodes the track and encodes the loop, and there is no "
            "ffmpeg on PATH",
            "put ffmpeg (with libvorbis, for an Ogg loop) on PATH",
        )
    return found


def _decode(path: Path) -> np.ndarray:
    raw = subprocess.run(
        [_ffmpeg(), "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "2",
         "-ar", str(RATE), "-"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float64)


def _encode(frames: np.ndarray, path: Path, quality: int) -> None:
    pcm = np.clip(np.round(frames), -32768, 32767).astype(np.int16).tobytes()
    codec = (["-c:a", "libvorbis", "-q:a", str(quality)]
             if path.suffix.lower() == ".ogg" else [])
    subprocess.run(
        [_ffmpeg(), "-v", "error", "-y", "-f", "s16le", "-ac", "2", "-ar", str(RATE),
         "-i", "-", *codec, str(path)],
        check=True, input=pcm,
    )


def _spectra(mono: np.ndarray, size: int = 2048, hop: int = 512) -> np.ndarray:
    window = np.hanning(size)
    starts = range(0, len(mono) - size, hop)
    return np.array([np.log1p(np.abs(np.fft.rfft(mono[i: i + size] * window)) * 20.0)
                     for i in starts])


def _flux(mono: np.ndarray, hop: int = 512) -> np.ndarray:
    frames = _spectra(mono, hop=hop)
    return np.maximum(np.diff(frames, axis=0), 0.0).sum(axis=1)


def _beat_grid(mono: np.ndarray) -> tuple[float, float]:
    """(seconds per beat, seconds to the first beat)."""
    hop = 256
    onsets = _flux(mono, hop=hop)
    onsets = np.maximum(onsets - np.convolve(onsets, np.ones(32) / 32, "same"), 0.0)
    per_second = RATE / hop
    best = (-1.0, 0.0, 0.0)
    for bpm in np.arange(TEMPOS[0], TEMPOS[1], 0.01):
        period = 60.0 / bpm * per_second
        for phase in np.linspace(0.0, period, 48, endpoint=False):
            steps = np.arange(0.0, len(onsets) - period, period)
            score = float(onsets[np.round(phase + steps).astype(int)].mean())
            if score > best[0]:
                best = (score, 60.0 / bpm, phase / per_second)
    return best[1], best[2]


def _rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(signal**2)))


def _cut_length(mono: np.ndarray, beat: float, first: float) -> tuple[int, int, float]:
    """The loop's length in samples, a whole number of bars from the track's start.

    Answers (samples, bars, how well that bar's opening matches the track's).
    """
    bar = 4 * beat
    two = int(2 * beat * RATE)
    opening = mono[int(first * RATE): int(first * RATE) + two]
    head = _spectra(opening).ravel()
    scored = []
    for k in range(1, int((len(mono) / RATE - first) / bar)):
        cut = round(k * bar * RATE)
        start = int((first + k * bar) * RATE)
        if k * bar < len(mono) / RATE / 2 or start + two > len(mono):
            continue
        there = mono[start: start + two]
        if not 1.0 / LEVEL <= _rms(there) / max(_rms(opening), 1e-9) <= LEVEL:
            continue
        likeness = float(np.corrcoef(_spectra(there).ravel(), head)[0, 1])
        scored.append((likeness, k, cut))
    if not scored:
        raise PolyweaveError(
            "sound.no-loop-point",
            "no bar line in the second half of the track is as loud as its opening, so "
            "there is nowhere to loop it",
            "give the whole track, intro to outro; a loop is cut where the music comes "
            "back round to how it started",
        )
    score, bars, cut = max(scored)
    # the grid is good to a few hundred samples; the waveform says where
    reach, span = int(0.03 * RATE), int(2.0 * RATE)
    near = mono[cut - reach: cut + reach + span]
    lags = np.correlate(near, mono[:span], "valid")
    energy = np.sqrt(np.convolve(near**2, np.ones(span), "valid"))
    best = int(np.argmax(lags / np.maximum(energy, 1e-9)))
    return cut - reach + best, bars, score


def _seam(frames: np.ndarray) -> tuple[float, float]:
    """The wrap against the track: its step and its spectral change, as bars read."""
    mono = frames.mean(axis=1)
    step = abs(mono[0] - mono[-1]) / float(np.percentile(np.abs(np.diff(mono)), 99))
    size, hop = 2048, 512
    wrapped = np.concatenate([mono[-4 * size:], mono[: 4 * size]])
    across = _flux(wrapped, hop=hop)
    middle = len(across) // 2
    body = _flux(mono, hop=hop)
    return step, float(across[middle - 4: middle + 4].max() / np.percentile(body, 90))


@operation("sound.loop")
def loop(
    track: Annotated[str, Param("the recorded track, intro to outro, in the project")],
    out: Annotated[str, Param("the loop to write, .ogg or .wav, under the project")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    quality: Annotated[
        int, Param("the Vorbis quality of an Ogg loop", lo=0, hi=10)
    ] = QUALITY,
) -> dict:
    """Cut a recorded track into a loop on its beat grid and prove its seam."""
    here = load(root).root
    source, target = here / track, here / out
    if not source.is_file():
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"there is no track at {track}",
            "name the recorded track as a path under the project",
        )
    frames = _decode(source)
    mono = frames.mean(axis=1)
    beat, first = _beat_grid(mono)
    length, bars, match = _cut_length(mono, beat, first)

    fade = round(beat * RATE)
    t = (np.arange(fade) + 0.5) / fade
    cut = frames[:length].copy()
    cut[:fade] = (frames[:fade] * np.sin(t * np.pi / 2)[:, None]
                  + frames[length: length + fade] * np.cos(t * np.pi / 2)[:, None])
    target.parent.mkdir(parents=True, exist_ok=True)
    _encode(cut, target, quality)

    heard = _decode(target)
    step, change = _seam(heard)
    if len(heard) != length:
        raise PolyweaveError(
            "sound.loop-gap",
            f"the encode came back {len(heard) - length:+d} samples long, which is a "
            "gap or an overlap at the loop point",
            "write the loop as .wav, or use an encoder that keeps the length exactly",
        )
    stands_out = step > STEP_LIMIT or change > FLUX_LIMIT
    tempo = 60.0 / beat
    return {
        "loop": out,
        "seconds": round(length / RATE, 3),
        "bpm": round(float(tempo), 2),
        "first_beat": round(float(first), 3),
        "bars": int(bars),
        "match": round(float(match), 3),
        "seam_step": round(float(step), 3),
        "seam_change": round(float(change), 3),
        "passed": not stands_out,
        "says": (
            "the seam stands out from the track: listen across it before using this"
            if stands_out else
            f"{bars} bars at {tempo:.2f} BPM, the seam like any ordinary moment"
        ),
    }
