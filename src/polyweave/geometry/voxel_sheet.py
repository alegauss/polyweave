"""A voxel model looked at in milliseconds, with no renderer (§PW94).

Authoring a shape is dozens of small edits, and each one wants a look. A render costs
Blender and seconds; cells are already an image. So a build draws four views of what it
made, straight from the grid, and the agent reads the picture, edits the declaration and
looks again inside one turn.

**Flat colour, no light, no engine.** An orthographic view is the nearest cell along
each pixel column in its palette colour; the isometric one is each cell's top and two
sides, the sides a step darker so the faces part. That replaces no renderer, only skips
one for a draft, which keeps it inside "Replacing Blender, Godot or the generative
service": the final look stays the render ladder's and the engine's. It is to a voxel
model what the readback in words is to a declaration — the cheapest look that can still
be disagreed with.

The views follow the axes every document shares: Y up and −Z forward. So the front view
looks along +Z, the side view in from +X, and the top view down from +Y with the front
at the bottom of the picture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

__all__ = ["SUFFIX", "sheet"]

#: What the sheet is written as, beside the cells.
SUFFIX = ".voxels.png"

#: What a cell wears when its material names no colour.
UNPAINTED = (154, 154, 154)

_PAPER = (244, 243, 240)
_INK = (60, 60, 60)
_GRID = (0, 0, 0, 40)
_MARGIN = 12
_CAPTION = 16

#: How much light each side of an isometric cube keeps: top, right, front.
_SHADE = (1.0, 0.78, 0.6)


def _rgb(entry: dict) -> tuple[int, int, int]:
    """A palette entry's colour, read off whichever key its material spells it with."""
    for key in ("colour", "color", "base_color"):
        stated = entry.get(key)
        if isinstance(stated, str) and len(stated.lstrip("#")) >= 6:
            hexed = stated.lstrip("#")
            return tuple(int(hexed[i : i + 2], 16) for i in (0, 2, 4))
        if isinstance(stated, list | tuple) and len(stated) >= 3:
            scale = 255.0 if max(float(v) for v in stated[:3]) <= 1.0 else 1.0
            return tuple(int(round(float(v) * scale)) for v in stated[:3])
    return UNPAINTED


