"""Music as an editable source an agent writes and polyweave checks (§PW186).

An agent composes well only when its output is structured and a validator answers it,
which is the loop piano's score format proved. A piece is also something a person
reopens and changes, so the file that is edited and the model that is checked are two
layers:

- the **source** is a `*.music.toml`, laid out like a tracker. `[music]` holds tempo,
  meter, key, the form and the loop; `[section.<name>]` its length in bars; `[pattern]`
  short named lines in Strudel's mini-notation, one cycle per bar; `[[track]]` an
  instrument, a layer and which pattern it plays in each section. Changing a riff is one
  line, and a diff reads as music;
- the **model** is derived from it and never edited: absolute ticks per note in the
  shape of piano's score JSON (`formatVersion`, `timing`, `parts`, `notes`,
  `sections`), with what piano has no field for (drums, instruments, layers, the loop)
  under one `extensions` key.

The PW184 spike chose the notation: ABC matched mini-notation note for note on three
pieces, but ran two to three times longer on drums and arpeggios, and its bar-long
accidentals turned one missed sharp into two wrong notes.

Every problem is reported at once, each with the source line it is on and a remedy,
because an agent repairing a score fixes all it is told about in one pass.
"""

from __future__ import annotations

import difflib
import re
import tomllib
import zlib
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Any

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: Piano's resolution, so a model reads in either program without rescaling.
TICKS = 480

#: What piano calls this format, and the key polyweave's own fields live under.
FORMAT_VERSION = 1
EXTENSION = "dev.alegauss.polyweave.music"

#: General MIDI percussion by the names mini-notation uses.
DRUMS = {
    "bd": 36, "rim": 37, "sd": 38, "cp": 39, "hh": 42, "ph": 44, "oh": 46, "lt": 45,
    "mt": 47, "cr": 49, "ht": 50, "rd": 51, "tb": 54, "cb": 56, "sh": 70,
}

_STEPS = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
_NOTE = re.compile(r"([a-g])(#|s|b)?(-1|\d)")
_TOKEN = re.compile(r"\s*([\[\]<>,~_*!@]|\d+(?:\.\d+)?|[a-z#][a-z#0-9-]*|\S)")
_NAME = re.compile(r"[a-z][a-z0-9_-]*")

#: A key the source must state.
REQUIRED = object()

#: Every key a table may hold: its type and its default. `float` means any number.
_MUSIC = {
    "title": (str, REQUIRED), "bpm": (float, REQUIRED), "meter": (list, [4, 4]),
    "key": (str, ""), "form": (list, REQUIRED), "loop": (bool, True),
    "loop_from": (str, ""),
}
_TRACK = {
    "name": (str, REQUIRED), "instrument": (str, REQUIRED), "layer": (str, "base"),
    "drums": (bool, False), "velocity": (float, 96), "groove": (float, 0.0),
    "wobble": (float, 0.0), "gate": (float, 0.9), "play": (dict, REQUIRED),
}
#: The ranges a number must fall in, inclusive.
_RANGES = {
    "bpm": (20, 400), "velocity": (1, 127), "groove": (0, 1), "wobble": (0, 64),
    "gate": (0.05, 4),
}
_TABLES = ("music", "section", "pattern", "track")


class _Problems:
    """What is wrong with one source, each against the line it is on."""

    def __init__(self, text: str):
        self.lines = text.splitlines()
        self.found: list[dict] = []

    def line(self, key: str, after: int = 0) -> int | None:
        """The first line past line `after` that sets `key`, counted from one."""
        pattern = re.compile(rf'^\s*"?{re.escape(key)}"?\s*=')
        for n, text in enumerate(self.lines[after:], start=after + 1):
            if pattern.match(text):
                return n
        return None

    def header(self, name: str, nth: int = 0) -> int | None:
        """The line of the `nth` `[name]` or `[[name]]` header, counted from one."""
        pattern = re.compile(rf"^\s*\[\[?\s*{re.escape(name)}\s*\]\]?")
        seen = 0
        for n, text in enumerate(self.lines, start=1):
            if pattern.match(text):
                if seen == nth:
                    return n
                seen += 1
        return None

    def add(self, code: str, line: int | None, message: str, remedy: str) -> None:
        self.found.append(
            {"code": code, "line": line, "message": message, "remedy": remedy}
        )


