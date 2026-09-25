"""Putting an asset where it will actually be seen.

The evidence is §PW10: Cottony's first modelled prop looked right in isolation and then
sat on a sheet beside five drawn siblings that each had a soft specular window and a
shadow beneath them. It had a pin-point highlight and it floated. **Nothing in a solo
render shows that**, and no measurement of a lone file can reach it.

Two forms, both cheap:

    sheet(["new.png", "sibling-a.png", …])   the odd one out, visible at a glance
    place("new.png", into="screen.png", …)   the asset in the screen it belongs to

What either returns is an image like any other, so the comparison runs against the
composite rather than against the asset's own file — which is the whole point.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from PIL import Image as PILImage

from .describe import Param, operation
from .errors import PolyweaveError
from .image import Image, load

#: Where an asset sits in the box it is given. `footprint` puts the base of the
#: silhouette on the bottom edge, which is §6's origin and what stops a prop floating.
ANCHORS = ("footprint", "centre")


def _as_pil(subject: Any) -> PILImage.Image:
    if isinstance(subject, Image):
        return PILImage.fromarray(subject.rgba, "RGBA")
    return PILImage.fromarray(load(subject).rgba, "RGBA")


def _as_image(pil: PILImage.Image, path: Path | None = None) -> Image:
    return Image(path=path, rgba=np.asarray(pil, dtype=np.uint8), had_alpha=True)


def fit(pil: PILImage.Image, box: tuple[int, int]) -> PILImage.Image:
    """Scale to fit inside `box` without distorting it."""
    width, height = box
    scale = min(width / pil.width, height / pil.height)
    size = (max(1, round(pil.width * scale)), max(1, round(pil.height * scale)))
    return pil.resize(size, PILImage.LANCZOS)


def sheet(
    tiles: Sequence[Any],
    *,
    columns: int | None = None,
    cell: int = 256,
    gap: int = 12,
    background: Sequence[int] = (0, 0, 0, 0),
    out: str | Path | None = None,
) -> Image:
    """Lay assets out side by side, so the one that does not belong stands out.

    Every tile gets the same cell and is anchored on its footprint, because a prop that
    floats is exactly the failure this is for and a centred layout would hide it.
    """
    if not tiles:
        raise PolyweaveError(
            "compose.no-tiles",
            "a contact sheet of nothing shows nothing",
            "pass the asset and the siblings it will be seen beside",
        )
    across = columns or math.ceil(math.sqrt(len(tiles)))
    down = math.ceil(len(tiles) / across)
    width = across * cell + (across + 1) * gap
    height = down * cell + (down + 1) * gap
    canvas = PILImage.new("RGBA", (width, height), tuple(background))

    for index, tile in enumerate(tiles):
        scaled = fit(_as_pil(tile), (cell, cell))
        row, column = divmod(index, across)
        left = gap + column * (cell + gap) + (cell - scaled.width) // 2
        # Sitting on the bottom of its cell, so a missing shadow reads as a gap.
        top = gap + row * (cell + gap) + (cell - scaled.height)
        canvas.alpha_composite(scaled, (left, top))

    return _write(canvas, out)


def place(
    asset: Any,
    into: Any,
    *,
    at: Sequence[int] = (0, 0),
    width: int | None = None,
    anchor: str = "footprint",
    out: str | Path | None = None,
) -> Image:
    """Composite an asset into a real capture of the screen it belongs to.

    `at` is where in the capture, in its own pixels. `width` is the size it will
    actually be drawn at, which is the other half of the question: detail that exists in
    the file and not on the screen is the failure `luma_bands` measures.
    """
    if anchor not in ANCHORS:
        raise PolyweaveError(
            "compose.unknown-anchor",
            f"there is no {anchor!r} anchor",
            f"use one of {', '.join(ANCHORS)}",
            given=anchor,
            allowed=ANCHORS,
        )
    canvas = _as_pil(into).copy()
    scaled = _as_pil(asset)
    if width:
        scale = width / scaled.width
        scaled = scaled.resize(
            (width, max(1, round(scaled.height * scale))), PILImage.LANCZOS
        )
    x, y = (int(v) for v in at)
    left = x - scaled.width // 2
    top = y - scaled.height if anchor == "footprint" else y - scaled.height // 2
    if not _overlaps(canvas, scaled, left, top):
        raise PolyweaveError(
            "compose.outside",
            f"the asset lands entirely outside a "
            f"{canvas.width}x{canvas.height} capture",
            f"place it within the capture; at={list(at)} put its box at "
            f"({left}, {top})",
        )
    canvas.alpha_composite(scaled, (max(0, left), max(0, top)))
    return _write(canvas, out)


def _overlaps(canvas, scaled, left: int, top: int) -> bool:
    return (
        left < canvas.width
        and top < canvas.height
        and left + scaled.width > 0
        and top + scaled.height > 0
    )


def _write(canvas: PILImage.Image, out: str | Path | None) -> Image:
    if out is None:
        return _as_image(canvas)
    where = Path(out)
    where.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(where)
    return _as_image(canvas, where)


def _landed(made: Image, out: str) -> dict:
    return {"out": str(made.path or out), "size": [made.width, made.height]}


@operation("compose.place")
def placed(
    asset: Annotated[str, Param("the asset's picture, by path")],
    into: Annotated[str, Param("the scene or background it is put in, by path")],
    *,
    out: Annotated[str, Param("where the composed picture is written")],
    at: Annotated[list, Param("where it stands, [x, y] in pixels")] = (0, 0),
    width: Annotated[int, Param("the width it is drawn at, if not its own")] = None,
    anchor: Annotated[
        str, Param("what `at` names", choices=ANCHORS)
    ] = "footprint",
) -> dict:
    """An asset put where it will actually be seen, and written to a file."""
    made = place(asset, into, at=tuple(at), width=width, anchor=anchor, out=out)
    return _landed(made, out)


@operation("compose.sheet")
def sheeted(
    tiles: Annotated[list, Param("the pictures to lay out, by path")],
    *,
    out: Annotated[str, Param("where the sheet is written")],
    columns: Annotated[int, Param("how many across; square if unset")] = None,
    cell: Annotated[int, Param("each tile's cell", lo=8, unit="px")] = 256,
) -> dict:
    """Several pictures laid out on one sheet, in order, and written to a file."""
    return _landed(sheet(tiles, columns=columns, cell=cell, out=out), out)
