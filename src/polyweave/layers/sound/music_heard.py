"""A recording drafted as a `*.music.toml`, heard into MIDI first (§PW559).

Spinhold's intro was bought as a recording and had to join the scores the game edits.
The project did it by hand: Demucs for stems, basic-pitch per stem in a scratch
environment, then the score typed in off the MIDI. `music.from_midi` kept the last
step; this keeps the first two, and hands what it heard to the same drafter.

What is heard, and how, is a draft's reading and says so:

- the stems are `sound.stems`' four (drums, bass, other, vocals), or with
  `split = "none"` the whole mix is one part and no drum is read;
- a pitched stem is read off its spectrum: each frame's pitch is the one whose
  harmonics hold the most (harmonic summation), that pitch's harmonics are taken out
  and the next is looked for, up to the voices that stem plays (a bass one, the other
  stem three); a pitch held over frames is a note, and one that swells again is struck
  again;
- the drums stem is read as onsets, each a kick, a snare or a hat by where its energy
  sits;
- the tempo is `sound.loop`'s, searched over the mix, unless `bpm` says it; the beats
  fall where most of what was heard was struck, and bar one starts on the first of
  them, so a pickup lands in the bar before.

The hearing is numpy's and no model's: basic-pitch, which the project used, does not
install on Python 3.13, and an optional dependency nobody can install is no route.

The MIDI it heard is written beside the score, so a draft at another grid is
`music.from_midi` on it and not the separation again. The timbres will differ from
the original's, so the answer ends in the two calls that lay the draft beside it.
"""

from __future__ import annotations

import math
from typing import Annotated

import numpy as np

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.sound import music_draft, sound_loop, sound_stems
from polyweave.layers.sound.music import DRUMS, validate

RATE = sound_loop.RATE
#: Ticks a quarter in the MIDI written: fine enough that the drafter does the rounding.
TPQ = 480
#: The analysis window and its hop. 8192 samples tell a bass's semitones apart by their
#: upper harmonics; the hop is 23 ms, a fifth of a sixteenth at 120 bpm.
SIZE, HOP = 8192, 1024
#: Harmonics a pitch is heard by, each weighed this much less than the one below.
HARMONICS, FALL = 5, 0.8
#: A frame is heard while its loudest pitch is this share of the stem's loudest.
FLOOR = 0.1
#: A further voice in a frame is heard at this share of the frame's first.
BESIDE = 0.5
#: Frames a note lasts at least; a pitch that swells by this much again is struck again.
LEAST_FRAMES = 3
SWELL = 1.25
#: A note starts on its first frame at this share of its own peak.
ONSET = 0.5

#: Per stem: the voices it plays at once, its range in MIDI pitches, the General MIDI
#: program (from zero) its track is drafted on.
PARTS = {
    "bass": (1, 28, 60, 33),
    "other": (3, 36, 96, 0),
    "vocals": (1, 48, 84, 53),
    "mix": (4, 28, 96, 0),
}
#: A drum hit is a kick below this, a hat above the other, a snare between.
KICK_HZ, HAT_HZ = 150.0, 5000.0
DRUM_CHANNEL = 9


def _mono(frames: np.ndarray) -> np.ndarray:
    return frames.mean(axis=1) / 32768.0


