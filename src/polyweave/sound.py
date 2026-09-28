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
    "and spec, its *.accept.toml"
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
        # Held to its spec where it has one; otherwise nothing but the ear judges it.
        spec = verdict._checked(heard, here)[2] if heard.get("spec") else None
        passed = bool(spec["passed"]) if spec else True
        heard["passed"] = passed
        drawn = folder / f"{heard['name']}.png"
        _drawn(drawn, heard, here)
        families[heard["name"]] = [heard]
        sheets[heard["name"]] = {
            "sheet": str(drawn),
            "members": [{"name": heard["name"], "passed": passed,
                         "failed": [verdict._said(r) for r in spec["predicates"]
                                    if not r["passed"]] if spec else []}],
        }
    if families:
        verdict._manifest(folder, families, sheets, here, choices=SOUND_CHOICES)
    return {
        "sitting": relative(folder / verdict.MANIFEST, here) if families else None,
        "sounds": list(families),
        "measured": {name: m[0]["measured"] for name, m in families.items()},
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
        y += 3 * line + gap
    looped = "played looped, so its seam is heard" if member["loop"] else "played once"
    draw.text((gap, y), f"{member['name']}: {looped}", fill=(255, 210, 90, 255))
    where.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(where)


@operation("sound.measure")
def measured(
    subject: Annotated[str, Param("the sound, as a path under the project")],
    root: Annotated[str, Param("the project the path resolves against")] = ".",
) -> dict:
    """A sound's seam, loudness, peak and length: what a sound predicate bounds."""
    where = Path(subject) if Path(subject).is_absolute() else Path(root) / subject
    return {"subject": subject, **measure(where)}
