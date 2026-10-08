"""A sound held to a spec, as a picture is (§PW113).

Nothing in the acceptance spec is 3D, and the owner decided sound belongs in it. Cottony
already wrote the bar outside this plugin: `tools/audio/loop_music.py` cuts a generated
track into the loop the game plays and fails the loop when its seam stands out. That
measure is here, as two numbers a predicate bounds, with three plainer ones beside them:

- `seam_step`: the jump from the last sample to the first, over the track's own
  99th-percentile step between samples. Above one, the wrap clicks louder than any
  ordinary moment of the music.
- `seam_flux`: the largest spectral change across the wrap, over the 98th percentile of
  the track's own onsets (the peaks of its spectral change). Above one, the seam
  changes more than the track's strong downbeats do, and sounds like a cut (§PW222).
- `seam_grid`: how far the loop's length is from a whole number of bars (from a
  polyweave render's record) or beats (estimated from the track's own onsets), 0 to
  0.5. Above a few hundredths, the loop was cut off its grid, which is the cut in a
  dense mix the other two cannot hear (§PW225). `grid` says where the grid came from.
- `loudness`: RMS level in dBFS; `peak`: the largest sample in dBFS; `duration`:
  seconds.

Each ratio is against the track itself, which is why the bar is one number for every
track: a seam may look like any ordinary moment of that music, and nothing more. A WAV
is read with the standard library; anything else is decoded by ffmpeg where it is on
PATH, and refused where it is not.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Annotated

import numpy as np

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: Every sound measure a predicate may bound, and what it says.
SOUNDS: dict[str, str] = {
    "seam_step": "the loop's wrap step over the track's 99th-percentile sample step",
    "seam_flux": "the spectral change across the wrap over the track's strong onsets",
    "seam_grid": "the loop's length off a whole number of bars or beats, 0 to 0.5",
    "loudness": "RMS level, in dBFS",
    "peak": "the largest sample, in dBFS",
    "duration": "length, in seconds",
    "fundamental": "the pitch of the loudest moment, in Hz, where it has one",
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
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(where), "-f", "s16le", "-ac", "2"]
        + ["-ar", str(RATE), "-"],
        check=False,
        capture_output=True,
    )
    if decoded.returncode or not decoded.stdout:
        # A file ffmpeg cannot decode is refused with a code, never let out as the
        # process's own error: an agent branches on the code (§PW224).
        said = decoded.stderr.decode("utf-8", "replace").strip().splitlines()
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"ffmpeg could not decode {where.name} as sound",
            "check the file is the audio it is named as; a truncated download or a "
            "service's error page saved with an audio suffix reads like this",
            detail=said[0] if said else f"ffmpeg exited {decoded.returncode}",
        )
    raw = decoded.stdout
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


#: Which of a track's onsets its seam is compared with: the 98th percentile of the
#: peaks of its spectral change, so a seam as strong as the track's own downbeats reads
#: below one (§PW222). Measured on the PW184 loops a person heard as seamless, against a
#: cut copy of each: the synthwave's seam restarts on a crash and read 3.07 against the
#: 90th percentile of all frames, and 0.91 here. Every loop read below one and the
#: suite's cut and faded fixtures still read 4.4 and 8.3.
ONSET_PERCENTILE = 98


def _onset_level(flux: np.ndarray) -> float:
    """How strong the track's own strong onsets are: a high percentile of flux peaks."""
    inner = flux[1:-1]
    peaks = inner[(inner >= flux[:-2]) & (inner >= flux[2:])]
    if not len(peaks):
        return float(np.percentile(flux, 90)) if len(flux) else 0.0
    return float(np.percentile(peaks, ONSET_PERCENTILE))


