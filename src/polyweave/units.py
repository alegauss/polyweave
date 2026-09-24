"""The scale an asset is baked at, against the one the engine draws it at.

The evidence is §PW24: Cottony's board tray renders at one unit per pixel because
somebody set the render rectangle to exactly the world rectangle the board covers, so
that its wells land on a cell size the game holds separately as its own constant. **The
two numbers agree because a person made them agree.** Nothing fails if either moves; the
sprite lands a few pixels off the grid and someone notices later, on a screen, by eye.

Declared instead, it is arithmetic:

- the **asset** states the world rectangle it covers and the pixels per unit it is baked
  at, and those two give the size in pixels it must be;
- the **engine** states its own pixels per unit;
- a **check** compares them, and a disagreement is a refusal **with both numbers in
  it** rather than a misalignment found visually three commits later.

**The engine's number is read from where the engine keeps it.** `[units] source` is
`path/to/file.gd:NAME`, and stating the number in `polyweave.toml` instead is the
weaker half of the same idea: a copy that can drift is the coincidence this line is
about. Where the constant is renamed or moved, that is `units.unreadable`, which is the
check doing its job rather than failing at it.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Annotated, Any

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: How a number is spelled where a game keeps one. Tried in order, and the first that
#: matches wins: a GDScript, TypeScript or Rust constant, a typed C-family one
#: (`const int CELL = 112`, `static readonly float PPU = 48f`, §PW117), a key in a JSON
#: file, a key in an ini-shaped one.
READS = (
    r"(?:const|var)\s+{name}\s*(?::\s*[\w\[\], ]+?)?\s*:?=\s*(-?\d+(?:\.\d+)?)",
    r"\b(?:const|static|final|readonly|constexpr)\b[^=;\n]*?\b{name}\s*=\s*"
    r"(-?\d+(?:\.\d+)?)",
    r"[\"']{name}[\"']\s*:\s*(-?\d+(?:\.\d+)?)",
    r"^[ \t]*{name}\s*=\s*(-?\d+(?:\.\d+)?)",
)

#: Under this, two scales are the same number written two ways rather than two scales.
CLOSE = 1e-6


ROOT = Param("the project whose scale this is")


@operation("units.read_number")
def read_number(
    address: Annotated[str, Param("path/to/file:NAME, relative to the project")],
    *,
    root: Annotated[str, ROOT] = ".",
) -> float:
    """One number, out of the file the project says holds it.

    `address` is `path/to/file:NAME`, relative to the project. Reading it here rather
    than copying it is the whole point: a constant that moves takes the check with it.
    """
    where = Path(root).resolve()
    path, _, name = address.rpartition(":")
    if not path or not name:
        raise PolyweaveError(
            "units.unreadable",
            f"{address!r} does not name a number in a file",
            "write it as path/to/file.gd:NAME",
        )
    source = Path(path)
    if not source.is_absolute():
        source = where / source
    if not source.is_file():
        raise PolyweaveError(
            "units.unreadable",
            f"there is no file at {source} to read {name} from",
            "point [units] source at the file the engine keeps its scale in",
        )
    text = source.read_text(encoding="utf-8", errors="replace")
    for pattern in READS:
        found = re.search(pattern.format(name=re.escape(name)), text, re.MULTILINE)
        if found:
            return float(found.group(1))
    raise PolyweaveError(
        "units.unreadable",
        f"{source.name} holds no number called {name}",
        f"check what {name} is called now; reading it from the engine's own file is "
        f"how a rename becomes this refusal instead of a misaligned sprite",
    )


@operation("units.engine_scale")
def engine_scale(root: Annotated[str, ROOT] = ".") -> dict:
    """The pixels per unit the engine draws at, and where that number came from."""
    settings = load(root)
    source = str(settings.get("units.source") or "").strip()
    if source:
        return {
            "pixels_per_unit": read_number(source, root=settings.root),
            "source": source,
        }
    stated = float(settings.get("units.pixels_per_unit") or 0.0)
    if stated > 0:
        return {"pixels_per_unit": stated, "source": "[units] pixels_per_unit"}
    raise PolyweaveError(
        "units.undeclared",
        "this project says nothing about the scale the engine draws at",
        "set [units] source to where the game keeps it, or [units] pixels_per_unit "
        "here; a scale nobody declares is one two numbers agree on by accident",
    )


def for_size(covers: Any, pixels_per_unit: float) -> tuple[int, int]:
    """The pixel size a rectangle at this scale comes to, refusing a fractional one."""
    wide, tall = _rectangle(covers)
    pixels = (wide * pixels_per_unit, tall * pixels_per_unit)
    for measure, along in zip(pixels, ("width", "height"), strict=True):
        if abs(measure - round(measure)) > 1e-6:
            raise PolyweaveError(
                "units.not-whole",
                f"{wide} x {tall} units at {pixels_per_unit:g} px/unit gives a "
                f"{along} of {measure:g} pixels",
                "round the rectangle, or bake at a scale it divides by; a sprite "
                "landing between two pixels cannot sit on the grid whatever else is "
                "right",
            )
    return (int(round(pixels[0])), int(round(pixels[1])))


def implied(covers: Any, size: Any) -> tuple[float, float]:
    """What a picture of this size over this rectangle actually is, per axis."""
    wide, tall = _rectangle(covers)
    across, down = _rectangle(size)
    return (across / wide, down / tall)


def _rectangle(value: Any) -> tuple[float, float]:
    """A rectangle's width and height, whether it was stated as a size or as a place."""
    corners = placed(value)
    if corners is not None:
        x0, y0, x1, y1 = corners
        wide, tall = x1 - x0, y1 - y0
    else:
        try:
            wide, tall = (float(v) for v in value)
        except (TypeError, ValueError) as exc:
            raise PolyweaveError(
                "units.undeclared",
                f"{value!r} is not a rectangle",
                "write it as [width, height], or as [x0, y0, x1, y1] where it has a "
                "place in the world",
            ) from exc
    if wide <= 0 or tall <= 0:
        raise PolyweaveError(
            "units.undeclared",
            f"a rectangle of {wide:g} x {tall:g} covers nothing",
            "write it as [width, height], both above zero, or as [x0, y0, x1, y1] "
            "with each far corner past its near one",
        )
    return wide, tall


