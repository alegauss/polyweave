"""A score rendered to WAV and OGG without a DAW open (§PW187).

The render orchestrates engines that already exist rather than being a synthesiser, as
the non-goal on replacing tools requires. The PW184 spike settled which: Surge XT, a
VST3 driven through Pedalboard, plays the synthesised parts, and FluidSynth's command
line plays the sampled ones from a General MIDI SoundFont. A person heard three loops
made this way and judged them good enough to ship.

What decides how professional the result sounds is the instruments and the mix more than
the notes, so one fixed chain is applied to every score, the one that person passed:

- every stem is levelled to one RMS before the track's own gain and pan apply;
- reverb and dotted-eighth delay are sends, set per track in decibels;
- the master compresses at 2.5:1 and limits to -18 dBFS RMS under a -1 dBFS peak. It
  runs over a loop as a loop, so the seam sees its own tail, and the render's tail is
  folded back onto the loop's start.

Three facts about Surge shape the code. A load takes 25 to 77 seconds, so one instance
serves a render. It is reset by restoring every parameter's raw value, because restoring
its saved state silences it. Its parameter names change with the oscillator type and its
times are discrete labels, so a patch is a table of names matched to the nearest label.
And JUCE's limiter lifts its threshold to 0 dBFS, so the ceiling is a gain after it.
"""

from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from . import music, sound
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The rate every stem and the master run at.
RATE = 44100
#: Seconds rendered past the end, so a release and a reverb have somewhere to ring.
TAIL = 4.0
#: Where every stem sits before its track's gain: the mix gains then mean what they say.
STEM_LEVEL = -20.0
#: The master's level and its ceiling, in dBFS.
LOUDNESS = -18.0
CEILING = -1.0

#: Where Surge XT installs itself, by platform, when `[paths] surge` names nothing.
_COMMON = os.environ.get("COMMONPROGRAMFILES", r"C:\Program Files\Common Files")
_SURGE_HOMES = {
    "win32": [Path(_COMMON) / "VST3" / "Surge Synth Team" / "Surge XT.vst3"],
    "darwin": [Path("/Library/Audio/Plug-Ins/VST3/Surge XT.vst3"),
               Path.home() / "Library/Audio/Plug-Ins/VST3/Surge XT.vst3"],
    "linux": [Path.home() / ".vst3/Surge XT.vst3", Path("/usr/lib/vst3/Surge XT.vst3"),
              Path("/usr/local/lib/vst3/Surge XT.vst3")],
}


# ---------------------------------------------------------------- the engines


def surge_binary(stated: str = "", platform: str = sys.platform) -> Path | None:
    """The Surge XT plug-in a render loads, or None where there is none.

    On Windows the loader needs the binary inside the bundle, not the bundle: Pedalboard
    refuses `Surge XT.vst3` the folder and loads `Contents/x86_64-win/Surge XT.vst3`.
    """
    candidates = [Path(stated)] if stated else _SURGE_HOMES.get(platform, [])
    for bundle in candidates:
        inner = bundle / "Contents" / "x86_64-win" / bundle.name
        if platform == "win32" and inner.is_file():
            return inner
        if bundle.exists():
            return bundle
    return None


def _refused(what: str, remedy: str) -> PolyweaveError:
    return PolyweaveError("music.no-engine", what, remedy)