def _fundamental(mono: np.ndarray, rate: int) -> float | None:
    """The pitch of the loudest moment, by autocorrelation; None where there is none.

    A sound bounded to a key's notes is held to this (§PW333). Noise, such as an
    explosion, has no lag its waveform repeats at, and answers no pitch rather than a
    made-up one.
    """
    size = min(len(mono), 4096)
    if size < 256:
        return None
    frames = max(1, len(mono) // size)
    energy = [
        float(np.sum(mono[i * size : (i + 1) * size] ** 2)) for i in range(frames)
    ]
    loud = int(np.argmax(energy))
    window = mono[loud * size:(loud + 1) * size]
    window = window - window.mean()
    if not np.any(window):
        return None
    full = np.correlate(window, window, mode="full")[len(window) - 1:]
    low, high = int(rate / 4000), min(int(rate / 30), len(full) - 1)
    if high <= low:
        return None
    span = full[low:high]
    best = float(span.max())
    if best < 0.5 * full[0]:
        return None
    # The first peak nearly as strong as the best, not the best: a cycle that is not
    # a whole number of samples correlates better over two, an octave low.
    peaks = [
        i for i in range(1, len(span) - 1)
        if span[i] >= span[i - 1] and span[i] >= span[i + 1] and span[i] >= 0.85 * best
    ]
    lag = low + (peaks[0] if peaks else int(np.argmax(span)))
    # A peak between two samples, placed by the parabola through it and its neighbours.
    if 0 < lag < len(full) - 1:
        a, b, c = full[lag - 1], full[lag], full[lag + 1]
        shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else 0.0
        lag = lag + max(-0.5, min(0.5, shift))
    return rate / lag if lag > 0 else None


_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_of(pitch: float) -> str:
    """The nearest note to a pitch and how far off it is, such as A5 +3c."""
    steps = 12 * math.log2(pitch / 440.0) + 57
    nearest = round(steps)
    cents = round((steps - nearest) * 100)
    return f"{_NAMES[nearest % 12]}{nearest // 12}{cents:+d}c"


def _db(value: float) -> float:
    return round(20.0 * float(np.log10(max(value, 1e-12))), 3)


#: The shortest sound a seam can be read on: four analysis windows either side of the
#: wrap. Anything shorter is a one-shot, measured without one (§PW221).
SEAM_WINDOWS = 8


def shortest_seam(rate: int = RATE) -> float:
    """The length, in seconds, below which a sound has no seam to measure."""
    return SEAM_WINDOWS * _SIZE / rate


def measure(path: str | Path) -> dict:
    """Every sound measure of one file, by name.

    A file too short to hear a seam in (a one-shot effect, typically) has its level,
    peak and length and no seam measures at all: a seam only means something for a
    loop, and refusing the whole file would leave an effect with nothing to bound.
    """
    samples, rate = read(path)
    mono = samples.mean(axis=1)
    if not len(mono):
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{Path(path).name} holds no samples",
            "check the file the game plays; it is empty",
        )
    found = {
        "loudness": _db(float(np.sqrt(np.mean(mono**2)))),
        "peak": _db(float(np.abs(samples).max())),
        "duration": round(len(mono) / rate, 4),
    }
    pitch = _fundamental(mono, rate)
    if pitch is not None:
        found["fundamental"] = round(pitch, 2)
        found["note"] = note_of(pitch)
    if len(mono) < SEAM_WINDOWS * _SIZE:
        return found
    steps = np.abs(np.diff(mono))
    step = abs(mono[0] - mono[-1]) / max(float(np.percentile(steps, 99)), 1e-12)
    wrapped = np.concatenate([mono[-4 * _SIZE :], mono[: 4 * _SIZE]])
    flux = _flux(mono)
    across = _flux(wrapped)
    middle = len(across) // 2
    ordinary = max(_onset_level(flux), 1e-12)
    seams = {
        "seam_step": round(float(step), 4),
        "seam_flux": round(float(across[middle - 4 : middle + 4].max()) / ordinary, 4),
    }
    off, grid = _off_grid(len(mono) / rate, flux, rate, Path(path))
    if off is not None:
        seams["seam_grid"] = round(off, 4)
    return {**seams, **found, "grid": grid}


#: The measures that mean something only for a sound that plays again from its start.
SEAM = ("seam_step", "seam_flux", "seam_grid")

#: How clearly a track must keep a pulse before its beat is estimated from it: the
#: autocorrelation's peak over its median. The PW184 chiptune and synthwave loops kept
#: theirs at 199 and 104, and the waltz's soft pizzicato at 1, which is no pulse at all.
CLEAR_PULSE = 10.0