def extent(value: Any) -> tuple[float, float]:
    """A declared rectangle's width and height, for a caller outside this module."""
    return _rectangle(value)


def placed(value: Any) -> tuple[float, float, float, float] | None:
    """The rectangle's corners where it was stated with a place, and None where not.

    **A place is what a grid needs** (§PW78). A size alone is centred on whatever the
    subject's bounds come to, so a wall, a bevel or a cushion that bulges on one side
    moves the frame and the grid with it. Cottony's trays are framed by a rectangle
    given outright for exactly that reason: the number comes from the game, and the
    picture does not get to choose where it stands.
    """
    try:
        numbers = [float(v) for v in value]
    except (TypeError, ValueError):
        return None
    if len(numbers) != 4:
        return None
    return (numbers[0], numbers[1], numbers[2], numbers[3])


def declared(source: Any, *, root: str | Path = ".") -> dict:
    """An asset's own statement of what it covers and what it is baked at.

    A mapping, or a TOML or JSON file holding one. Either way the two keys are the same
    two, because the declaration is the contract and not a convenience.
    """
    if isinstance(source, dict):
        stated = source
    else:
        path = Path(source)
        if not path.is_absolute():
            path = Path(root).resolve() / path
        if not path.is_file():
            raise PolyweaveError(
                "units.undeclared",
                f"there is no declaration at {path}",
                "write one with covers and pixels_per_unit in it",
            )
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            stated = json.loads(text)
        else:
            import tomllib

            stated = tomllib.loads(text)
        stated = stated.get("units", stated)

    if "covers" not in stated:
        raise PolyweaveError(
            "units.undeclared",
            "the declaration says nothing about the rectangle the asset covers",
            "add covers = [width, height], or [x0, y0, x1, y1] where it has a place, "
            "in the units the engine uses",
        )
    _rectangle(stated["covers"])  # refuses what is neither a size nor a place
    return {
        "covers": [float(v) for v in stated["covers"]],
        "pixels_per_unit": float(stated.get("pixels_per_unit") or 0.0),
    }


@operation("units.check")
def check(
    source: Annotated[
        Any, Param("the asset's declaration: covers and pixels_per_unit, or a file")
    ],
    *,
    size: Annotated[list, Param("the picture made, [width, height], if any")] = None,
    root: Annotated[str, ROOT] = ".",
    pixels_per_unit: Annotated[
        float, Param("the scale baked at, where the declaration omits it", lo=0.0)
    ] = None,
    tolerance: Annotated[
        float, Param("how far apart two scales may be; the project's where unset")
    ] = None,
) -> dict:
    """Does the asset's scale agree with the engine's, and with its own pixels.

    `size` is the picture that was produced, where there is one. Without it this is the
    declaration against the engine, which is the check worth making *before* a render.
    """
    settings = load(root)
    bar = float(settings.get("units.tolerance", tolerance))
    asset = declared(source, root=root)
    engine = engine_scale(root)

    mine = float(pixels_per_unit or asset["pixels_per_unit"] or 0.0)
    if mine <= 0:
        mine = engine["pixels_per_unit"]
    apart = abs(mine - engine["pixels_per_unit"])
    wanted = for_size(asset["covers"], mine)

    found = {
        "holds": True,
        "covers": asset["covers"],
        "pixels_per_unit": mine,
        "engine": engine,
        "size": list(wanted),
        "rendered": None,
        "why": "",
    }
    if apart > max(bar, CLOSE):
        return {
            **found,
            "holds": False,
            "why": f"the asset is baked at {mine:g} px/unit and the engine draws at "
            f"{engine['pixels_per_unit']:g}, from {engine['source']}",
        }
    if size is None:
        return found

    across, down = (int(round(v)) for v in _rectangle(size))
    found["rendered"] = [across, down]
    if (across, down) != wanted:
        wide, tall = _rectangle(asset["covers"])
        return {
            **found,
            "holds": False,
            "why": f"{wide:g} x {tall:g} units at "
            f"{mine:g} px/unit is {wanted[0]} x {wanted[1]} pixels, and the picture "
            f"is {across} x {down}",
        }
    return found


def require(source: Any, **how: Any) -> dict:
    """The same check as a gate, refusing with both numbers rather than one verdict."""
    found = check(source, **how)
    if found["holds"]:
        return found
    wrong_size = found["rendered"] is not None and found["rendered"] != found["size"]
    raise PolyweaveError(
        "units.wrong-size" if wrong_size else "units.mismatch",
        found["why"],
        "bake at the engine's scale, or change the engine's deliberately — the two "
        "agreeing by hand is what this replaces"
        if not wrong_size
        else f"render at {found['size'][0]} x {found['size'][1]}, the size the "
        f"declaration gives",
    )


def whole(value: float) -> bool:
    """Whether a number of pixels really is a number of pixels."""
    return math.isclose(value, round(value), abs_tol=1e-6)
