"""Preparing the picture a mesh gets asked for, before the credits go on it.

The evidence is §PW21: Cottony sent a photograph of a plush toy and got back the logo
the toy had been sitting on, fused into the model as geometry. No camera move removes
it, and the whole fetch was spent finding that out.

A photograph is an input like any other, and every one of the things that would have
caught this is a routine image operation:

- **cut the subject out** of whatever it was standing on;
- **flatten the background** to something uniform, so nothing in it reads as shape;
- **check the subject fills enough of the frame** to be read from at all;
- **say where the silhouette touches an edge**, because what runs off the frame is what
  the service invents.

The prepared image is what goes in the records, so the input that actually produced the
mesh is the one on file rather than whichever original a person happened to have open.

And where the project has already drawn the thing, **the drawing is the better
reference** — it has no background to cut, no lighting to undo and no lens. `pick` says
so rather than letting a photograph win by being the argument that was passed.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from . import measure
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import write_atomic
from .image import Image
from .image import load as load_image
from .provenance import sha256_of

#: The long side a prepared reference is written at. A generative service reads a
#: silhouette and a surface off this, not a print, and the cut is computed on exactly
#: the pixels that get sent — so what was measured is what was spent on.
LONGEST = 1024

#: How many pixels deep into the frame the background's colour is read from. One row
#: would be a dust speck away from deciding the whole cut.
BORDER = 2

#: A fill that has not converged by here stops. Stopping early only leaves background
#: behind, never eats into the subject, which is the direction to fail in.
PASSES = 4096


def is_drawing(subject: Image | str | Path) -> bool:
    """Whether this is already a drawing rather than a photograph.

    A drawing arrives with its background gone: a real alpha channel, and a border that
    is transparent in it. That is mechanical, and it is the only distinction that
    matters here — a picture with no background does not need one cut away.
    """
    image = subject if isinstance(subject, Image) else load_image(subject)
    if not image.had_alpha:
        return False
    edge = np.zeros(image.rgba.shape[:2], dtype=bool)
    edge[:BORDER, :] = edge[-BORDER:, :] = True
    edge[:, :BORDER] = edge[:, -BORDER:] = True
    return bool((image.alpha[edge] == 0).mean() > 0.9)


def pick(*candidates: str | Path, root: str | Path = ".") -> dict:
    """Which of these references to spend on, and why that one.

    A drawing beats a photograph, and the first drawing beats a later one. Nothing
    here ranks two drawings on how good they are — that is a judgement, and this only
    reports what each candidate is.
    """
    if not candidates:
        raise PolyweaveError(
            "fetch.no-reference",
            "no reference was named to choose between",
            "point it at the drawing or the photograph that asks for this shape",
        )
    where = Path(root).resolve()
    looked = []
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_absolute():
            path = where / path
        looked.append({"path": str(path), "drawing": is_drawing(path)})
    drawings = [seen for seen in looked if seen["drawing"]]
    chosen = drawings[0] if drawings else looked[0]
    return {
        "reference": chosen["path"],
        "drawing": chosen["drawing"],
        "considered": looked,
        "why": (
            "a drawing has no background to cut, no lighting to undo and no lens"
            if chosen["drawing"]
            else "no drawing was among them, so the photograph is what there is"
        ),
    }


# -- cutting the subject out -----------------------------------------------------------


def _shrunk(image: Image, longest: int) -> Image:
    if max(image.size) <= longest:
        return image
    from PIL import Image as PILImage

    scale = longest / max(image.size)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    smaller = PILImage.fromarray(image.rgba, "RGBA").resize(size, PILImage.LANCZOS)
    return Image(
        path=image.path,
        rgba=np.asarray(smaller, dtype=np.uint8),
        had_alpha=image.had_alpha,
    )


def _grown(mask: np.ndarray) -> np.ndarray:
    """The mask plus its four-connected neighbours, without wrapping at the edge."""
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def _reachable(seed: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Everything `allowed` that `seed` can be reached from, four-connected."""
    reach = seed & allowed
    for _ in range(PASSES):
        grown = _grown(reach) & allowed
        if np.array_equal(grown, reach):
            break
        reach = grown
    return reach