def _magnitudes(mono: np.ndarray) -> np.ndarray:
    # Half a window of silence each side, so the first frame is centred on time zero.
    mono = np.pad(mono, (SIZE // 2, SIZE // 2))
    window = np.hanning(SIZE)
    starts = np.arange(0, len(mono) - SIZE + 1, HOP)
    frames = np.stack([mono[s: s + SIZE] * window for s in starts])
    return np.sqrt(np.abs(np.fft.rfft(frames, axis=1)))


def _harmonic_bins(low: int, high: int) -> tuple[np.ndarray, np.ndarray]:
    """Each pitch's harmonics as fractional bins, and their weights."""
    pitches = np.arange(low, high + 1)
    hz = 440.0 * 2 ** ((pitches - 69) / 12)
    bins = hz[:, None] * np.arange(1, HARMONICS + 1)[None, :] * SIZE / RATE
    return bins, FALL ** np.arange(HARMONICS)


def _salience(mags: np.ndarray, bins: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Frames by pitches: what each pitch's harmonics hold, read between bins."""
    top = mags.shape[1] - 1
    below = np.clip(np.floor(bins).astype(int), 0, top)
    above = np.clip(below + 1, 0, top)
    share = bins - np.floor(bins)
    heard = mags[:, below] * (1 - share) + mags[:, above] * share
    heard[:, bins >= top] = 0.0
    return (heard * weights).sum(axis=2)


def transcribe(frames: np.ndarray, part: str) -> list[tuple[float, float, int, int]]:
    """A pitched stem's notes, (start s, end s, pitch, velocity)."""
    voices, low, high, _ = PARTS[part]
    mags = _magnitudes(_mono(frames))
    bins, weights = _harmonic_bins(low, high)
    salience = _salience(mags, bins, weights)
    loudest = float(salience.max()) if salience.size else 0.0
    heard = np.zeros_like(salience)
    if loudest <= 0:
        return []
    rows = np.arange(len(mags))
    first = None
    for _ in range(voices):
        best = salience.argmax(axis=1)
        value = salience[rows, best]
        first = value if first is None else first
        keep = (value >= FLOOR * loudest) & (value >= BESIDE * first)
        heard[rows[keep], best[keep]] = value[keep]
        # Its harmonics out of the spectrum, so the next voice is a pitch of its own.
        for h in range(HARMONICS):
            centre = np.floor(bins[best, h]).astype(int)
            for step in (-1, 0, 1, 2):
                column = np.clip(centre + step, 0, mags.shape[1] - 1)
                mags[rows[keep], column[keep]] = 0.0
        salience = _salience(mags, bins, weights)
    notes = []
    for index in range(heard.shape[1]):
        notes += _notes(heard[:, index], low + index, loudest)
    return sorted(notes)


def _notes(level: np.ndarray, pitch: int, loudest: float) -> list:
    found = []
    start = None
    for i in range(len(level) + 1):
        on = i < len(level) and level[i] > 0
        struck = (on and start is not None and i - start > LEAST_FRAMES
                  and level[i] > SWELL * level[i - 1])
        if start is not None and (not on or struck):
            peak = float(level[start:i].max())
            # The window reaches a note before it sounds: it starts where it is
            # half as loud as it gets, not where its first edge was caught.
            begin = start + int(np.argmax(level[start:i] >= ONSET * peak))
            if i - begin >= LEAST_FRAMES:
                found.append((_at(begin), _at(i), pitch,
                              int(40 + 70 * min(1.0, peak / loudest))))
            start = None
        if on and start is None:
            start = i
    return found


def _at(frame: int) -> float:
    """The time a frame stands for: its window's centre."""
    return frame * HOP / RATE


def drums(frames: np.ndarray) -> list[tuple[float, float, int, int]]:
    """The drums stem's hits, (start s, end s, drum, velocity)."""
    hop = 256
    # A window of silence first, so a hit on the very first sample still rises.
    mono = np.pad(_mono(frames), (2048, 0))
    if len(mono) < 4096:
        return []
    # The low band's own rise beside the whole spectrum's: a kick is a few bins, and
    # summed with the rest it is lost under the hats.
    change = np.maximum(np.diff(sound_loop._spectra(mono, hop=hop), axis=0), 0.0)
    flux = np.zeros(len(change))
    for band in (change, change[:, : int(KICK_HZ * 2048 / RATE) + 1]):
        summed = band.sum(axis=1)
        flux = np.maximum(flux, summed / max(float(summed.max()), 1e-12))
    rise = np.maximum(flux - np.convolve(flux, np.ones(32) / 32, "same"), 0.0)
    if not rise.size or rise.max() <= 0:
        return []
    near = 8
    hits = []
    for i in np.flatnonzero(rise >= 0.2 * rise.max()):
        if rise[i] < rise[max(0, i - near): i + near + 1].max():
            continue
        at = ((i + 1) * hop + 1024 - 2048) / RATE
        if hits and at - hits[-1][0] < 0.04:
            continue
        piece = mono[max(0, int((at - 0.005) * RATE) + 2048):
                     int((at + 0.05) * RATE) + 2048]
        if len(piece) < 64:
            continue
        power = np.abs(np.fft.rfft(piece * np.hanning(len(piece)))) ** 2
        hz = np.fft.rfftfreq(len(piece), 1 / RATE)
        whole = float(power.sum()) or 1.0
        low, high = power[hz < KICK_HZ].sum() / whole, power[hz > HAT_HZ].sum() / whole
        drum = "sd"
        if low >= 0.5:
            drum = "bd"
        elif high >= 0.4:
            drum = "hh"
        hits.append((at, at + 0.1, DRUMS[drum], int(40 + 70 * rise[i] / rise.max())))
    return hits


def _vlq(n: int) -> bytes:
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def smf(parts: list[tuple[str, int, int, list]], beat: float) -> bytes:
    """A format 1 MIDI file: one track per (name, channel, program, notes in ticks)."""
    tempo = round(beat * 1_000_000)

    def chunk(events: list[tuple[int, int, bytes]]) -> bytes:
        body, now = b"", 0
        for tick, _, data in sorted(events, key=lambda e: (e[0], e[1])):
            body += _vlq(tick - now) + data
            now = tick
        body += b"\x00\xff\x2f\x00"
        return b"MTrk" + len(body).to_bytes(4, "big") + body

    tracks = [chunk([(0, 0, b"\xff\x51\x03" + tempo.to_bytes(3, "big")),
                     (0, 0, b"\xff\x58\x04\x04\x02\x18\x08")])]
    for name, channel, program, notes in parts:
        word = name.encode()
        events = [(0, 0, b"\xff\x03" + _vlq(len(word)) + word)]
        if channel != DRUM_CHANNEL:
            events.append((0, 0, bytes([0xC0 | channel, program])))
        for start, end, pitch, velocity in notes:
            events.append((start, 2, bytes([0x90 | channel, pitch, velocity])))
            events.append((end, 1, bytes([0x80 | channel, pitch, 0])))
        tracks.append(chunk(events))
    head = (b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big")
            + len(tracks).to_bytes(2, "big") + TPQ.to_bytes(2, "big"))
    return head + b"".join(tracks)


def _first_beat(notes: list, beat: float) -> float:
    """Where the beats fall, in [0, beat): the phase most of what was struck sits on.

    Read off the notes heard, not off the mix's onset curve, which leads a soft attack
    by tens of milliseconds and puts every note a step early.
    """
    starts = np.array([n[0] for n in notes])
    weight = np.array([n[3] for n in notes], dtype=float)
    best, phase = -1.0, 0.0
    for candidate in np.linspace(0.0, beat, 96, endpoint=False):
        off = (starts - candidate + beat / 2) % beat - beat / 2
        score = float((weight * np.exp(-((off / (beat / 8)) ** 2))).sum())
        if score > best:
            best, phase = score, float(candidate)
    return phase


def _ticks(notes: list, offset: float, beat: float) -> list:
    out = []
    for start, end, pitch, velocity in notes:
        # A note a hair ahead of the first beat is on it (see `offset`), not before it.
        a = max(0, round((start - offset) / beat * TPQ))
        b = max(a + 1, round((end - offset) / beat * TPQ))
        out.append((a, b, pitch, velocity))
    return out


def _hear(sources: dict, mix: np.ndarray, stems: bool) -> tuple[dict, list]:
    """Each stem's notes or hits, and the stems nothing was heard in."""
    heard, silent = {}, []
    for name, played in sources.items():
        if stems and not sound_stems._spans(played, mix):
            silent.append(name)
            continue
        notes = drums(played) if name == "drums" else transcribe(played, name)
        if notes:
            heard[name] = notes
        else:
            silent.append(name)
    return heard, silent


def _parts(heard: dict, beat: float) -> list:
    """The MIDI tracks, bar one on the first beat; no pitched stem on channel 10."""
    every = [n for notes in heard.values() for n in notes]
    first = _first_beat(every, beat)
    earliest = min(n[0] for n in every)
    # A note a hair ahead of the first beat is on it, not a pickup a beat before.
    offset = first - beat * math.ceil(max(0.0, first - earliest - beat / 8) / beat)
    parts, channel = [], 0
    for name, notes in heard.items():
        if name == "drums":
            parts.append(("drums", DRUM_CHANNEL, 0, _ticks(notes, offset, beat)))
            continue
        parts.append((name, channel, PARTS[name][3], _ticks(notes, offset, beat)))
        channel += 2 if channel + 1 == DRUM_CHANNEL else 1
    return parts


@operation("music.from_audio")
def from_audio(
    track: Annotated[str, Param("the recording, relative to the project")],
    out: Annotated[str, Param("the *.music.toml to write; beside the track if unset")
                   ] = None,
    split: Annotated[
        str, Param("four: hear drums, bass, other and vocals apart (Demucs); none: "
                   "the mix as one part, no drums", choices=("four", "none"))
    ] = "four",
    bpm: Annotated[float, Param("the tempo if known; found from the mix if 0")] = 0.0,
    grid: Annotated[int, Param("steps a quarter note the notes are quantised to")] = 4,
    phrase: Annotated[int, Param("bars a section is read in, to find repeats")] = 4,
    replace: Annotated[bool, Param("write over a score already there")] = False,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Draft an editable score from a recording: stems heard as notes, then drafted.

    Writes the score and the MIDI it heard beside it; answers music.validate's result,
    how much of each track sat on the grid, and the music.render and sound.sitting
    calls that lay the draft beside the original for a person.
    """
    config = load(root)
    here = config.root
    source = config.path("paths.work", track)
    if not source.is_file():
        raise PolyweaveError("spec.unreadable-sound", f"there is no track at {track}",
                             "name the recording as a path under the project")
    stem = source.name.rsplit(".", 1)[0]
    target = config.path("paths.work", out) if out else source.with_name(
        f"{stem}.music.toml")
    if target.exists() and not replace:
        raise PolyweaveError(
            "music.draft-exists", f"{target.relative_to(here).as_posix()} is already "
            "there, and a draft would write over a score someone edited",
            "pass out, another path, or replace = true")
    if grid < 1 or phrase < 1 or bpm < 0:
        raise PolyweaveError("music.bad-value", "grid and phrase count from one, and "
                             "bpm is 0 or a tempo",
                             "pass grid = 4 for sixteenths and phrase = 4 bars")
    frames = sound_loop._decode(source)
    if split == "four":
        sources, engine = sound_stems._separate(frames)
        separator = f"{engine['name']} {engine['version']} {engine['model']}"
    else:
        sources, separator = {"mix": frames}, None
    beat = 60.0 / bpm if bpm else sound_loop._beat_grid(_mono(frames) * 32768.0)[0]
    heard, silent = _hear(sources, frames, split == "four")
    if not heard:
        raise PolyweaveError(
            "music.nothing-heard", f"no note or hit was heard in {track}",
            "pass the recording itself, with music in it")
    data = smf(_parts(heard, beat), beat)
    midi = target.with_name(target.name.removesuffix(".toml").removesuffix(".music")
                            + ".heard.mid")
    try:
        text, found = music_draft.draft(data, stem, grid, phrase,
                                        reference=source.relative_to(here).as_posix())
    except ValueError as exc:
        raise PolyweaveError("music.nothing-heard",
                             f"what was heard in {track} drafts to nothing: {exc}",
                             "pass the recording itself, with music in it") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    midi.write_bytes(data)
    target.write_text(text, encoding="utf-8")
    where = target.relative_to(here).as_posix()
    checked = validate(where, root)
    rendered = where.removesuffix(".toml").removesuffix(".music")
    return {
        "score": where, "track": track, "midi": midi.relative_to(here).as_posix(),
        "split": split, "separator": separator, "bpm_given": bool(bpm),
        **found, "silent": silent,
        "valid": checked["valid"], "problems": checked["problems"],
        "next": [
            {"operation": "music.render",
             "args": {"source": where, "formats": ["ogg"], "root": root}},
            {"operation": "sound.sitting",
             "args": {"members": [{"name": stem, "new": f"{rendered}.ogg",
                                   "old": track}],
                      "out": f"review/{stem}-draft", "root": root,
                      "about": "a draft heard off the recording: the notes, form and "
                               "tempo are what to judge, the timbres will differ"}},
        ],
        "says": f"{len(found['tracks'])} track(s) over {found['bars']} bars at "
                f"{found['bpm']} bpm; render it and hear it beside {track} with the "
                "two calls in next before keeping it",
    }
