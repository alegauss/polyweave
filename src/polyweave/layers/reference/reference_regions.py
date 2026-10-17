"""A reference video's fixed places, declared once, and its minimap read (§PW380).

In Resogun the radar strip at the top shows the whole cylinder, and it is the only place
a video says what spawns off camera and on which side; in a full frame it is a few dozen
pixels high, so reading it from a contact sheet guesses more than it reads. The score,
the multiplier and the humans counter sit in fixed places too.

A project declares those places once, as `[reference.<name>]` in polyweave.toml: the
frame `size` they were measured on, and `regions` as rectangles in its pixels.
`reference.regions` lays each region out on sheets of its own, enlarged with nearest
neighbour so a dot stays a dot. `reference.minimap` reads the region declared as the
minimap: each blip of a declared colour per frame, placed on the map's declared shape (a
`strip` whose ends meet, or a flat `rect`) and measured from the player's own blip, so
"left" and "right" of the player come out as data. Nothing here knows a game: the
regions, the shape and the colours are the project's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

from .reference_objects import _manifest, detect

#: How many region tiles a sheet holds, four by four, as the frames' own sheets do.
GRID = 4


def _frames(frames: str, reference: str, root: str):
    """The frames and the reference's declaration, the frames checked to its size."""
    from PIL import Image as Pil

    config = load(root)
    here = config.root
    manifest, listed = _manifest(frames, here)
    name, declared = config.reference(reference or None)
    shown = listed.get("frames", [])
    if shown:
        with Pil.open(manifest.parent / shown[0]["file"]) as first:
            size = list(first.size)
        if size != declared["size"]:
            raise PolyweaveError(
                "capture.wrong-size",
                f"the frames are {size[0]}x{size[1]}, and [reference.{name}] was "
                f"declared at {declared['size'][0]}x{declared['size'][1]}",
                "read the frames from the video the regions were measured on, or "
                "declare the reference at this size",
                given=f"{size[0]}x{size[1]}",
            )
    return here, manifest, listed, name, declared


def _crop(path: Path, box: list):
    from PIL import Image as Pil

    with Pil.open(path) as frame:
        return frame.convert("RGB").crop(tuple(int(v) for v in box))


