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
from typing import Any

from .config import load
from .errors import PolyweaveError

#: How a number is spelled where a game keeps one. Tried in order, and the first that
#: matches wins: a GDScript constant, a key in a JSON file, a key in an ini-shaped one.
READS = (
    r"(?:const|var)\s+{name}\s*(?::\s*[\w\[\], ]+?)?\s*:?=\s*(-?\d+(?:\.\d+)?)",
    r"[\"']{name}[\"']\s*:\s*(-?\d+(?:\.\d+)?)",
    r"^[ \t]*{name}\s*=\s*(-?\d+(?:\.\d+)?)",
)

#: Under this, two scales are the same number written two ways rather than two scales.
CLOSE = 1e-6


def read_number(address: str, *, root: str | Path = ".") -> float:
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


def engine_scale(root: str | Path = ".") -> dict:
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
    try:
        wide, tall = (float(v) for v in value)
    except (TypeError, ValueError) as exc:
        raise PolyweaveError(
            "units.undeclared",
            f"{value!r} is not a rectangle",
            "write it as [width, height]",
        ) from exc
    if wide <= 0 or tall <= 0:
        raise PolyweaveError(
            "units.undeclared",
            f"a rectangle of {wide} x {tall} covers nothing",
            "write it as [width, height], both above zero",
        )
    return wide, tall


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
            "add covers = [width, height], in the units the engine uses",
        )
    wide, tall = _rectangle(stated["covers"])
    return {
        "covers": [wide, tall],
        "pixels_per_unit": float(stated.get("pixels_per_unit") or 0.0),
    }


def check(
    source: Any,
    *,
    size: Any = None,
    root: str | Path = ".",
    pixels_per_unit: float | None = None,
    tolerance: float | None = None,
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
        return {
            **found,
            "holds": False,
            "why": f"{asset['covers'][0]:g} x {asset['covers'][1]:g} units at "
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