def engines(root: str | Path, model: dict) -> dict:
    """What this score needs to render, found now; one that is missing is refused."""
    config = load(root)
    tracks = model["extensions"][music.EXTENSION]["tracks"]
    kinds = {t["instrument"].split(":")[0] for t in tracks.values()}
    try:
        import pedalboard  # noqa: F401
    except ImportError:
        raise _refused(
            "rendering needs Pedalboard, which is not installed here",
            "pip install pedalboard (or polyweave[audio]) in the Python polyweave runs",
        ) from None
    found: dict[str, Any] = {"ffmpeg": shutil.which("ffmpeg")}
    if kinds & {"gm", "drums"}:
        found["fluidsynth"] = shutil.which(str(config.path("paths.fluidsynth")))
        if not found["fluidsynth"]:
            raise _refused(
                f"the score plays General MIDI and there is no FluidSynth at "
                f"{config.get('paths.fluidsynth')}",
                "install FluidSynth, or set [paths] fluidsynth to its binary",
            )
        font = str(config.get("paths.soundfont") or "")
        found["soundfont"] = config.path("paths.soundfont") if font else None
        if not found["soundfont"] or not found["soundfont"].is_file():
            raise _refused(
                "the score plays General MIDI and [paths] soundfont names no file",
                "set [paths] soundfont to a General MIDI .sf2, such as GeneralUser GS",
            )
    if "surge" in kinds:
        found["surge"] = surge_binary(str(config.get("paths.surge") or ""))
        if found["surge"] is None:
            raise _refused(
                "the score plays Surge patches and Surge XT is not installed where it "
                "usually is",
                "install Surge XT, or set [paths] surge to its .vst3",
            )
    return found


