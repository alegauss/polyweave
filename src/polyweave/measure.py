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


#: What each measure is, and what computes it. A name in `measurements.md` with nothing
#: here is in the vocabulary and not yet built — see `PENDING`.
COMPUTES: dict[str, Any] = {}

#: Measures the vocabulary declares and no line has built yet, each naming the line that
#: will. Refusing by name beats returning an answer that is quietly missing a field.
PENDING = {
    "saturation": "PW9 reports a distribution rather than a mean",
    "luma": "PW9 reports a distribution rather than a mean",
    "hue_spread": "PW9 reports a distribution rather than a mean",
    "region_colour": "PW10 judges an asset beside its siblings",
    "delta_e": "PW10 judges an asset beside its siblings",
    "silhouette_iou": "PW10 compares a render against a reference",
    "silhouette_centroid_offset": "PW10 compares a render against a reference",
    "silhouette_bbox_delta": "PW10 compares a render against a reference",
    "distance": "PW11 compares two renders with a tolerance",
    "changed_fraction": "PW11 compares two renders with a tolerance",
    "luma_bands": "PW10 measures what survives at display size",
}

#: The set a render answers with unless a caller names others, per `measurements.md`. It
#: grows as the measures above are built.
DEFAULT = ("alpha_coverage",)


def _computes(name: str):
    def register(fn):
        COMPUTES[name] = fn
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
    out = []
    for name in measures:
        fn = _resolve(name)
        out.append(
            {
                "measure": name,
                "region": _named(where),
                "rung": rung,
                "value": fn(image, mask, alpha_floor=alpha_floor),
            }
        )
    return out


def _resolve(name: str):
    base = base_measure(name)
    if base in COMPUTES:
        return COMPUTES[base]
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
