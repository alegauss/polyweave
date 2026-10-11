"""A timeline of what a reference video says happened, to split it at (§PW381).

A gameplay video has no markers, so an agent reading it stretch by stretch found "the
second wave starts here" by watching frames. The game's own signals already say it: a
score that jumps, a counter of humans that changes, a burst of explosions that floods
the screen, a sound when a wave begins.

`reference.events` reads three of them over the frames `reference.frames` wrote:

- **numbers** read off the regions of the frames' `[reference.<name>]` the call names
  (a score, a multiplier, a counter), each change an event, and every frame where the
  reading failed listed rather than guessed;
- **flashes**: frames where the play region's brightness, or the share of its pixels
  that changed since the last frame, stands far above the video's own run of frames;
- **onsets**: the soundtrack's strong onsets, the peaks of its spectral change, as
  polyweave measures its own sounds;
- **sections**: where the music changes section, the peaks of a novelty curve over the
  soundtrack's self-similarity (§PW405).

One `events.json` of all of them in seconds from the start, recorded, and a picture of
the timeline under its frames: thumbnails at a fixed step, each event's tick under the
thumbnail it falls in. Which event begins a wave stays the agent's reading.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import numpy as np

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .reference_objects import _manifest

#: How far above the video's own run a frame stands to be a flash: its median plus this
#: many times its median absolute deviation.
FLASH_SPREAD = 6.0

#: A pixel that moves by more than this share of full scale counts as changed.
CHANGED = 0.12

#: The rate the soundtrack is taken at for its onsets: a hop of 512 is 46 ms.
ONSET_RATE = 11025

#: How many times a number region is enlarged before it is read.
READ_SCALE = 3

#: Music sections are read a window of this many seconds at a time (§PW405).
SECTION_STEP = 0.5

#: How many windows each side of a moment the novelty kernel compares: two seconds, so a
#: drum fill is not a section and a new verse is.
SECTION_KERNEL = 4

#: The bands a window's energy is read in, log-spaced from SECTION_LOW hertz up.
SECTION_BANDS = 24
SECTION_LOW = 60.0

#: A window whose mean power is below this is silence.
SECTION_QUIET = 1e-6

#: A section's novelty is at least this share of the soundtrack's strongest, so a track
#: whose novelty is flat everywhere but one turn does not find a section in its noise.
SECTION_FLOOR = 0.25

#: The least novelty a section has at all, on a scale where one sound turning into a
#: wholly unlike one reads 1: a steady track's novelty is rounding noise, not a turn.
SECTION_LEAST = 0.05

#: How many thumbnails a timeline picture holds at most, and how many to a strip.
THUMBNAILS = 30
PER_STRIP = 10

#: The rows of the timeline picture, one a kind of event.
KINDS = ("number", "flash", "onset", "section")


def _robust_peaks(values: np.ndarray) -> list[int]:
    """The indices standing far above the run's own spread, each a local maximum."""
    if len(values) < 3:
        return []
    middle = float(np.median(values))
    spread = float(np.median(np.abs(values - middle))) or 1e-9
    bar = middle + FLASH_SPREAD * spread
    return [
        i for i in range(len(values))
        if values[i] > bar
        and (i == 0 or values[i] >= values[i - 1])
        and (i == len(values) - 1 or values[i] >= values[i + 1])
    ]


def flashes(frames: list, folder: Path, box: list | None) -> list[dict]:
    """Frames whose brightness or changed share spikes, each with what spiked."""
    from PIL import Image as Pil

    bright, moved, last = [], [], None
    for one in frames:
        with Pil.open(folder / one["file"]) as frame:
            grey = frame.convert("L")
            if box:
                grey = grey.crop(tuple(int(v) for v in box))
            pixels = np.asarray(grey.resize((160, 90)), dtype=np.float64) / 255.0
        bright.append(float(pixels.mean()))
        moved.append(0.0 if last is None
                     else float((np.abs(pixels - last) > CHANGED).mean()))
        last = pixels
    out = []
    peaks = {name: _robust_peaks(np.array(values))
             for name, values in (("bright", bright), ("changed", moved))}
    lit = {i for found in peaks.values() for i in found}
    for name, values in (("bright", bright), ("changed", moved)):
        for i in peaks[name]:
            # The frame after a flash changes as much going dark again: one flash, once.
            if i - 1 in lit:
                continue
            out.append({"at": frames[i]["ms"] / 1000, "kind": "flash", "what": name,
                        "value": round(values[i], 4)})
    return sorted(out, key=lambda e: e["at"])


