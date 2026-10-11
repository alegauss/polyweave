"""What moves in a reference video's frames, counted and followed (Â§PW379).

Rebuilding Resogun's first phase from a gameplay video (Spinhold, RK178) needs, per
stretch, the second each group appears, its count, formation and how it ends. Even with
`reference.frames`' contact sheets an agent counted twenty small enemies by eye in each
sheet, and a miscount reached the sheet the owner reviews.

`reference.objects` reads the frames `reference.frames` wrote and finds, in each, the
islands of colour the call's `kinds` declare: a colour, how far from it still counts,
and the size an object of that kind is. No genre and no game is built in; the kinds are
the project's, and they are kept in the record. Detections are joined across frames into
tracks, each with its first and last second, its path and how it ended (left the frame,
gone while inside it, or alive at the end), and tracks of one kind born close together
in time and place are a group, with a count and a rough formation. What it found is
written beside the frames as objects.json with its record, and a contact sheet with each
track's id drawn on, so the agent checks the data against the picture instead of
producing it. The transcription into a wave stays the agent's and the person's work.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The widest a frame is read at: an enemy a few pixels across survives, and labelling
#: islands in numpy stays a fraction of a second a frame.
READ_WIDTH = 480

#: How far from a kind's colour still counts, as a share of the widest RGB distance.
TOLERANCE = 0.12

#: A frame within this share of its width from an edge is at the edge.
EDGE = 0.04

_COLOUR = re.compile(r"#([0-9a-fA-F]{6})")


def _bad(what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("capture.bad-kinds", what, remedy, **extra)


def declared(kinds: Any) -> dict[str, dict]:
    """Each kind with its colour as RGB, its tolerance and its size range in pixels."""
    if not isinstance(kinds, dict) or not kinds:
        raise _bad("no kinds were declared",
                   'pass kinds, such as {"lander": {"colour": "#3fe8ff", '
                   '"size": [4, 400]}}')
    out = {}
    for name, kind in kinds.items():
        if not isinstance(kind, dict):
            raise _bad(f"kind {name!r} is not a table", "give it a colour and a size")
        found = _COLOUR.fullmatch(str(kind.get("colour", "")))
        if not found:
            raise _bad(f"kind {name!r} has colour {kind.get('colour')!r}",
                       "write its colour as #rrggbb")
        size = kind.get("size", [2, 10_000])
        if (not isinstance(size, list) or len(size) != 2
                or not all(isinstance(v, int | float) for v in size)
                or not 0 < size[0] <= size[1]):
            raise _bad(f"kind {name!r} has size {size!r}",
                       "write size as [least, most] pixels of the video's own frame")
        tolerance = kind.get("tolerance", TOLERANCE)
        if not isinstance(tolerance, int | float) or not 0 < tolerance <= 1:
            raise _bad(f"kind {name!r} has tolerance {tolerance!r}",
                       "write tolerance as a share from 0 to 1 of the widest colour "
                       "distance")
        rgb = found.group(1)
        out[str(name)] = {
            "colour": "#" + rgb.lower(),
            "rgb": [int(rgb[i:i + 2], 16) for i in (0, 2, 4)],
            "tolerance": float(tolerance),
            "size": [float(size[0]), float(size[1])],
        }
    return out


def islands(mask: np.ndarray) -> np.ndarray:
    """Each four-connected island of the mask labelled by its smallest flat index, and
    -1 outside it. Labels move to the smallest neighbour's until nothing changes."""
    tall, wide = mask.shape
    big = tall * wide
    labels = np.where(mask, np.arange(big).reshape(tall, wide), big)
    while True:
        least = labels.copy()
        least[1:, :] = np.minimum(least[1:, :], labels[:-1, :])
        least[:-1, :] = np.minimum(least[:-1, :], labels[1:, :])
        least[:, 1:] = np.minimum(least[:, 1:], labels[:, :-1])
        least[:, :-1] = np.minimum(least[:, :-1], labels[:, 1:])
        least = np.where(mask, least, big)
        if np.array_equal(least, labels):
            break
        labels = least
    return np.where(mask, labels, -1)