def _off_grid(seconds: float, flux: np.ndarray, rate: int,
              where: Path) -> tuple[float | None, str]:
    """How far a loop's length is from a whole number of bars or beats (§PW225).

    What a cut in a dense mix breaks is the grid: a loop is a whole number of bars and
    a cut one is not. A loop polyweave rendered says its bar in its record; any other
    has its beat estimated from its own onsets, and one without a clear pulse has no
    grid to be held to, which the answer says rather than guessing.
    """
    bar = _recorded_bar(where)
    if bar:
        unit, grid = bar, "record"
    else:
        unit = _beat(flux, rate)
        grid = "estimated" if unit else "none"
    if not unit:
        return None, grid
    count = seconds / unit
    return abs(count - round(count)), grid


def _recorded_bar(where: Path) -> float | None:
    """The bar a polyweave render recorded beside the file, in seconds."""
    import json

    sidecar = where.with_name(where.name + ".prov.json")
    try:
        record = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    bar = (record.get("params") or {}).get("bar_seconds")
    return float(bar) if isinstance(bar, int | float) and bar > 0 else None


def _beat(flux: np.ndarray, rate: int) -> float | None:
    """The track's beat in seconds, from its onsets, or None where it keeps no pulse.

    The autocorrelation of the onset envelope has no phase, so a flux peak that sits a
    fixed fraction of a frame late biases nothing, and its peaks at every multiple of
    the beat pin the period across the whole track: a comb locked to the track's start
    read the spike loops' clean lengths 0.08 beats off, this one 0.001.
    """
    fps = rate / _HOP
    envelope = np.concatenate([[0.0], flux]) - flux.mean()
    n = len(envelope)
    lags = np.arange(int(fps * 60 / 180), int(fps * 60 / 70) + 1)
    if n <= lags[-1] * 4:
        return None
    spectrum = np.fft.rfft(envelope, 2 * n)
    auto = np.fft.irfft(spectrum * np.conj(spectrum))[:n] / np.arange(n, 0, -1)
    rough = lags[int(np.argmax(auto[lags]))] / fps
    periods = np.linspace(rough * 0.97, rough * 1.03, 6001)
    count = int(0.75 * n / (periods.max() * fps))
    multiples = np.arange(1, count + 1)[None, :] * periods[:, None] * fps
    scores = np.interp(multiples, np.arange(n), auto).mean(axis=1)
    best = int(np.argmax(scores))
    spread = float(np.median(scores))
    clarity = (scores[best] - spread) / (abs(spread) + 1e-12)
    return float(periods[best]) if clarity >= CLEAR_PULSE else None


@operation("sound.declared")
def declared(
    family: Annotated[str, Param("one sound family; left out, every one")] = None,
    root: Annotated[str, Param("the project whose [sound] is read")] = ".",
) -> dict:
    """The audio a game declares: each cue's file, measured, and what is missing.

    A present file is measured as `sound.measure` would, without its seam unless the
    family's kind is `loop`; one that cannot be measured says why instead. Whether a
    measure is in bounds stays with the file's *.accept.toml.
    """
    config = load(root)
    if family:
        name, one = config.sound(family)
        families = {name: one}
    else:
        families = config.sounds()
    answer, missing = {}, []
    for name, sound in families.items():
        folder = Path(sound["folder"])
        cues = [
            _cue(cue, folder / f"{cue}.{sound['format']}", sound["kind"], config.root)
            for cue in sound["cues"]
        ]
        missing += [c["file"] for c in cues if not c["exists"]]
        answer[name] = {
            **{k: sound[k] for k in ("kind", "format", "duration", "loudness")},
            "folder": folder.relative_to(config.root).as_posix(),
            "cues": cues,
        }
    return {"families": answer, "missing": missing}


def _cue(cue: str, file: Path, kind: str, root: Path) -> dict:
    """One declared cue: where it lands, whether it is there, and what it measures."""
    entry: dict = {"cue": cue, "file": file.relative_to(root).as_posix()}
    entry["exists"] = file.is_file()
    if not entry["exists"]:
        return entry
    try:
        found = measure(file)
    except PolyweaveError as refused:
        entry["unmeasured"] = {"code": refused.code, "why": refused.message}
        return entry
    if kind != "loop":
        found = {k: v for k, v in found.items() if k not in SEAM}
    entry["measured"] = found
    return entry


