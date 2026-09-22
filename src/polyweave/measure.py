"""Measuring a render, in the same call that produced it.

The evidence is §PW8: judging a render is today a render call, then a file read to see
the image, then a separate measurement run — three calls, two of which exist only
because the first returned a path instead of an answer. In a sweep the number of turns
*is* the cost: eight samples at three calls each is twenty-four round trips for what
should be eight.

So a measurement is a value with its region and its rung beside it, computed where the
picture was, and returned with it. The vocabulary is `docs/specs/measurements.md` and it
is closed: a name outside it is refused rather than quietly skipped, and a name inside
it that no line has built yet is refused **by name, saying which line builds it**, so a
caller is never handed a shorter answer than it asked for.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from .errors import PolyweaveError
from .image import Image, load

#: The statistic suffixes `measurements.md` appends. `saturation_p99` is a statistic of
#: `saturation`, and the two are computed by the same thing.
SUFFIXES = ("_p1", "_p50", "_p99", "_mean", "_std")


def base_measure(measure: str) -> str:
    """The measure a statistic is a statistic of."""
    for suffix in SUFFIXES:
        if measure.endswith(suffix):
            return measure[: -len(suffix)]
    return measure


#: Measures reported as a **set of statistics, never as one number**. §PW9 is why:
#: Cottony's board matched the concept art's mean saturation to within 0.01 and was
#: plainly washed out, because the whole difference sat at the 99th percentile. A mean
#: over an image is dominated by whatever covers the most area, which is almost never
#: the thing being judged.
DISTRIBUTIONS: dict[str, Any] = {}

#: Measures that are one number by nature.
SCALARS: dict[str, Any] = {}

#: What each measure is, and what computes it. A name in `measurements.md` with nothing
#: here is in the vocabulary and not yet built — see `PENDING`.
COMPUTES: dict[str, Any] = {}

#: Measures the vocabulary declares and no line has built yet, each naming the line that
#: will. Refusing by name beats returning an answer that is quietly missing a field.
PENDING = {
    "region_colour": "PW10 judges an asset beside its siblings",
    "delta_e": "PW10 judges an asset beside its siblings",
    "silhouette_iou": "PW10 compares a render against a reference",
    "silhouette_centroid_offset": "PW10 compares a render against a reference",
    "silhouette_bbox_delta": "PW10 compares a render against a reference",
    "distance": "PW11 compares two renders with a tolerance",
    "changed_fraction": "PW11 compares two renders with a tolerance",
    "luma_bands": "PW10 measures what survives at display size",
}

#: The set a render answers with unless a caller names others, per `measurements.md`.
DEFAULT = ("saturation", "luma", "alpha_coverage")


def _computes(name: str):
    def register(fn):
        COMPUTES[name] = fn
        SCALARS[name] = fn
        return fn

    return register


def _distributes(name: str):
    """Register a measure whose answer is every statistic of it, not one number."""

    def register(fn):
        COMPUTES[name] = fn
        DISTRIBUTIONS[name] = fn
        return fn

    return register


@_computes("alpha_coverage")
def _alpha_coverage(
    image: Image, mask: np.ndarray, *, alpha_floor: float, **_
) -> float:
    """The fraction **of the region** whose alpha is above the floor.

    Of the region, not of the frame: a measurement taken over a rectangle answers about
    that rectangle, or a region would only ever report its own size.
    """
    within = int(mask.sum())
    if not within:
        return 0.0
    return round(float((image.subject(alpha_floor) & mask).sum() / within), 6)


# -- what a look is made of ---------------------------------------------------------


def srgb_to_linear(channel: np.ndarray) -> np.ndarray:
    """Undo the sRGB transfer function, because luminance is a linear quantity."""
    low = channel / 12.92
    high = ((channel + 0.055) / 1.055) ** 2.4
    return np.where(channel <= 0.04045, low, high)


def _hsl(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hue in turns, saturation and lightness, from sRGB in 0–1."""
    high = rgb.max(axis=-1)
    low = rgb.min(axis=-1)
    span = high - low
    lightness = (high + low) / 2.0
    saturation = np.where(
        span == 0, 0.0, span / np.maximum(1.0 - np.abs(2.0 * lightness - 1.0), 1e-12)
    )
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        hue = np.select(
            [span == 0, high == r, high == g],
            [0.0, ((g - b) / span) % 6.0, (b - r) / span + 2.0],
            default=(r - g) / span + 4.0,
        )
    return (hue / 6.0) % 1.0, np.clip(saturation, 0.0, 1.0), lightness


