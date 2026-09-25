"""One authored clip, in both shapes the same motion is needed in.

The evidence is §PW29: a **2D screen needs frames**, as a sprite sheet the interface
crossfades or plays; a **3D scene needs a clip** the engine plays on a skeleton. Cottony
has the first and will want the second, and authoring them separately means keeping two
things in step by hand.

So both come out of the one clip. `clip.compile` is the 3D half and this is the 2D one:
a sheet of frames **rendered through the same rig**, so the two genuinely match rather
than merely resemble each other, with an atlas beside it saying where each frame is and
how long it lasts.

**The trim is taken across the whole clip and not per frame.** A frame trimmed to its
own silhouette is a frame whose subject sits somewhere slightly different from the last
one, and a sprite that jitters on its own axis is exactly what nobody wants from a
settle. One rectangle, the union of every frame's, and every cell cut from it.

**The rate, the count and the trim are configuration** — `[sprites]` — because they are
a project's decisions and not ones taken inside code. The sheet's rate is its own: one
authored at 24 may be sampled at 12 for a screen that plays it small.

**Both outputs record the digest of the clip they came from.** That is what turns
"keeping them in step" from a discipline into a check: `matched` compares the two and
says whether a screen playing the sprite and a scene playing the clip play the same.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from . import clip as C
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import write_atomic
from .image import load as load_image


def moments(subject: dict, *, fps: int, frames: int = 0) -> list[float]:
    """Which moments of the clip become cells, at the sheet's own rate.

    A clip authored at 24 and sampled at 12 is half the cells over the same seconds.
    `frames` overrides the rate outright, for a sheet with a count to hit.
    """
    if frames > 0:
        if frames == 1:
            return [0.0]
        step = subject["duration"] / (frames - 1)
        return [round(index * step, 6) for index in range(frames)]
    count = max(1, int(round(subject["duration"] * max(1, int(fps)))))
    return [round(index / fps, 6) for index in range(count + 1)]


def _union(pictures: list[np.ndarray], floor: int) -> tuple[int, int, int, int]:
    """The one rectangle every frame is cut from."""
    left, top = pictures[0].shape[1], pictures[0].shape[0]
    right = bottom = 0
    for rgba in pictures:
        rows = np.flatnonzero((rgba[:, :, 3] > floor).any(axis=1))
        columns = np.flatnonzero((rgba[:, :, 3] > floor).any(axis=0))
        if not rows.size:
            continue
        left, top = min(left, int(columns[0])), min(top, int(rows[0]))
        right = max(right, int(columns[-1]) + 1)
        bottom = max(bottom, int(rows[-1]) + 1)
    if right <= left or bottom <= top:
        raise PolyweaveError(
            "clip.nothing-drawn",
            f"none of the {len(pictures)} frames has a subject in it to trim to",
            "check the rig and the rung, and look at the frames the run wrote",
        )
    return left, top, right, bottom


def _under(named: str, root: Path) -> Path:
    where = Path(named)
    return where if where.is_absolute() else root / where


def _read(rendered: list[dict], root: Path) -> list[np.ndarray]:
    # A render records its artefact the way the record spells it, which is relative to
    # the project. Reading it back is where that has to be undone.
    pictures = [load_image(_under(found["artefact"], root)).rgba for found in rendered]
    sizes = {picture.shape[:2] for picture in pictures}
    if len(sizes) > 1:
        raise PolyweaveError(
            "clip.frames-differ",
            f"the frames of this clip come in {len(sizes)} sizes: "
            f"{', '.join(f'{w}x{h}' for h, w in sorted(sizes))}",
            "render every frame at one rung; a sheet of cells that are not one size is "
            "a sheet nothing can index",
        )
    return pictures


def sheet(
    subject: dict,
    rendered: list[dict],
    *,
    out: str | Path,
    root: str | Path = ".",
    columns: int | None = None,
    trim: bool | None = None,
) -> dict:
    """Lay the rendered frames out as one sheet, with the atlas that indexes it.

    The atlas is JSON, because a machine writes it and a machine reads it.
    """
    from PIL import Image as PILImage

    settings = load(root)
    across = int(settings.get("sprites.columns", columns))
    cutting = bool(settings.get("sprites.trim", trim))
    floor = round(float(settings.get("tolerance.alpha_floor")) * 255)

    where = Path(out)
    if not where.is_absolute():
        where = settings.root / where
    if not rendered:
        raise PolyweaveError(
            "clip.no-frames",
            f"{subject['name']!r} has no rendered frames to lay out",
            "render the clip before baking a sheet of it",
        )

    pictures = _read(rendered, settings.root)
    tall, wide = pictures[0].shape[:2]
    box = _union(pictures, floor) if cutting else (0, 0, wide, tall)
    left, top, right, bottom = box
    cell = (right - left, bottom - top)

    across = across or max(1, int(np.ceil(np.sqrt(len(pictures)))))
    down = int(np.ceil(len(pictures) / across))
    canvas = np.zeros((down * cell[1], across * cell[0], 4), dtype=np.uint8)

    placed = []
    for index, (picture, found) in enumerate(
        zip(pictures, rendered, strict=True), start=0
    ):
        column, row = index % across, index // across
        x, y = column * cell[0], row * cell[1]
        canvas[y : y + cell[1], x : x + cell[0]] = picture[top:bottom, left:right]
        placed.append(
            {
                "frame": index,
                "at": found.get("at", round(index / max(1, len(rendered)), 6)),
                "rect": [x, y, cell[0], cell[1]],
            }
        )

    where.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(canvas, "RGBA").save(where)
    atlas = {
        "clip": subject["name"],
        "clip_sha256": C._digest(C.as_toml(subject)),
        "duration": subject["duration"],
        "sheet": where.name,
        "size": [int(canvas.shape[1]), int(canvas.shape[0])],
        "cell": [cell[0], cell[1]],
        "columns": across,
        "rows": down,
        "trim": {"left": left, "top": top, "of": [wide, tall]} if cutting else None,
        "frames": placed,
    }
    written = where.with_suffix(".atlas.json")
    write_atomic(written, json.dumps(atlas, indent=2) + "\n")
    # The atlas names the sheet beside it, which is what an engine loading the atlas
    # needs; the answer names where both landed, which is what the caller needs. The
    # two are not the same string, so the paths go on last.
    return {**atlas, "sheet": str(where), "atlas": str(written)}


def bake(
    subject: dict,
    mesh: Any,
    rig: dict,
    bound: dict,
    *,
    out: str | Path,
    root: str | Path = ".",
    fps: int | None = None,
    frames: int | None = None,
    columns: int | None = None,
    trim: bool | None = None,
    **how: Any,
) -> dict:
    """Render the clip's frames and lay them out as one sheet with its atlas."""
    settings = load(root)
    where = Path(out)
    if not where.is_absolute():
        where = settings.root / where

    when = moments(
        subject,
        fps=int(settings.get("sprites.fps", fps)),
        frames=int(settings.get("sprites.frames", frames)),
    )
    rendered = C.frames(
        subject,
        mesh,
        rig,
        bound,
        out=where.parent / f"{subject['name']}-frames",
        root=root,
        when=when,
        **how,
    )
    return sheet(subject, rendered, out=where, root=root, columns=columns, trim=trim)


