"""A capture held to the concept painting it copies, region by region (§PW477).

Cottony was asked to reach its concept art pixel for pixel. The painting is 1024x1536
and a capture 1080x1920, so no two pixels correspond: `distance` compares two renders of
one size, and `reference.compare` is for video. What was missing is a correspondence
declared once and a comparison across it.

A `*.concept.toml` names the painting and its regions, each a rectangle in the
painting's pixels and the same region's rectangle in the capture's:

    painting = "docs/design/screen1.png"

    [region.header]
    painting = [64, 40, 896, 220]     # x, y, width, height
    capture  = [60, 52, 960, 236]

`reference.concept` resamples each pair to one size, the painting's shape, and measures
what a person compares by eye: the palettes (CIEDE2000 between matched k-means centres),
saturation and luma percentiles as ratios of the capture's to the painting's, how much
edge each has, and a structural similarity at a scale coarse enough to ignore brushwork.
Each region also gets a sheet, painting beside capture beside where they differ.
"""

from __future__ import annotations

import itertools
import math
import tomllib
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop.measure import ciede2000, to_lab

#: How many colours a region's palette is read as.
PALETTE = 5

#: The long side a region's coarse structure is compared at, and its window: brushwork
#: is finer than one window, and a layout's masses are not.
COARSE, WINDOW = 64, 8