@_distributes("saturation")
def _saturation(image: Image, mask: np.ndarray, **_: Any) -> np.ndarray:
    """HSL saturation over the region, which is how colourful a pixel reads."""
    rgb = image.rgba[mask][:, :3].astype(np.float64) / 255.0
    return _hsl(rgb)[1]


@_distributes("luma")
def _luma(image: Image, mask: np.ndarray, **_: Any) -> np.ndarray:
    """Relative luminance, sRGB-weighted, on linear values because light adds."""
    linear = srgb_to_linear(image.rgba[mask][:, :3].astype(np.float64) / 255.0)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


@_computes("hue_spread")
def _hue_spread(image: Image, mask: np.ndarray, **_: Any) -> float:
    """How far apart the hues are, weighted by saturation.

    Circular, because hue wraps and a mean of 355° and 5° is not 180°. Reported as the
    circular **variance** — one minus the resultant length — which is the form of the
    quantity that fits the 0–1 the vocabulary declares; the standard deviation it is
    derived from is unbounded and could not.

    Weighted by saturation because the hue of a grey pixel is arbitrary, and an image of
    mostly grey would otherwise report a spread it does not have.
    """
    rgb = image.rgba[mask][:, :3].astype(np.float64) / 255.0
    hue, saturation, _ = _hsl(rgb)
    weight = saturation.sum()
    if weight <= 0.0:
        return 0.0  # nothing is coloured, so nothing is spread
    angle = hue * 2.0 * np.pi
    x = float((np.cos(angle) * saturation).sum() / weight)
    y = float((np.sin(angle) * saturation).sum() / weight)
    return round(float(1.0 - min(1.0, np.hypot(x, y))), 6)


def statistics(values: np.ndarray) -> dict[str, float]:
    """The five a distribution is reported as, per `measurements.md`."""
    p1, p50, p99 = np.percentile(values, [1, 50, 99])
    return {
        "_p1": round(float(p1), 6),
        "_p50": round(float(p50), 6),
        "_p99": round(float(p99), 6),
        "_mean": round(float(values.mean()), 6),
        "_std": round(float(values.std()), 6),
    }


# -- regions ---------------------------------------------------------------------


def region_mask(image: Image, region: Any, alpha_floor: float) -> np.ndarray:
    """Which pixels a measurement is taken over.

    `frame` is all of them; `subject` is where alpha exceeds the floor, and is the
    default wherever the image has an alpha channel — a prop measured over only its own
    pixels is not diluted by whatever background it happens to sit on.
    """
    if region == "frame":
        return np.ones(image.rgba.shape[:2], dtype=bool)
    if region == "subject":
        return image.subject(alpha_floor)
    if isinstance(region, list | tuple) and len(region) == 4:
        x0, y0, x1, y1 = (int(v) for v in region)
        if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
            raise PolyweaveError(
                "spec.bad-region",
                f"the rectangle {list(region)} is not inside a "
                f"{image.width}x{image.height} image",
                f"give [x0, y0, x1, y1] with x1 and y1 no greater than "
                f"{image.width} and {image.height}",
            )
        mask = np.zeros(image.rgba.shape[:2], dtype=bool)
        mask[y0:y1, x0:x1] = True
        return mask
    if isinstance(region, str | Path) and Path(region).is_file():
        return _mask_file(image, region)
    raise PolyweaveError(
        "spec.bad-region",
        f"{region!r} is not a region, and no mask file is there",
        "give 'frame', 'subject', a rectangle [x0, y0, x1, y1], or the path of a mask",
    )


