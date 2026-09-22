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
    "region_colour": "PW12 builds the predicates an acceptance spec is made of",
    "delta_e": "PW12 builds the predicates an acceptance spec is made of",
    "silhouette_iou": "PW12 builds the predicates an acceptance spec is made of",
    "silhouette_centroid_offset": "PW12 builds the predicates it compares against",
    "silhouette_bbox_delta": "PW12 builds the predicates it compares against",
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


@_computes("luma_bands")
def _luma_bands(
    image: Image, mask: np.ndarray, *, display: Any = None, **_: Any
) -> int:
    """How many distinct luminance levels survive at the size it will be drawn.

    Some detail exists in the file and is gone on the screen: Cottony's fluff read at
    1.2 and vanished at 1.0, at a third of the sprite's authored size. Downscaling first
    is the only way to ask that honestly, so the display size is an argument and not a
    default — a count taken at the authored size answers a question nobody asked.
    """
    if display is None:
        raise PolyweaveError(
            "spec.measure-needs",
            "luma_bands is a count at a display size, and none was given",
            "pass display=<px>, the size the asset is actually drawn at",
        )
    box = (
        (int(display), int(display))
        if isinstance(display, int | float)
        else (
            int(display[0]),
            int(display[1]),
        )
    )
    from PIL import Image as PILImage

    shown = np.where(mask[:, :, None], image.rgba, 0).astype(np.uint8)
    small = np.asarray(
        PILImage.fromarray(shown, "RGBA").resize(box, PILImage.LANCZOS), dtype=np.uint8
    )
    lit = small[:, :, 3] > 0
    if not lit.any():
        return 0
    linear = srgb_to_linear(small[lit][:, :3].astype(np.float64) / 255.0)
    luma = linear @ np.array([0.2126, 0.7152, 0.0722])
    return int(np.unique(np.round(luma * 255).astype(np.uint8)).size)


# -- comparing two renders -----------------------------------------------------------

#: D65, the white point sRGB is defined against.
_WHITE = np.array([0.95047, 1.00000, 1.08883])

#: Linear sRGB to CIE XYZ, D65.
_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)

#: A ΔE of 100 is "a different colour", which is what puts a distance in 0–1.
DELTA_E_FULL = 100.0