# ---------------------------------------------------------------- mini-notation


class NotationError(ValueError):
    """A pattern that does not parse, at a character offset into it."""

    def __init__(self, message: str, at: int):
        super().__init__(message)
        self.at = at


def _pitch(word: str, at: int) -> int:
    if word in DRUMS:
        return DRUMS[word]
    if word.isdigit():
        return int(word)
    match = _NOTE.fullmatch(word)
    if not match:
        raise NotationError(
            f"'{word}' is not a note (c4, eb3, f#5), a drum ({', '.join(DRUMS)}) or a "
            f"MIDI number",
            at,
        )
    letter, accidental, octave = match.groups()
    shift = {"#": 1, "s": 1, "b": -1}.get(accidental or "", 0)
    return 12 * (int(octave) + 1) + _STEPS[letter] + shift


class _Mini:
    """A subset of Strudel's mini-notation, where one cycle is one bar.

    Steps share the bar by weight (`@n`); `~` rests; `_` extends the step before it;
    `[a b]` subdivides; `[a, b]` stacks; `<a b>` takes one per bar; `x*n` repeats the
    step n times inside it; `x!n` replicates it as n steps.
    """

    def __init__(self, text: str):
        self.tokens = [(m.group(1), m.start(1)) for m in _TOKEN.finditer(text)]
        self.i = 0
        #: The drum names the pattern used, so a pitched track can refuse them.
        self.drums: list[str] = []

    def peek(self) -> str | None:
        return self.tokens[self.i][0] if self.i < len(self.tokens) else None

    def at(self) -> int:
        if not self.tokens:
            return 0
        return self.tokens[min(self.i, len(self.tokens) - 1)][1]

    def take(self, want: str | None = None) -> str:
        token = self.peek()
        if token is None or (want and token != want):
            raise NotationError(
                f"expected {want or 'a step'} but found {token or 'the end'}", self.at()
            )
        self.i += 1
        return token

    def stack(self, close: str | None):
        layers = [self.seq(close)]
        while self.peek() == ",":
            self.take(",")
            layers.append(self.seq(close))
        return ("stack", layers) if len(layers) > 1 else layers[0]

    def seq(self, close: str | None):
        steps: list[list] = []
        while self.peek() not in (close, ",", None):
            if self.peek() == "_":
                if not steps:
                    raise NotationError("'_' has no step before it", self.at())
                self.take()
                steps[-1][1] += 1
                continue
            node, weight, copies = self.term(), Fraction(1), 1
            while self.peek() in ("*", "@", "!"):
                node, weight, copies = self.modifier(node, weight, copies)
            steps.extend([node, weight] for _ in range(copies))
        if close == ">":
            return ("alt", [s[0] for s in steps])
        return ("seq", steps)

    def modifier(self, node, weight: Fraction, copies: int):
        op = self.take()
        if op == "!" and not (self.peek() or "").replace(".", "").isdigit():
            return node, weight, copies + 1
        at, number = self.at(), self.take()
        try:
            value = Fraction(number)
        except ValueError:
            raise NotationError(f"'{op}' takes a number, not {number}", at) from None
        if value <= 0:
            raise NotationError(f"'{op}{number}' must be above zero", at)
        if op == "*":
            return ("fast", node, int(value)), weight, copies
        if op == "@":
            return node, value, copies
        return node, weight, int(value)

    def term(self):
        at = self.at()
        token = self.take()
        if token == "[":
            node = self.stack("]")
            self.take("]")
            return node
        if token == "<":
            node = self.seq(">")
            self.take(">")
            if not node[1]:
                raise NotationError("'<>' holds nothing to alternate", at)
            return node
        if token == "~":
            return ("rest",)
        if token in "]>,*!@_":
            raise NotationError(f"'{token}' cannot start a step", at)
        if token in DRUMS:
            self.drums.append(token)
        return ("atom", _pitch(token, at))