def _largest(mask: np.ndarray) -> np.ndarray:
    """The biggest connected island in the mask, and nothing else.

    This is the step that drops the logo the toy was sitting on: a shape the fill could
    not reach from the frame's edge is still not the subject, it is a second thing in
    the picture, and only one of them is being asked for.
    """
    left = mask.copy()
    best = np.zeros_like(mask)
    found = 0
    while int(left.sum()) > found:
        first = int(np.flatnonzero(left.ravel())[0])
        seed = np.zeros_like(mask)
        seed.ravel()[first] = True
        island = _reachable(seed, left)
        size = int(island.sum())
        if size > found:
            best, found = island, size
        left &= ~island
    return best


def _ground(border: np.ndarray, tolerance: float) -> tuple[np.ndarray, float]:
    """The colour the frame's edge mostly is, and how much of it agrees.

    The **mode** and not the average. A subject that runs into the frame makes the
    border two colours, and their mean is a third colour that is neither — which is
    how a cut ends up removing nothing at all.
    """
    binned = np.round(border / max(tolerance, 1e-6)).astype(np.int64)
    _, index, counts = np.unique(
        binned, axis=0, return_inverse=True, return_counts=True
    )
    common = int(np.argmax(counts))
    return border[index.ravel() == common].mean(axis=0), float(
        counts[common] / len(border)
    )


def _background(image: Image, tolerance: float) -> tuple[np.ndarray, float]:
    """What the subject is standing on, grown in from the frame's own edge.

    Pixels within `tolerance` of the ground colour, reachable from the border, are that
    same ground — so a pocket of background colour enclosed by the subject stays
    subject, and a patterned floor stops the fill where the pattern starts rather than
    eating into the toy.

    The distance is Euclidean in CIELAB. It is a segmentation threshold and not a claim
    about perceptual equality, and at this size the difference between it and CIEDE2000
    is smaller than the difference between two photographs of the same sheet of paper.
    """
    lab = measure.to_lab(image.rgba[:, :, :3].astype(float) / 255.0)
    edge = np.zeros(lab.shape[:2], dtype=bool)
    edge[:BORDER, :] = edge[-BORDER:, :] = True
    edge[:, :BORDER] = edge[:, -BORDER:] = True
    ground, share = _ground(lab[edge], tolerance)
    near = np.sqrt(((lab - ground) ** 2).sum(axis=2)) <= tolerance
    return _reachable(edge, near), share


def _touching(mask: np.ndarray) -> list[str]:
    sides = []
    if mask[0, :].any():
        sides.append("top")
    if mask[-1, :].any():
        sides.append("bottom")
    if mask[:, 0].any():
        sides.append("left")
    if mask[:, -1].any():
        sides.append("right")
    return sides


def cut(
    photo: str | Path,
    *,
    tolerance: float | None = None,
    coverage: float | None = None,
    root: str | Path = ".",
    longest: int = LONGEST,
) -> dict:
    """The subject's own mask, and what is wrong with the picture it came from."""
    settings = load(root)
    bar = float(settings.get("tolerance.background_delta_e", tolerance))
    least = float(settings.get("tolerance.subject_coverage", coverage))

    image = _shrunk(load_image(photo), longest)
    share = 1.0
    if image.had_alpha and is_drawing(image):
        subject = image.subject(float(settings.get("tolerance.alpha_floor")))
    else:
        ground, share = _background(image, bar)
        subject = _largest(~ground)

    filled = float(subject.mean())
    if filled >= 0.995:
        raise PolyweaveError(
            "fetch.background-fused",
            f"nothing in {Path(photo).name} reads as background: the cut kept "
            f"{filled:.1%} of the frame",
            f"the service would return what it is standing on as geometry — cut the "
            f"subject out first, or raise [tolerance] background_delta_e above {bar}",
        )
    if filled < least:
        raise PolyweaveError(
            "fetch.subject-small",
            f"the subject fills {filled:.1%} of {Path(photo).name}, and {least:.0%} "
            f"was the least",
            "crop to the subject, or lower [tolerance] subject_coverage",
        )
    return {
        "image": image,
        "subject": subject,
        "coverage": round(filled, 6),
        "touches": _touching(subject),
        "background_delta_e": bar,
        # How much of the frame's edge agreed on one colour. Not a gate: a low number is
        # a busy ground, and what that costs is already caught by the two checks above.
        "ground_share": round(share, 6),
    }


