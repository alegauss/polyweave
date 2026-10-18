"""Bake the two trays through the plugin, framed by the game's numbers, and check they land.

    python tools/art/frame_trays.py

polyweave §PW78. The board tray and the booster tray are the two assets whose framing is not
a matter of taste: board.gd addresses a cell at CELL := 112, so the board's wells have to sit
on that grid, and the booster tray is its drawing's own size so the game centres it where it
always has. bake_model.py holds both with `plate`, a world rectangle given outright.

The plugin's equivalent is `covers` given as a place, `[x0, y0, x1, y1]`. Given as a size it
is centred on whatever the model's bounds come to, and a wall or a bulge on one side moves the
frame with it. **The rectangle comes from the game here, never from the render**: the board's
from CELL, BOARD_PAD and LIFT, the booster tray's from the drawing it is inflated from.

Nothing here writes to docs/design/art/. The pictures land in .polyweave/trays/ and are
compared: the board's silhouette with the shipped sprite's, to the pixel, and the booster
tray's with its drawing's body, whose centre it has to stand on. The look is a person's call
and the next step, not this one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy  # noqa: F401 - tray_model imports bmesh, which only exists once bpy has loaded
import polyweave
from PIL import Image
from polyweave import geometry, measure, render
from polyweave.geometry import build
from polyweave.image import load

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tray_model

ROOT = Path(__file__).resolve().parents[2]
WORK = ".polyweave/trays"
CELL = float(tray_model.CELL)

## how far a tray's silhouette may stand from where the shipped one does, in pixels
BOARD_EXACT = 0.0
BOOSTER_CENTRED = 1.0


class Quiet:
    """A bake reports its stages; a check that bakes two things has nobody to tell."""

    def stage(self, *_, **__):
        pass

    def progress(self, *_, **__):
        pass

    def note(self, *_):
        pass


def board_rectangle() -> list[float]:
    """The board's plate, in the declaration's cells: centred on the face box, y up."""
    half = tray_model.BOARD / 2.0
    return [-half / CELL, (half - tray_model.HEIGHT) / CELL, half / CELL, half / CELL]


DRAWN = ROOT / "tools/art/3d/booster_tray.drawn.png"


def booster_rectangle() -> list[float]:
    """The drawing's own pixels, which the plugin lays centred on the origin."""
    wide, tall = load(DRAWN).size
    return [-wide / 2 / CELL, -tall / 2 / CELL, wide / 2 / CELL, tall / 2 / CELL]


def booster_body() -> str:
    """The drawing's body alone, past half its alpha, as the shape to stand on.

    Not the shipped sprite and not the whole drawing: both carry a soft drop shadow below
    the cushion, which pulls their centre 11 px down from the body the game places.
    """
    alpha = load(DRAWN).rgba[..., 3]
    body = ((alpha > 127) * 255).astype("uint8")
    where = ROOT / WORK / "booster_tray.body.png"
    Image.merge("RGBA", [Image.fromarray(body, "L")] * 4).save(where)
    return str(where)


def bake(name: str, covers: list[float]) -> Path:
    declared = geometry.read(f"tools/art/{name}.toml", root=ROOT)
    build.write(declared, f"{WORK}/{name}.glb", root=ROOT)
    render.bake(
        Quiet(),
        out=f"{WORK}/{name}.png",
        model=f"{WORK}/{name}.glb",
        rung="final",
        covers=covers,
        azimuth=0.0,
        elevation=0.0,
        inline=False,
        root=str(ROOT),
    )
    return ROOT / WORK / f"{name}.png"


def against(picture: Path, reference: str) -> dict[str, float]:
    names = ("silhouette_iou", "silhouette_bbox_delta", "silhouette_centroid_offset")
    return {
        name: measure.measure(picture, [name], region="frame", against=reference, root=ROOT)[0]["value"]
        for name in names
    }


def main() -> int:
    polyweave.readable()
    board = against(bake("board_tray", board_rectangle()), "docs/design/art/ui/board_panel.png")
    booster = against(bake("booster_tray", booster_rectangle()), booster_body())
    for name, found in (("board_tray", board), ("booster_tray", booster)):
        print(
            f"  {name:<13} iou {found['silhouette_iou']:.4f}, "
            f"box off by {found['silhouette_bbox_delta']:g} px, "
            f"centre off by {found['silhouette_centroid_offset']:.2f} px"
        )
    lands = (
        board["silhouette_bbox_delta"] <= BOARD_EXACT
        and booster["silhouette_centroid_offset"] <= BOOSTER_CENTRED
    )
    print("both trays land where the game puts them" if lands else "a tray is off its place")
    return 0 if lands else 1


if __name__ == "__main__":
    sys.exit(main())
