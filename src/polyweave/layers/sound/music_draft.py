"""A MIDI file drafted as a `*.music.toml` a person edits and renders (§PW559).

Spinhold's intro was bought as a recording and had to join the scores the game edits.
The project transcribed it by hand: stems, a transcriber to MIDI in a scratch
environment, then tempo, key, chords and lines read off the MIDI and the score typed
in. This module is the last half of that, kept: a MIDI file in, a valid score out.

The draft is a tracker's reading of the MIDI, not a musician's:

- tempo and meter are the file's first, and the answer says when it changes later;
  the key is the file's signature, or estimated from the pitches (Krumhansl's
  profiles) and said to be;
- one `[[track]]` per MIDI track and channel, a drum channel as a drum track, its
  instrument the General MIDI program the file sets;
- notes are quantised to `grid` steps a quarter, cut at the bar line (a pattern is one
  bar), and written bar by bar in mini-notation: notes struck and released together
  are one chord, notes that overlap otherwise are stacked voices;
- the bars are read in phrases of `phrase` bars, and a phrase that comes back is the
  same section played again, so the form is found from repetition; inside a section
  a bar played several times running is folded with `!n`.

Each track answers how much of it sat on the grid, so a person knows which line to
listen to first.
"""

from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Annotated

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound.music import DRUMS, validate

_NAMES = ("c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b")
_KEYS = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
#: Krumhansl and Kessler's key profiles, C major and C minor.
_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
#: The drum channel, counted from zero.
_DRUM_CHANNEL = 9
#: An onset this close to a step, as a share of the step, is on the grid.
_ON_GRID = 0.2


def _read_midi(data: bytes) -> dict:
    """The parts of a Standard MIDI File, format 0 or 1, and its first meta events."""
    if data[:4] != b"MThd" or len(data) < 14:
        raise ValueError("it does not start with an MThd header")
    count = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    if division & 0x8000:
        raise ValueError("its time is in SMPTE frames, not ticks a quarter")
    found: dict = {"tpq": division, "tempo": [], "meter": [], "key": None, "parts": {}}
    at = 8 + int.from_bytes(data[4:8], "big")
    for track in range(count):
        if data[at:at + 4] != b"MTrk":
            raise ValueError(f"track {track + 1} has no MTrk header")
        size = int.from_bytes(data[at + 4:at + 8], "big")
        _read_track(data[at + 8:at + 8 + size], track, found)
        at += 8 + size
    return found


def _read_track(body: bytes, track: int, found: dict) -> None:
    i, tick, status, name = 0, 0, 0, ""
    programs: dict[int, int] = {}
    held: dict[tuple[int, int], list[tuple[int, int]]] = {}
    notes: dict[int, list[tuple[int, int, int, int]]] = {}

    def vlq() -> int:
        nonlocal i
        value = 0
        while True:
            byte = body[i]
            i += 1
            value = (value << 7) | (byte & 0x7F)
            if not byte & 0x80:
                return value

    while i < len(body):
        tick += vlq()
        if body[i] & 0x80:
            status = body[i]
            i += 1
        if status == 0xFF:
            kind = body[i]
            i += 1
            length = vlq()
            data = body[i:i + length]
            i += length
            if kind == 0x03 and not name:
                name = data.decode("utf-8", "replace")
            elif kind == 0x51 and len(data) == 3:
                found["tempo"].append((tick, int.from_bytes(data, "big")))
            elif kind == 0x58 and len(data) >= 2:
                found["meter"].append((tick, (data[0], 2 ** data[1])))
            elif kind == 0x59 and len(data) == 2 and found["key"] is None:
                found["key"] = (int.from_bytes(data[:1], "big", signed=True), data[1])
            elif kind == 0x2F:
                break
            continue
        if status in (0xF0, 0xF7):
            i += vlq()
            continue
        kind, channel = status & 0xF0, status & 0x0F
        if kind in (0xC0, 0xD0):
            if kind == 0xC0:
                programs.setdefault(channel, body[i])
            i += 1
            continue
        pitch, velocity = body[i], body[i + 1]
        i += 2
        if kind == 0x90 and velocity:
            held.setdefault((channel, pitch), []).append((tick, velocity))
        elif kind in (0x80, 0x90) and held.get((channel, pitch)):
            start, struck = held[(channel, pitch)].pop(0)
            notes.setdefault(channel, []).append((start, tick - start, pitch, struck))
    for channel, played in notes.items():
        found["parts"][(track, channel)] = {
            "name": name, "channel": channel, "program": programs.get(channel, 0),
            "notes": sorted(played),
        }