# -- writing the one that gets spent on ------------------------------------------------


def prepare(
    photo: str | Path,
    *,
    out: str | Path | None = None,
    root: str | Path = ".",
    matte: tuple[int, int, int] = (255, 255, 255),
    tolerance: float | None = None,
    coverage: float | None = None,
    longest: int = LONGEST,
) -> dict:
    """Cut, flatten, check, and write the picture the fetch will actually carry.

    The background is made transparent *and* flattened to one colour behind it, because
    a service that ignores alpha still has to see something uniform there — a cut that
    only sets alpha is a cut that half the world does not get.
    """
    from PIL import Image as PILImage

    settings = load(root)
    found = cut(
        photo, tolerance=tolerance, coverage=coverage, root=root, longest=longest
    )
    image, subject = found["image"], found["subject"]

    rgba = image.rgba.copy()
    rgba[~subject, :3] = np.array(matte, dtype=np.uint8)
    rgba[~subject, 3] = 0
    rgba[subject, 3] = 255

    where = Path(out) if out else None
    if where is None:
        where = settings.path("paths.references") / f"{Path(photo).stem}.prepared.png"
    elif not where.is_absolute():
        where = settings.root / where
    where.parent.mkdir(parents=True, exist_ok=True)

    buffer = BytesIO()
    PILImage.fromarray(rgba, "RGBA").save(buffer, format="PNG")
    write_atomic(where, buffer.getvalue())

    digest, length = sha256_of(where)
    warnings = []
    if found["touches"]:
        warnings.append(
            f"the silhouette runs off the {', '.join(found['touches'])} of the frame, "
            f"so the service invents whatever is past the edge"
        )
    return {
        "reference": str(where),
        "source": str(Path(photo)),
        "sha256": digest,
        "bytes": length,
        "size": [int(rgba.shape[1]), int(rgba.shape[0])],
        "coverage": found["coverage"],
        "touches": found["touches"],
        "background_delta_e": found["background_delta_e"],
        "warnings": warnings,
    }


def ready(subject: Any, *, root: str | Path = ".", **how: Any) -> dict:
    """The prepared reference for whatever was handed over, drawing or photograph.

    A drawing is already what it needs to be and is passed through untouched; a
    photograph is prepared. Either way what comes back is a path a fetch can carry and a
    digest a record can name, so the caller never has to know which it had.
    """
    path = Path(subject)
    if not path.is_absolute():
        path = Path(root).resolve() / path
    if is_drawing(path):
        digest, length = sha256_of(path)
        return {
            "reference": str(path),
            "source": str(path),
            "sha256": digest,
            "bytes": length,
            "prepared": False,
            "warnings": [],
            "why": "it is already a drawing, with no background to cut",
        }
    return {**prepare(path, root=root, **how), "prepared": True, "why": ""}