def _mask_file(image: Image, where: str | Path) -> np.ndarray:
    other = load(where)
    if other.size != image.size:
        raise PolyweaveError(
            "spec.bad-region",
            f"the mask is {other.width}x{other.height} and the image is "
            f"{image.width}x{image.height}",
            "give a mask the same size as the image being measured",
        )
    return other.alpha > 0


def _named(region: Any) -> Any:
    """The region as a record spells it: a word, a rectangle, or a path as a string."""
    if isinstance(region, str):
        return region
    if isinstance(region, Path):
        return str(region)
    return list(region)


def default_region(image: Image) -> str:
    """`subject` wherever the image has an alpha channel, `frame` otherwise."""
    return "subject" if image.had_alpha else "frame"


# -- the call ---------------------------------------------------------------------


def measure(
    subject: Any,
    measures: Sequence[str] = DEFAULT,
    *,
    region: Any = None,
    alpha_floor: float = 0.0,
    rung: str | None = None,
) -> list[dict]:
    """Every measure asked for, each with the region and rung it was taken at.

    The rung is reported and never inferred, so a verdict taken on a sphere is never
    mistaken for one taken on the final mesh.
    """
    image = subject if isinstance(subject, Image) else load(subject)
    where = default_region(image) if region is None else region
    mask = region_mask(image, where, alpha_floor)
    if not mask.any():
        raise PolyweaveError(
            "spec.empty-region",
            f"the region {_named(where)!r} holds no pixels to measure",
            "widen the region, or lower `[tolerance] alpha_floor` if the subject is "
            "fainter than the floor",
        )

    out = []
    for name in measures:
        base = _resolve(name)
        if base in DISTRIBUTIONS:
            values = DISTRIBUTIONS[base](image, mask, alpha_floor=alpha_floor)
            for suffix, value in statistics(values).items():
                if name == base or name.endswith(suffix):
                    out.append(_taken(base + suffix, where, rung, value))
        else:
            value = SCALARS[base](image, mask, alpha_floor=alpha_floor)
            out.append(_taken(name, where, rung, value))
    return out


def _taken(name: str, where: Any, rung: str | None, value: float) -> dict:
    return {
        "measure": name,
        "region": _named(where),
        "rung": rung,
        "value": value,
    }


def _resolve(name: str) -> str:
    """The measure a name asks for, or a refusal that says why it cannot be given."""
    base = base_measure(name)
    if base in COMPUTES:
        if base in SCALARS and name != base:
            raise PolyweaveError(
                "spec.unknown-measure",
                f"{base!r} is one number, so there is no {name!r}",
                f"ask for {base!r} on its own",
            )
        return base
    if base in PENDING:
        raise PolyweaveError(
            "spec.unmeasured",
            f"{name!r} is a measure this plugin does not compute yet",
            f"{PENDING[base]}; ask for {', '.join(sorted(COMPUTES))} meanwhile",
        )
    raise PolyweaveError(
        "spec.unknown-measure",
        f"{name!r} is not a measure",
        f"name one of {', '.join(sorted(set(COMPUTES) | set(PENDING)))}",
    )


def available() -> dict:
    """What can be measured now, and what is declared and still ahead of its code."""
    return {"computed": sorted(COMPUTES), "pending": dict(sorted(PENDING.items()))}


# -- the picture itself -------------------------------------------------------------


def inline_image(path: str | Path, image: Image | None = None) -> dict:
    """The picture, carried back with the numbers instead of left on disk.

    Base64 rather than raw bytes because this rides home inside a job record, which is
    JSON. The size is the rendered size and never a thumbnail: an image worth looking at
    is the other half of the answer, and a caller that has to open the file to see it is
    back to paying two calls for one question.
    """
    where = Path(path)
    data = where.read_bytes()
    shown = image or load(where)
    return {
        "path": str(where),
        "media_type": "image/png",
        "width": shown.width,
        "height": shown.height,
        "bytes": len(data),
        "base64": base64.b64encode(data).decode("ascii"),
    }


def summarise(measurements: Iterable[dict]) -> dict:
    """The measurements as a flat mapping, for a record wanting one value per name."""
    return {m["measure"]: m["value"] for m in measurements}