def _events(node, cycle: int, start: Fraction, span: Fraction, out: list) -> None:
    kind = node[0]
    if kind == "atom":
        out.append((start, span, node[1]))
    elif kind == "seq":
        total = sum(w for _, w in node[1]) or 1
        for child, weight in node[1]:
            _events(child, cycle, start, span * weight / total, out)
            start += span * weight / total
    elif kind == "stack":
        for child in node[1]:
            _events(child, cycle, start, span, out)
    elif kind == "alt":
        items = node[1]
        _events(items[cycle % len(items)], cycle // len(items), start, span, out)
    elif kind == "fast":
        _, child, n = node
        for i in range(n):
            _events(child, cycle * n + i, start + span * i / n, span / n, out)


def parse(text: str) -> _Mini:
    """A pattern's tree, refused where it does not parse."""
    parser = _Mini(text)
    parser.tree = parser.stack(None)
    if parser.peek() is not None:
        raise NotationError(f"'{parser.peek()}' is left over", parser.at())
    return parser


def bars(text: str, count: int, length: Fraction) -> list[list[tuple]]:
    """A pattern's notes over `count` bars, as (start, length, pitch) within each bar.

    `length` is the bar in quarter notes, and so are the starts and lengths.
    """
    tree = parse(text).tree
    out = []
    for bar in range(count):
        found: list = []
        _events(tree, bar, Fraction(0), length, found)
        out.append(sorted(found))
    return out


# ---------------------------------------------------------------- the source


def _typed(value: Any, kind: type) -> bool:
    if kind is float:
        return isinstance(value, int | float) and not isinstance(value, bool)
    return isinstance(value, kind)


def _strict(
    problems: _Problems, where: str, stated: Any, schema: dict, line: int | None
) -> dict:
    """One table's keys, typed and ranged; an unknown one is offered its nearest."""
    stated = stated if isinstance(stated, dict) else {}
    after = (line or 1) - 1
    out = {}
    for key, value in stated.items():
        at = problems.line(key, after) or line
        if key not in schema:
            near = difflib.get_close_matches(key, schema, n=1)
            problems.add(
                "music.unknown-key", at, f"{where} has no key {key!r}",
                f"did you mean {near[0]!r}?" if near
                else f"{where} takes {', '.join(schema)}",
            )
            continue
        kind = schema[key][0]
        if not _typed(value, kind):
            problems.add(
                "music.bad-value", at, f"{where} {key} is {value!r}",
                f"write it as a {'number' if kind is float else kind.__name__}",
            )
            continue
        low, high = _RANGES.get(key, (None, None))
        if low is not None and not low <= value <= high:
            problems.add(
                "music.bad-value", at, f"{where} {key} is {value}",
                f"write a {key} from {low} to {high}",
            )
            continue
        out[key] = value
    for key, (_, default) in schema.items():
        if key in out:
            continue
        if default is REQUIRED:
            if key not in stated:
                problems.add(
                    "music.missing", line, f"{where} has no {key}",
                    f"write {key} = … in {where}",
                )
            out[key] = None
        else:
            out[key] = list(default) if isinstance(default, list) else default
    return out


def compile_source(text: str, name: str = "score") -> tuple[dict | None, list[dict]]:
    """The note model a source compiles to, and every problem found on the way.

    The model is None whenever there is a problem: a half-compiled score is one a
    render would play wrong without saying so.
    """
    problems = _Problems(text)
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        found = re.search(r"line (\d+)", str(exc))
        problems.add(
            "music.unreadable", int(found.group(1)) if found else None,
            f"the source is not TOML: {exc}", "fix the syntax on that line",
        )
        return None, problems.found
    for table in raw:
        if table not in _TABLES:
            near = difflib.get_close_matches(table, _TABLES, n=1)
            problems.add(
                "music.unknown-key", problems.header(table),
                f"[{table}] is not a table a score has",
                f"did you mean [{near[0]}]?" if near
                else f"the tables are {', '.join(_TABLES)}",
            )
    music = _strict(problems, "[music]", raw.get("music"), _MUSIC,
                    problems.header("music"))
    meter = _meter(problems, music)
    sections = _sections(problems, raw.get("section", {}), music)
    patterns = _patterns(problems, raw.get("pattern", {}))
    tracks = [
        _strict(problems, f"track {n + 1}", t, _TRACK, problems.header("track", n))
        for n, t in enumerate(raw.get("track", []))
    ]
    if not tracks:
        problems.add("music.missing", None, "the score has no [[track]]",
                     "add a [[track]] with a name, an instrument and what it plays")
    if problems.found:
        return None, problems.found
    model = _model(problems, music, sections, patterns, tracks, meter, name)
    return (None if problems.found else model), problems.found


def _meter(problems: _Problems, music: dict) -> tuple[int, int]:
    meter = music["meter"] or [4, 4]
    if (
        len(meter) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) and v > 0
                   for v in meter)
        or meter[1] not in (1, 2, 4, 8, 16, 32)
    ):
        problems.add(
            "music.bad-value", problems.line("meter"), f"meter is {meter!r}",
            "write [beats, unit], such as [4, 4], [3, 4] or [6, 8]",
        )
        return 4, 4
    return meter[0], meter[1]


