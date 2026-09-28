"""A store's capsule set, cut from one key art (§PW268).

A Steam page asks for one key art in about ten shapes, each with its own size and
aspect and most carrying the logo, and Starship wrote a crop script of its own for it.
The shapes are data (`stores/<name>.toml` beside this module, or a project's own file of
the same shape): the size, and how the logo goes on it. Each capsule is the key art
cover-cropped around a focus point the caller gives, never stretched, with the logo
placed by its shape's rule.

**Nothing is upscaled.** A key art or a logo too small for a shape is refused before
anything is written, naming the shape and the size it needs: a capsule blown up from a
smaller picture is soft, and a store's reviewer sees it at once.

**A logo is held to reading at its size.** Its thinnest stroke, measured on the logo's
alpha at the scale each shape draws it, must be at least the store's `min_stroke`
pixels; a capsule under it is written and failed, so the person looking sees why.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated

import numpy as np

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: Where the stores this plugin knows are declared, one file each.
STORES = Path(__file__).with_name("stores")

#: How a logo may go on a shape.
LOGOS = ("centre", "lower", "only", "none")


def _store(store: str, root: Path) -> dict:
    """A store's shapes: one this plugin knows by name, or a project's file by path."""
    known = STORES / f"{store}.toml"
    where = known if known.is_file() else root / store
    if not where.is_file():
        known_names = sorted(p.stem for p in STORES.glob("*.toml"))
        raise PolyweaveError(
            "store.unknown",
            f"there is no store {store!r}",
            f"name one of {', '.join(known_names)}, or the path of a store file of the "
            "same shape under the project",
            given=store,
            allowed=known_names,
        )
    declared = tomllib.loads(where.read_text(encoding="utf-8"))
    for name, shape in (declared.get("shape") or {}).items():
        size = shape.get("size")
        if (not isinstance(size, list) or len(size) != 2
                or not all(isinstance(v, int) and v > 0 for v in size)
                or shape.get("logo", "none") not in LOGOS):
            raise PolyweaveError(
                "store.bad-shape",
                f"{where.name} has a shape {name} that is not one",
                f"give it size = [width, height] in pixels and logo, one of "
                f"{', '.join(LOGOS)}",
                at=f"shape.{name}",
            )
    return declared


def _opened(path: Path, role: str):
    from PIL import Image

    if not path.is_file():
        raise PolyweaveError(
            "store.no-picture",
            f"there is no {role} at {path.name}",
            f"name the {role} as a path under the project",
        )
    with Image.open(path) as picture:
        return picture.convert("RGBA")


def _logo_size(shape: dict, logo) -> tuple[int, int] | None:
    """The size the logo is drawn at on a shape, or None where it is left off."""
    width, height = shape["size"]
    rule = shape.get("logo", "none")
    if rule == "none":
        return None
    if rule == "only":
        scale = min(width / logo.width, height / logo.height)
    else:
        scale = width * float(shape.get("logo_width", 0.6)) / logo.width
        scale = min(scale, height * 0.9 / logo.height)
    return max(1, round(logo.width * scale)), max(1, round(logo.height * scale))


def _runs(mask: np.ndarray) -> np.ndarray:
    """Each set pixel's run length along its row."""
    out = np.zeros(mask.shape, dtype=np.int32)
    for y, row in enumerate(mask):
        edges = np.flatnonzero(np.diff(np.concatenate([[0], row.astype(np.int8), [0]])))
        for start, stop in zip(edges[::2], edges[1::2], strict=True):
            out[y, start:stop] = stop - start
    return out


def thinnest(logo, scale: float) -> float:
    """The logo's thinnest stroke in pixels at a scale: the 10th percentile, over its
    opaque pixels, of the shorter of each one's horizontal and vertical run."""
    mask = np.asarray(logo)[..., 3] > 127
    if not mask.any():
        return 0.0
    shorter = np.minimum(_runs(mask), _runs(mask.T).T)[mask]
    return round(float(np.percentile(shorter, 10)) * scale, 2)


