"""How well each target stands out from what lies right behind it (§PW272).

Starship's owner could not tell the ship's shots from the hostile ones over a lit city,
and proving the fix meant measuring each shot against the box beside it, twice per shot,
in a script of the project's own. Here each target is a point with a radius, or a box,
and its surround is the ring around it:

- `ratio`: the WCAG luminance ratio, (lighter + 0.05) / (darker + 0.05), of the target's
  bright core (its 90th-percentile luminance, since a shot reads by its brightest part)
  against the ring's median;
- `delta_e`: the CIEDE2000 distance between the median colour of the target's brighter
  half and the ring's median colour.

A set of targets answers the minimum and the median of each, so a spec bounds the worst
shot (`contrast_min >= 3`) rather than an average that hides it. Targets can come from
a line the game printed, `target: <x> <y> [radius]` or `target: box <l> <t> <r> <b>`,
so the capture that placed the shots names them, or from a JSON file holding the list.

A radius smaller than the shot puts the ring on the shot itself, and the ratio reads
1.0 as if the shot were invisible (§PW279). Where the ring matches the target and the
band past it does not, the measure refuses and says to widen the radius.

A line of text is a target of its own, `{text: [l, t, r, b]}` or `target: text ...`
(§PW319): a box against its ring would rate the whole line against the scene beside it,
which says nothing about whether a glyph reads over what is behind it. Its glyphs are
told from the background inside the box, and each stretch of the line one line-height
wide is rated glyph against the background behind it; the line answers its worst
stretch, and `text_contrast_min` the worst line.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from .describe import Param, operation
from .errors import PolyweaveError

#: A target as a game prints it.
LINE = re.compile(
    r"^target:\s*(?:(?P<kind>box|text)\s+(?P<l>-?\d+(?:\.\d+)?)\s+(?P<t>-?\d+(?:\.\d+)?)\s+"
    r"(?P<r>-?\d+(?:\.\d+)?)\s+(?P<b>-?\d+(?:\.\d+)?)|(?P<x>-?\d+(?:\.\d+)?)\s+"
    r"(?P<y>-?\d+(?:\.\d+)?)(?:\s+(?P<radius>\d+(?:\.\d+)?))?)",
    re.MULTILINE,
)

#: A point target's radius where none is given, and the ring's width, in pixels.
RADIUS, RING = 3.0, 6


#: How close to the target's own light a ring may read before its surround is suspect,
#: and how far the band past the ring must differ from it to say the ring is inside.
SAME, APART = 1.25, 1.5


def targets_in(text: str, radius: float = RADIUS) -> list[dict]:
    """Every target a log names, in the order it printed them."""
    found = []
    for match in LINE.finditer(text):
        if match["l"] is not None:
            found.append({match["kind"]: [float(match[k]) for k in "ltrb"]})
        else:
            found.append({"at": [float(match["x"]), float(match["y"])],
                          "radius": float(match["radius"] or radius)})
    return found


def _listed(text: str, where: Path) -> list | None:
    """The targets a JSON file holds, or None where the file is not JSON."""
    if where.suffix.lower() != ".json" and not text.lstrip().startswith(("[", "{")):
        return None
    try:
        held = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolyweaveError(
            "spec.no-targets",
            f"{where.name} is not readable as JSON",
            "write it as a list of {at: [x, y], radius} or {box: [l, t, r, b]}, or "
            "as a log whose lines say `target: <x> <y> [radius]`",
            detail=str(exc),
        ) from exc
    if isinstance(held, dict):
        held = held.get("targets")
    if not isinstance(held, list):
        raise PolyweaveError(
            "spec.no-targets",
            f"{where.name} holds no list of targets",
            'write it as a list, or as {"targets": [...]}',
        )
    return held


def _read(targets: Any, root: Path, radius: float = RADIUS) -> list[dict]:
    if isinstance(targets, str | Path):
        where = Path(targets)
        where = where if where.is_absolute() else root / where
        if not where.is_file():
            raise PolyweaveError(
                "spec.no-targets",
                f"there is no file at {where.name} to read targets from",
                "name the log the capture wrote or a JSON list, or pass the targets",
            )
        text = where.read_text(encoding="utf-8", errors="replace")
        found = _listed(text, where)
        if found is None:
            found = targets_in(text, radius)
    else:
        found = list(targets or [])
    # A point given without its own radius takes the one the caller stated.
    found = [
        {**one, "radius": float(radius)}
        if isinstance(one, dict) and "at" in one and "radius" not in one else one
        for one in found
    ]
    if not found:
        raise PolyweaveError(
            "spec.no-targets",
            "no target to measure contrast at",
            "pass targets, each {at: [x, y], radius} or {box: [l, t, r, b]}, or a log "
            "whose lines say `target: <x> <y>`",
        )
    return found


def _masks(target: dict, shape: tuple, ring: int) -> tuple[np.ndarray, ...]:
    """A target's own pixels, the ring around it and the band past that, as masks."""
    rows, cols = np.mgrid[0 : shape[0], 0 : shape[1]]
    if "box" in target:
        left, top, right, bottom = (float(v) for v in target["box"])

        def grown(by: int) -> np.ndarray:
            return ((cols >= left - by) & (cols <= right + by)
                    & (rows >= top - by) & (rows <= bottom + by))

        inside = grown(0)
        return inside, grown(ring) & ~inside, grown(2 * ring) & ~grown(ring)
    if "at" not in target:
        raise PolyweaveError(
            "spec.no-targets",
            f"a target is {target!r}, which is neither a point nor a box",
            "give each target at: [x, y] with a radius, or box: [l, t, r, b]",
        )
    x, y = (float(v) for v in target["at"])
    radius = float(target.get("radius", RADIUS))
    apart = np.hypot(cols - x, rows - y)
    edge = radius + 1 + ring
    return (apart <= radius, (apart > radius + 1) & (apart <= edge),
            (apart > edge) & (apart <= edge + ring))