def nearest_label(labels: list, value: Any) -> Any:
    """The label a Surge parameter shows that is nearest a number, in its own unit.

    Surge's time and pitch parameters take one of a list of labels ("5.0 ms", "1.00 s",
    "7.00 semitones"), not a number, so a patch writes the number and this finds the
    label. A value that is not a number, or a parameter whose values are not labels, is
    passed through as it is.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        return value
    if not labels or not isinstance(labels[0], str):
        return value
    best, gap = value, None
    for label in labels:
        match = re.match(r"\s*(-?[\d.]+)\s*(\w*)", label)
        if not match:
            continue
        number = float(match.group(1)) * (1000.0 if match.group(2) == "s" else 1.0)
        if gap is None or abs(number - value) < gap:
            best, gap = label, abs(number - value)
    return best


class _Surge:
    """One Surge XT instance, reset between patches rather than loaded again."""

    def __init__(self, binary: Path):
        from pedalboard import load_plugin

        self.plugin = load_plugin(str(binary))
        self.init = {k: p.raw_value for k, p in self.plugin.parameters.items()}
        self.touched: set[str] = set()

    def patch(self, name: str, settings: dict) -> None:
        params = self.plugin.parameters
        # A type first, since the names under it change with it.
        for key in sorted(self.touched, key=lambda k: not k.endswith("_type")):
            if key in self.init and key in params:
                params[key].raw_value = self.init[key]
            if key.endswith("_type"):
                params = self.plugin.parameters
        self.touched = set()
        params = self.plugin.parameters
        for key, value in settings.items():
            if key not in params:
                near = difflib.get_close_matches(key, params, n=1)
                raise PolyweaveError(
                    "music.unknown-parameter",
                    f"patch {name} sets {key}, which Surge XT does not have here",
                    f"did you mean {near[0]}?" if near
                    else "name a parameter Surge shows, after any _type it depends on",
                    given=key,
                    allowed=sorted(params),
                )
            setattr(self.plugin, key, nearest_label(params[key].valid_values, value))
            self.touched.add(key)
            if key.endswith("_type"):
                params = self.plugin.parameters

    def render(self, notes: list[dict], seconds_per_tick: float, total: float):
        # Pedalboard takes raw MIDI bytes with a time in seconds, so no MIDI library.
        timeline = []
        for note in notes:
            on = note["start"] * seconds_per_tick
            off = (note["start"] + note["duration"]) * seconds_per_tick
            timeline.append((on, 1, bytes([0x90, note["pitch"], note["velocity"]])))
            timeline.append((off, 0, bytes([0x80, note["pitch"], 0])))
        # A release before a new strike at the same moment, as in the MIDI file.
        timeline.sort(key=lambda e: (e[0], e[1]))
        out = self.plugin([(data, at) for at, _, data in timeline], duration=total,
                          sample_rate=RATE, reset=True)
        return np.asarray(out, dtype=np.float64).T


#: A loaded Surge per binary, kept for the life of the process: loading is the cost.
_SURGES: dict[Path, _Surge] = {}


def _fluid(part: dict, notes: list[dict], settings: dict, model: dict, total: float,
           found: dict, work: Path) -> np.ndarray:
    alone = {**model, "parts": [part], "notes": notes,
             "extensions": {music.EXTENSION: {"tracks": {part["id"]: settings}}}}
    until = int(total / _seconds_per_tick(model))
    midi, wav = work / f"{part['id']}.mid", work / f"{part['id']}.wav"
    midi.write_bytes(music.midi_bytes(alone, until=until))
    subprocess.run(
        [found["fluidsynth"], "-ni", "-q", "-R", "0", "-C", "0", "-g", "0.5",
         "-r", str(RATE), "-o", "synth.polyphony=256", "-F", str(wav),
         str(found["soundfont"]), str(midi)],
        check=True, capture_output=True,
    )
    samples, rate = sound.read(wav)
    if rate != RATE:
        raise PolyweaveError("music.no-engine", f"FluidSynth wrote {rate} Hz",
                             f"check that it honours -r {RATE}")
    return samples


# ---------------------------------------------------------------- the mix


def _db(value: float) -> float:
    return 20.0 * float(np.log10(max(value, 1e-12)))


def _fit(audio: np.ndarray, n: int) -> np.ndarray:
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if len(audio) >= n:
        return audio[:n]
    return np.vstack([audio, np.zeros((n - len(audio), 2))])


def stem_level(audio: np.ndarray) -> float:
    """Where a stem plays: the 95th percentile of its 50 ms RMS windows, linear.

    A percentile rather than a mean, so a part that rests for half the piece is levelled
    by how loud it is when it plays.
    """
    mono = audio.mean(axis=1)
    width = int(0.05 * RATE)
    frames = mono[: len(mono) // width * width].reshape(-1, width)
    if not len(frames):
        return 0.0
    return float(np.percentile(np.sqrt((frames**2).mean(axis=1)), 95))


def _pan(audio: np.ndarray, position: float) -> np.ndarray:
    angle = (position + 1.0) * np.pi / 4.0
    return audio * np.array([np.cos(angle), np.sin(angle)]) * np.sqrt(2.0)


def _send(level: float | None) -> float:
    return 0.0 if level is None else 10 ** (level / 20.0)


def mix(stems: dict[str, np.ndarray], tracks: dict, room: float,
        seconds_per_beat: float) -> np.ndarray:
    """Level, pan and send every stem, and return the stereo sum with its effects."""
    from pedalboard import Delay, HighpassFilter, Pedalboard, Reverb

    n = len(next(iter(stems.values())))
    dry, verb, echo = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    for name, audio in stems.items():
        level = stem_level(audio)
        if level < 1e-6:
            continue
        settings = tracks[name]
        placed = audio * 10 ** ((STEM_LEVEL - _db(level) + settings["gain"]) / 20.0)
        placed = _pan(placed, settings["pan"])
        dry += placed
        verb += placed * _send(settings["reverb"])
        echo += placed * _send(settings["delay"])
    reverb = Pedalboard([Reverb(room_size=room, damping=0.5, wet_level=1.0,
                                dry_level=0.0, width=1.0)])
    delay = Pedalboard([Delay(delay_seconds=seconds_per_beat * 0.75, feedback=0.35,
                              mix=1.0), HighpassFilter(250)])
    return (dry + reverb(verb.T.astype(np.float32), RATE).T
            + delay(echo.T.astype(np.float32), RATE).T)


def master(audio: np.ndarray, cyclic: bool) -> np.ndarray:
    """Compress, level and limit; a loop is run as a loop, so its seam sees its tail."""
    from pedalboard import Compressor, Gain, HighpassFilter, Limiter, Pedalboard

    pre = min(RATE * 2, len(audio)) if cyclic else 0
    body = np.vstack([audio[len(audio) - pre:], audio]) if pre else audio
    squeezed = Pedalboard([HighpassFilter(30), Compressor(
        threshold_db=-20, ratio=2.5, attack_ms=15, release_ms=200)])(
        body.T.astype(np.float32), RATE)
    # JUCE's limiter lifts its threshold to 0 dBFS, so the ceiling is a gain after it,
    # and the level going in is found by measuring what comes out.
    want = LOUDNESS - CEILING
    gain = want - _db(float(np.sqrt(np.mean(squeezed[:, pre:] ** 2))))
    for _ in range(4):
        limited = Pedalboard([Gain(gain), Limiter(threshold_db=-3.0, release_ms=120)])(
            squeezed, RATE)
        gain += want - _db(float(np.sqrt(np.mean(limited[:, pre:] ** 2))))
    return (limited[:, pre:] * 10 ** (CEILING / 20.0)).T.astype(np.float64)


def _write_wav(where: Path, audio: np.ndarray) -> None:
    pcm = np.clip(np.round(audio * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(where), "wb") as held:
        held.setnchannels(2)
        held.setsampwidth(2)
        held.setframerate(RATE)
        held.writeframes(pcm.tobytes())


def _seconds_per_tick(model: dict) -> float:
    tempo = model["timing"]["tempo"][0]["microsecondsPerQuarter"]
    return tempo / 1_000_000 / model["timing"]["ticksPerQuarter"]


# ---------------------------------------------------------------- the operation


@operation("music.render", kind="bake", injects=("report",))
def render(
    report,
    source: Annotated[str, Param("the *.music.toml, relative to the project")],
    out: Annotated[
        str, Param("where to write, without a suffix; beside the score if unset")
    ] = None,
    root: Annotated[str, Param("the project the score belongs to")] = ".",
) -> dict:
    """Render a valid score to WAV and OGG through Surge XT and FluidSynth.

    Every part is rendered, then levelled, panned, sent and mastered through one fixed
    chain; a looping score's tail is folded onto its loop. A score with several layers
    also writes one file per layer, <out>.<layer>, all one length, which add up to the
    whole. The answer carries what sound.measure says of each file.
    """
    config = load(root)
    here, where = config.root, config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError(
            "music.unreadable",
            f"there is no score at {source}",
            "name a *.music.toml relative to the project root",
        )
    text = where.read_text(encoding="utf-8")
    model, problems = music.compile_source(text, where.stem)
    if model is None:
        raise PolyweaveError(
            "music.invalid",
            f"{source} has {len(problems)} problem(s); the first, on line "
            f"{problems[0]['line']}: {problems[0]['message']}",
            f"call music.validate on {source} and fix what it names",
        )
    report.stage("building", note="finding the engines this score plays through")
    found = engines(here, model)
    ext = model["extensions"][music.EXTENSION]
    per_tick = _seconds_per_tick(model)
    end = max(s["endTick"] for s in model["sections"])
    total = end * per_tick + TAIL
    stem = where.name.removesuffix(".toml").removesuffix(".music")
    work = config.path("paths.work") / "music" / stem
    work.mkdir(parents=True, exist_ok=True)

    report.stage("rendering", note="rendering each part")
    stems, played_by = {}, {}
    for index, part in enumerate(model["parts"]):
        settings = ext["tracks"][part["id"]]
        notes = [n for n in model["notes"] if n["part"] == part["id"]]
        engine, _, name = settings["instrument"].partition(":")
        report.progress(index / len(model["parts"]), note=f"{part['id']} on {engine}")
        if engine == "surge":
            binary = found["surge"]
            if binary not in _SURGES:
                report.note("loading Surge XT, which takes about a minute")
                _SURGES[binary] = _Surge(binary)
            _SURGES[binary].patch(name, ext["patches"][name])
            audio = _SURGES[binary].render(notes, per_tick, total)
        else:
            audio = _fluid(part, notes, settings, model, total, found, work)
        stems[part["id"]] = _fit(audio, int(round(total * RATE)))
        played_by[part["id"]] = engine

    report.progress(1.0, note="mixing and mastering")
    spb = per_tick * model["timing"]["ticksPerQuarter"]
    loop = ext["loop"]
    body, cyclic = _folded(mix(stems, ext["tracks"], ext["room"], spb), loop, per_tick)
    final = master(body, cyclic=cyclic)

    target = where.with_name(stem) if not out else config.path("paths.work", out)
    target.parent.mkdir(parents=True, exist_ok=True)
    answer = {
        **_written(target, final, found["ffmpeg"], loop, here),
        "parts": played_by,
        "loop": ({"start": round(loop["startTick"] * per_tick, 3),
                  "end": round(loop["endTick"] * per_tick, 3)} if loop else None),
    }
    layers = _layers(ext["tracks"])
    if len(layers) > 1:
        # Each layer rides the gain the master applied to the whole, moment by moment,
        # so the layers add back up to what the game hears with every layer in.
        riding = _gain_curve(body, final)
        answer["layers"] = {}
        for layer in layers:
            own = {k: v for k, v in stems.items() if ext["tracks"][k]["layer"] == layer}
            part, _ = _folded(mix(own, ext["tracks"], ext["room"], spb), loop, per_tick)
            answer["layers"][layer] = _written(
                target.with_name(f"{target.name}.{layer}"),
                _high_passed(part) * riding[:, None],
                found["ffmpeg"], loop, here,
            )
    return answer


def _layers(tracks: dict) -> list[str]:
    """The score's layers in the order its tracks first name them, `base` first."""
    named = list(dict.fromkeys(t["layer"] for t in tracks.values()))
    return sorted(named, key=lambda layer: layer != "base")


