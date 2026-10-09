"""Flashes counted in a captured run, against the guidance on photosensitivity (§PW354).

WCAG 2.3.1, and the Harding test broadcasters use, limit a sequence to three general
flashes and three red flashes in any one second. A flash is a pair of opposing changes:

- **general**: relative luminance (linear sRGB, 0.2126 R + 0.7152 G + 0.0722 B) moves
  by at least `luminance` (0.1 of the maximum), the darker state below `dark` (0.8);
- **red**: a saturated red, R / (R + G + B) at least 0.8, whose (R - G - B) * 320 moves
  by more than `red` (20), read as zero where the colour is not a saturated red;

over a combined area of at least `area` of the screen. The guidance's area is a quarter
of any 10 degree field, which it puts at 341 by 256 pixels of a 1024 by 768 screen, so
0.0277 of it; this counts the pixels changing anywhere on the frame together, which
finds at least what a search over every field would. Each pixel's change is read from
the last extreme it reached, so a ramp over several frames counts as the change it is.

It reads what capture.movie wrote: the frames named in `sequence.json`, at its rate. It
certifies nothing beyond the frames it read, and every answer says so: a flash in a
scene nobody captured is not found.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import numpy as np

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What a predicate may bound, and what it says.
FLASHES: dict[str, str] = {
    "flashes": "the most flashes, general or red, in any one second of a captured run",
    "flash_share": "the largest share of the screen one flash in that second covered",
}

#: Frames are read at most this many pixels on their longer side, averaged in linear
#: light first, so a 4K capture costs what a small one does and a flash keeps its area.
_SIDE = 320


def is_flash(name: str) -> bool:
    return name in FLASHES


def _frames(capture: Path, fps: float, here: Path) -> tuple[list[Path], float]:
    """The frames in order and their rate: a capture.movie folder, or one of PNGs."""
    folder = capture.parent if capture.name == "sequence.json" else capture
    manifest = folder / "sequence.json"
    if manifest.is_file():
        sequence = json.loads(manifest.read_text(encoding="utf-8"))
        frames = [folder / one["file"] for one in sequence.get("frames", [])]
        rate = fps or float(sequence.get("fps") or 0)
    elif folder.is_dir():
        frames = sorted(folder.glob("*.png"))
        rate = fps or float(load(here).get("engine.fixed_fps") or 0)
    else:
        raise PolyweaveError(
            "capture.no-frames",
            f"there is no capture at {capture}",
            "capture the run with capture.movie and name the folder it wrote",
            given=str(capture),
        )
    if len(frames) < 2:
        raise PolyweaveError(
            "capture.no-frames",
            f"{folder.name} holds {len(frames)} frame(s), and a flash takes two",
            "capture the run with capture.movie, between two marks a second or more "
            "apart",
            given=str(capture),
        )
    if rate <= 0:
        raise PolyweaveError(
            "capture.no-rate",
            f"nothing says at what rate the frames in {folder.name} were taken",
            "pass fps, or capture with capture.movie, whose sequence.json says it",
        )
    return frames, rate


def _linear(path: Path) -> np.ndarray:
    """A frame as linear-light RGB, averaged down to _SIDE on its longer side."""
    from PIL import Image

    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    rgb = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    step = max(1, int(np.ceil(max(rgb.shape[:2]) / _SIDE)))
    if step > 1:
        h, w = (rgb.shape[0] // step) * step, (rgb.shape[1] // step) * step
        rgb = rgb[:h, :w].reshape(h // step, step, w // step, step, 3).mean(axis=(1, 3))
    return rgb


class _Changes:
    """Each pixel's opposing changes, read from the last extreme it reached."""

    def __init__(self, first: np.ndarray, step: float, dark: float | None):
        self.step, self.dark = step, dark
        self.low = first.copy()
        self.high = first.copy()
        self.direction = np.zeros(first.shape, dtype=np.int8)

    def __call__(self, value: np.ndarray) -> np.ndarray:
        """The pixels whose change completed at this frame."""
        rose = (value - self.low >= self.step) & (self.direction <= 0)
        fell = (self.high - value >= self.step) & (self.direction >= 0)
        if self.dark is not None:
            rose &= self.low < self.dark
            fell &= value < self.dark
        both = rose & fell
        # where one frame both rose and fell from the two ends, the larger change wins
        rose &= ~both | (value - self.low >= self.high - value)
        fell &= ~rose
        changed = rose | fell
        self.direction = np.where(rose, 1, np.where(fell, -1, self.direction)).astype(
            np.int8
        )
        self.low = np.where(changed | (value < self.low), value, self.low)
        self.high = np.where(changed | (value > self.high), value, self.high)
        return changed