def soundtrack(video: Path) -> tuple[np.ndarray | None, str]:
    """The video's soundtrack as mono floats at ONSET_RATE, or None and why not."""
    if shutil.which("ffmpeg") is None:
        return None, "there is no ffmpeg on PATH to read the soundtrack"
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-f", "s16le", "-ac", "1",
         "-ar", str(ONSET_RATE), "-"],
        capture_output=True, check=False,
    )
    if decoded.returncode or not decoded.stdout:
        return None, "the video has no soundtrack ffmpeg could read"
    return np.frombuffer(decoded.stdout, np.int16).astype(np.float64) / 32768.0, ""


def onsets(mono: np.ndarray, start: float = 0.0) -> tuple[list[dict], str]:
    """The soundtrack's strong onsets, or none and why where there are none to find."""
    from .sound import _HOP, _SIZE, _flux, _onset_level

    flux = _flux(mono)
    if len(flux) < 3:
        return [], "the soundtrack is too short to have onsets"
    bar = _onset_level(flux)
    inner = range(1, len(flux) - 1)
    found = [i for i in inner
             if flux[i] >= bar and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    # Flux i compares window i + 1 with window i, and a sharp onset first shows in the
    # newest hop of window i + 1: its end, less half a hop, is when it struck.
    return [{"at": round(start + ((i + 1) * _HOP + _SIZE - _HOP / 2) / ONSET_RATE, 3),
             "kind": "onset", "value": round(float(flux[i]), 2)} for i in found], ""


def _features(mono: np.ndarray, rate: int) -> np.ndarray:
    """Each SECTION_STEP of sound as its log energy in SECTION_BANDS bands, and one more
    for quiet, unit length, so two windows alike in timbre and pitch read alike."""
    size = int(rate * SECTION_STEP)
    count = len(mono) // size
    if count == 0:
        return np.zeros((0, SECTION_BANDS + 1))
    windows = mono[:count * size].reshape(count, size) * np.hanning(size)
    power = np.abs(np.fft.rfft(windows, axis=1)) ** 2
    hertz = np.fft.rfftfreq(size, 1 / rate)
    edges = np.geomspace(SECTION_LOW, rate / 2, SECTION_BANDS + 1)
    bands = np.stack([power[:, (hertz >= lo) & (hertz < hi)].sum(axis=1)
                      for lo, hi in zip(edges[:-1], edges[1:], strict=True)], axis=1)
    loud = np.log1p(bands / size)
    # A window with next to nothing in it is silence, and every silence is alike.
    quiet = (windows ** 2).mean(axis=1) < SECTION_QUIET
    loud[quiet] = 0.0
    feature = np.concatenate([loud, quiet[:, None].astype(np.float64)], axis=1)
    norm = np.linalg.norm(feature, axis=1, keepdims=True)
    return feature / np.where(norm > 0, norm, 1.0)


def sections(mono: np.ndarray, rate: int = ONSET_RATE,
             start: float = 0.0) -> list[dict]:
    """Where the music changes section: the peaks of a checkerboard kernel's novelty
    over the soundtrack's self-similarity, above the curve's own spread (§PW405)."""
    feature = _features(mono, rate)
    half = SECTION_KERNEL
    if len(feature) < 2 * half + 1:
        return []
    alike = feature @ feature.T
    sign = np.concatenate([-np.ones(half), np.ones(half)])
    kernel = np.outer(sign, sign)  # alike within each side counts, across it subtracts
    novelty = np.zeros(len(feature))
    for t in range(half, len(feature) - half + 1):
        novelty[t] = float((kernel * alike[t - half:t + half, t - half:t + half]).sum())
    # Within each side alike counts 2·half², across the turn as much again unlike: two
    # wholly unlike halves read 1.
    novelty = np.maximum(novelty, 0.0) / (2 * half * half) / 2
    middle = float(np.median(novelty))
    spread = float(np.median(np.abs(novelty - middle)))
    bar = max(middle + FLASH_SPREAD * spread, SECTION_FLOOR * float(novelty.max()),
              SECTION_LEAST)
    peaks = [t for t in range(1, len(novelty) - 1)
             if novelty[t] > bar and novelty[t] >= novelty[t - 1]
             and novelty[t] >= novelty[t + 1]]
    kept: list[int] = []
    for t in sorted(peaks, key=lambda i: -novelty[i]):
        if all(abs(t - other) >= half for other in kept):
            kept.append(t)
    return [{"at": round(start + t * SECTION_STEP, 3), "kind": "section",
             "value": round(float(novelty[t]), 3)} for t in sorted(kept)]


_DIGITS = re.compile(r"\d[\d,.]*")


def numbers(frames: list, folder: Path, regions: dict, engine: str | None,
            language: str = "eng") -> tuple[list[dict], dict]:
    """Each named region's number per frame: its changes as events, and the frames
    where it could not be read."""
    from PIL import Image as Pil

    events, failed = [], {name: [] for name in regions}
    if not engine:
        return [], {name: "no OCR engine to read it" for name in regions}
    last: dict[str, int] = {}
    for one in frames:
        with Pil.open(folder / one["file"]) as frame:
            image = frame.convert("L")
        at = one["ms"] / 1000
        for name, box in regions.items():
            part = image.crop(tuple(int(v) for v in box))
            part = part.resize((part.width * READ_SCALE, part.height * READ_SCALE))
            value = _read(engine, part, language)
            if value is None:
                failed[name].append(at)
                continue
            if name in last and value != last[name]:
                events.append({"at": at, "kind": "number", "what": name,
                               "from": last[name], "to": value})
            last[name] = value
    return events, failed


def _read(engine: str, part, language: str) -> int | None:
    import tempfile

    with tempfile.TemporaryDirectory() as scratch:
        where = Path(scratch) / "region.png"
        part.save(where)
        done = subprocess.run(  # noqa: S603 - the engine is the project's own binary
            [engine, str(where), "stdout", "-l", language, "--psm", "7"],
            capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
        )
    found = _DIGITS.search(done.stdout or "") if done.returncode == 0 else None
    if not found:
        return None
    digits = re.sub(r"\D", "", found.group(0))
    return int(digits) if digits else None


def thumbnailed(frames: list) -> list[dict]:
    """The frames the timeline shows, at a fixed step along the video."""
    step = max(1, -(-len(frames) // THUMBNAILS))
    return frames[::step]


def placed(events: list[dict], starts: list[float]) -> list[tuple[int, float]]:
    """Each event's thumbnail, the last one starting at or before it, and how far into
    that thumbnail's stretch it falls, from 0 to 1 (§PW405)."""
    out = []
    for one in events:
        at = one["at"]
        index = max(0, int(np.searchsorted(starts, at, side="right")) - 1)
        begin = starts[index]
        # The last thumbnail's stretch is as long as the one before it.
        step = starts[-1] - starts[-2] if len(starts) > 1 else 1.0
        end = starts[index + 1] if index + 1 < len(starts) else begin + step
        out.append((index, min(1.0, max(0.0, (at - begin) / max(end - begin, 1e-9)))))
    return out


def drawn(events: list[dict], frames: list, folder: Path, target: Path) -> Path:
    """The timeline under its frames: thumbnails at a fixed step, and under each, a row
    a kind with a tick where each event falls in its stretch, a number's new value
    beside it, so what each tick was is read without opening the frames (§PW405)."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    shown = thumbnailed(frames)
    tile, tall, row, left = 160, 90, 20, 70
    strips = max(1, -(-len(shown) // PER_STRIP))
    strip = tall + row * len(KINDS) + 24
    picture = Pil.new("RGB", (left + tile * PER_STRIP, strip * strips), (20, 20, 20))
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default(size=12)
    for n, one in enumerate(shown):
        x, y = left + (n % PER_STRIP) * tile, (n // PER_STRIP) * strip
        with Pil.open(folder / one["file"]) as frame:
            picture.paste(frame.convert("RGB").resize((tile - 2, tall)), (x + 1, y))
        # On a dark backing, so a white frame's second still reads.
        draw.rectangle((x + 1, y, x + 50, y + 15), fill=(0, 0, 0))
        draw.text((x + 3, y + 2), f"{one['ms'] / 1000:.2f}s", fill=(255, 255, 255),
                  font=font)
    for s in range(strips):
        for k, kind in enumerate(KINDS):
            draw.text((4, s * strip + tall + k * row + 3), kind, fill=(200, 200, 200),
                      font=font)
    starts = [one["ms"] / 1000 for one in shown]
    for one, (index, share) in zip(events, placed(events, starts), strict=True):
        x = left + (index % PER_STRIP) * tile + share * (tile - 1)
        y = (index // PER_STRIP) * strip + tall + KINDS.index(one["kind"]) * row
        draw.line((x, y + 2, x, y + row - 2), fill=(255, 220, 90), width=2)
        if one["kind"] == "number":
            draw.text((x + 3, y + 3), str(one["to"]), fill=(255, 220, 90), font=font)
    picture.save(target)
    return target


@operation("reference.events")
def events(
    frames: Annotated[
        str, Param("the folder reference.frames wrote, or its frames.json")
    ],
    *,
    reference: Annotated[
        str, Param("the [reference.<name>] with the regions; the only one if empty")
    ] = "",
    numbers_in: Annotated[
        list, Param("the regions holding a number to read: score, a counter")
    ] = (),
    play: Annotated[
        str, Param("the region flashes are looked for in; the whole frame if empty")
    ] = "",
    sound: Annotated[
        bool, Param("read the soundtrack's onsets and music sections too")
    ] = True,
    root: Annotated[str, Param("the project the frames are under")] = ".",
) -> dict:
    """A timeline of a reference video's events, to split it into stretches at.

    Numbers read off the named regions (each change an event, each unread frame
    listed), flashes where the play region's brightness or changed share spikes, the
    soundtrack's strong onsets and where its music changes section, in seconds from
    the start. events.json and the timeline drawn under its frames land beside them,
    recorded. Which event begins a wave stays the agent's reading.
    """
    config = load(root)
    here = config.root
    manifest, listed = _manifest(frames, here)
    folder = manifest.parent
    shown = listed.get("frames", [])
    regions: dict = {}
    if reference or numbers_in or play:
        _, declared = config.reference(reference or None)
        regions = declared["regions"]
    wanted = list(numbers_in)
    unknown = [r for r in [*wanted, *([play] if play else [])] if r not in regions]
    if unknown:
        raise PolyweaveError(
            "capture.unknown-region",
            f"{unknown[0]!r} is not a region the reference declares",
            f"name one of {', '.join(sorted(regions)) or 'its regions'}",
            given=unknown[0], allowed=sorted(regions),
        )
    found: list[dict] = []
    engine = shutil.which(str(config.path("paths.tesseract")))
    read, unread = numbers(shown, folder, {r: regions[r] for r in wanted}, engine)
    found += read
    found += flashes(shown, folder, regions.get(play) if play else None)
    heard, why = [], "not asked for"
    if sound:
        from .reference_register import video_of

        video = Path(str(listed.get("video", "")))
        if video.is_file():
            # The soundtrack is the registered video's, never a file swapped in since.
            video, _ = video_of(str(listed.get("reference") or video), here)
        mono, why = soundtrack(video) if video.is_file() else (
            None, "the video frames.json names is not there")
        if mono is not None:
            heard, why = onsets(mono)
            heard += sections(mono)
    found += heard
    found.sort(key=lambda e: (e["at"], e["kind"]))
    length = shown[-1]["ms"] / 1000 if shown else 0.0
    if heard:
        length = max(length, max(e["at"] for e in heard))
    picture = drawn(found, shown, folder, folder / "events.png")
    written = {"frames": provenance.relative(manifest, here), "length": length,
               "events": found, "unread": unread, "sound": why or "read"}
    target = folder / "events.json"
    target.write_text(json.dumps(written, indent=1) + "\n", encoding="utf-8",
                      newline="\n")
    used = [*wanted, *([play] if play else [])]
    provenance.write(provenance.build(
        "capture", target, engine={"name": "reference.events"},
        inputs=[provenance.source("frames", manifest, root=here)],
        params={"numbers": wanted, "play": play, "sound": bool(sound),
                "regions": {r: regions[r] for r in used}},
        root=here,
    ), here)
    count = {kind: sum(e["kind"] == kind for e in found) for kind in KINDS}
    return {
        "events": provenance.relative(target, here),
        "timeline": provenance.relative(picture, here),
        "counted": count,
        "unread": {k: len(v) if isinstance(v, list) else v
                   for k, v in unread.items()},
        "sound": why or "read",
        "says": f"{count['number']} number changes, {count['flash']} flashes, "
        f"{count['onset']} onsets and {count['section']} music sections over "
        f"{length:.1f} s; split at them and read each stretch",
    }