def _grids(model: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The model as three arrays over its grid: filled, palette slot and node."""
    size = tuple(model["size"])
    cells = model["cells"]
    where = tuple(np.asarray([cells[a] for a in "xyz"], dtype=int))
    filled = np.zeros(size, dtype=bool)
    slot = np.full(size, -1, dtype=int)
    node = np.full(size, -1, dtype=int)
    if len(cells["x"]):
        filled[where] = True
        slot[where] = cells["palette"]
        node[where] = cells["node"]
    return filled, slot, node


def _nearest(filled: np.ndarray, slot: np.ndarray, axis: int, reverse: bool):
    """Along one axis, the slot of the first filled cell seen, or -1 where none is."""
    if reverse:
        filled, slot = np.flip(filled, axis), np.flip(slot, axis)
    first = np.argmax(filled, axis=axis)
    seen = np.take_along_axis(slot, np.expand_dims(first, axis), axis).squeeze(axis)
    return np.where(filled.any(axis=axis), seen, -1)


def _orthographic(filled: np.ndarray, slot: np.ndarray) -> dict[str, np.ndarray]:
    """Front, side and top, each as rows top to bottom and columns left to right."""
    # Front: along +Z from the -Z side, so x runs right and y runs up.
    front = _nearest(filled, slot, 2, reverse=False)  # [x, y]
    # Side: in from +X, so -z runs right and y runs up.
    side = _nearest(filled, slot, 0, reverse=True)  # [y, z]
    # Top: down from +Y, x running right and the front (-z) at the bottom, where a
    # drawing puts the edge nearest the front view.
    top = _nearest(filled, slot, 1, reverse=True)  # [x, z]
    return {
        "front": np.flipud(front.T),
        "side": np.flipud(np.fliplr(side)),
        "top": np.flipud(top.T),
    }


def _paint(view: np.ndarray, colours: np.ndarray, pixels: int, grid: bool):
    """One view as an image, a cell to `pixels` square."""
    rows, columns = view.shape
    image = np.zeros((rows, columns, 4), dtype=np.uint8)
    inked = view >= 0
    image[inked, :3] = colours[view[inked]]
    image[inked, 3] = 255
    image = np.repeat(np.repeat(image, pixels, axis=0), pixels, axis=1)
    picture = Image.fromarray(image, "RGBA")
    if grid and pixels >= 4:
        draw = ImageDraw.Draw(picture, "RGBA")
        for x in range(0, columns * pixels + 1, pixels):
            draw.line([(x, 0), (x, rows * pixels)], fill=_GRID)
        for y in range(0, rows * pixels + 1, pixels):
            draw.line([(0, y), (columns * pixels, y)], fill=_GRID)
    return picture


def _isometric(filled: np.ndarray, slot: np.ndarray, colours: np.ndarray, pixels: int):
    """Each cell's top, right and front, drawn back to front."""
    across, deep = np.cos(np.pi / 6) * pixels, np.sin(np.pi / 6) * pixels
    nx, ny, nz = filled.shape

    def at(x: float, y: float, z: float) -> tuple[float, float]:
        toward = nz - z  # -Z is toward the viewer
        return ((x - toward) * across, (x + toward) * deep - y * pixels)

    corners = [at(x, y, z) for x in (0, nx) for y in (0, ny) for z in (0, nz)]
    low = np.min(corners, axis=0)
    high = np.max(corners, axis=0)
    wide, tall = (int(np.ceil(v)) + 2 for v in high - low)
    picture = Image.new("RGBA", (wide, tall), (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)

    def place(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] - low[0] + 1, point[1] - low[1] + 1)

    padded = np.pad(filled, 1)
    where = np.argwhere(filled)
    # Back to front: the viewer is at +X, +Y and -Z, so larger x and y and smaller z
    # are nearer and are drawn last.
    where = where[np.argsort(where[:, 0] + where[:, 1] - where[:, 2], kind="stable")]
    for x, y, z in where:
        colour = np.asarray(colours[slot[x, y, z]], dtype=float)
        faces = []
        if not padded[x + 1, y + 2, z + 1]:
            faces.append(
                (
                    0,
                    [
                        (x, y + 1, z),
                        (x + 1, y + 1, z),
                        (x + 1, y + 1, z + 1),
                        (x, y + 1, z + 1),
                    ],
                )
            )
        if not padded[x + 2, y + 1, z + 1]:
            faces.append(
                (
                    1,
                    [
                        (x + 1, y, z),
                        (x + 1, y + 1, z),
                        (x + 1, y + 1, z + 1),
                        (x + 1, y, z + 1),
                    ],
                )
            )
        if not padded[x + 1, y + 1, z]:
            faces.append(
                (2, [(x, y, z), (x + 1, y, z), (x + 1, y + 1, z), (x, y + 1, z)])
            )
        for shade, quad in faces:
            fill = tuple(int(round(v * _SHADE[shade])) for v in colour) + (255,)
            draw.polygon([place(at(*one)) for one in quad], fill=fill)
    return picture


def _labels(picture: Image.Image, model: dict, filled, node, pixels: int) -> None:
    """Each node's id on the front view, over a cell of its that the view shows.

    Only what is seen is named: a label over a node hidden behind another reads as the
    other one's name. And it sits on the shown cell nearest the node's middle, because
    the middle itself of a node in two halves, like a pair of wings, is the gap between.
    """
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default()
    seen = _orthographic(filled, node)["front"]
    for index, name in enumerate(model["nodes"]):
        shown = np.argwhere(seen == index)
        if not len(shown):
            continue
        middle = shown.mean(axis=0)
        row, column = shown[np.argmin(((shown - middle) ** 2).sum(axis=1))]
        draw.text(
            ((column + 0.5) * pixels, (row + 0.5) * pixels),
            name,
            fill=_INK,
            font=font,
            anchor="mm",
        )


def sheet(
    model: dict,
    out: str | Path,
    *,
    pixels: int = 8,
    grid: bool = False,
    labels: bool = False,
) -> dict:
    """Front, side, top and isometric views of a voxel model, as one PNG.

    `pixels` is how many a cell is drawn at. `grid` rules the cell edges on the three
    flat views, and `labels` writes each node's id where its cells are on the front one.
    """
    filled, slot, node = _grids(model)
    colours = np.asarray([_rgb(entry) for entry in model["palette"]] or [UNPAINTED])
    views = {
        name: _paint(view, colours, pixels, grid)
        for name, view in _orthographic(filled, slot).items()
    }
    if labels:
        _labels(views["front"], model, filled, node, pixels)
    views["iso"] = _isometric(filled, slot, colours, pixels)

    wide = sum(view.width for view in views.values()) + _MARGIN * (len(views) + 1)
    tall = max(view.height for view in views.values()) + _MARGIN * 2 + _CAPTION
    picture = Image.new("RGB", (wide, tall), _PAPER)
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default()
    left = _MARGIN
    for name, view in views.items():
        draw.text((left, _MARGIN), name, fill=_INK, font=font)
        picture.paste(view, (left, _MARGIN + _CAPTION), view)
        left += view.width + _MARGIN

    where = Path(out)
    where.parent.mkdir(parents=True, exist_ok=True)
    picture.save(where)
    return {"sheet": str(where), "size": [wide, tall], "views": list(views)}


def beside(cells: Path) -> Path:
    """Where a sheet goes, given where its cells were written."""
    from .voxels import SUFFIX as CELLS

    return cells.with_name(cells.name[: -len(CELLS)] + SUFFIX)


def options(given: Any) -> dict:
    """The sheet's own settings out of a write's keyword arguments."""
    return {k: given.pop(k) for k in ("pixels", "grid", "labels") if k in given}