def detect(rgb: np.ndarray, kinds: dict[str, dict], scale: float) -> list[dict]:
    """Every object of every kind in one frame read at `scale` of the video's size,
    each with its centre and area in the video's own pixels."""
    found = []
    pixels = rgb[..., :3].astype(np.float64)
    widest = math.sqrt(3) * 255.0
    for name, kind in kinds.items():
        distance = np.sqrt(((pixels - np.array(kind["rgb"])) ** 2).sum(axis=2))
        labels = islands(distance <= kind["tolerance"] * widest)
        ids, counts = np.unique(labels[labels >= 0], return_counts=True)
        least, most = (v * scale * scale for v in kind["size"])
        for label, count in zip(ids, counts, strict=True):
            if not least <= count <= most:
                continue
            ys, xs = np.nonzero(labels == label)
            found.append({"kind": name, "x": round(float(xs.mean()) / scale, 1),
                          "y": round(float(ys.mean()) / scale, 1),
                          "area": round(float(count) / (scale * scale), 1)})
    return found


def tracked(
    seen: list[tuple[float, list[dict]]], reach: float, size: tuple
) -> list[dict]:
    """Detections joined across frames, nearest first, within `reach` pixels a second.

    `seen` is each frame's second and its detections, in order. A track ends where no
    detection of its kind is close enough in the next frame.
    """
    wide, tall = size
    open_: list[dict] = []
    done: list[dict] = []
    last_at = None
    for at, found in seen:
        step = reach * (at - last_at) if last_at is not None else 0.0
        pairs = sorted(
            (math.dist((t["path"][-1][1], t["path"][-1][2]), (d["x"], d["y"])), i, j)
            for i, t in enumerate(open_) for j, d in enumerate(found)
            if t["kind"] == d["kind"]
        )
        taken_t, taken_d = set(), set()
        for gap, i, j in pairs:
            if gap > step or i in taken_t or j in taken_d:
                continue
            taken_t.add(i)
            taken_d.add(j)
            open_[i]["path"].append([at, found[j]["x"], found[j]["y"]])
        still = []
        for i, track in enumerate(open_):
            (still if i in taken_t else done).append(track)
        for j, one in enumerate(found):
            if j not in taken_d:
                still.append({"kind": one["kind"], "path": [[at, one["x"], one["y"]]]})
        open_ = still
        last_at = at
    margin = EDGE * max(wide, tall)
    out = []
    for track in done + open_:
        _, x, y = track["path"][-1]
        if track in open_:
            ended = "alive"
        elif min(x, y, wide - x, tall - y) <= margin:
            ended = "left"
        else:
            ended = "gone"
        path = track["path"]
        out.append({"kind": track["kind"], "first": path[0][0], "last": path[-1][0],
                    "ended": ended, "path": path})
    out.sort(key=lambda t: (t["first"], t["path"][0][1], t["path"][0][2]))
    for number, track in enumerate(out, start=1):
        track["id"] = number
    return out


def formation(points: list[tuple[float, float]]) -> str:
    """A group's rough shape where it was born: line, ring or cluster."""
    if len(points) == 1:
        return "single"
    if len(points) == 2:
        return "pair"
    at = np.array(points, dtype=np.float64)
    centred = at - at.mean(axis=0)
    spread = np.linalg.svd(centred, compute_uv=False)
    if spread[0] > 0 and spread[1] / spread[0] < 0.2:
        return "line"
    radii = np.hypot(centred[:, 0], centred[:, 1])
    angles = np.sort(np.arctan2(centred[:, 1], centred[:, 0]))
    widest_gap = np.max(np.diff(np.concatenate([angles, angles[:1] + 2 * np.pi])))
    if (len(points) >= 4 and radii.mean() > 0 and radii.std() / radii.mean() < 0.25
            and widest_gap < np.pi * 0.75):
        return "ring"
    return "cluster"


