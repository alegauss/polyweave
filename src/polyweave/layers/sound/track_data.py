"""A track's waveform peaks and beat grid, as a file a game's own tools read (§PW611).

Spinhold's stage editor draws the world's music under its timeline and snaps an entry to
a beat. Godot plays an Ogg stream and gives a running game none of its samples, so the
waveform cannot be drawn there, and the tempo it snapped to was copied from the score
by hand. So beside each track it plays, a game finds `<track>.track.json`:

    {"format": 1, "audio": "music/theme.ogg", "seconds": 32.0, "rate": 44100,
     "channels": 2,
     "grid": {"estimated": false, "tempo": [{"at": 0.0, "bpm": 120.0}],
              "meter": [4, 4], "beats": [0.0, 0.5, ...], "bars": [0.0, 2.0, ...],
              "sections": [{"id": "a-1", "name": "a", "start": 0.0, "end": 16.0}],
              "loop": {"start": 0.0, "end": 32.0}},
     "peaks": [{"per_second": 10, "min": [[...], [...]], "max": [[...], [...]],
                "loudness": [...]}, ...]}

The peaks are each channel's lowest and highest sample per bucket, at each of a few
resolutions, so a tool zooms without decoding audio; `loudness` is the bucket's RMS in
dBFS, both channels together, for a tool that marks the drops. `music.render` writes
the file from the score it rendered, so its grid is declared; `music.track` writes it
for any other track from the sound alone, where the tempo and the first beat are
estimated, the meter is taken as 4/4, there are no sections, and `estimated` says so.
The record names the audio and its hash, so a track rendered again reads outdated
until its file is written again.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: The file's own format, raised when a key changes meaning.
FORMAT = 1
#: The buckets a second of audio is cut into, coarse to fine.
RESOLUTIONS = (10, 50, 200)
#: The quietest a bucket is said to be, in dBFS: digital silence has no logarithm.
FLOOR = -90.0
#: Samples the heard beat runs ahead of the hit: sound_loop's spectral window.
LEAD = 2048


def peaks(audio: np.ndarray, rate: int) -> list[dict]:
    """Each resolution's per-channel minimum and maximum and its loudness per bucket.

    `audio` is samples by channels, at full scale 1.0.
    """
    frames = audio if audio.ndim == 2 else audio[:, None]
    out = []
    for per_second in RESOLUTIONS:
        # Bucket i starts at i / per_second exactly: a width rounded to whole samples
        # (220 for 220.5 at 200 a second) drifted 0.4 s over three minutes.
        count = int(np.ceil(len(frames) * per_second / rate))
        starts = np.round(np.arange(count) * rate / per_second).astype(int)
        widths = np.diff(np.append(starts, len(frames)))
        if not count:
            low = high = np.zeros((0, frames.shape[1]))
            rms = np.zeros(0)
        else:
            low = np.minimum.reduceat(frames, starts, axis=0)
            high = np.maximum.reduceat(frames, starts, axis=0)
            power = np.add.reduceat((frames**2).sum(axis=1), starts)
            rms = np.sqrt(power / (widths * frames.shape[1]))
        loud = 20.0 * np.log10(np.maximum(rms, 10 ** (FLOOR / 20.0)))
        out.append({
            "per_second": per_second,
            "min": np.round(low.T, 4).tolist(),
            "max": np.round(high.T, 4).tolist(),
            "loudness": np.round(loud, 1).tolist(),
        })
    return out


def declared_grid(model: dict) -> dict:
    """The beats, bars, tempo, sections and loop a score declares, in seconds."""
    timing = model["timing"]
    per_quarter = timing["ticksPerQuarter"]
    tempos = sorted(timing["tempo"], key=lambda t: t["tick"])
    signature = timing["timeSignatures"][0]

    def seconds(tick: float) -> float:
        # Through the tempo map: each change holds from its tick to the next one's.
        passed = 0.0
        for index, change in enumerate(tempos):
            per_tick = change["microsecondsPerQuarter"] / 1_000_000 / per_quarter
            upto = tempos[index + 1]["tick"] if index + 1 < len(tempos) else tick
            if tick <= upto:
                return round(passed + (tick - change["tick"]) * per_tick, 6)
            passed += (upto - change["tick"]) * per_tick
        return round(passed, 6)

    beat = per_quarter * 4 / signature["denominator"]
    bar = beat * signature["numerator"]
    end = max((s["endTick"] for s in model["sections"]), default=0)
    ext = next(iter(model.get("extensions", {}).values()), {})
    loop = ext.get("loop")
    return {
        "estimated": False,
        "tempo": [{"at": seconds(t["tick"]),
                   "bpm": round(60_000_000 / t["microsecondsPerQuarter"], 3)}
                  for t in tempos],
        "meter": [signature["numerator"], signature["denominator"]],
        "beats": [seconds(t) for t in np.arange(0, end, beat)],
        "bars": [seconds(t) for t in np.arange(0, end, bar)],
        "sections": [{"id": s["id"], "name": s.get("label", s["id"]),
                      "start": seconds(s["startTick"]), "end": seconds(s["endTick"])}
                     for s in model["sections"]],
        "loop": ({"start": seconds(loop["startTick"]), "end": seconds(loop["endTick"])}
                 if loop else None),
    }


def estimated_grid(audio: np.ndarray) -> dict:
    """A grid heard from the sound, decoded at sound_loop's rate: its tempo and first
    beat estimated, bars of four."""
    from . import sound_loop

    rate = sound_loop.RATE
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    beat, first = sound_loop._beat_grid(mono * 32768.0)
    # The flux sees a hit as it enters the analysis window, one window before it lands:
    # measured 45 to 53 ms early on click tracks at 95 to 150 BPM, so the beat a tool
    # snaps to is moved on by the window (§PW611).
    first = (first + LEAD / rate) % beat
    length = len(mono) / rate
    beats = [round(float(t), 6) for t in np.arange(first, length, beat)]
    return {
        "estimated": True,
        "tempo": [{"at": 0.0, "bpm": round(60.0 / beat, 3)}],
        "meter": [4, 4],
        "beats": beats,
        "bars": beats[::4],
        "sections": [],
        "loop": None,
    }


def written(audio_file: Path, audio: np.ndarray, rate: int, grid: dict, here: Path,
            inputs: list[dict] = (), out: Path | None = None) -> str:
    """The track's file written beside it and recorded; its path under the project."""
    stem = audio_file.name.removesuffix(audio_file.suffix)
    target = out or audio_file.with_name(f"{stem}.track.json")
    held = audio if audio.ndim == 2 else audio[:, None]
    body = {
        "format": FORMAT,
        "audio": provenance.relative(audio_file, here),
        "seconds": round(len(held) / rate, 6),
        "rate": rate,
        "channels": int(held.shape[1]),
        "grid": grid,
        "peaks": peaks(held, rate),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, separators=(",", ":")) + "\n", encoding="utf-8",
                      newline="\n")
    provenance.write(provenance.build(
        "sound", target, engine={"name": "track_data"},
        inputs=[provenance.source("audio", audio_file, here), *inputs],
        params={"resolutions": list(RESOLUTIONS), "estimated": grid["estimated"]},
        root=here,
    ), here)
    return provenance.relative(target, here)


@operation("music.track")
def track(
    audio: Annotated[str, Param("the track a game plays, .ogg or .wav")],
    *,
    out: Annotated[
        str, Param("the file to write; <track>.track.json beside it if unset")
    ] = "",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Waveform peaks and an estimated beat grid beside a track polyweave did not
    render, for a game's own tools to draw and snap to (§PW611).

    music.render writes the same file for its own tracks, with the grid the score
    declares; here the tempo and first beat are heard and the grid says `estimated`.
    """
    from . import sound_loop

    here = load(root).root
    source = here / audio
    if not source.is_file():
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"there is no track at {audio}",
            "name the track as a path under the project",
            given=audio,
        )
    frames = sound_loop._decode(source) / 32768.0
    grid = estimated_grid(frames)
    made = written(source, frames, sound_loop.RATE, grid, here,
                   out=(here / out) if out else None)
    return {
        "track": made,
        "seconds": round(len(frames) / sound_loop.RATE, 3),
        "bpm": grid["tempo"][0]["bpm"],
        "beats": len(grid["beats"]),
        "estimated": True,
    }
