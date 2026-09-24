"""A bound's room, measured from how much its measure moves on its own (§PW107).

Every margin in Cottony's star specs was chosen by eye: roughly a tenth over the
shipped value, the same for a median as for a 99th percentile. A tail moves more than a
median under the same harmless change, so one rule is too loose on one predicate and too
tight on the next, which is how 0.37 came to refuse a star a person had accepted.

Renders are cheap enough to measure the noise instead:

    found = calibrate(spec, "renders/star.png", root=".")   # proposes, writes nothing
    apply("docs/accept/star.accept.toml", found, root=".")   # the separate call

The accepted picture's own record says how it was made, so it is made again under the
changes that should not change the look — another seed, the sample count one rung down,
the size one step either way. The spread of each measure across those is its noise, and
the proposed bound is the accepted value plus a stated multiple of it, written with
origin `measured` and the spread beside it. A bound a person agreed on is left alone: a
person's verdict outranks a statistic.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import accept, provenance
from .accept import Spec
from .errors import PolyweaveError

#: How many spreads of noise a bound leaves above the accepted value. Stated in every
#: answer, because a bound nobody can re-derive is the guess this replaces.
MULTIPLE = 3.0

#: One step of size, as a share of the side. Small enough to be the same picture.
STEP = 0.125

#: The rig's own fields, which a record carries under `params` by these names.
RIG = (
    "azimuth",
    "elevation",
    "margin",
    "focal_mm",
    "key",
    "fill",
    "rim",
    "light_distance",
    "ambient",
    "exposure",
    "transparent",
)


def request_of(record: dict) -> dict:
    """The bake call that made a render, read back off its record."""
    params = record.get("params") or {}
    request = {name: params[name] for name in RIG if name in params}
    for name in ("material", "scrub", "covers", "pixels_per_unit", "size"):
        if name in params:
            request[name] = params[name]
    mesh = next((i for i in record.get("inputs", ()) if i.get("role") == "mesh"), None)
    if mesh:
        request["model"] = mesh["path"]
    for name in ("rung", "seed", "samples"):
        if name in record:
            request[name] = record[name]
    return request


def variations(request: dict, side: int, root: str | Path = ".") -> list[dict]:
    """The changes that should not change the look, each as what it overrides.

    `side` is the accepted picture's width. A change the render has no room for — no
    rung below the sphere's samples — is left out, and the answer says so.
    """
    from .config import load
    from .render.ladder import RUNGS

    seed = int(request.get("seed", 0))
    out = [
        {"name": f"seed {seed + 1}", "change": {"seed": seed + 1}},
        {"name": f"seed {seed + 2}", "change": {"seed": seed + 2}},
    ]
    rung = request.get("rung")
    below = RUNGS[RUNGS.index(rung) - 1] if rung in RUNGS[1:] else None
    fewer = load(root).get("render.samples").get(below) if below else None
    if fewer and int(fewer) != int(request.get("samples", 0)):
        out.append(
            {"name": f"{below}'s {fewer} samples", "change": {"samples": int(fewer)}}
        )
    if request.get("covers"):
        # A rectangle's size follows from its scale, so the scale is what steps.
        scale = float(request["pixels_per_unit"])
        for sign, word in ((-1, "smaller"), (1, "larger")):
            stepped = round(scale * (1 + sign * STEP), 6)
            out.append(
                {"name": f"one step {word}", "change": {"pixels_per_unit": stepped}}
            )
    else:
        for sign, word in ((-1, "smaller"), (1, "larger")):
            stepped = max(8, round(side * (1 + sign * STEP)))
            out.append({"name": f"one step {word}", "change": {"size": stepped}})
    return out


def propose(
    spec: Spec,
    accepted: str | Path,
    variants: dict[str, str | Path],
    *,
    multiple: float = MULTIPLE,
    rung: str | None = None,
    root: str | Path = ".",
) -> dict:
    """Each bound's room, from the accepted picture and its harmless variants.

    Pure given the pictures: nothing is rendered and nothing is written. The spread is
    the range of a measure across the accepted picture and every variant — with a
    handful of renders the range is the honest statistic, where a deviation would claim
    a distribution there are too few samples to have.
    """
    if not variants:
        raise PolyweaveError(
            "spec.no-variants",
            "a bound cannot be calibrated against the one picture it was accepted on",
            "render the accepted request again under at least one harmless change",
        )
    base = _values(spec, accepted, rung, root)
    moved = {name: _values(spec, where, rung, root) for name, where in variants.items()}
    predicates, bounds = [], {}
    for p in spec.predicates:
        value = base[p.id]
        seen = {name: taken[p.id] for name, taken in moved.items()}
        spread = round(max([value, *seen.values()]) - min([value, *seen.values()]), 6)
        sides = []
        for side, old in (("min", p.minimum), ("max", p.maximum)):
            if old is None:
                continue
            origin = p.origins.get(side) or {}
            one = {"side": side, "old": old, "old_origin": origin.get("origin")}
            if origin.get("origin") == "person":
                one["kept"] = "a person agreed on it, which outranks a statistic"
            else:
                new = _placed(value, spread * multiple, side)
                one["new"] = new
                bounds.setdefault(p.id, {})[side] = {
                    "value": new,
                    "origin": "measured",
                    "measured": round(value, 6),
                    "spread": spread,
                    "old": old,
                }
            sides.append(one)
        predicates.append(
            {
                "id": p.id,
                "measure": p.measure,
                "accepted": round(value, 6),
                "values": {name: round(v, 6) for name, v in seen.items()},
                "spread": spread,
                "bounds": sides,
            }
        )
    return {
        "asset": spec.asset,
        "accepted": str(accepted),
        "multiple": multiple,
        "varied": sorted(variants),
        "predicates": predicates,
        # What `apply` writes, and nothing it has not been shown here first.
        "apply": bounds,
    }


def calibrate(
    spec: Spec,
    accepted: str | Path,
    *,
    root: str | Path = ".",
    multiple: float = MULTIPLE,
    draw: Callable[[dict, Path], Any] | None = None,
) -> dict:
    """Render the accepted request again under harmless changes, and propose bounds.

    `draw(request, picture)` renders one request to one path; the default is `bake`.
    The variants land under the project's work directory, not beside the artefact.
    """
    from PIL import Image

    from .config import load

    here = Path(root).resolve()
    picture = Path(accepted) if Path(accepted).is_absolute() else here / accepted
    request = request_of(provenance.read(picture, root=here))
    with Image.open(picture) as opened:
        side = opened.size[0]
    changes = variations(request, side, root=here)
    folder = load(here).path("paths.work") / "calibrate" / (spec.asset or picture.stem)
    folder.mkdir(parents=True, exist_ok=True)
    render = draw or _baked(here)
    variants = {}
    for index, one in enumerate(changes):
        where = folder / f"{picture.stem}-{index}{picture.suffix}"
        render({**request, **one["change"]}, where)
        variants[one["name"]] = where
    found = propose(
        spec,
        picture,
        variants,
        multiple=multiple,
        rung=request.get("rung"),
        root=here,
    )
    found["accepted"] = provenance.relative(picture, here)
    found["changes"] = changes
    return found


def _baked(root: Path) -> Callable[[dict, Path], Any]:
    from . import render as R

    class Quiet:
        """A calibration reports its own answer; each render has nobody to tell."""

        def stage(self, stage, *, progress=None, note=None):
            return None

        def progress(self, value, *, note=None):
            return None

        def note(self, text):
            return None

    def draw(request: dict, picture: Path) -> dict:
        return R.bake(
            Quiet(), out=str(picture), inline=False, root=str(root), **request
        )

    return draw


def _values(spec: Spec, picture, rung, root) -> dict[str, float]:
    found = accept.check(spec, Path(picture), rung=rung, root=root)
    return {r["id"]: float(r["value"]) for r in found["predicates"]}


def _placed(value: float, room: float, side: str) -> float:
    """The accepted value moved out by its room, rounded away from it at four places."""
    if side == "max":
        return math.ceil((value + room) * 1e4) / 1e4
    return math.floor((value - room) * 1e4) / 1e4


# -- applying -------------------------------------------------------------------------


def apply(spec_path: str | Path, proposal: dict, *, root: str | Path = ".") -> dict:
    """Write a proposal's bounds into the spec, and only those.

    Each bound is one line rewritten in place, so a person's comments and layout stay.
    A bound that has moved since the proposal was made is refused, because the
    proposal was measured against the old one; a person's bound is never written over.
    """
    where = Path(spec_path)
    where = where if where.is_absolute() else Path(root) / where
    current = accept.read(where)
    text = where.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    blocks = _predicate_blocks(lines)
    by_id = {p.id: p for p in current.predicates}
    written, kept = [], []
    for name, sides in (proposal.get("apply") or {}).items():
        p = by_id.get(name)
        if p is None or name not in blocks:
            raise PolyweaveError(
                "spec.stale-proposal",
                f"the proposal bounds {name!r} and {where.name} has no such predicate",
                "calibrate again against the spec as it is now",
            )
        for side, bound in sides.items():
            now = p.minimum if side == "min" else p.maximum
            if (p.origins.get(side) or {}).get("origin") == "person":
                kept.append(f"{name}:{side}")
                continue
            if now != bound["old"]:
                raise PolyweaveError(
                    "spec.stale-proposal",
                    f"{name}'s {side} is {now} and the proposal was measured against "
                    f"{bound['old']}",
                    "calibrate again against the spec as it is now",
                )
            at = _bound_line(lines, blocks[name], side, name, where)
            lead = re.match(r"\s*(min|max)\s*=\s*", lines[at]).group(0)
            ending = "\n" if lines[at].endswith("\n") else ""
            lines[at] = lead + _inline(bound) + ending
            written.append(f"{name}:{side}")
    where.write_text("".join(lines), encoding="utf-8")
    try:
        accept.read(where)
    except PolyweaveError:
        where.write_text(text, encoding="utf-8")
        raise
    return {"spec": str(where), "written": written, "kept": kept}


def _predicate_blocks(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Each predicate's id, with the lines its table spans."""
    starts = [i for i, line in enumerate(lines) if line.strip() == "[[predicate]]"]
    blocks = {}
    for n, start in enumerate(starts):
        end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if lines[i].lstrip().startswith("[")
            ),
            len(lines),
        )
        if n + 1 < len(starts):
            end = min(end, starts[n + 1])
        for line in lines[start:end]:
            found = re.match(r"\s*id\s*=\s*[\"'](.+?)[\"']", line)
            if found:
                blocks[found.group(1)] = (start, end)
                break
    return blocks


def _bound_line(lines, block, side, name, where) -> int:
    start, end = block
    for i in range(start, end):
        if re.match(rf"\s*{side}\s*=", lines[i]):
            value = lines[i].split("=", 1)[1]
            if value.count("{") == value.count("}"):
                return i
    raise PolyweaveError(
        "spec.unwritable-bound",
        f"{name}'s {side} in {where.name} is not written on one line",
        f"write it as `{side} = <number>` or as an inline table, and apply again",
    )


def _inline(bound: dict) -> str:
    return (
        f'{{ value = {bound["value"]:g}, origin = "measured", '
        f"measured = {bound['measured']:g}, spread = {bound['spread']:g} }}"
    )