def _key(signature: tuple[int, int] | None, notes: list) -> tuple[str, bool]:
    """The key the file states, or the one its pitches fit best, and whether stated."""
    if signature is not None:
        sharps, minor = signature
        tonic = (sharps * 7 + (9 if minor else 0)) % 12
        return f"{_KEYS[tonic]} {'minor' if minor else 'major'}", True
    weight = [0.0] * 12
    for _, length, pitch, _ in notes:
        weight[pitch % 12] += length
    best, named = -2.0, "C major"
    for tonic in range(12):
        for profile, mode in ((_MAJOR, "major"), (_MINOR, "minor")):
            fit = _correlation(weight, profile[-tonic:] + profile[:-tonic])
            if fit > best:
                best, named = fit, f"{_KEYS[tonic]} {mode}"
    return named, False


def _correlation(a: list[float], b: tuple) -> float:
    mean_a, mean_b = sum(a) / 12, sum(b) / 12
    top = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    under = math.sqrt(sum((x - mean_a) ** 2 for x in a)
                      * sum((y - mean_b) ** 2 for y in b))
    return top / under if under else -1.0


def _token(pitches: list[int], drums: bool) -> str:
    """One step's sound: a note, a drum or a chord, as mini-notation spells it."""
    names = {v: k for k, v in DRUMS.items()}
    words = [names.get(p, str(p)) if drums else f"{_NAMES[p % 12]}{p // 12 - 1}"
             for p in sorted(pitches)]
    return words[0] if len(words) == 1 else f"[{','.join(words)}]"


def _bar(events: list[tuple[int, int, int]], steps: int, drums: bool) -> str:
    """One bar's notes, (step, length, pitch) inside it, as mini-notation."""
    if not events:
        return "~"
    chords: dict[tuple[int, int], list[int]] = {}
    for start, length, pitch in events:
        chords.setdefault((start, length), []).append(pitch)
    voices: list[list[tuple[int, int, list[int]]]] = []
    for (start, length), pitches in sorted(chords.items()):
        free = next((v for v in voices if v[-1][0] + v[-1][1] <= start), None)
        if free is None:
            voices.append(free := [])
        free.append((start, length, pitches))
    return ", ".join(_voice(v, steps, drums) for v in voices)


def _voice(chords: list[tuple[int, int, list[int]]], steps: int, drums: bool) -> str:
    parts: list[tuple[str, int]] = []
    now = 0
    for start, length, pitches in chords:
        if start > now:
            parts.append(("~", start - now))
        parts.append((_token(pitches, drums), length))
        now = start + length
    if now < steps:
        parts.append(("~", steps - now))
    whole = math.gcd(*(n for _, n in parts))
    words = [w if n == whole else f"{w}@{n // whole}" for w, n in parts]
    period = _period(words)
    if period < len(words):
        unit = " ".join(words[:period])
        unit = unit if period == 1 else f"[{unit}]"
        return f"{unit}!{len(words) // period}"
    return " ".join(_runs(words))


