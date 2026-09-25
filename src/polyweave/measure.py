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
import math
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from .describe import Param, operation
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
PENDING: dict[str, str] = {}

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


# -- colour at a place ----------------------------------------------------------------


def from_hex(colour: str) -> np.ndarray:
    """A hex colour as sRGB in 0–1. §6 fixes every authored colour as sRGB."""
    text = str(colour).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise PolyweaveError(
            "spec.bad-colour",
            f"{colour!r} is not a colour",
            "write it as #RRGGBB",
        )
    return np.array([int(text[i : i + 2], 16) for i in (0, 2, 4)]) / 255.0


@_computes("region_colour")
def _region_colour(image: Image, mask: np.ndarray, **_: Any) -> list[float]:
    """The mean CIELAB colour over the region.

    Averaged in Lab rather than in sRGB: the mean of two sRGB values is not the colour
    halfway between them, and "does this read as the right colour" is a perceptual
    question throughout.
    """
    rgb = image.rgba[mask][:, :3].astype(np.float64) / 255.0
    return [round(float(v), 4) for v in to_lab(rgb).mean(axis=0)]


@_computes("delta_e")
def _delta_e(image: Image, mask: np.ndarray, *, target: Any = None, **_: Any) -> float:
    """CIEDE2000 between the region's colour and a target.

    Perceptual, because the question being asked is always "does this read as the right
    colour", and an RGB distance answers a different question. Under 2 is a difference a
    person has to look for; over 5 is a different colour.
    """
    if target is None:
        raise PolyweaveError(
            "spec.measure-needs",
            "delta_e is a distance to a target colour, and none was given",
            "pass target='#RRGGBB', the colour it should read as",
        )
    here = np.array(_region_colour(image, mask))
    there = to_lab(from_hex(target)) if isinstance(target, str) else np.array(target)
    return round(ciede2000(here, there), 4)


@_distributes("pixel_delta_e")
def _pixel_delta_e(
    image: Image, mask: np.ndarray, *, target: Any = None, **_: Any
) -> np.ndarray:
    """CIEDE2000 from every pixel of the region to a target, as a distribution.

    `delta_e` measures from the region's mean, and a mean is the one statistic this
    vocabulary exists to avoid (§PW86). Cottony's mushroom cap is covered in white
    spots, so its recorded bar is a median: over any rectangle on it the mean is pulled
    toward white by however many spots it catches, and `_p50` here is the body colour
    through them. `delta_e` keeps its meaning, so no spec already written changes.

    Each distinct colour is measured once, which is what makes a per-pixel CIEDE2000
    affordable: a sprite has thousands of pixels and far fewer colours.
    """
    if target is None:
        raise PolyweaveError(
            "spec.measure-needs",
            "pixel_delta_e is a distance to a target colour, and none was given",
            "pass target='#RRGGBB', the colour it should read as",
        )
    there = to_lab(from_hex(target)) if isinstance(target, str) else np.array(target)
    colours, which = np.unique(image.rgba[mask][:, :3], axis=0, return_inverse=True)
    each = to_lab(colours.astype(np.float64) / 255.0)
    apart = np.array([ciede2000(one, there) for one in each])
    return apart[np.asarray(which).reshape(-1)]


def ciede2000(one: np.ndarray, two: np.ndarray) -> float:
    """The CIE's 2000 colour difference, between two Lab values."""
    l1, a1, b1 = (float(v) for v in one)
    l2, a2, b2 = (float(v) for v in two)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0
    g = 0.5 * (1.0 - math.sqrt(c_bar**7 / (c_bar**7 + 25.0**7))) if c_bar else 0.0

    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0 if (a2p or b2) else 0.0

    dlp = l2 - l1
    dcp = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    else:
        dhp = h2p - h1p - 360.0 if h2p > h1p else h2p - h1p + 360.0
    dHp = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2.0)

    lp_bar = (l1 + l2) / 2.0
    cp_bar = (c1p + c2p) / 2.0
    if c1p * c2p == 0:
        hp_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hp_bar = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        hp_bar = (h1p + h2p + 360.0) / 2.0
    else:
        hp_bar = (h1p + h2p - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(hp_bar - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * hp_bar))
        + 0.32 * math.cos(math.radians(3.0 * hp_bar + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * hp_bar - 63.0))
    )
    sl = 1.0 + (0.015 * (lp_bar - 50.0) ** 2) / math.sqrt(20.0 + (lp_bar - 50.0) ** 2)
    sc = 1.0 + 0.045 * cp_bar
    sh = 1.0 + 0.015 * cp_bar * t
    rt = (
        -2.0
        * math.sqrt(cp_bar**7 / (cp_bar**7 + 25.0**7))
        * math.sin(math.radians(60.0 * math.exp(-(((hp_bar - 275.0) / 25.0) ** 2))))
        if cp_bar
        else 0.0
    )
    return math.sqrt(
        (dlp / sl) ** 2
        + (dcp / sc) ** 2
        + (dHp / sh) ** 2
        + rt * (dcp / sc) * (dHp / sh)
    )


