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
    r"^target:\s*(?:box\s+(?P<l>-?\d+(?:\.\d+)?)\s+(?P<t>-?\d+(?:\.\d+)?)\s+"
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
            found.append({"box": [float(match[k]) for k in "ltrb"]})
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


def _wcag(one: float, other: float) -> float:
    return (max(one, other) + 0.05) / (min(one, other) + 0.05)


def contrasts(image, targets: Any, *, ring: int = RING, radius: float = RADIUS,
              root: Path = Path(".")) -> dict:
    """Each target's ratio and ΔE against its ring, with the worst and the median."""
    from .measure import ciede2000, srgb_to_linear, to_lab

    rgb = image.rgba[..., :3].astype(np.float64) / 255.0
    luminance = srgb_to_linear(rgb) @ np.array([0.2126, 0.7152, 0.0722])
    lab = to_lab(rgb)
    each = []
    for index, target in enumerate(_read(targets, root, radius)):
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
    ring: Annotated[int, Param("the surround's width", lo=1, unit="px")] = RING,
    radius: Annotated[
        float, Param("a point's default radius", lo=0, unit="px")
    ] = RADIUS,
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
                        radius=radius, root=here)}