@operation("reference.pick")
def picked(
    candidates: Annotated[list, Param("the pictures to choose between, by path")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Which of several pictures is the one to fetch from, and why."""
    return pick(*candidates, root=root)


@operation("reference.prepare")
def prepared(
    photo: Annotated[str, Param("the photograph, as a path under the project")],
    out: Annotated[str, Param("where the prepared reference is written")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    tolerance: Annotated[
        float, Param("how far from the edge colour is still background")
    ] = None,
    coverage: Annotated[float, Param("the least of the frame it fills")] = None,
    longest: Annotated[int, Param("the longest side it is sized to", lo=16)] = 1024,
) -> dict:
    """A photograph cut from its background and sized, ready to send to the service."""
    return prepare(
        photo,
        out=out,
        root=root,
        tolerance=tolerance,
        coverage=coverage,
        longest=longest,
    )


#: How many frames a contact sheet holds across and down, and how wide each tile is.
SHEET_GRID, TILE = 4, 320


@operation("reference.frames")
def frames(
    video: Annotated[str, Param("the gameplay video, anywhere; it is never copied in")],
    *,
    rate: Annotated[float, Param("frames a second across the video", lo=0.01)] = 2.0,
    ranges: Annotated[
        list, Param("denser stretches: [start, end, rate] in seconds and per second")
    ] = None,
    changed: Annotated[
        float, Param("keep a frame only where it differs by this share; 0 keeps all",
                     lo=0.0, hi=1.0)
    ] = 0.0,
    crop: Annotated[
        list, Param("[left, top, right, bottom] pixels: a second sheet of that strip")
    ] = None,
    out: Annotated[str, Param("the folder under the project the frames land in")] = (
        None
    ),
    root: Annotated[str, Param("the project the frames are written into")] = ".",
) -> dict:
    """A reference video sampled into frames and contact sheets an agent can read.

    Frames are named by their time in milliseconds, at `rate` across the video and
    denser inside `ranges`. A contact sheet holds sixteen of them with the time burnt
    in, so sixteen moments of play are one read; `crop` adds a sheet of that strip
    alone (a radar, say). `frames.json` lists them, and its record holds the video's
    SHA-256, the rate and the ranges, so what was read can be traced to the source
    (§PW328). Reading what happened in them stays the agent's and the person's work.
    """
    import json
    import shutil
    import subprocess
    import tempfile

    from . import provenance

    config = load(root)
    here = config.root
    source = Path(video) if Path(video).is_absolute() else here / video
    if not source.is_file():
        raise PolyweaveError(
            "fetch.no-reference",
            f"there is no video at {source}",
            "name the gameplay video's path; it stays where it is",
            given=str(video),
        )
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise PolyweaveError(
            "sound.no-encoder",
            "there is no ffmpeg on PATH to read the video's frames",
            "put ffmpeg on PATH",
        )
    stretches = [(None, None, float(rate))]
    for one in ranges or ():
        if not isinstance(one, list | tuple) or len(one) != 3 or not (
            0 <= float(one[0]) < float(one[1]) and float(one[2]) > 0
        ):
            raise PolyweaveError(
                "fetch.no-reference",
                f"a range is {one!r}, and a range is [start, end, rate]",
                "give each as [start seconds, end seconds, frames a second]",
                given=str(one),
            )
        stretches.append((float(one[0]), float(one[1]), float(one[2])))
    folder = config.path("paths.work", out or f"references/{source.stem}")
    folder.mkdir(parents=True, exist_ok=True)
    taken: dict[int, Path] = {}
    with tempfile.TemporaryDirectory() as scratch:
        for index, (start, end, every) in enumerate(stretches):
            place = Path(scratch) / str(index)
            place.mkdir()
            argv = [ffmpeg, "-v", "error"]
            if start is not None:
                argv += ["-ss", f"{start:.3f}", "-to", f"{end:.3f}"]
            argv += ["-i", str(source), "-vf", f"fps={every}", str(place / "%06d.png")]
            done = subprocess.run(argv, capture_output=True, check=False)
            if done.returncode:
                raise PolyweaveError(
                    "fetch.no-reference",
                    f"ffmpeg could not read {source.name}",
                    "read the detail; check the file is a video",
                    detail=done.stderr[:400].decode("utf-8", "replace"),
                )
            for frame in sorted(place.glob("*.png")):
                at = (start or 0.0) + (int(frame.stem) - 1) / every
                taken.setdefault(int(round(at * 1000)), frame)
        kept = _changed(taken, float(changed))
        for old in folder.glob("t*.png"):
            old.unlink()
        names = []
        for ms in kept:
            name = folder / f"t{ms:08d}.png"
            shutil.copyfile(taken[ms], name)
            names.append((ms, name))
    sheets = _sheets(names, folder, "sheet", None)
    cropped = _sheets(names, folder, "crop", crop) if crop else []
    listed = {
        "video": source.resolve().as_posix(),
        "rate": float(rate),
        "ranges": [list(one) for one in stretches[1:]],
        "changed": float(changed),
        "frames": [{"ms": ms, "file": name.name} for ms, name in names],
        "sheets": [one.name for one in sheets],
        "crops": [one.name for one in cropped],
    }
    manifest = folder / "frames.json"
    manifest.write_text(json.dumps(listed, indent=1) + "\n", encoding="utf-8",
                        newline="\n")
    record = provenance.build(
        "capture", manifest, engine={"name": "ffmpeg"},
        inputs=[provenance.source("video", source, root=here)],
        params={"rate": float(rate), "ranges": listed["ranges"],
                "changed": float(changed), "crop": list(crop) if crop else None},
        root=here,
    )
    provenance.write(record, here)
    rel = provenance.relative
    return {
        "frames": len(names),
        "sampled": len(taken),
        "folder": rel(folder, here),
        "manifest": rel(manifest, here),
        "sheets": [rel(one, here) for one in sheets],
        "crops": [rel(one, here) for one in cropped],
        "says": f"{len(names)} frames of {source.name} on {len(sheets)} sheet"
        f"{'' if len(sheets) == 1 else 's'}, sixteen moments a read",
    }


def _changed(taken: dict, bound: float) -> list[int]:
    """The frames worth reading: each that differs from the last kept by `bound`."""
    from PIL import Image as Pil

    order = sorted(taken)
    if bound <= 0:
        return order
    kept, last = [], None
    for ms in order:
        with Pil.open(taken[ms]) as frame:
            pixels = np.asarray(frame.convert("L").resize((96, 54)), dtype=np.float64)
        if last is None or float(np.mean(np.abs(pixels - last))) / 255.0 > bound:
            kept.append(ms)
            last = pixels
    return kept


def _sheets(names: list, folder: Path, stem: str, crop) -> list[Path]:
    """Contact sheets of the frames, sixteen a sheet, each with its time burnt in."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    for old in folder.glob(f"{stem}_*.png"):
        old.unlink()
    font = ImageFont.load_default(size=18)
    made = []
    per = SHEET_GRID * SHEET_GRID
    for at in range(0, len(names), per):
        group = names[at : at + per]
        tiles = []
        for ms, name in group:
            with Pil.open(name) as frame:
                image = frame.convert("RGB")
                if crop:
                    left, top, right, bottom = (int(v) for v in crop)
                    image = image.crop((left, top, right, bottom))
                tall = max(1, round(image.height * TILE / max(image.width, 1)))
                tiles.append((ms, image.resize((TILE, tall))))
        tall = max(tile.height for _, tile in tiles)
        sheet = Pil.new("RGB", (SHEET_GRID * TILE, SHEET_GRID * tall), (20, 20, 20))
        draw = ImageDraw.Draw(sheet)
        for i, (ms, tile) in enumerate(tiles):
            x, y = (i % SHEET_GRID) * TILE, (i // SHEET_GRID) * tall
            sheet.paste(tile, (x, y))
            said = f"{ms // 60000}:{ms / 1000 % 60:06.3f}"
            draw.rectangle((x, y, x + 110, y + 22), fill=(0, 0, 0))
            draw.text((x + 4, y + 2), said, fill=(255, 220, 90), font=font)
        where = folder / f"{stem}_{at // per + 1:03d}.png"
        sheet.save(where)
        made.append(where)
    return made