def _bad(what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("capture.bad-concept", what, remedy, **extra)


def _box(region: str, side: str, value: Any, size: tuple[int, int]) -> tuple[int, ...]:
    """A region's rectangle on one side, checked to sit inside that picture."""
    numbers = isinstance(value, list) and len(value) == 4 and all(
        isinstance(v, int | float) and not isinstance(v, bool) for v in value)
    if not numbers or value[2] < 2 or value[3] < 2:
        raise _bad(f"region {region}: {side} is {value!r}",
                   f"write {side} = [x, y, width, height] in its pixels, each side "
                   "at least 2")
    x, y, w, h = (int(round(v)) for v in value)
    if x < 0 or y < 0 or x + w > size[0] or y + h > size[1]:
        raise _bad(f"region {region}: {side} [{x}, {y}, {w}, {h}] runs off the "
                   f"{size[0]}x{size[1]} picture",
                   "measure the rectangle on the picture it names")
    return (x, y, x + w, y + h)


def _read(concept: str, here: Path) -> tuple[Path, dict]:
    """The painting and every region of a concept file, each checked."""
    where = here / concept
    if not where.is_file():
        raise _bad(f"there is no concept file at {concept}",
                   "name a *.concept.toml relative to the project root")
    try:
        table = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise _bad(f"{concept} is not TOML", "fix the syntax the detail names",
                   detail=str(exc)) from exc
    painting = here / str(table.get("painting", ""))
    if not table.get("painting") or not painting.is_file():
        raise _bad(f"{concept} names no painting there is a file for",
                   'write painting = "<path under the project>"')
    regions = table.get("region")
    if not isinstance(regions, dict) or not regions:
        raise _bad(f"{concept} declares no region",
                   "write each as [region.<name>] with painting and capture rectangles")
    return painting, regions


def _palette(lab: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A region's colours as PALETTE centres and their shares, by k-means in Lab,
    started from the luma quantiles so the same picture reads the same palette."""
    pixels = lab.reshape(-1, 3)
    order = np.argsort(pixels[:, 0])
    starts = order[np.linspace(0, len(order) - 1, PALETTE).astype(int)]
    centres = pixels[starts].copy()
    for _ in range(12):
        nearest = np.argmin(((pixels[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)
        for k in range(PALETTE):
            mine = pixels[nearest == k]
            if len(mine):
                centres[k] = mine.mean(axis=0)
    shares = np.bincount(nearest, minlength=PALETTE) / len(pixels)
    return centres, shares


def _palette_distance(one: np.ndarray, two: np.ndarray) -> float:
    """CIEDE2000 between two palettes: the painting's centres matched to the capture's
    in the order that costs least, each pair weighted by the painting's share."""
    first, weights = _palette(one)
    second, _ = _palette(two)
    apart = np.array([[ciede2000(a, b) for b in second] for a in first])
    best = min(itertools.permutations(range(PALETTE)),
               key=lambda order: float((apart[range(PALETTE), order] * weights).sum()))
    return round(float((apart[range(PALETTE), best] * weights).sum()), 4)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def _saturation(rgb: np.ndarray) -> np.ndarray:
    high, low = rgb.max(axis=-1), rgb.min(axis=-1)
    return np.where(high > 0, (high - low) / np.maximum(high, 1e-9), 0.0)


def _edges(rgb: np.ndarray) -> float:
    """How much edge a region has: its mean luma step between neighbours, across and
    down. A count of pixels past a threshold changes with how wide resampling spreads
    an edge; the sum of an edge's steps does not, so two cuts of one picture agree."""
    luma = _luma(rgb)
    across = np.abs(np.diff(luma, axis=1))[:-1, :]
    down = np.abs(np.diff(luma, axis=0))[:, :-1]
    return float((across + down).mean())


def _structure(one, two) -> float:
    """Structural similarity of two regions at a coarse scale, in -1 to 1, averaged
    over windows of the layout's masses rather than the brush's strokes."""
    from PIL import Image as Pil

    w, h = one.size
    scale = COARSE / max(w, h)
    small = (max(WINDOW, round(w * scale)), max(WINDOW, round(h * scale)))
    a, b = (_luma(np.asarray(p.resize(small, Pil.Resampling.BOX), dtype=float) / 255.0)
            for p in (one, two))
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    scores = []
    for y in range(0, small[1] - WINDOW + 1, WINDOW // 2):
        for x in range(0, small[0] - WINDOW + 1, WINDOW // 2):
            p, q = a[y:y + WINDOW, x:x + WINDOW], b[y:y + WINDOW, x:x + WINDOW]
            mp, mq = p.mean(), q.mean()
            cov = ((p - mp) * (q - mq)).mean()
            scores.append(((2 * mp * mq + c1) * (2 * cov + c2))
                          / ((mp ** 2 + mq ** 2 + c1) * (p.var() + q.var() + c2)))
    return round(float(np.mean(scores)), 4)


#: How far an alignment looks: the shift as a share of the region's own size each way,
#: and the scales it tries, both at the coarse size.
REACH, SCALES = 0.25, (0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.25)


def _aligned(painting, taken, box: tuple[int, ...]) -> dict:
    """Where the painting's region really sits in the capture, near its declared box.

    Both are compared as coarse luma, the capture's box shifted by up to REACH of its
    size and scaled through SCALES about its centre, and the placement with the least
    mean difference wins: a header that sits 40 px low answers an offset of 40, as
    geometry, instead of a colour difference in every number.
    """
    from PIL import Image as Pil

    shape = painting.size
    want = _luma(np.asarray(painting, float) / 255.0)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # Searched on a copy at twice the coarse size, so a full-size capture costs what a
    # small one does; offsets are still answered in the capture's own pixels.
    k = min(1.0, 2 * max(shape) / max(w, h))
    small = taken.resize((max(1, round(taken.size[0] * k)),
                          max(1, round(taken.size[1] * k))), Pil.Resampling.BOX)

    def miss(dx: float, dy: float, s: float) -> float:
        half_w, half_h = w * s / 2, h * s / 2
        cut = (cx + dx - half_w, cy + dy - half_h, cx + dx + half_w, cy + dy + half_h)
        if cut[0] < 0 or cut[1] < 0 or cut[2] > taken.size[0] or cut[3] > taken.size[1]:
            return math.inf
        # The copy's size was rounded, so a cut ending on the capture's own edge can
        # overshoot it by a fraction of a pixel: held to the copy's bounds (§PW619).
        box = (cut[0] * k, cut[1] * k, min(cut[2] * k, small.size[0]),
               min(cut[3] * k, small.size[1]))
        got = small.resize(shape, Pil.Resampling.BOX, box=box)
        return float(np.abs(_luma(np.asarray(got, float) / 255.0) - want).mean())

    best = (miss(0, 0, 1.0), 0.0, 0.0, 1.0)
    step = max(w, h) * REACH / 6
    for s in SCALES:
        for dx in np.arange(-6, 7) * step:
            for dy in np.arange(-6, 7) * step:
                best = min(best, (miss(dx, dy, s), dx, dy, s))
    # Then finer, around the best, a pixel at a time.
    _, bx, by, bs = best
    for dx in np.arange(-step, step + 1, max(1.0, step / 6)):
        for dy in np.arange(-step, step + 1, max(1.0, step / 6)):
            best = min(best, (miss(bx + dx, by + dy, bs), bx + dx, by + dy, bs))
    _, dx, dy, s = best
    return {"offset": [round(float(dx), 1), round(float(dy), 1)], "scale": s,
            "moved": bool(math.hypot(dx, dy) > 0.02 * max(w, h) or abs(s - 1) > 0.03)}


def _ratio(capture: float, painting: float) -> float | None:
    return round(capture / painting, 4) if painting > 1e-9 else None


def _measured(one, two) -> dict:
    """Every number a region is compared by, the capture's against the painting's."""
    a = np.asarray(one, dtype=float) / 255.0
    b = np.asarray(two, dtype=float) / 255.0
    la, lb = _luma(a), _luma(b)
    sa, sb = _saturation(a), _saturation(b)
    ea, eb = _edges(a), _edges(b)
    return {
        "palette_delta_e": _palette_distance(to_lab(a), to_lab(b)),
        "saturation_p90_ratio": _ratio(np.percentile(sb, 90), np.percentile(sa, 90)),
        "luma_p50_ratio": _ratio(np.percentile(lb, 50), np.percentile(la, 50)),
        "luma_p90_ratio": _ratio(np.percentile(lb, 90), np.percentile(la, 90)),
        "edge_density": {"painting": round(ea, 4), "capture": round(eb, 4),
                         "ratio": _ratio(eb, ea)},
        "structure": _structure(one, two),
    }


def _sheet(one, two):
    """Painting, capture and where they differ, side by side, the difference as grey
    from none (black) to a different colour (white, at a CIE76 step of 50)."""
    from PIL import Image as Pil

    apart = np.linalg.norm(to_lab(np.asarray(one, dtype=float) / 255.0)
                           - to_lab(np.asarray(two, dtype=float) / 255.0), axis=-1)
    grey = np.clip(apart / 50.0 * 255.0, 0, 255).astype(np.uint8)
    w, h = one.size
    sheet = Pil.new("RGB", (w * 3 + 8, h), (40, 40, 40))
    sheet.paste(one, (0, 0))
    sheet.paste(two, (w + 4, 0))
    sheet.paste(Pil.fromarray(grey, "L").convert("RGB"), (2 * w + 8, 0))
    return sheet


def _compared(drawn, taken, name: str, region: Any, size: int) -> tuple:
    """One region's numbers, the two cuts they were read on, and the two boxes."""
    from PIL import Image as Pil

    if not isinstance(region, dict) or set(region) - {"painting", "capture"}:
        raise _bad(f"region {name} must hold painting and capture rectangles only",
                   "write painting = [x, y, w, h] and capture = [x, y, w, h]")
    mine = _box(name, "painting", region.get("painting"), drawn.size)
    theirs = _box(name, "capture", region.get("capture"), taken.size)
    w, h = mine[2] - mine[0], mine[3] - mine[1]
    # Never larger than the smaller of the two cuts: an upsampled side's edges soften,
    # and edge density would measure the resampling rather than the art.
    long = min(size, max(w, h), max(theirs[2] - theirs[0], theirs[3] - theirs[1]))
    scale = long / max(w, h)
    shape = (max(2, round(w * scale)), max(2, round(h * scale)))
    # Averaged down, never sharpened: a sharpening filter's ringing is edge too.
    one = drawn.crop(mine).resize(shape, Pil.Resampling.BOX)
    two = taken.crop(theirs).resize(shape, Pil.Resampling.BOX)
    measured = _measured(one, two)
    coarse = 48 / max(shape)
    small = (max(4, round(shape[0] * coarse)), max(4, round(shape[1] * coarse)))
    measured["geometry"] = _aligned(one.resize(small, Pil.Resampling.BOX), taken,
                                    theirs)
    return measured, one, two, mine, theirs


#: What a spec's predicate may bound about a concept region (§PW477), each read off
#: the region its `region` names in the file its `concept` names.
CONCEPTS: dict[str, str] = {
    "concept_palette_delta_e": "CIEDE2000 between the region's palettes",
    "concept_saturation_ratio": "the capture's p90 saturation over the painting's",
    "concept_luma_ratio": "the capture's median luma over the painting's",
    "concept_luma_p90_ratio": "the capture's p90 luma over the painting's",
    "concept_edge_ratio": "the capture's edge density over the painting's",
    "concept_structure": "coarse structural similarity, -1 to 1",
    "concept_offset": "how far the region sits from its declared box, in pixels",
    "concept_scale": "the scale the region sits at against its declared box",
}

#: Each measure's value where the region is the painting's, which a person's target
#: may be set a fraction of the way to (§PW620).
IDEALS: dict[str, float] = {
    "concept_palette_delta_e": 0.0,
    "concept_saturation_ratio": 1.0,
    "concept_luma_ratio": 1.0,
    "concept_luma_p90_ratio": 1.0,
    "concept_edge_ratio": 1.0,
    "concept_structure": 1.0,
    "concept_offset": 0.0,
    "concept_scale": 1.0,
}


def concept_value(measure: str, *, concept: Any, region: Any, subject: Path,
                  here: Path, size: int = 256) -> float:
    """One concept measure of a capture, for a spec's predicate to bound."""
    from PIL import Image as Pil

    if not concept or not region:
        raise _bad(f"{measure} reads a region of a concept file, and the predicate "
                   "names no concept or no region",
                   'give it concept = "<*.concept.toml>" and region = "<its region>"')
    painting, regions = _read(str(concept), here)
    if str(region) not in regions:
        raise _bad(f"{concept} has no region {region!r}", "name one it declares",
                   given=str(region), allowed=sorted(regions))
    with Pil.open(painting) as opened:
        drawn = opened.convert("RGB")
    with Pil.open(subject) as opened:
        taken = opened.convert("RGB")
    found = _compared(drawn, taken, str(region), regions[str(region)], size)[0]
    value = {
        "concept_palette_delta_e": found["palette_delta_e"],
        "concept_saturation_ratio": found["saturation_p90_ratio"],
        "concept_luma_ratio": found["luma_p50_ratio"],
        "concept_luma_p90_ratio": found["luma_p90_ratio"],
        "concept_edge_ratio": found["edge_density"]["ratio"],
        "concept_structure": found["structure"],
        "concept_offset": round(math.hypot(*found["geometry"]["offset"]), 2),
        "concept_scale": found["geometry"]["scale"],
    }[measure]
    if value is None:
        raise _bad(f"{measure} of region {region} has no value: the painting's is "
                   "zero, so the capture's cannot be a share of it",
                   "bound another of the region's measures")
    return float(value)


@operation("reference.concept")
def concept(
    concept: Annotated[str, Param("the *.concept.toml naming painting and regions")],
    capture: Annotated[str, Param("the capture held to it, a path under the project")],
    *,
    out: Annotated[
        str, Param("the folder each region's sheet is written to; none if unset")
    ] = None,
    size: Annotated[
        int, Param("the long side both regions are resampled to", lo=16, hi=1024,
                   unit="px")
    ] = 256,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Hold a capture to its concept painting region by region, across a layout change.

    Each region declared in the concept file is cut from both, resampled to `size` on
    its long side in the painting's shape (or to the smaller cut, never enlarged), and
    measured: `palette_delta_e`, the CIEDE2000
    between the two five-colour palettes; saturation and luma percentiles as ratios of
    the capture's to the painting's; `edge_density`; `structure`, a coarse structural
    similarity that ignores brushwork; and `geometry`, where the region really sits
    against its declared box. With `out`, a recorded sheet per region shows painting,
    capture and where they differ.
    """
    from PIL import Image as Pil

    here = load(root).root
    painting, regions = _read(concept, here)
    subject = here / capture
    if not subject.is_file():
        raise _bad(f"there is no capture at {capture}",
                   "name the capture's PNG under the project")
    with Pil.open(painting) as opened:
        drawn = opened.convert("RGB")
    with Pil.open(subject) as opened:
        taken = opened.convert("RGB")
    folder = here / out if out else None
    if folder:
        folder.mkdir(parents=True, exist_ok=True)
    answer: dict[str, dict] = {}
    for name, region in regions.items():
        answer[name], one, two, mine, theirs = _compared(drawn, taken, name, region,
                                                         size)
        if folder:
            where = folder / f"{Path(capture).stem}.{name}.concept.png"
            _sheet(one, two).save(where)
            provenance.write(provenance.build(
                "picture", where, engine={"name": "reference.concept"},
                inputs=[provenance.source("reference", painting, here),
                        provenance.source("capture", subject, here)],
                params={"region": name, "painting": list(mine),
                        "capture": list(theirs), "size": size},
                root=here,
            ), here)
            answer[name]["sheet"] = provenance.relative(where, here)
    return {"painting": provenance.relative(painting, here),
            "capture": provenance.relative(subject, here), "regions": answer}


def predicate(p: Any, subject: Any, root: str | Path, seen: dict) -> dict:
    """A concept region's measure of the capture checked, for accept.check (§PW477):
    `region` names the region of the concept file `concept` names, so a search aims at
    the painting (§PW503)."""
    here = Path(root)
    where = Path(p.of) if p.of else Path(subject)
    where = where if where.is_absolute() else here / where
    value = concept_value(p.measure, concept=p.arguments.get("concept"),
                          region=p.region, subject=where, here=here)
    return {"value": value, "of": str(where), "region": p.region}
