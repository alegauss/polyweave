"""A rebuilt level laid against the video it copies (§PW382).

Rebuilding a phase from a gameplay video (Spinhold, RK178) is as much the list of places
it plays differently as the phase itself, and that list was an agent looking at a
capture of the game and the video's frames apart and remembering both.

`reference.compare` takes the reference's frames and the game's, both as
`reference.frames` writes them (a capture of the game, `capture.movie` say, is sampled
the same way), aligns them in time by a plain offset or by the first second something
of a declared kind appears on each side, and lays them side by side: sheets of the
reference frame beside the game's at the same aligned second, a chart of how many
objects each side shows over time, counted as `reference.objects` counts them, and the
seconds where the two counts differ by more than `bound`, each with its two frames, so
every gap is a line an agent can file. Whether a difference is a bug or a choice stays
the owner's call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import numpy as np

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .reference_objects import READ_WIDTH, _manifest, declared, detect

#: Pairs a side-by-side sheet holds, one pair a row.
PAIRS = 8

#: A tile's width on a sheet.
TILE = 400


def counted(frames: list, folder: Path, kinds: dict) -> list[tuple[float, int]]:
    """How many objects of the kinds each frame shows, by its second."""
    from PIL import Image as Pil

    out = []
    for one in frames:
        with Pil.open(folder / one["file"]) as frame:
            image = frame.convert("RGB")
        scale = min(1.0, READ_WIDTH / max(image.width, 1))
        read = image.resize((max(1, round(image.width * scale)),
                             max(1, round(image.height * scale))))
        out.append((one["ms"] / 1000, len(detect(np.asarray(read), kinds, scale))))
    return out


def nearest(seconds: list[float], at: float) -> int:
    """The index of the second nearest `at`."""
    return int(np.argmin(np.abs(np.array(seconds) - at)))


def _chart(reference: list, capture: list, offset: float, target: Path) -> Path:
    """Both sides' counts over the reference's seconds, the game's moved by `offset`."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    wide, tall, pad = 1200, 360, 40
    picture = Pil.new("RGB", (wide, tall), (20, 20, 20))
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default(size=14)
    points = [(t, n) for t, n in reference] + [(t - offset, n) for t, n in capture]
    first = min(t for t, _ in points)
    last = max(t for t, _ in points)
    most = max(1, max(n for _, n in points))

    def place(t: float, n: int) -> tuple[float, float]:
        x = pad + (wide - 2 * pad) * (t - first) / max(last - first, 1e-6)
        return x, tall - pad - (tall - 2 * pad) * n / most

    for counts, colour, shift in ((reference, (90, 200, 255), 0.0),
                                  (capture, (255, 160, 60), offset)):
        line = [place(t - shift, n) for t, n in counts]
        if len(line) > 1:
            draw.line(line, fill=colour, width=2)
    draw.text((pad, 8), "reference", fill=(90, 200, 255), font=font)
    draw.text((pad + 100, 8), "game", fill=(255, 160, 60), font=font)
    draw.text((pad, tall - pad + 8), f"{first:.1f}s", fill=(160, 160, 160), font=font)
    draw.text((wide - pad - 40, tall - pad + 8), f"{last:.1f}s", fill=(160, 160, 160),
              font=font)
    draw.text((6, pad - 8), str(most), fill=(160, 160, 160), font=font)
    picture.save(target)
    return target