def _sections(problems: _Problems, stated: Any, music: dict) -> dict[str, int]:
    found = {}
    for name, table in (stated if isinstance(stated, dict) else {}).items():
        line = problems.header(f"section.{name}")
        count = table.get("bars") if isinstance(table, dict) else None
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            problems.add(
                "music.bad-value", line, f"section {name} has bars = {count!r}",
                "write bars = a whole number of at least one",
            )
            continue
        extra = sorted(set(table) - {"bars"})
        if extra:
            problems.add(
                "music.unknown-key", line, f"section {name} has {', '.join(extra)}",
                "a section takes bars only; what plays goes in each track's play",
            )
        found[name] = count
    form = music["form"] or []
    if music["form"] is not None and not form:
        problems.add(
            "music.missing", problems.line("form"), "the form is empty",
            'write form = ["A", "B"], the sections in the order they play',
        )
    for name in form:
        if name not in found:
            near = difflib.get_close_matches(str(name), found, n=1)
            problems.add(
                "music.unknown-section", problems.line("form"),
                f"the form plays section {name!r}, which no [section] declares",
                f"did you mean {near[0]!r}?" if near
                else f"declare [section.{name}] with its bars",
            )
    if music["loop_from"] and music["loop_from"] not in form:
        problems.add(
            "music.unknown-section", problems.line("loop_from"),
            f"loop_from is {music['loop_from']!r}, which the form never plays",
            f"name one of {', '.join(map(str, form))}",
        )
    return found


def _patterns(problems: _Problems, stated: Any) -> dict[str, tuple[str, _Mini]]:
    """Every pattern, parsed once: a pattern that does not parse is one problem."""
    found = {}
    after = (problems.header("pattern") or 1) - 1
    for name, text in (stated if isinstance(stated, dict) else {}).items():
        line = problems.line(name, after)
        if not isinstance(text, str):
            problems.add("music.bad-value", line, f"pattern {name} is {text!r}",
                         "write the pattern as a string of mini-notation")
            continue
        try:
            found[name] = (text, parse(text))
        except NotationError as exc:
            problems.add(
                "music.bad-pattern", (line or 0) + text[: exc.at].count("\n") or None,
                f"pattern {name}, character {exc.at + 1}: {exc}",
                "fix the step there; the notation is Strudel's mini-notation, one "
                "cycle per bar",
            )
    return found


