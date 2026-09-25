"""A bought picture put on the project's grid when it arrives (§PW171).

A picture service returns an image at a size it chose, with a margin it chose, centred
where it chose. An icon or a flat sprite needs the project's cell, the project's padding
and an alpha edge that sits cleanly on the game's own background. That is the same kind
of work as turning a mesh round until it faces forward, and it gets the same answer: it
is mechanical, so it happens on arrival, once, and is recorded as one transform.

The family's `[style]` says what the grid is (`cell`, `margin`, `anchor`, `filter`), so
nothing about any one game is compiled in. The original stays on file with its digest,
named as the fitted file's input, so a change to the cell is one refit and never one
more purchase.
"""

from __future__ import annotations

from typing import Annotated

import numpy as np

from . import provenance, style
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: How far out, in pixels, the fringe's colour is taken from the opaque subject. A
#: generator's halo is a pixel or two wide; this covers it with room.
DEFRINGE_REACH = 16

#: At or above this alpha a pixel is the subject's own colour and not a blend.
OPAQUE = 0.98


@operation("picture.fit")
def fit(
    picture: Annotated[str, Param("the picture as it arrived, under the project")],
    out: Annotated[str, Param("where the fitted picture the engine loads is written")],
    *,
    family: Annotated[str, Param("the asset family, needed only among several")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Put a picture on its family's grid: defringed, trimmed, fitted and anchored.

    The fringe's colour is replaced by the subject's own, so a halo of the generator's
    background never reaches the engine, and it is measured before and after. The
    subject is trimmed to its alpha, scaled to fit the cell inside the margin with the
    family's filter (`pixel` is never smoothed and is quantised to the palette), and
    placed at the anchor. The whole transform is on the fitted file's record.
    """
    from PIL import Image as PILImage

    from .image import Image
    from .image import load as load_image

    config = load(root)
    here = config.root
    name, declared = config.style(family)
    floor = config.tolerances().alpha_floor
    source = here / picture
    image = load_image(source)
    subject = image.subject(floor)
    if not subject.any():
        raise PolyweaveError(
            "style.no-subject",
            f"{picture} has no pixel above the alpha floor to fit",
            "check the picture is the asset and not an empty frame",
        )
    before = _halo(image, floor)
    cleaned = Image(path=image.path, rgba=_defringed(image.rgba), had_alpha=True)
    after = _halo(cleaned, floor)

    rows, columns = np.nonzero(subject)
    box = (
        int(columns.min()),
        int(rows.min()),
        int(columns.max()) + 1,
        int(rows.max()) + 1,
    )
    trimmed = PILImage.fromarray(cleaned.rgba).crop(box)

    margin = int(declared["margin"])
    cell = list(declared["cell"]) or [
        trimmed.width + 2 * margin,
        trimmed.height + 2 * margin,
    ]
    room = (cell[0] - 2 * margin, cell[1] - 2 * margin)
    if room[0] <= 0 or room[1] <= 0:
        raise PolyweaveError(
            "config.bad-type",
            f"the {name} style's margin of {margin} leaves no room in a {cell} cell",
            "make the margin less than half the cell",
        )
    scale = min(room[0] / trimmed.width, room[1] / trimmed.height)
    size = (max(1, round(trimmed.width * scale)), max(1, round(trimmed.height * scale)))
    pixel = declared["filter"] == "pixel"
    resized = trimmed.resize(
        size,
        PILImage.Resampling.NEAREST if pixel else PILImage.Resampling.LANCZOS,
    )
    rgba = np.asarray(resized).copy()
    if pixel:
        rgba = _hard(rgba, declared.get("palette") or [], floor)

    across = (cell[0] - size[0]) // 2
    down = (
        (cell[1] - size[1]) // 2
        if declared["anchor"] == "centre"
        else (cell[1] - margin - size[1])
    )
    canvas = PILImage.new("RGBA", tuple(cell), (0, 0, 0, 0))
    canvas.paste(PILImage.fromarray(rgba), (across, down))
    target = here / out
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)

    transform = {
        "family": name,
        "trim": list(box),
        "scale": round(scale, 6),
        "size": list(size),
        "offset": [across, down],
        "cell": cell,
        "margin": margin,
        "anchor": declared["anchor"],
        "filter": declared["filter"],
        "halo_delta_e": {"before": before, "after": after},
    }
    provenance.write(
        provenance.build(
            "picture",
            target,
            inputs=[provenance.source("original", source, root=here)],
            extra={"transform": transform},
            root=here,
        ),
        root=here,
    )
    return {"picture": picture, "out": provenance.relative(target, here), **transform}


def _halo(image, floor: float) -> float:
    from .measure import to_lab

    rgb = image.rgba[..., :3].astype(np.float64) / 255.0
    edge = style._edge(image, image.subject(floor), to_lab(rgb), floor)
    return edge["halo_delta_e"] or 0.0


def _defringed(rgba: np.ndarray) -> np.ndarray:
    """Every blended pixel given the colour of the nearest opaque one; alpha kept.

    A cut-out's soft edge carries the colour of whatever it was cut from, which on a
    game's own background reads as a halo. Growing the opaque subject's colours outward
    over the fringe replaces that colour and keeps the edge's softness, which is alpha.
    """
    out = rgba.copy()
    colour = rgba[..., :3].astype(np.int32)
    known = rgba[..., 3] >= round(OPAQUE * 255)
    if not known.any():
        return out
    for _ in range(DEFRINGE_REACH):
        grown = known.copy()
        for axis, step in ((0, 1), (0, -1), (1, 1), (1, -1)):
            shifted_known = _shifted(known, step, axis)
            shifted_colour = _shifted(colour, step, axis)
            take = shifted_known & ~grown
            colour[take] = shifted_colour[take]
            grown |= take
        settled = grown.all() or bool((grown == known).all())
        known = grown
        if settled:
            break
    out[..., :3] = np.clip(colour, 0, 255).astype(np.uint8)
    return out


def _shifted(values: np.ndarray, step: int, axis: int) -> np.ndarray:
    """`values` moved one pixel along an axis, nothing coming in from the far edge."""
    out = np.zeros_like(values)
    ahead = [slice(None)] * values.ndim
    behind = [slice(None)] * values.ndim
    if step > 0:
        ahead[axis], behind[axis] = slice(1, None), slice(None, -1)
    else:
        ahead[axis], behind[axis] = slice(None, -1), slice(1, None)
    out[tuple(ahead)] = values[tuple(behind)]
    return out


def _hard(rgba: np.ndarray, palette: list[str], floor: float) -> np.ndarray:
    """Pixel art's own edge: alpha all or nothing, colour taken from the palette."""
    from .measure import from_hex, to_lab

    out = rgba.copy()
    solid = out[..., 3] > round(floor * 255)
    out[..., 3] = np.where(solid, 255, 0).astype(np.uint8)
    if palette and solid.any():
        swatches = np.array([from_hex(c) for c in palette])
        lab = to_lab(out[..., :3][solid].astype(np.float64) / 255.0)
        nearest = np.linalg.norm(
            lab[:, None, :] - to_lab(swatches)[None], axis=-1
        ).argmin(axis=1)
        out[..., :3][solid] = np.round(swatches[nearest] * 255).astype(np.uint8)
    return out