# -- silhouette ---------------------------------------------------------------------


def _reference_mask(image: Image, against: Any, alpha_floor: float) -> np.ndarray:
    """The reference's own silhouette, scaled to the image being measured.

    Both masks are normalised to the same dimensions first, so a render and a drawing of
    different sizes still compare — which is the whole point of measuring a shape rather
    than a file.
    """
    other = _other(against, "a silhouette measure")
    if other.size == image.size:
        return other.subject(alpha_floor)
    from PIL import Image as PILImage

    scaled = PILImage.fromarray(other.rgba, "RGBA").resize(image.size, PILImage.NEAREST)
    edge = round(alpha_floor * 255)
    return np.asarray(scaled, dtype=np.uint8)[:, :, 3] > edge


def _boxes(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    if not rows.size or not columns.size:
        return None
    return (int(columns[0]), int(rows[0]), int(columns[-1]), int(rows[-1]))


@_computes("silhouette_iou")
def _silhouette_iou(
    image: Image,
    mask: np.ndarray,
    *,
    against: Any = None,
    alpha_floor: float,
    **_,
) -> float:
    """Intersection over union of the two alpha masks.

    The measure that would have caught the tall dome returned for a wide low cap, before
    the credits were spent.
    """
    here = image.subject(alpha_floor) & mask
    there = _reference_mask(image, against, alpha_floor) & mask
    union = int((here | there).sum())
    if not union:
        return 1.0  # two empty silhouettes are the same silhouette
    return round(float(int((here & there).sum()) / union), 6)


@_computes("silhouette_centroid_offset")
def _silhouette_centroid_offset(
    image: Image,
    mask: np.ndarray,
    *,
    against: Any = None,
    alpha_floor: float,
    **_,
) -> float:
    """How far apart the two silhouettes' middles are, in pixels."""
    here = image.subject(alpha_floor) & mask
    there = _reference_mask(image, against, alpha_floor) & mask
    if not here.any() or not there.any():
        return 0.0
    a = np.argwhere(here).mean(axis=0)
    b = np.argwhere(there).mean(axis=0)
    return round(float(np.hypot(*(a - b))), 4)


@_computes("silhouette_bbox_delta")
def _silhouette_bbox_delta(
    image: Image,
    mask: np.ndarray,
    *,
    against: Any = None,
    alpha_floor: float,
    **_,
) -> float:
    """The largest per-edge difference between the two bounding boxes, in pixels."""
    here = _boxes(image.subject(alpha_floor) & mask)
    there = _boxes(_reference_mask(image, against, alpha_floor) & mask)
    if here is None or there is None:
        return 0.0
    return float(max(abs(a - b) for a, b in zip(here, there, strict=True)))


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


#: The measures that compare two shapes, which default to the whole frame rather than to
#: the render's own subject (§PW87).
SILHOUETTES = frozenset(
    {"silhouette_iou", "silhouette_centroid_offset", "silhouette_bbox_delta"}
)


# -- the call ---------------------------------------------------------------------


def measure(
    subject: Any,
    measures: Sequence[str] = DEFAULT,
    *,
    region: Any = None,
    alpha_floor: float | None = None,
    rung: str | None = None,
    root: str | Path = ".",
    **params: Any,
) -> list[dict]:
    """Every measure asked for, each with the region and rung it was taken at.

    The rung is reported and never inferred, so a verdict taken on a sphere is never
    mistaken for one taken on the final mesh. `params` carries what one measure needs
    and the others do not — `display` for `luma_bands`, a count at a stated size.

    This is the boundary where a tolerance is resolved (§PW40). The measures below it
    take the number and none of them defaults it, so there is one home for what counts
    as the subject; here the project's own answer is read unless the caller states one.
    """
    from .config import load as load_config

    alpha_floor = float(load_config(root).get("tolerance.alpha_floor", alpha_floor))
    image = subject if isinstance(subject, Image) else load(subject)
    masks: dict[str, tuple[Any, np.ndarray]] = {}

    def within(base: str) -> tuple[Any, np.ndarray]:
        # Two shapes are compared over the whole frame when nobody says otherwise
        # (§PW87): cut to the render's own subject, the reference outside the render
        # was never counted, and a render missing half the drawing scored near one.
        where = region
        if where is None:
            where = "frame" if base in SILHOUETTES else default_region(image)
        key = repr(_named(where))
        if key not in masks:
            mask = region_mask(image, where, alpha_floor)
            if not mask.any():
                raise PolyweaveError(
                    "spec.empty-region",
                    f"the region {_named(where)!r} holds no pixels to measure",
                    "widen the region, or lower `[tolerance] alpha_floor` if the "
                    "subject is fainter than the floor",
                )
            masks[key] = (where, mask)
        return masks[key]

    out = []
    for name in measures:
        base = resolve(name)
        where, mask = within(base)
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


def resolve(name: str) -> str:
    """The measure a name asks for, or a refusal that says why it cannot be given."""
    base = base_measure(name)
    if base in COMPUTES:
        if base in SCALARS and name != base:
            raise PolyweaveError(
                "spec.unknown-measure",
                f"{base!r} is one number, so there is no {name!r}",
                f"ask for {base!r} on its own",
                given=name,
                allowed=(base,),
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
        given=name,
        allowed=set(COMPUTES) | set(PENDING),
    )


@operation("measure.available")
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


def noise_floor(
    one: Any,
    two: Any,
    *,
    region: Any = None,
    alpha_floor: float,
) -> float:
    """The distance between two renders of one unchanged scene: the floor itself.

    §PW44. A configured floor is a guess, and measuring proves it is usually the wrong
    one. On Blender 5.2.1 two seeds of one unchanged sphere came back 0.0234 apart at
    the sphere rung, 0.0195 at preview and 0.0122 at final, against a single configured
    default of 0.004 — so every comparison at every rung read as a change.

    The controls matter more than the numbers. The same seed rendered twice is 0.0
    exactly, so what is measured here is sampler noise and not the pipeline wobbling;
    and a changed material measures 0.63, thirty times the widest floor, so nothing is
    being hidden by a bar this size.

    A floor measured this way costs one render and is right on this machine at this
    sample count for this scene, which a number in a file never is.
    """
    taken = measure(
        one,
        ["distance"],
        region=region,
        alpha_floor=alpha_floor,
        against=two,
        root=".",
    )
    return float(summarise(taken)["distance"])


PICTURE = Param("a picture, as a path under the project")
REGION = Param("where to measure: frame, subject, a rectangle, or a mask file")
FLOOR = Param("the alpha below which a pixel is background; the project's if unset")


@operation("measure.same")
def same(
    subject: Annotated[Any, PICTURE],
    against: Annotated[Any, Param("the other picture, as a path under the project")],
    *,
    tolerance: Annotated[
        float, Param("the distance still called the same; measured or the rung's")
    ] = None,
    delta: Annotated[float, Param("the colour difference a pixel may move by")] = None,
    region: Annotated[Any, REGION] = None,
    alpha_floor: Annotated[float, FLOOR] = None,
    twin: Annotated[
        Any, Param("a second render of the unchanged scene, to measure the floor")
    ] = None,
    rung: Annotated[str, Param("the rung both were rendered at")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Whether two renders are the same picture, with a tolerance rather than equality.

    Two runs of one unchanged path-traced scene differ: Cottony measured 29,696
    differing pixels across a render nobody had touched, none by more than 1/255. So a
    gate comparing bytes fires on every run, and the question needs a threshold.

    Three ways to get one, best first (§PW44):

    - `twin`, a second render of the subject's own unchanged scene at another seed. The
      floor is then **measured** rather than assumed, and is right at whatever sample
      count and on whatever machine this is. It costs one render.
    - `tolerance`, stated by the caller who knows their own bar.
    - `[tolerance] render_noise` for the rung, which is keyed by rung because the floor
      at four samples is not the floor at five hundred. The rung is read from the
      subject's own provenance record where there is one, so a verdict taken on a sphere
      is not held to a final render's bar.

    The answer says which of the three it used, because a verdict rests on its floor and
    a floor nobody can see is a number nobody can argue with.

    This has a root, so it is where the resolving happens: `measure` below it takes the
    numbers and invents none (§PW40).
    """
    from .config import load as load_config

    config = load_config(root)
    floor_alpha = float(config.get("tolerance.alpha_floor", alpha_floor))
    at = rung or _rung_of(subject, root)
    if twin is not None:
        bar = noise_floor(subject, twin, region=region, alpha_floor=floor_alpha)
        source = "measured from a twin render"
    elif tolerance is not None:
        bar = float(tolerance)
        source = "stated by the caller"
    else:
        bar = config.tolerances(at).render_noise
        source = f"[tolerance] render_noise for the {at or 'strictest'} rung"

    floor = delta if delta is not None else bar
    taken = measure(
        subject,
        ["distance", "changed_fraction"],
        region=region,
        alpha_floor=floor_alpha,
        against=against,
        delta=floor,
        root=root,
    )
    found = summarise(taken)
    apart = found["distance"]
    return {
        "same": apart <= bar,
        "distance": apart,
        "changed_fraction": found["changed_fraction"],
        "tolerance": bar,
        "tolerance_from": source,
        "rung": at,
        "why": ""
        if apart <= bar
        else f"the 99th percentile difference is {apart}, past a tolerance of {bar} "
        f"({source})",
    }


def _rung_of(subject: Any, root: str | Path) -> str | None:
    """Which rung a render was taken at, off the record already written beside it.

    Read rather than asked for, because the record carries it and a caller repeating it
    is a caller who can get it wrong (§PW6). None where there is no record, which is the
    ordinary case for an image that came from somewhere else.
    """
    if not isinstance(subject, str | Path):
        return None
    from .errors import PolyweaveError
    from .provenance import read as read_record

    try:
        return read_record(subject, root=root).get("rung")
    except PolyweaveError:
        return None


@operation("measure.take")
def taken(
    subject: Annotated[str, PICTURE],
    measures: Annotated[list, Param("the measures to take, by name")] = DEFAULT,
    *,
    region: Annotated[Any, REGION] = None,
    alpha_floor: Annotated[float, FLOOR] = None,
    rung: Annotated[str, Param("the rung the picture was made at, if known")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    target: Annotated[str, Param("the colour delta_e is measured to")] = None,
    against: Annotated[
        str, Param("the picture a silhouette or distance compares with")
    ] = None,
    display: Annotated[list, Param("the size luma_bands counts at")] = None,
    delta: Annotated[float, Param("the difference changed_fraction counts")] = None,
) -> list[dict]:
    """Take measurements of a picture, each with the region and rung it was taken at.

    `measure` is the same with any argument a measure takes; this names the four the
    vocabulary has, so a caller reaching it by name can be told what they are.
    """
    extra = {
        name: value
        for name, value in (
            ("target", target),
            ("against", against),
            ("display", display),
            ("delta", delta),
        )
        if value is not None
    }
    here = Path(root)
    picture = Path(subject) if Path(subject).is_absolute() else here / subject
    if isinstance(extra.get("against"), str):
        extra["against"] = str(here / extra["against"])
    return measure(
        picture,
        list(measures),
        region=region,
        alpha_floor=alpha_floor,
        rung=rung,
        root=root,
        **extra,
    )


def summarise(measurements: Iterable[dict]) -> dict:
    """The measurements as a flat mapping, for a record wanting one value per name."""
    return {m["measure"]: m["value"] for m in measurements}