def _model(problems: _Problems, music: dict, sections: dict, patterns: dict,
           tracks: list, meter: tuple[int, int], name: str) -> dict:
    per_bar = Fraction(meter[0] * 4, meter[1])  # quarter notes in one bar
    form = music["form"]
    spans, starts, tick = [], {}, 0
    for index, section in enumerate(form):
        end = tick + int(sections[section] * per_bar * TICKS)
        starts.setdefault(section, tick)
        spans.append({"id": f"{section}-{index + 1}", "label": section,
                      "startTick": tick, "endTick": end})
        tick = end
    names = [t["name"] for t in tracks]
    parts, notes = [], []
    for n, track in enumerate(tracks):
        line = problems.header("track", n)
        if not _NAME.fullmatch(track["name"]) or names.count(track["name"]) > 1:
            problems.add(
                "music.bad-value", problems.line("name", (line or 1) - 1) or line,
                f"track name {track['name']!r} is not a unique lower-case id",
                "name each track once, in lower case, such as lead or drums",
            )
            continue
        parts.append({"id": track["name"], "name": track["name"],
                      "role": "bass" if "bass" in track["name"] else "other"})
        notes += _track_notes(problems, track, form, sections, patterns, per_bar,
                              line, f"{name}/{track['name']}")
    head = starts[music["loop_from"] or form[0]]
    return {
        "formatVersion": FORMAT_VERSION,
        "metadata": {"title": music["title"],
                     **({"key": music["key"]} if music["key"] else {})},
        "timing": {
            "ticksPerQuarter": TICKS,
            "tempo": [{"tick": 0,
                       "microsecondsPerQuarter": round(60_000_000 / music["bpm"])}],
            "timeSignatures": [{"tick": 0, "numerator": meter[0],
                                "denominator": meter[1]}],
        },
        "parts": parts,
        "notes": sorted(notes, key=lambda x: (x["start"], x["part"], x["pitch"])),
        "sections": spans,
        "extensions": {EXTENSION: {
            "bpm": music["bpm"],
            "loop": {"startTick": head, "endTick": tick} if music["loop"] else None,
            "tracks": {
                t["name"]: {k: t[k] for k in ("instrument", "layer", "drums")}
                for t in tracks
            },
        }},
    }


def _track_notes(problems: _Problems, track: dict, form: list, sections: dict,
                 patterns: dict, per_bar: Fraction, line: int | None,
                 seed: str) -> list[dict]:
    after = (line or 1) - 1
    for section in track["play"]:
        if section not in sections:
            problems.add(
                "music.unknown-section", problems.line(section, after) or line,
                f"track {track['name']} plays in section {section!r}, which no "
                f"[section] declares",
                f"name one of {', '.join(sections)}",
            )
    wobble = _Wobble(zlib.crc32(seed.encode()))
    notes: list[dict] = []
    bar0 = 0
    for section in form:
        chosen = track["play"].get(section)
        if chosen is not None:
            at = problems.line(section, after) or line
            notes += _section_notes(problems, track, patterns, chosen,
                                    sections[section], bar0, per_bar, wobble, at)
        bar0 += sections[section]
    return _clamped(problems, track, notes, line)