def _wcag(one, other):
    return (np.maximum(one, other) + 0.05) / (np.minimum(one, other) + 0.05)


#: How far a pixel of the frame must differ from the same pixel behind the text to be a
#: glyph's, as a luminance ratio; an antialiased rim fainter than this is background.
GLYPH = 1.2

#: The share of a stretch's glyph pixels at or under the ratio it answers: the upper
#: quartile, since a glyph reads by its stroke and its antialiased rim is the low tail.
STROKE = 75


def _split(values: np.ndarray) -> float:
    """Otsu's threshold over luminance: the cut that best parts two populations."""
    counts, edges = np.histogram(values, bins=256, range=(0.0, 1.0))
    centres = (edges[:-1] + edges[1:]) / 2
    weight = np.cumsum(counts)
    total = weight[-1]
    mean = np.cumsum(counts * centres)
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (mean[-1] * weight / total - mean) ** 2 / (weight * (total - weight))
    return float(edges[int(np.nanargmax(between)) + 1])


def _text(index: int, target: dict, luminance: np.ndarray, under) -> dict:
    """One line's glyphs against what is behind them, its worst stretch named."""
    left, top, right, bottom = (int(round(float(v))) for v in target["text"])
    left, top = max(left, 0), max(top, 0)
    right = min(right, luminance.shape[1] - 1)
    bottom = min(bottom, luminance.shape[0] - 1)
    if right <= left or bottom <= top:
        raise PolyweaveError(
            "spec.no-targets",
            f"the text box {target['text']!r} has no pixels of the picture",
            "give the line's box inside the picture, as [left, top, right, bottom]",
        )
    line = luminance[top : bottom + 1, left : right + 1]
    back = None if under is None else under[top : bottom + 1, left : right + 1]
    stride = max(1, bottom - top + 1)
    stretches, glyphs = [], 0
    for start in range(0, line.shape[1], stride):
        lit = line[:, start : start + stride]
        if back is not None:
            # The same frame without the text: a glyph is what differs from it, and
            # its background is the pixel right behind it.
            behind = back[:, start : start + stride]
            mine = _wcag(lit, behind) >= GLYPH
            behind = behind[mine]
        else:
            # Without it, a stretch parts into two populations and the glyphs are the
            # fewer; a stretch of one light holds no glyph.
            if float(_wcag(lit.max(), lit.min())) < GLYPH:
                continue
            dark = lit < _split(lit)
            mine = dark if dark.sum() <= (~dark).sum() else ~dark
            behind = float(np.median(lit[~mine]))
        if mine.sum() < 3:
            continue
        glyphs += int(mine.sum())
        ratio = float(np.percentile(_wcag(lit[mine], behind), STROKE))
        stretches.append((ratio, start))
    if not stretches:
        raise PolyweaveError(
            "spec.no-targets",
            f"the text box {index + 1} holds no glyphs told apart from what is behind "
            "them",
            "check the box sits on the line, or pass behind: the same frame without "
            "the text",
            detail=f"box {target['text']!r}",
        )
    ratio, start = min(stretches)
    return {
        **target,
        "ratio": round(ratio, 3),
        "worst_at": [left + start, top, min(left + start + stride - 1, right), bottom],
        "glyphs": glyphs,
    }


def _luminance(image) -> np.ndarray:
    from .measure import srgb_to_linear

    rgb = image.rgba[..., :3].astype(np.float64) / 255.0
    return srgb_to_linear(rgb) @ np.array([0.2126, 0.7152, 0.0722])


