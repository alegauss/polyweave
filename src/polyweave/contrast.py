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
so the capture that placed the shots names them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from .describe import Param, operation
from .errors import PolyweaveError

#: A target as a game prints it.
LINE = re.compile(
    r"^target:\s*(?:box\s+(?P<l>-?\d+(?:\.\d+)?)\s+(?P<t>-?\d+(?:\.\d+)?)\s+"
    r"(?P<r>-?\d+(?:\.\d+)?)\s+(?P<b>-?\d+(?:\.\d+)?)|(?P<x>-?\d+(?:\.\d+)?)\s+"
    r"(?P<y>-?\d+(?:\.\d+)?)(?:\s+(?P<radius>\d+(?:\.\d+)?))?)",
    re.MULTILINE,
)

#: A point target's radius where none is given, and the ring's width, in pixels.
RADIUS, RING = 3.0, 6


def targets_in(text: str) -> list[dict]:
    """Every target a log names, in the order it printed them."""
    found = []
    for match in LINE.finditer(text):
        if match["l"] is not None:
            found.append({"box": [float(match[k]) for k in "ltrb"]})
        else:
            found.append({"at": [float(match["x"]), float(match["y"])],
                          "radius": float(match["radius"] or RADIUS)})
    return found


def _read(targets: Any, root: Path) -> list[dict]:
    if isinstance(targets, str | Path):
        where = Path(targets)
        where = where if where.is_absolute() else root / where
        if not where.is_file():
            raise PolyweaveError(
                "spec.no-targets",
                f"there is no log at {where.name} to read targets from",
                "name the log the capture wrote, or pass the targets as a list",
            )
        found = targets_in(where.read_text(encoding="utf-8", errors="replace"))
    else:
        found = list(targets or [])
    if not found:
        raise PolyweaveError(
            "spec.no-targets",
            "no target to measure contrast at",
            "pass targets, each {at: [x, y], radius} or {box: [l, t, r, b]}, or a log "
            "whose lines say `target: <x> <y>`",
        )
    return found


def _masks(target: dict, shape: tuple, ring: int) -> tuple[np.ndarray, np.ndarray]:
    """A target's own pixels and the ring around it, as masks the picture's size."""
    rows, cols = np.mgrid[0 : shape[0], 0 : shape[1]]
    if "box" in target:
        left, top, right, bottom = (float(v) for v in target["box"])
        inside = (cols >= left) & (cols <= right) & (rows >= top) & (rows <= bottom)
        grown = ((cols >= left - ring) & (cols <= right + ring)
                 & (rows >= top - ring) & (rows <= bottom + ring))
        return inside, grown & ~inside
    if "at" not in target:
        raise PolyweaveError(
            "spec.no-targets",
            f"a target is {target!r}, which is neither a point nor a box",
            "give each target at: [x, y] with a radius, or box: [l, t, r, b]",
        )
    x, y = (float(v) for v in target["at"])
    radius = float(target.get("radius", RADIUS))
    apart = np.hypot(cols - x, rows - y)
    return apart <= radius, (apart > radius + 1) & (apart <= radius + 1 + ring)


def contrasts(image, targets: Any, *, ring: int = RING, root: Path = Path(".")) -> dict:
    """Each target's ratio and ΔE against its ring, with the worst and the median."""
    from .measure import ciede2000, srgb_to_linear, to_lab

    rgb = image.rgba[..., :3].astype(np.float64) / 255.0
    luminance = srgb_to_linear(rgb) @ np.array([0.2126, 0.7152, 0.0722])
    lab = to_lab(rgb)
    each = []
    for target in _read(targets, root):
        inside, around = _masks(target, luminance.shape, int(ring))
        if not inside.any() or not around.any():
            raise PolyweaveError(
                "spec.no-targets",
                f"the target {target!r} has no pixels of the picture, or no ring",
                "place targets inside the picture, with room for the ring around them",
            )
        core = float(np.percentile(luminance[inside], 90))
        behind = float(np.median(luminance[around]))
        lighter, darker = max(core, behind), min(core, behind)
        bright = inside & (luminance >= np.median(luminance[inside]))
        delta = ciede2000(
            np.median(lab[bright], axis=0), np.median(lab[around], axis=0)
        )
        each.append({**target, "ratio": round((lighter + 0.05) / (darker + 0.05), 3),
                     "delta_e": round(delta, 2)})
    ratios = [one["ratio"] for one in each]
    return {
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
        str, Param("a log whose `target: x y` lines name the targets, instead")
    ] = None,
    ring: Annotated[int, Param("the surround's width", lo=1, unit="px")] = RING,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """How well each target stands out from the ring around it, the worst named.

    Each target answers its WCAG luminance `ratio` and its `delta_e` against its ring;
    the answer adds `contrast_min`, `contrast_median` and `delta_e_min`, which a spec
    bounds as it bounds any measure, and the `worst` target.
    """
    from .image import load as load_image

    here = Path(root).resolve()
    where = Path(picture) if Path(picture).is_absolute() else here / picture
    return {"picture": picture,
            **contrasts(load_image(where), log if log else targets, ring=ring,
                        root=here)}
