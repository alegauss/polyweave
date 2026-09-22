"""What must be true of a picture before the operation that made it returns.

A render that came out empty, black or transparent is the cheapest failure there is to
detect and the most expensive one to find two steps downstream, where the evidence of
which step broke has already been overwritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..errors import PolyweaveError
from ..image import Image, load

ACCEPTS_RENDER = frozenset({"size", "alpha_floor", "allow_uniform"})
ACCEPTS_TEXTURE = frozenset({"size", "alpha_floor", "allow_uniform"})
ACCEPTS_CAPTURE = frozenset({"size"})


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
    allow_uniform: bool,
) -> np.ndarray:
    """Not fully transparent, and not one flat colour.

    The two codes are passed in rather than assembled from `what`: a code is part of the
    published contract, and one built at runtime is one nothing can enumerate.
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
    if len(visible) and bool((visible.min(axis=0) == visible.max(axis=0)).all()):
        colour = "#" + "".join(f"{int(v):02x}" for v in visible[0])
        raise PolyweaveError(
            uniform,
            f"every visible pixel of the {what} is {colour}, so it carries no image",
            f"the scene was empty or the light never fired; if a flat {colour} is what "
            f"was wanted, pass allow_uniform=True",
        )
    return mask


def check_render(
    subject: Any,
    *,
    size: Any = None,
    alpha_floor: float = 0.0,
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
        allow_uniform=allow_uniform,
    )
    return _measure(image, alpha_floor)


def check_texture(
    subject: Any,
    *,
    size: Any = None,
    alpha_floor: float = 0.0,
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
        allow_uniform=allow_uniform,
    )
    return _measure(image, alpha_floor)


def check_capture(subject: Any, *, size: Any = None) -> dict:
    """The named artefact exists on disk and is a readable image.

    Weaker than a render on purpose: a screenshot of a loading screen is a legitimate
    capture, and §PW25 is about the settings that produced it rather than its content.
    """
    image = as_image(subject)
    _check_size(image, size, code="post.capture-size", what="capture")
    measured = _measure(image, 0.0)
    measured["path"] = str(image.path) if image.path else None
    return measured