def _high_passed(audio: np.ndarray) -> np.ndarray:
    """The master's own 30 Hz high-pass, the one linear stage of its chain."""
    from pedalboard import HighpassFilter, Pedalboard

    passed = Pedalboard([HighpassFilter(30)])(audio.T.astype(np.float32), RATE)
    return passed.T.astype(np.float64)


def _gain_curve(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """The gain the master applied, per sample, from 10 ms windows of the whole.

    The compressor and the limiter are one gain that moves over time, so it is read off
    what went in and what came out and put on each layer; a window that was silent going
    in takes the typical gain rather than a ratio of two nothings.
    """
    passed = _high_passed(before)
    width = int(0.01 * RATE)
    count = len(passed) // width
    if count == 0:
        return np.ones(len(after))

    def level(audio: np.ndarray) -> np.ndarray:
        framed = audio[: count * width].reshape(count, width, 2)
        return np.sqrt((framed**2).mean(axis=(1, 2)))

    went, came = level(passed), level(after)
    heard = went > 1e-5
    typical = float(np.median(came[heard] / went[heard])) if heard.any() else 1.0
    ratio = np.where(heard, came / np.maximum(went, 1e-12), typical)
    centres = (np.arange(count) + 0.5) * width
    return np.interp(np.arange(len(after)), centres, ratio)


def _folded(summed: np.ndarray, loop: dict | None,
            per_tick: float) -> tuple[np.ndarray, bool]:
    """A loop's body with its tail folded onto its start, and whether it is a cycle.

    A stinger keeps its tail as it is.
    """
    if not loop:
        return summed, False
    head = int(round(loop["startTick"] * per_tick * RATE))
    tail_at = int(round(loop["endTick"] * per_tick * RATE))
    body, ring = summed[:tail_at].copy(), summed[tail_at:]
    span = min(len(ring), tail_at - head)
    body[head: head + span] += ring[:span]
    return body, head == 0


def _written(target: Path, audio: np.ndarray, ffmpeg: str | None, loop: dict | None,
             here: Path) -> dict:
    """One file written as WAV, encoded as OGG where ffmpeg is, and measured."""
    wav = target.with_name(f"{target.name}.wav")
    _write_wav(wav, audio)
    ogg = None
    if ffmpeg:
        ogg = target.with_name(f"{target.name}.ogg")
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(wav), "-c:a",
                        "libvorbis", "-q:a", "6", str(ogg)],
                       check=True, capture_output=True)
    measured = sound.measure(wav)
    if not loop:
        measured = {k: v for k, v in measured.items() if k not in sound.SEAM}
    return {
        "wav": wav.relative_to(here).as_posix(),
        "ogg": ogg.relative_to(here).as_posix() if ogg else None,
        "why_no_ogg": None if ogg else "no ffmpeg on PATH to encode it",
        "measured": measured,
    }
