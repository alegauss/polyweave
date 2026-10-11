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
  polyweave measures its own sounds.

One `events.json` of all of them in seconds from the start, recorded, and a picture of
the timeline, a row a kind. Which event begins a wave stays the agent's reading.
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


def onsets(video: Path, start: float = 0.0) -> tuple[list[dict], str]:
    """The soundtrack's strong onsets, or none and why where it cannot be read."""
    from .sound import _HOP, _SIZE, _flux, _onset_level

    if shutil.which("ffmpeg") is None:
        return [], "there is no ffmpeg on PATH to read the soundtrack"
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-f", "s16le", "-ac", "1",
         "-ar", str(ONSET_RATE), "-"],
        capture_output=True, check=False,
    )
    if decoded.returncode or not decoded.stdout:
        return [], "the video has no soundtrack ffmpeg could read"
    mono = np.frombuffer(decoded.stdout, np.int16).astype(np.float64) / 32768.0
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


def drawn(events: list[dict], length: float, target: Path) -> Path:
    """The timeline as a picture: a row a kind, a tick at every event's second."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    kinds = ["number", "flash", "onset"]
    wide, row, left = 1600, 40, 80
    picture = Pil.new("RGB", (wide, row * (len(kinds) + 1)), (20, 20, 20))
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default(size=14)
    span = max(length, 1e-6)
    for i, kind in enumerate(kinds):
        y = row * i + row // 2
        draw.text((6, y - 8), kind, fill=(220, 220, 220), font=font)
        for one in events:
            if one["kind"] == kind:
                x = left + (wide - left - 10) * one["at"] / span
                draw.line((x, y - 12, x, y + 12), fill=(255, 220, 90), width=2)
    y = row * len(kinds) + 8
    for second in range(0, int(span) + 1, max(1, int(span) // 10 or 1)):
        x = left + (wide - left - 10) * second / span
        draw.line((x, y, x, y + 6), fill=(160, 160, 160))
        draw.text((x + 2, y + 6), f"{second}s", fill=(160, 160, 160), font=font)
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
    sound: Annotated[bool, Param("read the soundtrack's onsets too")] = True,
    root: Annotated[str, Param("the project the frames are under")] = ".",
) -> dict:
    """A timeline of a reference video's events, to split it into stretches at.

    Numbers read off the named regions (each change an event, each unread frame
    listed), flashes where the play region's brightness or changed share spikes, and
    the soundtrack's strong onsets, in seconds from the start. events.json and a
    picture of the timeline land beside the frames, recorded. Which event begins a
    wave stays the agent's reading.
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
        video = Path(str(listed.get("video", "")))
        heard, why = onsets(video) if video.is_file() else (
            [], "the video frames.json names is not there")
    found += heard
    found.sort(key=lambda e: (e["at"], e["kind"]))
    length = shown[-1]["ms"] / 1000 if shown else 0.0
    if heard:
        length = max(length, heard[-1]["at"])
    picture = drawn(found, length, folder / "events.png")
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
    count = {kind: sum(e["kind"] == kind for e in found)
             for kind in ("number", "flash", "onset")}
    return {
        "events": provenance.relative(target, here),
        "timeline": provenance.relative(picture, here),
        "counted": count,
        "unread": {k: len(v) if isinstance(v, list) else v
                   for k, v in unread.items()},
        "sound": why or "read",
        "says": f"{count['number']} number changes, {count['flash']} flashes and "
        f"{count['onset']} onsets over {length:.1f} s; split at them and read each "
        "stretch",
    }