def _worst(shares: list[float], fps: float, area: float) -> dict:
    """The one second holding the most flashes, two opposing changes making one."""
    events = [i for i, share in enumerate(shares) if share >= area]
    window = max(1, round(fps))
    best = {"flashes": 0, "frame": None, "second": None, "share": 0.0}
    for start in events:
        inside = [i for i in events if start <= i < start + window]
        flashes = len(inside) // 2
        if flashes > best["flashes"]:
            best = {
                "flashes": flashes,
                "frame": start,
                "second": round(start / fps, 3),
                "share": round(max(shares[i] for i in inside), 4),
            }
    return best


def count(frames: list[Path], fps: float, bounds: dict) -> dict:
    """The worst second of general and of red flashes over a run's frames, in order."""
    first = _linear(frames[0])
    luminance = first @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    def redness(rgb: np.ndarray) -> np.ndarray:
        total = rgb.sum(axis=2)
        saturated = rgb[..., 0] >= 0.8 * np.maximum(total, 1e-6)
        return np.where(
            saturated & (total > 0),
            np.maximum(rgb[..., 0] - rgb[..., 1] - rgb[..., 2], 0) * 320,
            0,
        )

    general = _Changes(luminance, float(bounds["luminance"]), float(bounds["dark"]))
    red = _Changes(redness(first), float(bounds["red"]), None)
    shares = {"general": [0.0], "red": [0.0]}
    for path in frames[1:]:
        rgb = _linear(path)
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        shares["general"].append(float(general(lum).mean()))
        shares["red"].append(float(red(redness(rgb)).mean()))
    return {kind: _worst(found, fps, float(bounds["area"]))
            for kind, found in shares.items()}


def measured(capture: str | Path, fps: float = 0.0, root: str | Path = ".") -> dict:
    """Every flash measure of a captured run, by name, with what it rests on."""
    config = load(root)
    here = config.root
    where = Path(capture) if Path(capture).is_absolute() else here / capture
    frames, rate = _frames(where, float(fps), here)
    bounds = config.table("flashes")
    kinds = count(frames, rate, bounds)
    kind = max(kinds, key=lambda k: kinds[k]["flashes"])
    worst = {"kind": kind, **kinds[kind]}
    if worst["frame"] is not None:
        worst["file"] = frames[worst["frame"]].name
    limit = int(bounds["limit"])
    return {
        "flashes": worst["flashes"],
        "flash_share": worst["share"],
        "worst": worst,
        "general": kinds["general"],
        "red": kinds["red"],
        "limit": limit,
        "passed": worst["flashes"] <= limit,
        "frames": len(frames),
        "fps": rate,
        "seconds": round(len(frames) / rate, 3),
        "bounds": dict(bounds),
        "certifies": f"only the {len(frames)} frames of this run, "
        f"{len(frames) / rate:.2f} s: a flash in a scene nobody captured is not found",
    }


@operation("measure.flashes")
def flashes(
    capture: Annotated[
        str, Param("the folder capture.movie wrote, its sequence.json, or PNG frames")
    ],
    *,
    fps: Annotated[
        float, Param("the frames' rate; sequence.json's, or [engine] fixed_fps", lo=0)
    ] = 0.0,
    root: Annotated[str, Param("the project the path resolves against")] = ".",
) -> dict:
    """The worst second of flashes in a captured run, held to the guidance's limit.

    Counts general flashes (a luminance change of 0.1 with the darker state under 0.8)
    and red flashes (a saturated red changing by more than 20) over at least 0.0277 of
    the screen, WCAG 2.3.1's defaults, which `[flashes]` overrides. Answers the worst
    second: its `flashes`, `kind`, starting `frame` and `file`, and the `share` of the
    screen involved, `passed` against `limit` (3), and `certifies`, which says that a
    flash in a scene nobody captured is not found (§PW354).
    """
    found = measured(capture, fps, root)
    worst = found["worst"]
    says = (
        f"at most {worst['flashes']} flash(es) in any second of {found['seconds']} s"
        if found["passed"]
        else f"{worst['flashes']} {worst['kind']} flashes in the second from "
        f"{worst['file']} ({worst['second']} s), over the {found['limit']} allowed"
    )
    return {"capture": capture, **found, "says": says}