def to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB in 0–1 to CIELAB, which is the space a difference is perceptual in."""
    xyz = srgb_to_linear(rgb) @ _TO_XYZ.T / _WHITE
    big = xyz > 0.008856
    f = np.where(big, np.cbrt(np.abs(xyz)), 7.787 * xyz + 16.0 / 116.0)
    return np.stack(
        [
            116.0 * f[..., 1] - 16.0,
            500.0 * (f[..., 0] - f[..., 1]),
            200.0 * (f[..., 1] - f[..., 2]),
        ],
        axis=-1,
    )


#: How big a patch the difference is pooled over before the worst one is taken. This is
#: what separates noise from a change: a sampler's error is uncorrelated between
#: neighbours and averages away inside a block, while a highlight that moved fills one.
POOL = 8


def _delta_field(image: Image, other: Image) -> np.ndarray:
    """Per-pixel perceptual difference between two images, laid out as the image is."""
    if image.size != other.size:
        raise PolyweaveError(
            "spec.size-mismatch",
            f"a {image.width}x{image.height} render cannot be compared with a "
            f"{other.width}x{other.height} one",
            "render both at the same rung, or scale one before comparing",
        )
    return np.linalg.norm(_composited(image) - _composited(other), axis=-1)


def _composited(image: Image) -> np.ndarray:
    """The image as a viewer receives it, in Lab.

    Alpha is applied before the comparison because **the colour under a transparent
    pixel is undefined**. A path tracer writes whatever it happened to have there, and
    two runs of one unchanged scene disagree about it completely, so comparing raw
    channels over a transparent background measures the renderer's scratch memory.
    """
    rgb = image.rgba[:, :, :3].astype(np.float64) / 255.0
    if not image.had_alpha:
        return to_lab(rgb)
    alpha = image.rgba[:, :, 3:4].astype(np.float64) / 255.0
    return to_lab(rgb * alpha)


def pooled(field: np.ndarray, mask: np.ndarray, block: int = POOL) -> np.ndarray:
    """The mean difference inside each `block`×`block` patch of the region.

    Pooling is the whole separation. A path tracer's error is uncorrelated between
    neighbouring pixels, so it averages down inside a patch however many pixels carry
    it. A real change is contiguous, so it survives the average at full strength.
    Counting pixels cannot tell those apart; averaging over a neighbourhood can.
    """
    height, width = field.shape
    down = -(-height // block) * block
    across = -(-width // block) * block
    padded = np.zeros((down, across))
    padded[:height, :width] = np.where(mask, field, 0.0)
    weight = np.zeros((down, across))
    weight[:height, :width] = mask

    shape = (down // block, block, across // block, block)
    tiles = padded.reshape(shape).sum(axis=(1, 3))
    counts = weight.reshape(shape).sum(axis=(1, 3))
    return np.where(counts > 0, tiles / np.maximum(counts, 1.0), 0.0)


def _other(against: Any, name: str) -> Image:
    if against is None:
        raise PolyweaveError(
            "spec.measure-needs",
            f"{name} compares two renders, and only one was given",
            "pass against=<the other render>",
        )
    return against if isinstance(against, Image) else load(against)


@_computes("distance")
def _distance(
    image: Image, mask: np.ndarray, *, against: Any = None, block: int = POOL, **_: Any
) -> float:
    """How far apart two renders are, perceptually: the worst patch of the region.

    The worst rather than the average, because §PW9's lesson applies to a comparison too
    — a mean over the frame is dominated by whatever covers the most area, and a
    highlight that moved is small. Pooled rather than per-pixel, because the worst
    single pixel is whatever the sampler did last.

    Reported against a ΔE of 100, which is where two colours are simply different.
    """
    field = _delta_field(image, _other(against, "distance"))
    if not mask.any():
        return 0.0
    worst = pooled(field, mask, block).max()
    return round(float(min(1.0, worst / DELTA_E_FULL)), 6)


@_computes("changed_fraction")
def _changed_fraction(
    image: Image, mask: np.ndarray, *, against: Any = None, delta: Any = None, **_: Any
) -> float:
    """How much of the region moved by more than a stated amount."""
    if delta is None:
        raise PolyweaveError(
            "spec.measure-needs",
            "changed_fraction counts pixels past a stated difference, and none was "
            "given",
            "pass delta=<0–1>, the difference that counts as a change",
        )
    field = _delta_field(image, _other(against, "changed_fraction"))[mask]
    if not field.size:
        return 0.0
    return round(float((field > float(delta) * DELTA_E_FULL).mean()), 6)


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
    **params: Any,
) -> list[dict]:
    """Every measure asked for, each with the region and rung it was taken at.

    The rung is reported and never inferred, so a verdict taken on a sphere is never
    mistaken for one taken on the final mesh. `params` carries what one measure needs
    and the others do not — `display` for `luma_bands`, a count at a stated size.
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
            values = DISTRIBUTIONS[base](image, mask, alpha_floor=alpha_floor, **params)
            for suffix, value in statistics(values).items():
                if name == base or name.endswith(suffix):
                    out.append(_taken(base + suffix, where, rung, value))
        else:
            value = SCALARS[base](image, mask, alpha_floor=alpha_floor, **params)
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


def same(
    subject: Any,
    against: Any,
    *,
    tolerance: float | None = None,
    delta: float | None = None,
    region: Any = None,
    alpha_floor: float = 0.0,
    root: str | Path = ".",
) -> dict:
    """Whether two renders are the same picture, with a tolerance rather than equality.

    Two runs of one unchanged path-traced scene differ: Cottony measured 29,696
    differing pixels across a render nobody had touched, none by more than 1/255. So a
    gate comparing bytes fires on every run, and the question needs a threshold.

    The threshold is `[tolerance] render_noise` unless the caller states one, because
    the bar for sampler noise is not the bar for a silhouette that has to land within
    three pixels.
    """
    from .config import load as load_config

    config = load_config(root)
    bar = float(config.get("tolerance.render_noise", tolerance))
    floor = delta if delta is not None else bar
    taken = measure(
        subject,
        ["distance", "changed_fraction"],
        region=region,
        alpha_floor=alpha_floor,
        against=against,
        delta=floor,
    )
    found = summarise(taken)
    apart = found["distance"]
    return {
        "same": apart <= bar,
        "distance": apart,
        "changed_fraction": found["changed_fraction"],
        "tolerance": bar,
        "why": ""
        if apart <= bar
        else f"the 99th percentile difference is {apart}, past a tolerance of {bar}",
    }


def summarise(measurements: Iterable[dict]) -> dict:
    """The measurements as a flat mapping, for a record wanting one value per name."""
    return {m["measure"]: m["value"] for m in measurements}