def _section_notes(problems: _Problems, track: dict, patterns: dict, chosen: Any,
                   count: int, bar0: int, per_bar: Fraction, wobble: _Wobble,
                   line: int | None) -> list[dict]:
    if chosen not in patterns:
        near = difflib.get_close_matches(str(chosen), patterns, n=1)
        problems.add(
            "music.unknown-pattern", line,
            f"track {track['name']} plays pattern {chosen!r}, which [pattern] does "
            f"not hold",
            f"did you mean {near[0]!r}?" if near
            else f'add {chosen} = "…" under [pattern]',
        )
        return []
    text, parsed = patterns[chosen]
    if parsed.drums and not track["drums"]:
        problems.add(
            "music.bad-pattern", line,
            f"pattern {chosen} names drums ({', '.join(sorted(set(parsed.drums)))}) "
            f"and track {track['name']} is not a drum track",
            "set drums = true on the track, or give it a pattern of notes",
        )
        return []
    out = []
    for n, bar in enumerate(bars(text, count, per_bar)):
        for start, length, pitch in bar:
            if not 0 <= pitch <= 127:
                problems.add(
                    "music.out-of-range", line, f"pattern {chosen} plays pitch {pitch}",
                    "keep notes between c-1 (0) and g9 (127)",
                )
                return []
            at = (bar0 + n) * per_bar + start
            out.append({
                "pitch": pitch,
                "start": int(round(at * TICKS)),
                "duration": max(1, int(round(length * track["gate"] * TICKS))),
                "velocity": _velocity(track, at, per_bar, wobble),
                "part": track["name"],
            })
    return out


class _Wobble:
    """A seeded wobble, so the same source always compiles to the same velocities."""

    def __init__(self, seed: int):
        self.state = seed or 1

    def next(self) -> float:
        self.state = (1103515245 * self.state + 12345) % (1 << 31)
        return self.state / (1 << 31) * 2 - 1


def _velocity(track: dict, at: Fraction, per_bar: Fraction, wobble: _Wobble) -> int:
    """The track's level, its groove on the grid, and the wobble."""
    within = at % 1
    if within == 0:
        accent = 10 if at % per_bar == 0 else 4
    else:
        accent = 0 if within == Fraction(1, 2) else -12
    value = track["velocity"] + track["groove"] * accent
    value += track["wobble"] * wobble.next()
    return int(min(127, max(1, round(value))))


def _clamped(problems: _Problems, track: dict, notes: list[dict],
             line: int | None) -> list[dict]:
    """Same-pitch notes in one track may not overlap: the earlier is cut at the later.

    Two onsets of one pitch at one tick are one key struck twice, which MIDI cannot
    hold, so that is refused rather than cut.
    """
    notes.sort(key=lambda x: (x["pitch"], x["start"]))
    for a, b in zip(notes, notes[1:], strict=False):
        if a["pitch"] != b["pitch"]:
            continue
        if a["start"] == b["start"]:
            problems.add(
                "music.overlap", line,
                f"track {track['name']} strikes pitch {a['pitch']} twice at tick "
                f"{a['start']}",
                "remove the duplicate from the stack",
            )
            return []
        a["duration"] = min(a["duration"], b["start"] - a["start"])
    return notes


# ---------------------------------------------------------------- MIDI


def _vlq(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(out))


def _meta(kind: int, data: bytes) -> bytes:
    return bytes([0xFF, kind]) + _vlq(len(data)) + data


def _chunk(events: list[tuple[int, bytes]]) -> bytes:
    """One track: events in time, a note's release before a new strike on one tick."""
    body, now = b"", 0
    for tick, data in sorted(events, key=lambda e: (e[0], e[1][0] & 0xF0 != 0x80)):
        body += _vlq(tick - now) + data
        now = tick
    body += b"\x00\xff\x2f\x00"
    return b"MTrk" + len(body).to_bytes(4, "big") + body