@operation("reference.regions")
def regions(
    frames: Annotated[
        str, Param("the folder reference.frames wrote, or its frames.json")
    ],
    *,
    reference: Annotated[
        str, Param("the [reference.<name>] with the regions; the only one if empty")
    ] = "",
    scale: Annotated[int, Param("how many times each region is enlarged", lo=1)] = 4,
    root: Annotated[str, Param("the project the frames are under")] = ".",
) -> dict:
    """Each region a reference declares, laid out enlarged on sheets of its own.

    Sixteen moments of the region a sheet, each tile enlarged by `scale` with nearest
    neighbour so a radar's dots stay dots, its time written on it. Frames of another
    size than the regions were declared at are refused.
    """
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    here, manifest, listed, name, declared = _frames(frames, reference, root)
    folder = manifest.parent
    font = ImageFont.load_default(size=14)
    shown = listed.get("frames", [])
    made: dict[str, list[str]] = {}
    for region, box in declared["regions"].items():
        for old in folder.glob(f"region_{region}_*.png"):
            old.unlink()
        sheets = []
        per = GRID * GRID
        for start in range(0, len(shown), per):
            tiles = []
            for one in shown[start:start + per]:
                part = _crop(folder / one["file"], box)
                tile = part.resize((part.width * scale, part.height * scale),
                                   Pil.Resampling.NEAREST)
                draw = ImageDraw.Draw(tile)
                draw.rectangle((0, 0, 64, 16), fill=(0, 0, 0))
                draw.text((3, 1), f"{one['ms'] / 1000:.2f}s", fill=(255, 220, 90),
                          font=font)
                tiles.append(tile)
            wide = max(t.width for t in tiles)
            tall = max(t.height for t in tiles)
            columns = 1 if wide > 4 * tall else GRID
            rows = -(-len(tiles) // columns)
            sheet = Pil.new("RGB", (columns * wide, rows * tall), (20, 20, 20))
            for i, tile in enumerate(tiles):
                sheet.paste(tile, ((i % columns) * wide, (i // columns) * tall))
            target = folder / f"region_{region}_{start // per + 1:03d}.png"
            sheet.save(target)
            sheets.append(provenance.relative(target, here))
        made[region] = sheets
    return {"reference": name, "regions": made,
            "says": f"{len(declared['regions'])} regions of [reference.{name}] over "
            f"{len(shown)} frames, enlarged {scale} times"}


def _place(x: float, y: float, box: list) -> tuple[float, float]:
    """A blip's place on the map, as shares of the minimap's width and height."""
    return (x - box[0]) / (box[2] - box[0]), (y - box[1]) / (box[3] - box[1])


@operation("reference.minimap")
def minimap(
    frames: Annotated[
        str, Param("the folder reference.frames wrote, or its frames.json")
    ],
    *,
    reference: Annotated[
        str, Param("the [reference.<name>] with the minimap; the only one if empty")
    ] = "",
    root: Annotated[str, Param("the project the frames are under")] = ".",
) -> dict:
    """Each blip on a minimap per frame placed and measured from the player.

    On a `strip` map a place is an angle round it, 0 to 360, and each blip's angle from
    the player's, -180 to 180, says on which side it is; on a `rect` map it is the share
    across and down, and the offset from the player. minimap.json lands beside the
    frames, recorded, with how many of each blip stood on each side frame by frame.
    """
    here, manifest, listed, name, declared = _frames(frames, reference, root)
    region = declared["minimap"]
    if not region:
        raise PolyweaveError(
            "capture.unknown-region",
            f"[reference.{name}] declares no minimap",
            f"set its minimap to one of {', '.join(sorted(declared['regions']))}",
            allowed=sorted(declared["regions"]),
        )
    box = declared["regions"][region]
    least, most = declared["blip_size"]

    def kind(colour: str) -> dict:
        rgb = colour.lstrip("#")
        return {"rgb": [int(rgb[i:i + 2], 16) for i in (0, 2, 4)],
                "tolerance": float(declared["tolerance"]),
                "size": [float(least), float(most)]}

    kinds = {f"blip:{k}": kind(v) for k, v in declared["blips"].items()}
    if declared["player"]:
        kinds["player"] = kind(declared["player"])
    strip = declared["map"] == "strip"
    read = []
    for one in listed.get("frames", []):
        part = np.asarray(_crop(manifest.parent / one["file"], box))
        found = detect(part, kinds, 1.0)
        player = max((f for f in found if f["kind"] == "player"),
                     key=lambda f: f["area"], default=None)
        mine = (_place(player["x"] + box[0], player["y"] + box[1], box)
                if player else None)
        blips, sides = [], {}
        for f in found:
            if f["kind"] == "player":
                continue
            u, v = _place(f["x"] + box[0], f["y"] + box[1], box)
            blip = {"kind": f["kind"].removeprefix("blip:"), "u": round(u, 4),
                    "v": round(v, 4)}
            if strip:
                blip["angle"] = round(u * 360.0, 1)
                if mine:
                    turn = ((u - mine[0] + 0.5) % 1.0 - 0.5) * 360.0
                    blip["from_player"] = round(turn, 1)
                    blip["side"] = "left" if turn < 0 else "right"
            elif mine:
                blip["from_player"] = [round(u - mine[0], 4), round(v - mine[1], 4)]
                blip["side"] = "left" if u < mine[0] else "right"
            if "side" in blip:
                key = f"{blip['kind']}:{blip['side']}"
                sides[key] = sides.get(key, 0) + 1
            blips.append(blip)
        read.append({"at": one["ms"] / 1000,
                     "player": {"u": round(mine[0], 4), "v": round(mine[1], 4)}
                     if mine else None,
                     "blips": blips, "sides": sides})
    written = {"frames": provenance.relative(manifest, here), "reference": name,
               "region": region, "map": declared["map"], "read": read}
    target = manifest.parent / "minimap.json"
    target.write_text(json.dumps(written, indent=1) + "\n", encoding="utf-8",
                      newline="\n")
    provenance.write(provenance.build(
        "capture", target, engine={"name": "reference.minimap"},
        inputs=[provenance.source("frames", manifest, root=here)],
        params={"reference": name, "region": region, "box": box,
                "map": declared["map"], "player": declared["player"],
                "blips": declared["blips"], "tolerance": declared["tolerance"]},
        root=here,
    ), here)
    unseen = sum(1 for one in read if one["player"] is None)
    return {
        "minimap": provenance.relative(target, here),
        "frames": len(read),
        "player_unseen": unseen,
        "blips": sum(len(one["blips"]) for one in read),
        "says": f"{len(read)} frames of [reference.{name}]'s {region}; the player was "
        f"not found in {unseen}",
    }