def _period(items: list[str]) -> int:
    """The shortest run the items are made of, repeated whole; their count if none."""
    return next(p for p in range(1, len(items) + 1)
                if len(items) % p == 0 and items == items[:p] * (len(items) // p))


def _runs(items: list[str]) -> list[str]:
    """The items with one played several times running written once, as `x!n`."""
    runs: list[list] = []
    for item in items:
        if runs and runs[-1][0] == item:
            runs[-1][1] += 1
        else:
            runs.append([item, 1])
    return [item if times == 1 else f"{item}!{times}" for item, times in runs]


def _folded(bars: list[str]) -> str:
    """A section's bars for one track, one a bar, a cycle or a bar played again folded.

    `<a b>` takes one a bar and starts again, so bars that cycle are written once.
    """
    if len(set(bars)) == 1:
        return bars[0]
    words = [bar if re.fullmatch(r"[^\s,\[\]]+|\[[^\[\]]*\]", bar) else f"[{bar}]"
             for bar in bars]
    return f"<{' '.join(_runs(words[:_period(words)]))}>"


def _ident(text: str, fallback: str, taken: set[str]) -> str:
    name = re.sub(r"[^a-z0-9_-]+", "_", text.lower()).strip("_-")
    name = name if re.match(r"[a-z]", name or "") else fallback
    unique, n = name, 2
    while unique in taken:
        unique, n = f"{name}{n}", n + 1
    taken.add(unique)
    return unique


def draft(data: bytes, title: str, grid: int = 4, phrase: int = 4) -> tuple[str, dict]:
    """The score a MIDI file drafts to, and what the drafting found on the way."""
    midi = _read_midi(data)
    if not midi["parts"]:
        raise ValueError("it holds no notes")
    tpq = midi["tpq"]
    tempo = midi["tempo"][0][1] if midi["tempo"] else 500_000
    meter = midi["meter"][0][1] if midi["meter"] else (4, 4)
    bpm = round(60_000_000 / tempo, 2)
    per_step = Fraction(tpq, grid)
    steps = Fraction(meter[0] * 4, meter[1]) * grid
    if steps.denominator != 1:
        raise ValueError(f"a {meter[0]}/{meter[1]} bar is not a whole number of steps "
                         f"at {grid} a quarter")
    steps = int(steps)
    pitched = [n for p in midi["parts"].values() if p["channel"] != _DRUM_CHANNEL
               for n in p["notes"]]
    key, stated = _key(midi["key"], pitched)
    taken: set[str] = set()
    tracks = []
    for (track, channel), part in sorted(midi["parts"].items()):
        drums = channel == _DRUM_CHANNEL
        name = _ident(part["name"], "drums" if drums else f"track{track + 1}", taken)
        placed: dict[tuple[int, int], tuple[int, int]] = {}
        on_grid = cut = 0
        for start, length, pitch, _ in part["notes"]:
            exact = start / per_step
            onset = round(exact)
            on_grid += abs(exact - onset) <= _ON_GRID
            span = max(1, round((start + length) / per_step) - onset)
            room = steps - onset % steps
            cut += span > room
            span = min(span, room)
            if placed.get((onset, pitch), (0, 0))[0] < span:
                placed[(onset, pitch)] = (span, pitch)
        tracks.append({
            "name": name, "drums": drums, "program": part["program"],
            "velocity": sorted(v for *_, v in part["notes"])[len(part["notes"]) // 2],
            "placed": placed, "notes": len(part["notes"]),
            "on_grid": round(on_grid / len(part["notes"]), 3), "cut": cut,
            "merged": len(part["notes"]) - len(placed),
        })
    total = 1 + max(o // steps for t in tracks for o, _ in t["placed"])
    for t in tracks:
        bars: list[list] = [[] for _ in range(total)]
        for (onset, pitch), (span, _) in t["placed"].items():
            bars[onset // steps].append((onset % steps, span, pitch))
        t["bars"] = [_bar(sorted(b), steps, t["drums"]) for b in bars]
    sections: dict[tuple, str] = {}
    form, lengths = [], {}
    for first in range(0, total, phrase):
        shape = tuple(tuple(t["bars"][first:first + phrase]) for t in tracks)
        if shape not in sections:
            sections[shape] = chr(ord("A") + len(sections)) if len(sections) < 26 \
                else f"S{len(sections) + 1}"
            lengths[sections[shape]] = len(shape[0])
        form.append(sections[shape])
    patterns: dict[str, str] = {}
    for n, t in enumerate(tracks):
        t["play"] = {}
        for shape, section in sections.items():
            if all(b == "~" for b in shape[n]):
                continue
            text = _folded(list(shape[n]))
            name = next((k for k, v in patterns.items()
                         if v == text and k.startswith(f"{t['name']}_")), None)
            if name is None:
                name = f"{t['name']}_{section.lower()}"
                patterns[name] = text
            t["play"][section] = name
    found = {
        "bpm": bpm, "meter": list(meter), "key": key, "key_stated": stated,
        "bars": total, "form": form,
        "tempo_changes": len({v for _, v in midi["tempo"]}) - 1 if midi["tempo"] else 0,
        "meter_changes": len({v for _, v in midi["meter"]}) - 1 if midi["meter"] else 0,
        "tracks": {t["name"]: {
            "instrument": "drums:0" if t["drums"] else f"gm:{t['program']}",
            "notes": t["notes"], "on_grid": t["on_grid"], "cut_at_bar": t["cut"],
            "merged": t["merged"], "plays": sorted(t["play"]),
        } for t in tracks},
    }
    return _source(title, found, lengths, patterns, tracks), found


def _source(title: str, found: dict, lengths: dict, patterns: dict,
            tracks: list) -> str:
    def text(value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    bpm = found["bpm"]
    out = [
        "# Drafted by music.from_midi: quantised to the grid, one pattern a bar,",
        "# the sections found from repetition. Hear it beside the original first.",
        "",
        "[music]",
        f"title = {text(title)}",
        f"bpm   = {int(bpm) if bpm == int(bpm) else bpm}",
        f"meter = [{found['meter'][0]}, {found['meter'][1]}]",
        f"key   = {text(found['key'])}",
        f"form  = [{', '.join(text(s) for s in found['form'])}]",
        "loop  = false",
        "",
    ]
    for section, bars in lengths.items():
        out += [f"[section.{section}]", f"bars = {bars}", ""]
    out.append("[pattern]")
    out += [f"{name} = {text(value)}" for name, value in patterns.items()]
    for t in tracks:
        if not t["play"]:
            continue
        play = ", ".join(f"{s} = {text(p)}" for s, p in t["play"].items())
        out += ["", "[[track]]", f"name       = {text(t['name'])}"]
        if t["drums"]:
            out += ['instrument = "drums:0"', "drums      = true"]
        else:
            out.append(f'instrument = "gm:{t["program"]}"')
        out += [f"velocity   = {t['velocity']}", "gate       = 1.0",
                f"play       = {{ {play} }}"]
    return "\n".join(out) + "\n"


@operation("music.from_midi")
def from_midi(
    midi: Annotated[str, Param("the .mid to draft from, relative to the project")],
    out: Annotated[str, Param("the *.music.toml to write; beside the MIDI if unset")
                   ] = None,
    grid: Annotated[int, Param("steps a quarter note the notes are quantised to")] = 4,
    phrase: Annotated[int, Param("bars a section is read in, to find repeats")] = 4,
    replace: Annotated[bool, Param("write over a score already there")] = False,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Draft an editable score from a MIDI file: tempo, key, tracks and repeats found.

    Answers the score's music.validate result and, per track, how much sat on the
    grid; a person hears the draft beside the original before it replaces it.
    """
    config = load(root)
    source = config.path("paths.work", midi)
    if not source.is_file():
        raise PolyweaveError("music.unreadable", f"there is no MIDI file at {midi}",
                             "name a .mid relative to the project root")
    stem = source.name.rsplit(".", 1)[0]
    target = config.path("paths.work", out) if out else source.with_name(
        f"{stem}.music.toml")
    if target.exists() and not replace:
        raise PolyweaveError(
            "music.draft-exists", f"{target.relative_to(config.root).as_posix()} is "
            "already there, and a draft would write over a score someone edited",
            "pass out, another path, or replace = true")
    if grid < 1 or phrase < 1:
        raise PolyweaveError("music.bad-value", "grid and phrase count from one",
                             "pass grid = 4 for sixteenths and phrase = 4 bars")
    try:
        text, found = draft(source.read_bytes(), stem, grid, phrase)
    except (ValueError, IndexError) as exc:
        raise PolyweaveError(
            "music.not-midi", f"{midi} cannot be drafted: {exc}",
            "pass a Standard MIDI File, format 0 or 1, with notes in it") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    where = target.relative_to(config.root).as_posix()
    checked = validate(where, root)
    return {
        "score": where, "midi": midi, **found,
        "valid": checked["valid"], "problems": checked["problems"],
        "says": f"{len(found['tracks'])} track(s) over {found['bars']} bars; hear it "
                "with music.render beside the original before keeping it",
    }
