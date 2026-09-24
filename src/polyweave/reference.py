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