def _covered(art, size: tuple[int, int], focus: tuple[float, float]):
    """The key art scaled to cover a size and cropped there around the focus."""
    from PIL import Image

    width, height = size
    scale = max(width / art.width, height / art.height)
    scaled = art.resize(
        (max(width, round(art.width * scale)), max(height, round(art.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = min(max(round(focus[0] * scaled.width - width / 2), 0), scaled.width - width)
    top = min(max(round(focus[1] * scaled.height - height / 2), 0),
              scaled.height - height)
    return scaled.crop((left, top, left + width, top + height))


@operation("store.capsules")
def capsules(
    key_art: Annotated[str, Param("the key art every capsule is cut from")],
    logo: Annotated[str, Param("the game's logo, a picture with alpha")],
    *,
    out: Annotated[str, Param("the folder the capsules are written into")],
    store: Annotated[
        str, Param("a store this plugin knows, such as steam, or a store file's path")
    ] = "steam",
    focus: Annotated[
        list, Param("the point every crop keeps, as fractions [x, y] of the key art")
    ] = (0.5, 0.5),
    shapes: Annotated[
        list, Param("only these of the store's shapes; all if unset")
    ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Cut a store's whole capsule set from one key art and a logo, each recorded.

    Each shape is the key art cover-cropped around `focus` with the logo placed by the
    store's rule, or the logo alone, or no logo where the store asks for none. A key art
    or logo too small for any shape is refused before anything is written. Each
    capsule's logo stroke is measured at its size, and one under the store's
    `min_stroke` is written and failed.
    """
    from PIL import Image

    config = load(root)
    here = config.root
    declared = _chosen(_store(store, here), shapes, store)
    _focused(focus)
    art_path, logo_path = here / key_art, here / logo
    art, mark = _opened(art_path, "key art"), _opened(logo_path, "logo")
    _large_enough(declared, art, mark)
    folder = config.path("paths.work", out)
    folder.mkdir(parents=True, exist_ok=True)
    floor = float(declared.get("min_stroke", 2.0))
    inputs = [provenance.source("key art", art_path, here),
              provenance.source("logo", logo_path, here)]
    made, failed = {}, []
    for name, shape in declared["shape"].items():
        size = tuple(shape["size"])
        rule = shape.get("logo", "none")
        canvas = (Image.new("RGBA", size, (0, 0, 0, 0)) if rule == "only"
                  else _covered(art, size, tuple(focus)))
        drawn, stroke = _logo_size(shape, mark), None
        if drawn:
            placed = mark.resize(drawn, Image.Resampling.LANCZOS)
            middle = float(shape.get("logo_at", 0.5)) if rule == "lower" else 0.5
            top = round(middle * size[1] - drawn[1] / 2)
            at = ((size[0] - drawn[0]) // 2, min(max(top, 0), size[1] - drawn[1]))
            canvas.alpha_composite(placed, at)
            stroke = thinnest(mark, drawn[0] / mark.width)
        legible = stroke is None or stroke >= floor
        target = folder / f"{name}.png"
        canvas.save(target)
        provenance.write(provenance.build(
            "picture", target, engine={"name": "store.capsules"}, inputs=inputs,
            params={"store": declared.get("name", store), "shape": name,
                    "focus": [float(v) for v in focus]},
            measurements={"logo_stroke": stroke} if stroke is not None else {},
            root=here,
        ), here)
        made[name] = {"file": provenance.relative(target, here), "size": list(size),
                      "logo": rule, "stroke": stroke, "legible": legible}
        if not legible:
            failed.append(name)
    return {
        "store": declared.get("name", store),
        "capsules": made,
        "failed": failed,
        "ok": not failed,
        "min_stroke": floor,
        "says": f"{len(made)} capsules written"
        + (f"; the logo would not read on {', '.join(failed)}: its thinnest stroke "
           f"falls under {floor:g} px there" if failed else ""),
    }


def _chosen(declared: dict, wanted: list | None, store: str) -> dict:
    """The store with only the shapes asked for, every one named checked."""
    if wanted is None:
        return declared
    unknown = sorted(set(wanted) - set(declared["shape"]))
    if unknown or not wanted:
        raise PolyweaveError(
            "store.bad-shape",
            f"{declared.get('name', store)} has no shape "
            f"{', '.join(unknown) or '(none asked)'}",
            f"name some of {', '.join(declared['shape'])}",
            allowed=list(declared["shape"]),
        )
    kept = {k: v for k, v in declared["shape"].items() if k in wanted}
    return {**declared, "shape": kept}


def _focused(focus) -> None:
    if (not isinstance(focus, list | tuple) or len(focus) != 2
            or not all(isinstance(v, int | float) and 0 <= v <= 1 for v in focus)):
        raise PolyweaveError(
            "store.bad-focus",
            f"focus is {focus!r}",
            "give it [x, y], each a fraction of the key art from 0 to 1",
        )


def _large_enough(declared: dict, art, mark) -> None:
    """Refuse before anything is written where a shape would need an upscale."""
    small, cuttable = [], []
    for name, shape in declared["shape"].items():
        width, height = shape["size"]
        before = len(small)
        if shape.get("logo") != "only" and (art.width < width or art.height < height):
            small.append(f"{name} needs {width}x{height} of key art")
        drawn = _logo_size(shape, mark)
        if drawn and (drawn[0] > mark.width or drawn[1] > mark.height):
            small.append(f"{name} draws the logo at {drawn[0]}x{drawn[1]}")
        if len(small) == before:
            cuttable.append(name)
    if small:
        raise PolyweaveError(
            "store.too-small",
            f"the key art is {art.width}x{art.height} and the logo "
            f"{mark.width}x{mark.height}, and {'; '.join(small)}",
            "give a larger key art or logo, or cut the other shapes now with shapes=; "
            "nothing is upscaled, since a capsule blown up from a smaller picture is "
            "soft",
            allowed=cuttable,
        )