def both(
    subject: dict,
    mesh: Any,
    rig: dict,
    bound: dict,
    *,
    out: str | Path,
    root: str | Path = ".",
    **how: Any,
) -> dict:
    """The one clip in both shapes, from the one source.

    The saved authoring pass is not the point. The point is that a change to the timing
    lands in both, so a screen playing the sprite and a scene playing the clip cannot
    drift apart without someone noticing.
    """
    where = Path(out)
    animation = C.compile(
        subject, mesh, rig, bound, out=where.with_suffix(".glb"), root=root
    )
    sprite = bake(
        subject, mesh, rig, bound, out=where.with_suffix(".png"), root=root, **how
    )
    return {
        "clip": subject["name"],
        "clip_sha256": C._digest(C.as_toml(subject)),
        "animation": animation,
        "sprites": sprite,
        "matched": True,
    }


@operation("sprites.matched")
def matched(
    animation: Annotated[Any, Param("the compiled animation, or its record")],
    atlas: Annotated[Any, Param("the sheet's atlas, as a path or its table")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Whether the two outputs came from the same clip, which is the whole claim.

    The record beside a compiled animation and the atlas beside a sheet each carry the
    digest of the authored text. Equal digests are the two playing the same thing; a
    difference names which one is behind.
    """
    from . import provenance

    where = Path(root).resolve()
    stated = (
        atlas
        if isinstance(atlas, dict)
        else json.loads(Path(atlas).read_text(encoding="utf-8"))
    )
    if isinstance(animation, dict) and "clip_sha256" in animation:
        recorded = animation
    else:
        path = Path(
            animation.get("artefact") if isinstance(animation, dict) else animation
        )
        recorded = provenance.read(path, root=where).get("params", {})

    here, there = recorded.get("clip_sha256"), stated.get("clip_sha256")
    return {
        "matched": bool(here) and here == there,
        "animation": here,
        "sprites": there,
        "clip": stated.get("clip"),
        "why": ""
        if here == there
        else "the animation and the sheet were made from different clips, so a scene "
        "and a screen would play different motion",
    }
