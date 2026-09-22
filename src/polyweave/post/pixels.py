"""What must be true of a picture before the operation that made it returns.

A render that came out empty, black or transparent is the cheapest failure there is to
detect and the most expensive one to find two steps downstream, where the evidence of
which step broke has already been overwritten.

Every check here takes `alpha_floor` and **none of them defaults it** (§PW40). These are
pure — they read no files, which is what lets them run inside Blender — so the tolerance
has to arrive from the operation that resolved it. Defaulting it here put a second value
of one number in the codebase, and the two disagreed: zero against the 0.02 the config
declared, so a caller who forgot measured the background as part of the subject and
nothing reported that a choice had been made. `Config.tolerances()` is where it comes
from now, and a call that states none is refused rather than answered wrongly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..errors import PolyweaveError
from ..image import Image, load

ACCEPTS_RENDER = frozenset({"size", "alpha_floor", "render_noise", "allow_uniform"})
ACCEPTS_TEXTURE = frozenset({"size", "alpha_floor", "render_noise", "allow_uniform"})
ACCEPTS_CAPTURE = frozenset({"size", "alpha_floor"})
ACCEPTS_FIELD = frozenset({"size", "levels", "bits", "alpha_floor"})

#: Bits per channel, by the mode the file opens as. §PW38 needs the file's own depth and
#: not the working array's, because the two failures it separates are a renderer that
#: wrote eight bits and a buffer that flattened sixteen down to eight — and by the time
#: an image is an RGBA byte array both look identical.
DEPTHS: dict[str, int] = {
    "1": 1,
    "L": 8,
    "P": 8,
    "LA": 8,
    "PA": 8,
    "RGB": 8,
    "RGBA": 8,
    "CMYK": 8,
    "YCbCr": 8,
    "I;16": 16,
    "I;16L": 16,
    "I;16B": 16,
    "I;16N": 16,
    "I": 32,
    "F": 32,
}


def as_image(subject: Any) -> Image:
    if isinstance(subject, Image):
        return subject
    if isinstance(subject, str | Path):
        return load(subject)
    raise PolyweaveError(
        "post.not-an-image",
        f"a {type(subject).__name__} is not an image or a path to one",
        "pass the path the operation wrote, or a loaded image",
    )


def _measure(image: Image, alpha_floor: float) -> dict:
    mask = image.subject(alpha_floor)
    coverage = float(mask.mean())
    return {
        "size": list(image.size),
        "alpha_coverage": round(coverage, 6),
        "had_alpha": image.had_alpha,
    }


def _check_size(image: Image, size: Any, *, code: str, what: str) -> None:
    if size is None:
        return
    wanted = tuple(int(v) for v in size)
    if image.size != wanted:
        raise PolyweaveError(
            code,
            f"the {what} is {image.width}x{image.height}, and "
            f"{wanted[0]}x{wanted[1]} was asked for",
            f"the renderer ignored or clamped the size; ask for "
            f"{wanted[0]}x{wanted[1]} again, or accept what it produced by "
            f"dropping `size`",
        )


def _check_not_blank(
    image: Image,
    *,
    transparent: str,
    uniform: str,
    what: str,
    alpha_floor: float,
    render_noise: float,
    allow_uniform: bool,
) -> np.ndarray:
    """Not fully transparent, and not one flat colour.

    The two codes are passed in rather than assembled from `what`: a code is part of the
    published contract, and one built at runtime is one nothing can enumerate.

    **Flat is a tolerance, not an equality** (§PW42). A real render is never exactly
    anything: an unlit sphere through Cycles at four samples came back with two
    distinct colours, (0,0,0) across the subject and (1,1,1) on the antialiased edge, so
    a picture that is black to any observer passed the assertion that exists to catch
    it, on one least significant bit. The spread across the visible pixels is measured
    instead, and compared with `[tolerance] render_noise`.

    That number is deliberately tight. 1/255 is 0.0039 and the floor is 0.0040, so this
    catches the render measured above and would not call a two-value spread flat. The
    door out for a render that really is one colour is `allow_uniform`, which is why the
    tolerance does not need to be generous.
    """
    mask = image.subject(alpha_floor)
    if image.had_alpha and not mask.any():
        raise PolyweaveError(
            transparent,
            f"every pixel of the {what} is below the alpha floor, so nothing is there",
            "the subject was outside the frame, or the camera never saw it; check the "
            "framing before spending another render",
        )
    if allow_uniform:
        return mask
    visible = image.rgba[mask][:, :3]
    if len(visible):
        spread = float((visible.max(axis=0) - visible.min(axis=0)).max()) / 255.0
        if spread <= render_noise:
            colour = "#" + "".join(f"{int(v):02x}" for v in visible[0])
            about = "is" if spread == 0.0 else f"is within {spread:.4f} of"
            raise PolyweaveError(
                uniform,
                f"every visible pixel of the {what} {about} {colour}, so it carries "
                f"no image",
                f"the scene was empty or the light never fired; if a flat {colour} is "
                f"what was wanted, pass allow_uniform=True",
            )
    return mask


def check_render(
    subject: Any,
    *,
    size: Any = None,
    alpha_floor: float,
    render_noise: float,
    allow_uniform: bool = False,
) -> dict:
    """Not a single uniform colour, not fully transparent, dimensions as requested."""
    image = as_image(subject)
    _check_size(image, size, code="post.render-size", what="render")
    _check_not_blank(
        image,
        transparent="post.render-transparent",
        uniform="post.render-uniform",
        what="render",
        alpha_floor=alpha_floor,
        render_noise=render_noise,
        allow_uniform=allow_uniform,
    )
    return _measure(image, alpha_floor)


def check_texture(
    subject: Any,
    *,
    size: Any = None,
    alpha_floor: float,
    render_noise: float,
    allow_uniform: bool = False,
) -> dict:
    """Not fully transparent, not a single uniform colour."""
    image = as_image(subject)
    _check_size(image, size, code="post.texture-size", what="texture")
    _check_not_blank(
        image,
        transparent="post.texture-transparent",
        uniform="post.texture-uniform",
        what="texture",
        alpha_floor=alpha_floor,
        render_noise=render_noise,
        allow_uniform=allow_uniform,
    )
    return _measure(image, alpha_floor)


def _as_written(subject: Any) -> tuple[np.ndarray | None, int | None]:
    """The file's own samples and its own bits per channel, before any conversion.

    `Image` holds every picture as RGBA bytes, which is right for everything that asks a
    question about colour and wrong for the only question this check asks. A sixteen-bit
    height field converted to bytes has already lost the precision being measured, so
    this reads the file a second time rather than measuring the conversion.

    `(None, None)` where the subject is an already-loaded image rather than a path: the
    file is not there to re-read, and reporting a depth inferred from the array would be
    reporting the conversion's depth as the file's.
    """
    if not isinstance(subject, str | Path):
        return None, None
    try:
        from PIL import Image as PILImage

        with PILImage.open(subject) as opened:
            return np.asarray(opened), DEPTHS.get(opened.mode)
    except (OSError, ValueError):  # pragma: no cover - `as_image` already refused these
        return None, None


def _levels_in(samples: np.ndarray, mask: np.ndarray) -> list[int]:
    """Distinct values per channel over the subject, which is the staircase's height.

    Per channel and not over the whole array, because a field packed into three channels
    is three separate signals and the flattest one is the one that broke.
    """
    if samples.ndim == 2:
        samples = samples[:, :, None]
    if mask.shape != samples.shape[:2]:  # pragma: no cover - a re-read that disagrees
        mask = np.ones(samples.shape[:2], dtype=bool)
    channels = samples[mask]
    if not len(channels):
        return []
    return [int(np.unique(channels[:, c]).size) for c in range(channels.shape[1])]


def check_field(
    subject: Any,
    *,
    size: Any = None,
    levels: int = 0,
    bits: int = 0,
    alpha_floor: float,
) -> dict:
    """A height, normal or displacement field still carries the precision it needs.

    §PW38, the third of the three silent failures the post-conditions were drawn from.
    A height field blurred through an eight-bit buffer comes back as a staircase: the
    gradient is still there, the image is not uniform, it is not transparent, it is the
    size that was asked for, and every other assertion here passes it.

    What separates this from `texture` is that it has to know what the image is **for**.
    A colour texture with forty distinct levels is fine; a displacement map with forty
    is broken, and nothing in the file says which it is. So the caller declares it, by
    checking a `field` rather than a `texture` and by stating the precision it meant to
    keep.

    The two failures are separate codes because their remedies point at different code.
    Too few bits in the file is the renderer writing too little. Enough bits holding too
    few distinct values is a buffer in the middle of the pipeline that flattened them,
    and the renderer is innocent.
    """
    image = as_image(subject)
    _check_size(image, size, code="post.field-size", what="field")
    samples, depth = _as_written(subject)
    if samples is None:
        samples, depth = image.rgba[:, :, :3], 8

    if bits and depth is not None and depth < int(bits):
        raise PolyweaveError(
            "post.field-shallow",
            f"the file holds {depth} bits per channel, and {int(bits)} was asked for",
            f"the renderer wrote {depth} bits; ask it for {int(bits)}, or accept what "
            f"it produced by lowering `bits`",
        )

    mask = image.subject(alpha_floor)
    found = _levels_in(samples, mask)
    flattest = min(found) if found else 0
    if levels and flattest < int(levels):
        raise PolyweaveError(
            "post.field-quantised",
            f"the flattest channel holds {flattest} distinct values over the subject, "
            f"and {int(levels)} was asked for",
            f"a {depth}-bit file this flat went through an eight-bit buffer somewhere "
            f"between the renderer and the disk; find the conversion rather than "
            f"re-rendering"
            if depth and depth > 8
            else f"the gradient was quantised before it was written; ask the renderer "
            f"for more than {depth or 8} bits, or lower `levels`",
        )

    measured = _measure(image, alpha_floor)
    measured["bits"] = depth
    measured["levels"] = flattest
    measured["levels_per_channel"] = found
    return measured


def check_capture(subject: Any, *, size: Any = None, alpha_floor: float) -> dict:
    """The named artefact exists on disk and is a readable image.

    Weaker than a render on purpose: a screenshot of a loading screen is a legitimate
    capture, and §PW25 is about the settings that produced it rather than its content.
    The floor is still required, because the coverage it reports is measured against it
    and a number invented here would be the second home §PW40 is about.
    """
    image = as_image(subject)
    _check_size(image, size, code="post.capture-size", what="capture")
    measured = _measure(image, alpha_floor)
    measured["path"] = str(image.path) if image.path else None
    return measured