def midi_bytes(model: dict) -> bytes:
    """A Standard MIDI File, format 1: a conductor track, then one track per part.

    A drum part plays on channel 10, and an instrument written `gm:<program>` sets its
    program; any other instrument is the renderer's business and plays as channel
    default in a DAW.
    """
    timing = model["timing"]
    signature = timing["timeSignatures"][0]
    tempo = timing["tempo"][0]["microsecondsPerQuarter"]
    conductor = [
        (0, _meta(0x03, model["metadata"]["title"].encode("utf-8"))),
        (0, _meta(0x51, tempo.to_bytes(3, "big"))),
        (0, _meta(0x58, bytes([signature["numerator"],
                               signature["denominator"].bit_length() - 1, 24, 8]))),
    ]
    chunks = [_chunk(conductor)]
    own = model.get("extensions", {}).get(EXTENSION, {}).get("tracks", {})
    channels = iter(c for c in range(16) if c != 9)
    for part in model["parts"]:
        settings = own.get(part["id"], {})
        channel = 9 if settings.get("drums") else next(channels, 15)
        events = [(0, _meta(0x03, part["name"].encode("utf-8")))]
        program = str(settings.get("instrument", ""))
        if channel != 9 and program.startswith("gm:") and program[3:].isdigit():
            events.append((0, bytes([0xC0 | channel, int(program[3:]) & 0x7F])))
        for note in model["notes"]:
            if note["part"] == part["id"]:
                end = note["start"] + note["duration"]
                events.append((note["start"], bytes([0x90 | channel, note["pitch"],
                                                     note["velocity"]])))
                events.append((end, bytes([0x80 | channel, note["pitch"], 0])))
        chunks.append(_chunk(events))
    header = b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big")
    header += len(chunks).to_bytes(2, "big")
    header += timing["ticksPerQuarter"].to_bytes(2, "big")
    return header + b"".join(chunks)


# ---------------------------------------------------------------- operations


def _score(source: str, root: str) -> tuple[Path, Path]:
    """The project root and the score's path inside it, refused outside or missing."""
    config = load(root)
    # A path setting's check, so a score is never read from outside the tree.
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError(
            "music.unreadable",
            f"there is no score at {source}",
            "name a *.music.toml relative to the project root",
        )
    return config.root, where


def summary(model: dict) -> dict:
    """What a caller checks a compiled score by: its length, its notes and its loop."""
    ext = model["extensions"][EXTENSION]
    end = max((s["endTick"] for s in model["sections"]), default=0)
    counts: dict[str, int] = {}
    for note in model["notes"]:
        counts[note["part"]] = counts.get(note["part"], 0) + 1
    return {
        "seconds": round(end / TICKS * 60 / ext["bpm"], 3),
        "notes": counts,
        "loop": ext["loop"],
    }


@operation("music.validate")
def validate(
    source: Annotated[str, Param("the *.music.toml, relative to the project")],
    root: Annotated[str, Param("the project the score belongs to")] = ".",
) -> dict:
    """Compile a score and answer every problem at once, each with its line and fix.

    Fix every problem named and call again until `valid` is true; a valid score
    answers its length in seconds, its notes per track and its loop in ticks.
    """
    base, where = _score(source, root)
    model, problems = compile_source(where.read_text(encoding="utf-8"), where.stem)
    answer: dict = {
        "source": where.relative_to(base).as_posix(),
        "valid": not problems,
        "problems": problems,
    }
    if model is not None:
        answer.update(summary(model))
    return answer


@operation("music.to_midi")
def to_midi(
    source: Annotated[str, Param("the *.music.toml, relative to the project")],
    out: Annotated[str, Param("where the .mid goes; beside the score if unset")] = None,
    root: Annotated[str, Param("the project the score belongs to")] = ".",
) -> dict:
    """Write a valid score as a Standard MIDI File a DAW opens, one track per part."""
    base, where = _score(source, root)
    model, problems = compile_source(where.read_text(encoding="utf-8"), where.stem)
    if model is None:
        first = problems[0]
        raise PolyweaveError(
            "music.invalid",
            f"{source} has {len(problems)} problem(s); the first, on line "
            f"{first['line']}: {first['message']}",
            f"call music.validate on {source} and fix what it names",
        )
    stem = where.name.removesuffix(".toml").removesuffix(".music")
    target = where.with_name(f"{stem}.mid")
    if out:
        target = load(root).path("paths.work", out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(midi_bytes(model))
    return {
        "midi": target.relative_to(base).as_posix(),
        "tracks": len(model["parts"]),
        **summary(model),
    }
