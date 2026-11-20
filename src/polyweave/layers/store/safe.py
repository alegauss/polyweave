"""Burned-in text held to the part of a frame a platform leaves visible (§PW698).

A vertical video's captions compete with the platform's own controls: on a Short the
buttons ran down the right edge and the title and channel covered the bottom, and the
Scion Shorts' captions were placed by looking at four stills. `video.safe_area` reads
every line of the subtitle file that is burned in (ASS, the format libass burns), works
out where each one lands at the video's size from its style, alignment, margins and any
`\\pos` or `\\an` it carries, measures its width with the style's font, and says which
lines reach outside the safe box or into an area the platform covers, by how many
pixels, and when. The bounds are a preset's, as fractions of the frame, or the call's
own; they are observations of a platform, not its specification, so a project names
its own wherever it knows better.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: Where a platform's controls sit, as fractions of the frame (left, top, right,
#: bottom), and the box text is kept inside. Observed on 1080x1920 Shorts on 2026-11-12:
#: the buttons over x 940..1080, y 900..1700, the title and channel the bottom 420 px.
PRESETS: dict[str, dict] = {
    "youtube-shorts": {
        "safe": [0.0, 0.0, 1.0, 1.0],
        "exclude": {
            "buttons": [940 / 1080, 900 / 1920, 1.0, 1700 / 1920],
            "title": [0.0, 1500 / 1920, 1.0, 1.0],
        },
    },
    "none": {"safe": [0.0, 0.0, 1.0, 1.0], "exclude": {}},
}

_TAGS = re.compile(r"\{[^}]*\}")
_POS = re.compile(r"\\pos\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")
_AN = re.compile(r"\\an([1-9])")
_FS = re.compile(r"\\fs([\d.]+)")


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("video.bad-subtitles", message, remedy, **extra)


def _seconds(stamp: str) -> float:
    hours, minutes, seconds = stamp.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read(source: Path) -> dict:
    """The script's play size, its styles and its dialogue lines, as ASS has them."""
    try:
        text = source.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise _bad(f"there is no subtitle file at {source}",
                   "name the .ass file that is burned into the video") from exc
    play = {"PlayResX": 384, "PlayResY": 288}
    styles: dict[str, dict] = {}
    lines: list[dict] = []
    section, fields = "", {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section, fields = line.lower(), {}
            continue
        key, _, value = line.partition(":")
        if section == "[script info]" and key in play:
            play[key] = int(float(value))
        elif key == "Format":
            fields = {name.strip(): i for i, name in enumerate(value.split(","))}
        elif key == "Style" and fields:
            parts = [one.strip() for one in value.split(",")]
            styles[parts[fields["Name"]]] = {
                name: parts[i] for name, i in fields.items() if i < len(parts)}
        elif key == "Dialogue" and fields:
            parts = value.split(",", len(fields) - 1)
            row = {name: parts[i].strip() if name != "Text" else parts[i]
                   for name, i in fields.items() if i < len(parts)}
            lines.append(row)
    if not lines:
        raise _bad(f"{source.name} holds no Dialogue line",
                   "name an .ass file with [Events] and Dialogue lines")
    return {"play": (play["PlayResX"], play["PlayResY"]), "styles": styles,
            "lines": lines}


def _font(name: str, size: float, fonts: Path | None):
    """The style's font at its size, as Pillow finds it; its default where none is."""
    from PIL import ImageFont

    size = max(1, round(size))
    tried = [name, f"{name}.ttf", f"{name.lower()}.ttf",
             f"{name.replace(' ', '')}.ttf"]
    if fonts is not None:
        tried = [str(fonts / one) for one in tried[1:]] + tried
    for one in tried:
        try:
            return ImageFont.truetype(one, size), one
        except OSError:
            continue
    return ImageFont.load_default(size), "Pillow's default"


def _box(row: dict, style: dict, scale: tuple[float, float], size: tuple[int, int],
         fonts: Path | None) -> tuple[list[float], str]:
    """Where one line's text lands at the video's size, and the font it was measured
    with: its width and height from the font, placed by alignment, margins or \\pos."""
    raw = row.get("Text", "")
    tags = "".join(_TAGS.findall(raw))
    words = _TAGS.sub("", raw).replace("\\N", "\n").replace("\\n", "\n")
    sx, sy = scale
    font_size = float(style.get("Fontsize", 20))
    sized = _FS.search(tags)
    if sized:
        font_size = float(sized.group(1))
    font, found = _font(style.get("Fontname", "Arial"), font_size * sy, fonts)
    stretch_x = float(style.get("ScaleX", 100)) / 100
    stretch_y = float(style.get("ScaleY", 100)) / 100
    rows = words.split("\n") or [""]
    width = max(font.getlength(one) for one in rows) * stretch_x
    height = font_size * sy * stretch_y * len(rows)
    edge = (float(style.get("Outline", 0)) + float(style.get("Shadow", 0))) * sy
    align = int(style.get("Alignment", 2))
    turned = _AN.search(tags)
    if turned:
        align = int(turned.group(1))
    column, band = (align - 1) % 3, (align - 1) // 3   # 0 left/bottom .. 2 right/top
    placed = _POS.search(tags)
    if placed:
        x, y = float(placed.group(1)) * sx, float(placed.group(2)) * sy
    else:
        margin_l = float(row.get("MarginL") or 0) or float(style.get("MarginL", 0))
        margin_r = float(row.get("MarginR") or 0) or float(style.get("MarginR", 0))
        margin_v = float(row.get("MarginV") or 0) or float(style.get("MarginV", 0))
        x = (margin_l * sx, size[0] / 2, size[0] - margin_r * sx)[column]
        y = (size[1] - margin_v * sy, size[1] / 2, margin_v * sy)[band]
    left = x - width * (0, 0.5, 1)[column]
    top = y - height * (1, 0.5, 0)[band]
    return [round(left - edge, 1), round(top - edge, 1), round(left + width + edge, 1),
            round(top + height + edge, 1)], found


def _crossings(box: list[float], safe: list[float], exclude: dict) -> list[dict]:
    """How far a box reaches past the safe box and into each excluded one, in px."""
    found = []
    past = max(safe[0] - box[0], safe[1] - box[1], box[2] - safe[2], box[3] - safe[3])
    if past > 0:
        found.append({"area": "safe", "by_px": round(past, 1)})
    for name, area in exclude.items():
        into = min(box[2] - area[0], area[2] - box[0], box[3] - area[1],
                   area[3] - box[1])
        if into > 0:
            found.append({"area": name, "by_px": round(into, 1)})
    return found


@operation("video.safe_area")
def safe_area(
    subtitles: Annotated[str, Param("the .ass file burned into the video")],
    *,
    size: Annotated[
        list, Param("the video's width and height in px, as [1080, 1920]")
    ] = None,
    preset: Annotated[
        str, Param("a platform's observed bounds", choices=tuple(PRESETS))
    ] = "youtube-shorts",
    safe: Annotated[
        list, Param("the box text stays in, [left, top, right, bottom] in px")
    ] = None,
    exclude: Annotated[
        dict, Param("areas the platform covers, by name, each [l, t, r, b] in px")
    ] = None,
    fonts: Annotated[str, Param("a folder holding the styles' font files")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Which burned-in lines reach outside the safe box or under a platform's controls.

    Every Dialogue line of the .ass is placed at `size` from its style and overrides
    and measured with its font, outline and shadow included. The bounds are the
    preset's, scaled to `size`, with `safe` and `exclude` replacing them where given.
    Each line that crosses one is named with its time, text, box and how many px it
    reaches in; `passed` is true where none does. The measure is the font Pillow finds
    for the style, which the answer names, so a missing font reads as an estimate.
    """
    here = load(root).root
    source = here / subtitles
    script = read(source)
    width, height = (size or script["play"])
    if not (isinstance(width, int | float) and isinstance(height, int | float)
            and width > 0 and height > 0):
        raise _bad(f"size is {size!r}", "give size as [width, height] in px")
    scale = (width / script["play"][0], height / script["play"][1])
    bounds = PRESETS[preset]

    def px(box: list[float]) -> list[float]:
        return [box[0] * width, box[1] * height, box[2] * width, box[3] * height]

    kept = list(safe) if safe else px(bounds["safe"])
    covered = ({name: list(box) for name, box in exclude.items()} if exclude is not None
               else {name: px(box) for name, box in bounds["exclude"].items()})
    folder = here / fonts if fonts else None
    crossed, measured_with = [], set()
    for index, row in enumerate(script["lines"], 1):
        style = script["styles"].get(row.get("Style", ""), {})
        box, found = _box(row, style, scale, (width, height), folder)
        measured_with.add(found)
        hits = _crossings(box, kept, covered)
        if hits:
            crossed.append({
                "line": index,
                "start": round(_seconds(row.get("Start", "0:00:00")), 3),
                "end": round(_seconds(row.get("End", "0:00:00")), 3),
                "text": _TAGS.sub("", row.get("Text", "")).replace("\\N", " "),
                "box": box, "crosses": hits,
            })
    return {
        "subtitles": subtitles, "size": [width, height], "preset": preset,
        "safe": [round(v, 1) for v in kept],
        "exclude": {name: [round(v, 1) for v in box] for name, box in covered.items()},
        "lines": len(script["lines"]), "crossed": crossed, "passed": not crossed,
        "fonts": sorted(measured_with),
    }
