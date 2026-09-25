"""A sound held to a spec, as a picture is (§PW113).

Nothing in the acceptance spec is 3D, and the owner decided sound belongs in it. Cottony
already wrote the bar outside this plugin: `tools/audio/loop_music.py` cuts a generated
track into the loop the game plays and fails the loop when its seam stands out. That
measure is here, as two numbers a predicate bounds, with three plainer ones beside them:

- `seam_step`: the jump from the last sample to the first, over the track's own
  99th-percentile step between samples. Above one, the wrap clicks louder than any
  ordinary moment of the music.
- `seam_flux`: the largest spectral change across the wrap, over the track's own
  90th-percentile change. Above one, the seam sounds like a cut rather than a note.
- `loudness`: RMS level in dBFS; `peak`: the largest sample in dBFS; `duration`:
  seconds.

Each ratio is against the track itself, which is why the bar is one number for every
track: a seam may look like any ordinary moment of that music, and nothing more. A WAV
is read with the standard library; anything else is decoded by ffmpeg where it is on
PATH, and refused where it is not.
"""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path
from typing import Annotated

import numpy as np

from .describe import Param, operation
from .errors import PolyweaveError

#: Every sound measure a predicate may bound, and what it says.
SOUNDS: dict[str, str] = {
    "seam_step": "the loop's wrap step over the track's 99th-percentile sample step",
    "seam_flux": "the spectral change across the wrap over the track's 90th percentile",
    "loudness": "RMS level, in dBFS",
    "peak": "the largest sample, in dBFS",
    "duration": "length, in seconds",
}

#: What is read as sound rather than as a picture.
SUFFIXES = (".wav", ".ogg", ".flac", ".mp3", ".opus")

#: The rate a decode through ffmpeg comes back at.
RATE = 44100

_SIZE, _HOP = 2048, 512


def is_sound(name: str) -> bool:
    return name in SOUNDS


def is_audio(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUFFIXES


def read(path: str | Path) -> tuple[np.ndarray, int]:
    """The samples as floats in [-1, 1], one column per channel, and the rate."""
    where = Path(path)
    if not where.is_file():
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"there is no sound at {where}",
            "name the audio file the game plays, as a path under the project",
        )
    if where.suffix.lower() == ".wav":
        return _wav(where)
    if shutil.which("ffmpeg") is None:
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{where.name} needs ffmpeg to decode, and there is none on PATH",
            "put ffmpeg on PATH, or check the WAV the track was made from",
        )
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(where), "-f", "s16le", "-ac", "2"]
        + ["-ar", str(RATE), "-"],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, np.int16).reshape(-1, 2).astype(
        np.float64
    ) / 32768.0, RATE


def _wav(where: Path) -> tuple[np.ndarray, int]:
    try:
        with wave.open(str(where), "rb") as held:
            width, channels = held.getsampwidth(), held.getnchannels()
            rate, raw = held.getframerate(), held.readframes(held.getnframes())
    except (wave.Error, EOFError) as exc:
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{where.name} is not a PCM WAV this can read",
            "write it as 16-bit PCM, or decode it with ffmpeg first",
            detail=str(exc),
        ) from exc
    if width == 3:
        bytes_ = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        whole = (
            bytes_[:, 0].astype(np.int32)
            | bytes_[:, 1].astype(np.int32) << 8
            | bytes_[:, 2].astype(np.int32) << 16
        )
        samples = np.where(whole >= 1 << 23, whole - (1 << 24), whole) / float(1 << 23)
    elif width in (1, 2, 4):
        kind = {1: np.uint8, 2: np.int16, 4: np.int32}[width]
        samples = np.frombuffer(raw, kind).astype(np.float64)
        samples = (
            (samples - 128.0) / 128.0 if width == 1 else samples / 2 ** (8 * width - 1)
        )
    else:
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{where.name} has {width}-byte samples, which this does not read",
            "write it as 16-bit PCM",
        )
    return samples.reshape(-1, channels), rate


def _spectra(mono: np.ndarray) -> np.ndarray:
    window = np.hanning(_SIZE)
    starts = range(0, max(len(mono) - _SIZE, 0), _HOP)
    return np.array(
        [
            np.log1p(np.abs(np.fft.rfft(mono[i : i + _SIZE] * window)) * 20.0)
            for i in starts
        ]
    )


def _flux(mono: np.ndarray) -> np.ndarray:
    frames = _spectra(mono)
    if len(frames) < 2:
        return np.zeros(0)
    return np.maximum(np.diff(frames, axis=0), 0.0).sum(axis=1)


def _db(value: float) -> float:
    return round(20.0 * float(np.log10(max(value, 1e-12))), 3)


def measure(path: str | Path) -> dict:
    """Every sound measure of one file, by name."""
    samples, rate = read(path)
    mono = samples.mean(axis=1)
    if len(mono) < 8 * _SIZE:
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{Path(path).name} is {len(mono) / rate:.3f} s, too short for a seam",
            f"give it at least {8 * _SIZE / rate:.2f} s",
        )
    steps = np.abs(np.diff(mono))
    step = abs(mono[0] - mono[-1]) / max(float(np.percentile(steps, 99)), 1e-12)
    wrapped = np.concatenate([mono[-4 * _SIZE :], mono[: 4 * _SIZE]])
    across = _flux(wrapped)
    middle = len(across) // 2
    ordinary = max(float(np.percentile(_flux(mono), 90)), 1e-12)
    return {
        "seam_step": round(float(step), 4),
        "seam_flux": round(float(across[middle - 4 : middle + 4].max()) / ordinary, 4),
        "loudness": _db(float(np.sqrt(np.mean(mono**2)))),
        "peak": _db(float(np.abs(samples).max())),
        "duration": round(len(mono) / rate, 4),
    }


@operation("sound.measure")
def measured(
    subject: Annotated[str, Param("the sound, as a path under the project")],
    root: Annotated[str, Param("the project the path resolves against")] = ".",
) -> dict:
    """A sound's seam, loudness, peak and length: what a sound predicate bounds."""
    where = Path(subject) if Path(subject).is_absolute() else Path(root) / subject
    return {"subject": subject, **measure(where)}