#: What a person can say of a sound heard beside the one it replaces (§PW256).
SOUND_CHOICES = {
    "accept": "it sounds right: the new one replaces the old",
    "look": "it does not: say why, and it goes back to be made again",
}

LISTENED = (
    "each member: name and new, and optionally old (the sound it replaces), loop, "
    "spec, its *.accept.toml, and line, the words a spoken take should say"
)


@operation("sound.sitting")
def sitting(
    members: Annotated[list, Param(LISTENED)],
    *,
    out: Annotated[str, Param("the folder the sitting is laid out in")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Put sounds on the review page, each new one beside the one it replaces.

    Each sound is its own family, so a person gives a verdict per sound: the page plays
    the old and the new side by side, a loop looped so its seam is heard, with what
    sound.measure says of both drawn on its sheet. The answer lands through
    verdict.judge, which keeps it in the new sound's record; verdict.answers resumes
    from it. A loop is a member whose cue a `[sound]` family of kind loop declares, or
    one that says `loop`.
    """
    from . import verdict
    from .provenance import relative

    config = load(root)
    here = config.root
    looped = {
        (Path(sound["folder"]) / f"{cue}.{sound['format']}").resolve()
        for sound in config.sounds().values()
        if sound["kind"] == "loop"
        for cue in sound["cues"]
    }
    folder = config.path("paths.work", out)
    families, sheets = {}, {}
    for member in members:
        heard = {"name": str(member["name"]), "sound": True}
        for key in ("new", "old", "spec"):
            if member.get(key):
                heard[key] = relative(config.path("paths.work", member[key]), here)
        if "new" not in heard:
            raise PolyweaveError(
                "sound.no-source",
                f"{heard['name']} names no new sound to hear",
                "give each member new, the file the game will play",
            )
        loop = bool(member.get("loop")) or (here / heard["new"]).resolve() in looped
        heard["loop"] = loop
        heard["measured"] = {
            key: _heard(here / heard[key], loop)
            for key in ("old", "new")
            if key in heard
        }
        # A spoken take is held to its line as well, and shows what it measures beside
        # it, so a person's ear goes to the takes worth it (§PW323).
        spoken_fails = []
        if member.get("line"):
            heard["line"] = str(member["line"])
            found = speech(here / heard["new"], heard["line"], _names(here))
            spoken_fails = held(found, config.table("voice"))
            heard["speech"] = {**found, "failed": spoken_fails}
        # Held to its spec where it has one; otherwise nothing but the ear judges it.
        spec = verdict._checked(heard, here)[2] if heard.get("spec") else None
        passed = (bool(spec["passed"]) if spec else True) and not spoken_fails
        heard["passed"] = passed
        drawn = folder / f"{heard['name']}.png"
        _drawn(drawn, heard, here)
        families[heard["name"]] = [heard]
        sheets[heard["name"]] = {
            "sheet": str(drawn),
            "members": [{"name": heard["name"], "passed": passed,
                         "failed": ([verdict._said(r) for r in spec["predicates"]
                                     if not r["passed"]] if spec else [])
                         + [_spoke(one) for one in spoken_fails]}],
        }
    if families:
        verdict._manifest(folder, families, sheets, here, kind="sound")
    return {
        "sitting": relative(folder / verdict.MANIFEST, here) if families else None,
        "sounds": list(families),
        "measured": {name: m[0]["measured"] for name, m in families.items()},
        **({"speech": {name: m[0]["speech"] for name, m in families.items()
                       if "speech" in m[0]}}
           if any("speech" in m[0] for m in families.values()) else {}),
        "choices": dict(SOUND_CHOICES),
        "says": f"{len(families)} sound{'' if len(families) == 1 else 's'} for a "
        "person to hear on the review page; verdict.answers resumes from what they "
        "said",
    }


def _heard(path: Path, loop: bool) -> dict:
    """What a sound measures, its seam only where it loops."""
    if not path.is_file():
        raise PolyweaveError(
            "sound.no-source",
            f"there is no sound at {path.name} to hear",
            "name files under the project, as the game loads them",
        )
    found = measure(path)
    return found if loop else {k: v for k, v in found.items() if k not in SEAM}


def _drawn(where: Path, member: dict, here: Path) -> None:
    """One sound's sheet: each version's waveform, with what it measures under it."""
    from PIL import Image, ImageDraw

    width, tall, gap, line = 640, 80, 8, 16
    rows = [key for key in ("old", "new") if key in member]
    height = gap + len(rows) * (tall + 3 * line + gap) + 2 * line + gap
    canvas = Image.new("RGBA", (width + 2 * gap, height), (40, 40, 40, 255))
    draw = ImageDraw.Draw(canvas)
    y = gap
    for key in rows:
        samples, _ = read(here / member[key])
        mono = samples.mean(axis=1)
        columns = np.array_split(np.abs(mono), width) if len(mono) >= width else [mono]
        middle = y + tall // 2
        for x, column in enumerate(columns):
            reach = float(np.max(np.abs(column))) if len(column) else 0.0
            draw.line([(gap + x, middle - reach * tall / 2),
                       (gap + x, middle + reach * tall / 2)], fill=(120, 190, 255, 255))
        y += tall
        said = ", ".join(f"{k} {v:g}" for k, v in member["measured"][key].items()
                         if isinstance(v, int | float))
        draw.text((gap, y), f"{key}: {member[key]}", fill=(235, 235, 235, 255))
        draw.text((gap, y + line), said, fill=(235, 235, 235, 255))
        if key == "new" and member.get("speech"):
            draw.text((gap, y + 2 * line), _speech_said(member["speech"]),
                      fill=(255, 150, 150, 255) if member["speech"]["failed"]
                      else (235, 235, 235, 255))
        y += 3 * line + gap
    looped = "played looped, so its seam is heard" if member["loop"] else "played once"
    draw.text((gap, y), f"{member['name']}: {looped}", fill=(255, 210, 90, 255))
    where.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(where)


def _spoke(failed: dict) -> str:
    """A failed speech measure as a sitting says it."""
    if failed["measure"] == "said":
        return (f"said: missing {', '.join(failed['missing']) or 'nothing'}, heard "
                f"{', '.join(failed['extra']) or 'nothing else'}")
    bound = failed.get("max", failed.get("band"))
    return f"{failed['measure']} {failed['value']:g} outside {bound}"


def _speech_said(found: dict) -> str:
    """One line of what a spoken take measures, for its sheet."""
    said = (f"lead {found['lead_silence']:g}s, tail {found['tail_silence']:g}s, "
            f"{found['rate']:g} chars/s")
    if found.get("said"):
        said += "; said as written" if found["said"]["matches"] else (
            "; heard: " + found["said"]["heard"][:60])
    return said


#: How far under a take's loudest frame a frame still counts as speech, in dB, and the
#: frame it is judged over in seconds: a breath or room tone sits well under a word.
SPEECH_FLOOR, SPEECH_FRAME = 40.0, 0.02


def _span(path: str | Path) -> tuple[float, float, float]:
    """Where a take's speech starts and ends, and how long the take is, in seconds."""
    samples, rate = read(path)
    mono = samples.mean(axis=1)
    size = max(1, int(rate * SPEECH_FRAME))
    frames = len(mono) // size
    if not frames:
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{Path(path).name} is too short to hold a word",
            "check the take; it is empty or a click",
        )
    levels = np.array([
        _db(float(np.sqrt(np.mean(mono[i * size : (i + 1) * size] ** 2))))
        for i in range(frames)
    ])
    spoken = np.flatnonzero(levels >= max(levels.max() - SPEECH_FLOOR, -60.0))
    first, last = spoken[0] * size / rate, (spoken[-1] + 1) * size / rate
    return first, last, len(mono) / rate


def speech(path: str | Path, text: str, vocabulary=()) -> dict:
    """What a spoken take measures against its line (§PW323).

    The silence before the first word and after the last, the line's characters per
    second spoken, its loudness, and `said`: the words a local transcription heard that
    the line does not have, or misses, where faster-whisper is installed.
    """
    first, last, duration = _span(path)
    letters = len(re.sub(r"\s+", "", text))
    found = {
        "lead_silence": round(first, 3),
        "tail_silence": round(max(duration - last, 0.0), 3),
        "rate": round(letters / max(last - first, 1e-6), 2),
        "loudness": measure(path)["loudness"],
        "duration": round(duration, 3),
    }
    heard = _transcribed(Path(path), vocabulary)
    if heard is None:
        found["said"] = None
        found["unheard"] = "faster-whisper is not installed; the words go unchecked"
    else:
        found["said"] = _differs(text, heard)
    return found


def _transcribed(path: Path, vocabulary=()) -> str | None:
    """What a local speech-to-text model hears, or None where there is none.

    Local on purpose: paying a service to check a take would be spending on the
    agent's own judgement. The world's names are passed as the words to expect.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    model = WhisperModel("base", device="cpu", compute_type="int8")
    parts, _ = model.transcribe(
        str(path), initial_prompt=", ".join(vocabulary) or None
    )
    return " ".join(part.text for part in parts).strip()


def _differs(line: str, heard: str) -> dict:
    """The words of the line a transcription missed, and those it heard instead."""
    import difflib

    def words(text: str) -> list[str]:
        return re.findall(r"[\w']+", text.lower())

    wanted, got = words(line), words(heard)
    missing, extra = [], []
    for op, a, b, c, d in difflib.SequenceMatcher(a=wanted, b=got).get_opcodes():
        if op in ("delete", "replace"):
            missing += wanted[a:b]
        if op in ("insert", "replace"):
            extra += got[c:d]
    return {"heard": heard, "missing": missing, "extra": extra,
            "matches": not missing and not extra}


def held(found: dict, bounds: dict) -> list[dict]:
    """Each speech measure outside the project's `[voice]` bound, as a finding."""
    failed = []
    for key in ("lead_silence", "tail_silence"):
        if bounds.get(key) and found[key] > float(bounds[key]):
            failed.append({"measure": key, "value": found[key], "max": bounds[key]})
    for key in ("rate", "loudness"):
        band = bounds.get(key) or []
        if len(band) == 2 and not float(band[0]) <= found[key] <= float(band[1]):
            failed.append({"measure": key, "value": found[key], "band": list(band)})
    if found.get("said") and not found["said"]["matches"]:
        failed.append({"measure": "said", "missing": found["said"]["missing"],
                       "extra": found["said"]["extra"]})
    return failed


@operation("sound.speech")
def spoken(
    take: Annotated[str, Param("the spoken take, as a path under the project")],
    text: Annotated[str, Param("the line it should say; its record's where unset")] = (
        None
    ),
    root: Annotated[str, Param("the project the path resolves against")] = ".",
) -> dict:
    """A spoken take held to its line and the project's `[voice]` bounds (§PW323).

    `failed` names each measure outside its bound. A take that fails is reported, never
    bought again: whether to spend on another is the person's ceiling.
    """
    from . import provenance

    config = load(root)
    here = config.root
    where = config.path("paths.work", take)
    if text is None:
        try:
            text = provenance.read(str(where), root=here).get("prompt")
        except PolyweaveError:
            text = None
    if not text:
        raise PolyweaveError(
            "spec.unreadable-sound",
            f"{take} names no line to hold it to",
            "pass text, the words the take should say",
        )
    found = speech(where, text, _names(here))
    return {"take": take, "text": text, **found,
            "failed": held(found, config.table("voice"))}


def _names(here: Path) -> list[str]:
    """The world's names, for a transcription to expect; none without a world."""
    from .world import declared

    try:
        _, entities, _ = declared(None, here)
    except PolyweaveError:
        return []
    return sorted({one["name"] for one in entities.values()})


@operation("sound.measure")
def measured(
    subject: Annotated[str, Param("the sound, as a path under the project")],
    root: Annotated[str, Param("the project the path resolves against")] = ".",
) -> dict:
    """A sound's seam, loudness, peak and length: what a sound predicate bounds."""
    where = Path(subject) if Path(subject).is_absolute() else Path(root) / subject
    return {"subject": subject, **measure(where)}
