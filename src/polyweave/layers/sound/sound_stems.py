"""A recorded track split into its stems, and where each one plays (§PW558).

Spinhold's intro was bought finished, with "Viglet Games" spoken over its closing chord.
Cutting before the voice lost the ending, so the voice had to come out of the mix, and
the project did that by hand: Demucs in a scratch environment, run outside provenance,
and a transcriber to find where the voice was. This is that step, kept.

The split is Demucs' `htdemucs`, the four sources it was trained on: drums, bass, other
and vocals. `split = "vocals"` keeps the voice apart and sums the rest into
`no_vocals`, which is the instrumental a game ships; `split = "four"` writes all four.

Each stem answers where it plays, as spans of time, so "where is the voice" is read off
the answer rather than found by ear, and a stem that is silent says so: a vocals stem
with no span is a track that had no voice to take out.
"""

from __future__ import annotations

from typing import Annotated

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import sound
from polyweave.layers.sound.sound_loop import RATE, _decode, _encode

#: The separation model. htdemucs is Demucs 4's default and the one it publishes
#: numbers for; its weights are fetched once into torch's cache.
MODEL = "htdemucs"

#: Which stems each split writes, in the order the answer lists them.
SPLITS = {
    "vocals": ("vocals", "no_vocals"),
    "four": ("drums", "bass", "other", "vocals"),
}

#: A stem plays where its 100 ms level is within BELOW_MIX dB of the mix's at that
#: moment, and above the floor. Read against the mix, not against the stem's own peak:
#: on Spinhold's intro the vocals stem held a residue at -40 dBFS the whole minute,
#: under a voice at -15, and a bar below the stem's peak read the residue as singing.
#: Separation's leakage sits 25 dB and more under the mix; a part that plays does not.
WINDOW = 0.1
BELOW_MIX = 15.0
FLOOR = -50.0

#: Full scale for the int16 stems. A stem may peak over it where the mix did not (a
#: drum's transient, the voice's share of a clipped master): then every stem is
#: lowered by one gain, so the stems still add up to the mix, and the answer says so.
FULL = 32767.0

#: Spans closer than this are one span, and one shorter than the least is a click.
JOIN = 0.5
LEAST = 0.2

#: An answer lists at most this many spans a stem, and says how many it left out.
SHOWN = 12


def _separate(frames: np.ndarray) -> tuple[dict[str, np.ndarray], dict]:
    """The four sources of a stereo mix at RATE, and what separated them.

    Frames are int16-scaled, as `_decode` gives them, and so is what comes back.
    """
    try:
        import demucs
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
    except ImportError as missing:
        raise PolyweaveError(
            "sound.no-separator",
            f"splitting a track needs Demucs and torch, and {missing.name} is not "
            "installed",
            "pip install polyweave-gamekit[stems] (CPU torch is enough; a minute of "
            "music takes about a minute)",
        ) from missing
    model = get_model(MODEL)
    model.eval()
    wav = torch.tensor((frames / 32768.0).T, dtype=torch.float32)
    # Scaled to unit spread as Demucs' own driver does, but its mean is not added back
    # to every source after: on Spinhold's intro that put the mix's DC offset into each
    # stem four times over, a -41 dBFS floor under the closing silence.
    scale = wav.mean(0).std().clamp_min(1e-8)
    with torch.no_grad():
        out = apply_model(model, (wav / scale)[None], device="cpu",
                          split=True, overlap=0.25, progress=False)[0]
    out = out * scale
    sources = {name: out[i].numpy().T.astype(np.float64) * 32768.0
               for i, name in enumerate(model.sources)}
    return sources, {"name": "demucs", "version": demucs.__version__, "model": MODEL}


def _levels(frames: np.ndarray) -> np.ndarray:
    """The 100 ms RMS levels of a stereo signal, in dBFS."""
    mono = frames.mean(axis=1) / 32768.0
    hop = int(WINDOW * RATE)
    count = len(mono) // hop
    return 10 * np.log10(
        (mono[: count * hop].reshape(count, hop) ** 2).mean(axis=1) + 1e-12)


def _spans(frames: np.ndarray, mix: np.ndarray) -> list[list[float]]:
    """Where a stem plays in its mix, as [start, end] seconds."""
    level, whole = _levels(frames), _levels(mix)
    loud = (level >= FLOOR) & (level >= whole - BELOW_MIX)
    found: list[list[float]] = []
    for i in np.flatnonzero(loud):
        start, end = i * WINDOW, (i + 1) * WINDOW
        if found and start - found[-1][1] < JOIN:
            found[-1][1] = end
        else:
            found.append([start, end])
    return [[round(a, 1), round(b, 1)] for a, b in found if b - a >= LEAST]


@operation("sound.stems")
def stems(
    track: Annotated[str, Param("the recorded track, in the project")],
    out: Annotated[str, Param("the stems' folder; <track>.stems if unset")] = None,
    split: Annotated[
        str, Param("vocals: vocals, no_vocals; four: drums, bass, other, vocals",
                   choices=tuple(SPLITS))
    ] = "vocals",
    format: Annotated[str, Param("the stems' format", choices=("wav", "ogg"))] = "wav",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Split a recorded track into stems, each saying where it plays."""
    here = load(root).root
    source = here / track
    if not source.is_file():
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"there is no track at {track}",
            "name the recorded track as a path under the project",
        )
    folder = (here / out) if out else source.with_name(f"{source.stem}.stems")
    frames = _decode(source)
    sources, engine = _separate(frames)
    if split == "vocals":
        sources = {"vocals": sources["vocals"],
                   "no_vocals": sum(v for k, v in sources.items() if k != "vocals")}
    loudest = max(float(np.abs(sources[name]).max()) for name in SPLITS[split])
    gain = min(1.0, FULL / max(loudest, 1e-9))
    folder.mkdir(parents=True, exist_ok=True)
    inputs = [provenance.source("track", source, here)]
    made = {}
    for name in SPLITS[split]:
        target = folder / f"{name}.{format}"
        _encode(sources[name] * gain, target, quality=6)
        measured = sound.measure(target)
        provenance.write(provenance.build(
            "sound", target, inputs=inputs,
            engine={"name": "sound.stems", "model": engine["model"],
                    "separator": f"{engine['name']} {engine['version']}"},
            params={"split": split, "stem": name, "gain": round(gain, 4)},
            measurements=measured, root=here,
        ), here)
        played = _spans(sources[name], frames)
        made[name] = {
            "path": target.relative_to(here).as_posix(),
            "loudness": measured.get("loudness"),
            "peak": measured.get("peak"),
            "plays": played[:SHOWN],
            **({"more": len(played) - SHOWN} if len(played) > SHOWN else {}),
        }
    silent = [name for name, stem in made.items() if not stem["plays"]]
    return {
        "track": track,
        "seconds": round(len(frames) / RATE, 3),
        "split": split,
        "stems": made,
        "gain_db": round(20 * float(np.log10(gain)), 2),
        "separator": engine,
        "says": (f"{', '.join(silent)} silent: nothing of that kind was in the track"
                 if silent else
                 f"{len(made)} stems in {folder.relative_to(here).as_posix()}"),
    }