def _behind(behind: Any, root: Path, shape: tuple) -> np.ndarray | None:
    """The frame without its text, as luminance, where one is given (§PW319)."""
    if behind is None:
        return None
    from .image import load as load_image

    where = Path(behind)
    where = where if where.is_absolute() else root / where
    under = _luminance(load_image(where))
    if under.shape != shape:
        raise PolyweaveError(
            "spec.no-targets",
            f"{where.name} is {under.shape[1]}x{under.shape[0]}, and the picture "
            f"{shape[1]}x{shape[0]}",
            "capture the frame without the text at the picture's own size",
        )
    return under


def contrasts(image, targets: Any, *, ring: int = RING, radius: float = RADIUS,
              root: Path = Path("."), behind: Any = None) -> dict:
    """Each target's ratio and ΔE against its ring, with the worst and the median.

    A text target answers on its own (§PW319), its glyphs against what is behind them,
    and the lines add `text_contrast_min` and `text_worst`; `behind` is the frame
    without the text, which tells each glyph from the scene exactly.
    """
    from .measure import ciede2000, to_lab

    luminance = _luminance(image)
    found = _read(targets, root, radius)
    texts = [one for one in found if isinstance(one, dict) and "text" in one]
    said: dict = {}
    if texts:
        under = _behind(behind, root, luminance.shape)
        lines = [
            _text(index, one, luminance, under) for index, one in enumerate(texts)
        ]
        worst = min(lines, key=lambda one: one["ratio"])
        said = {
            "texts": lines, "text_contrast_min": worst["ratio"], "text_worst": worst
        }
    found = [one for one in found if not (isinstance(one, dict) and "text" in one)]
    if not found:
        return said
    lab = to_lab(image.rgba[..., :3].astype(np.float64) / 255.0)
    each = []
    for index, target in enumerate(found):
        inside, around, past = _masks(target, luminance.shape, int(ring))
        if not inside.any() or not around.any():
            raise PolyweaveError(
                "spec.no-targets",
                f"the target {target!r} has no pixels of the picture, or no ring",
                "place targets inside the picture, with room for the ring around them",
            )
        core = float(np.percentile(luminance[inside], 90))
        behind = float(np.median(luminance[around]))
        if past.any() and _wcag(core, behind) < SAME:
            beyond = float(np.median(luminance[past]))
            if _wcag(behind, beyond) >= APART and _wcag(core, beyond) >= APART:
                raise PolyweaveError(
                    "spec.ring-inside-target",
                    f"the ring around target {index + 1} lies inside it: it reads as "
                    "the target's own light while the picture past it does not",
                    "widen radius (on the target, or the predicate's default) so it "
                    "covers the whole shot, or give the target as a box",
                    detail=f"target {target!r}: core {core:.4f}, ring {behind:.4f}, "
                    f"past the ring {beyond:.4f} (linear luminance)",
                )
        lighter, darker = max(core, behind), min(core, behind)
        bright = inside & (luminance >= np.median(luminance[inside]))
        delta = ciede2000(
            np.median(lab[bright], axis=0), np.median(lab[around], axis=0)
        )
        each.append({**target, "ratio": round((lighter + 0.05) / (darker + 0.05), 3),
                     "delta_e": round(delta, 2)})
    ratios = [one["ratio"] for one in each]
    return {
        **said,
        "targets": each,
        "contrast_min": min(ratios),
        "contrast_median": round(float(np.median(ratios)), 3),
        "delta_e_min": min(one["delta_e"] for one in each),
        "worst": each[int(np.argmin(ratios))],
    }


@operation("measure.contrast")
def measured(
    picture: Annotated[str, Param("the picture, as a path under the project")],
    targets: Annotated[
        list, Param("each {at: [x, y], radius} or {box: [l, t, r, b]}, in pixels")
    ] = None,
    log: Annotated[
        str, Param("a `target: x y [r]` log or JSON list of targets, instead")
    ] = None,
    behind: Annotated[
        str, Param("the frame without its text, for text lines")
    ] = None,
    ring: Annotated[int, Param("the surround's width", lo=1, unit="px")] = RING,
    radius: Annotated[
        float, Param("a point's default radius", lo=0, unit="px")
    ] = RADIUS,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """How well each target stands out from the ring around it, the worst named.

    Each target answers its WCAG luminance `ratio` and its `delta_e` against its ring;
    the answer adds `contrast_min`, `contrast_median` and `delta_e_min`, which a spec
    bounds as it bounds any measure, and the `worst` target. A line of text,
    `{text: [l, t, r, b]}`, answers `text_contrast_min` instead (§PW319).
    """
    from .image import load as load_image

    here = Path(root).resolve()
    where = Path(picture) if Path(picture).is_absolute() else here / picture
    return {"picture": picture,
            **contrasts(load_image(where), log if log else targets, ring=ring,
                        radius=radius, root=here, behind=behind)}