def grouped(tracks: list[dict], together: float, apart: float) -> list[dict]:
    """Tracks of one kind born within `together` seconds and `apart` pixels of another
    in the group, joined: each group with when it was born, its count and formation."""
    parent = list(range(len(tracks)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(tracks):
        for j in range(i + 1, len(tracks)):
            b = tracks[j]
            if (a["kind"] == b["kind"] and abs(a["first"] - b["first"]) <= together
                    and math.dist(a["path"][0][1:], b["path"][0][1:]) <= apart):
                parent[root(i)] = root(j)
    members: dict[int, list[dict]] = {}
    for i, track in enumerate(tracks):
        members.setdefault(root(i), []).append(track)
    out = []
    for joined in sorted(members.values(), key=lambda g: min(t["first"] for t in g)):
        out.append({
            "kind": joined[0]["kind"],
            "born": min(t["first"] for t in joined),
            "count": len(joined),
            "formation": formation([tuple(t["path"][0][1:]) for t in joined]),
            "ended": {how: sum(t["ended"] == how for t in joined)
                      for how in ("left", "gone", "alive")},
            "tracks": [t["id"] for t in joined],
        })
    for number, group in enumerate(out, start=1):
        group["id"] = number
    return out


def _manifest(frames: str, here: Path) -> tuple[Path, dict]:
    where = Path(frames)
    where = where if where.is_absolute() else here / where
    if where.is_dir():
        where = where / "frames.json"
    if not where.is_file():
        raise PolyweaveError(
            "capture.no-reference-frames",
            f"there is no frames.json at {frames}",
            "name the folder reference.frames wrote, or its frames.json",
            given=str(frames),
        )
    return where, json.loads(where.read_text(encoding="utf-8"))


def _sheet(folder: Path, listed: list, tracks: list[dict]) -> list[Path]:
    """Contact sheets of the frames with each track's id drawn where it was seen."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    from .reference import SHEET_GRID, TILE

    for old in folder.glob("objects_*.png"):
        old.unlink()
    font = ImageFont.load_default(size=14)
    where_at: dict[float, list] = {}
    for track in tracks:
        for at, x, y in track["path"]:
            where_at.setdefault(at, []).append((track["id"], x, y))
    made = []
    per = SHEET_GRID * SHEET_GRID
    for start in range(0, len(listed), per):
        tiles = []
        for one in listed[start:start + per]:
            with Pil.open(folder / one["file"]) as frame:
                image = frame.convert("RGB")
            k = TILE / max(image.width, 1)
            tile = image.resize((TILE, max(1, round(image.height * k))))
            draw = ImageDraw.Draw(tile)
            for number, x, y in where_at.get(one["ms"] / 1000, []):
                cx, cy = x * k, y * k
                draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), outline=(255, 220, 90))
                draw.text((cx + 6, cy - 7), str(number), fill=(255, 220, 90), font=font)
            draw.rectangle((0, 0, 72, 16), fill=(0, 0, 0))
            draw.text((3, 1), f"{one['ms'] / 1000:.2f}s", fill=(255, 255, 255),
                      font=font)
            tiles.append(tile)
        tall = max(tile.height for tile in tiles)
        sheet = Pil.new("RGB", (SHEET_GRID * TILE, SHEET_GRID * tall), (20, 20, 20))
        for i, tile in enumerate(tiles):
            sheet.paste(tile, ((i % SHEET_GRID) * TILE, (i // SHEET_GRID) * tall))
        target = folder / f"objects_{start // per + 1:03d}.png"
        sheet.save(target)
        made.append(target)
    return made


@operation("reference.objects")
def objects(
    frames: Annotated[
        str, Param("the folder reference.frames wrote, or its frames.json")
    ],
    kinds: Annotated[
        dict,
        Param('each kind of object by name: {"colour": "#rrggbb", "size": [least, '
              'most] pixels, "tolerance": 0 to 1}'),
    ],
    *,
    area: Annotated[
        list, Param("[left, top, right, bottom] pixels of the play area; all if empty")
    ] = None,
    speed: Annotated[
        float, Param("the most an object moves a second, as a share of the frame's "
                     "width", lo=0.0, unit="1/s")
    ] = 0.5,
    together: Annotated[
        float, Param("seconds apart two tracks may be born and be one group", lo=0.0,
                     unit="s")
    ] = 0.5,
    apart: Annotated[
        float, Param("how far apart, as a share of the frame's width, two tracks "
                     "may be born and be one group", lo=0.0)
    ] = 0.25,
    root: Annotated[str, Param("the project the frames are under")] = ".",
) -> dict:
    """Count and follow what moves in a reference video's frames, by kinds you declare.

    Each frame's islands of a kind's colour and size become detections, joined into
    tracks (first and last second, path, and whether each left the frame, was gone
    inside it or was alive at the end) and into groups born together, with a count and
    a formation. objects.json and contact sheets with each track's id land beside the
    frames, recorded. Checking the counts against the sheets stays the agent's work.
    """
    from PIL import Image as Pil

    here = load(root).root
    manifest, listed = _manifest(frames, here)
    folder = manifest.parent
    kinds_ = declared(kinds)
    if area is not None and (len(area) != 4 or not area[0] < area[2]
                             or not area[1] < area[3]):
        raise _bad(f"area is {area!r}", "write it as [left, top, right, bottom] pixels")
    seen, size = [], (0, 0)
    for one in listed.get("frames", []):
        with Pil.open(folder / one["file"]) as frame:
            image = frame.convert("RGB")
        size = image.size
        left, top = 0, 0
        if area:
            left, top = int(area[0]), int(area[1])
            image = image.crop(tuple(int(v) for v in area))
        scale = min(1.0, READ_WIDTH / max(image.width, 1))
        read = image.resize((max(1, round(image.width * scale)),
                             max(1, round(image.height * scale))))
        found = detect(np.asarray(read), kinds_, scale)
        for one_found in found:
            one_found["x"] = round(one_found["x"] + left, 1)
            one_found["y"] = round(one_found["y"] + top, 1)
        seen.append((one["ms"] / 1000, found))
    wide = size[0] or 1
    tracks = tracked(seen, speed * wide, size)
    groups = grouped(tracks, together, apart * wide)
    sheets = _sheet(folder, listed.get("frames", []), tracks) if tracks else []
    written = {
        "frames": provenance.relative(manifest, here),
        "kinds": {k: {key: v[key] for key in ("colour", "tolerance", "size")}
                  for k, v in kinds_.items()},
        "area": list(area) if area else None,
        "per_frame": [{"at": at, "count": len(found)} for at, found in seen],
        "tracks": tracks,
        "groups": groups,
        "sheets": [one.name for one in sheets],
    }
    target = folder / "objects.json"
    target.write_text(json.dumps(written, indent=1) + "\n", encoding="utf-8",
                      newline="\n")
    provenance.write(provenance.build(
        "capture", target, engine={"name": "reference.objects"},
        inputs=[provenance.source("frames", manifest, root=here)],
        params={"kinds": written["kinds"], "area": written["area"], "speed": speed,
                "together": together, "apart": apart},
        root=here,
    ), here)
    return {
        "objects": provenance.relative(target, here),
        "sheets": [provenance.relative(one, here) for one in sheets],
        "tracks": len(tracks),
        "groups": [{key: g[key] for key in ("id", "kind", "born", "count", "formation",
                                            "ended")} for g in groups],
        "says": f"{len(tracks)} tracks in {len(groups)} groups over {len(seen)} "
        "frames; check them against the sheets before writing a wave from them",
    }