def _sheets(pairs: list, folders: tuple[Path, Path], target: Path) -> list[Path]:
    """Sheets of each reference frame beside the game's at the same aligned second."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    font = ImageFont.load_default(size=14)
    for old in target.parent.glob(f"{target.stem}_*.png"):
        old.unlink()
    made = []
    for start in range(0, len(pairs), PAIRS):
        rows = []
        for ref, cap in pairs[start:start + PAIRS]:
            tiles = []
            for (at, file), folder in ((ref, folders[0]), (cap, folders[1])):
                with Pil.open(folder / file) as frame:
                    image = frame.convert("RGB")
                tile = image.resize((TILE, max(1, round(image.height * TILE
                                                        / max(image.width, 1)))))
                draw = ImageDraw.Draw(tile)
                draw.rectangle((0, 0, 70, 16), fill=(0, 0, 0))
                draw.text((3, 1), f"{at:.2f}s", fill=(255, 220, 90), font=font)
                tiles.append(tile)
            rows.append(tiles)
        tall = max(t.height for row in rows for t in row)
        sheet = Pil.new("RGB", (2 * TILE, tall * len(rows)), (20, 20, 20))
        for r, (left, right) in enumerate(rows):
            sheet.paste(left, (0, r * tall))
            sheet.paste(right, (TILE, r * tall))
        where = target.parent / f"{target.stem}_{start // PAIRS + 1:03d}.png"
        sheet.save(where)
        made.append(where)
    return made


@operation("reference.compare")
def compare(
    reference: Annotated[
        str, Param("the reference video's frames folder, or its frames.json")
    ],
    capture: Annotated[
        str, Param("the game's capture's frames folder, or its frames.json")
    ],
    kinds: Annotated[
        dict, Param("the kinds of object counted, as reference.objects takes them")
    ],
    *,
    capture_kinds: Annotated[
        dict, Param("the game's own kinds where its colours differ; kinds if empty")
    ] = None,
    offset: Annotated[
        float, Param("seconds the game runs ahead of the reference", unit="s")
    ] = 0.0,
    anchor: Annotated[
        str, Param("align by this instead of offset", choices=("", "first"))
    ] = "",
    bound: Annotated[
        int, Param("objects the two sides may differ by before a second is a gap",
                   lo=0)
    ] = 2,
    root: Annotated[str, Param("the project both are under")] = ".",
) -> dict:
    """A rebuilt level's capture laid against the reference video it copies.

    Aligned by `offset`, or by the first second an object of `kinds` appears on each
    side (`anchor` first). Side-by-side sheets at the same aligned second, a chart of
    objects on screen on both sides, and the seconds where the counts differ by more
    than `bound`, each with its two frames. Whether a gap is a bug is the owner's call.
    """
    here = load(root).root
    ref_manifest, ref_listed = _manifest(reference, here)
    cap_manifest, cap_listed = _manifest(capture, here)
    ref_frames, cap_frames = ref_listed.get("frames", []), cap_listed.get("frames", [])
    if not ref_frames or not cap_frames:
        raise PolyweaveError(
            "capture.no-reference-frames",
            "one side has no frames to compare",
            "sample both with reference.frames first",
        )
    own = declared(kinds)
    theirs = declared(capture_kinds) if capture_kinds else own
    ref_count = counted(ref_frames, ref_manifest.parent, own)
    cap_count = counted(cap_frames, cap_manifest.parent, theirs)
    if anchor == "first":
        firsts = [next((t for t, n in side if n > 0), None)
                  for side in (ref_count, cap_count)]
        if None in firsts:
            raise PolyweaveError(
                "capture.bad-kinds",
                "no object of the kinds shows on "
                f"{'the reference' if firsts[0] is None else 'the game'}, so there is "
                "nothing to anchor on",
                "check the kinds against that side's frames, or pass offset instead",
            )
        offset = firsts[1] - firsts[0]
    cap_seconds = [t for t, _ in cap_count]
    # Half the capture's own step either side of it: a second aligned outside the
    # game's footage is said unmatched, never compared with its nearest edge frame.
    step = float(np.median(np.diff(cap_seconds))) if len(cap_seconds) > 1 else 0.0
    pairs, gaps, unmatched = [], [], []
    for (at, n), one in zip(ref_count, ref_frames, strict=True):
        if not cap_seconds[0] - step / 2 <= at + offset <= cap_seconds[-1] + step / 2:
            unmatched.append(at)
            continue
        j = nearest(cap_seconds, at + offset)
        other = cap_frames[j]
        pairs.append(((at, one["file"]), (cap_seconds[j], other["file"])))
        if abs(n - cap_count[j][1]) > bound:
            gaps.append({"at": at, "reference": n, "game": cap_count[j][1],
                         "reference_frame": one["file"], "game_frame": other["file"],
                         "game_at": cap_seconds[j]})
    folder = ref_manifest.parent
    sheets = _sheets(pairs, (folder, cap_manifest.parent), folder / "compare.png")
    chart = _chart(ref_count, cap_count, offset, folder / "compare_counts.png")
    written = {
        "reference": provenance.relative(ref_manifest, here),
        "capture": provenance.relative(cap_manifest, here),
        "offset": round(offset, 3), "anchor": anchor, "bound": bound,
        "reference_counts": ref_count, "game_counts": cap_count, "gaps": gaps,
        "unmatched": unmatched,
        "sheets": [one.name for one in sheets], "chart": chart.name,
    }
    target = folder / "compare.json"
    target.write_text(json.dumps(written, indent=1) + "\n", encoding="utf-8",
                      newline="\n")
    provenance.write(provenance.build(
        "capture", target, engine={"name": "reference.compare"},
        inputs=[provenance.source("reference", ref_manifest, root=here),
                provenance.source("capture", cap_manifest, root=here)],
        params={"offset": round(offset, 3), "anchor": anchor, "bound": bound,
                "kinds": {k: v["colour"] for k, v in own.items()}},
        root=here,
    ), here)
    return {
        "compare": provenance.relative(target, here),
        "sheets": [provenance.relative(one, here) for one in sheets],
        "chart": provenance.relative(chart, here),
        "offset": round(offset, 3),
        "gaps": gaps,
        "unmatched": unmatched,
        "says": f"{len(gaps)} of {len(pairs)} seconds differ by more than {bound} "
        f"objects, {len(unmatched)} fall outside the game's footage; each gap is a "
        "line to file or a choice to keep",
    }
