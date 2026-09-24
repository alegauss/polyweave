"""What a voxel model is checked for before anything renders it (§PW97).

A cell that floats free, a piece hanging on by an edge, a thread one cell thick and a
model over the cells a game can afford all read badly on screen or cost it frames, and
every one of them is countable from the cells. So a voxel build measures them and
reports them with its readback.

**Reported, not refused.** A mesh with no faces is broken; a ship with a loose antenna
is a design that may be wrong. The one refusal is a model with no cells at all.
Everything else comes back as a finding that **names its cells**, so the fix is a local
edit rather than a hunt.

**The numbers are the project's.** How many cells a game can draw, how long a thread
may run and how big a model should be are a game's decisions, so they arrive from the
project config and nothing here defaults them.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..errors import PolyweaveError

#: What `check_voxels` takes; every one is stated by the caller.
ACCEPTS_VOXELS = frozenset({"parts", "thread", "budget", "extent", "near_symmetry"})

#: How many cells a finding lists before it says how many more there are.
NAMED = 12

_FACES = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
_AROUND = [
    (x, y, z)
    for x in (-1, 0, 1)
    for y in (-1, 0, 1)
    for z in (-1, 0, 1)
    if (x, y, z) != (0, 0, 0)
]


def _grid(model: dict) -> np.ndarray:
    filled = np.zeros(tuple(model["size"]), dtype=bool)
    cells = model["cells"]
    if len(cells["x"]):
        filled[
            (np.asarray(cells["x"]), np.asarray(cells["y"]), np.asarray(cells["z"]))
        ] = True
    return filled


def _shifted(array: np.ndarray, step: tuple[int, int, int], fill: Any) -> np.ndarray:
    """`array` moved by one step, what moves in from outside being `fill`."""
    out = np.full_like(array, fill)
    source = tuple(
        slice(max(0, -s), array.shape[a] - max(0, s)) for a, s in enumerate(step)
    )
    target = tuple(
        slice(max(0, s), array.shape[a] - max(0, -s)) for a, s in enumerate(step)
    )
    out[target] = array[source]
    return out


def components(filled: np.ndarray, steps: list) -> np.ndarray:
    """A label per filled cell, shared by all it reaches through `steps`; -1 if empty.

    Each label falls to the smallest among its neighbours until none moves, which is a
    flood fill written as whole-array operations — numpy alone, no scipy.
    """
    big = np.iinfo(np.int64).max
    labels = np.where(filled, np.arange(filled.size).reshape(filled.shape), big)
    while True:
        lowest = labels
        for step in steps:
            lowest = np.minimum(lowest, _shifted(labels, step, big))
        lowest = np.where(filled, lowest, big)
        if np.array_equal(lowest, labels):
            break
        labels = lowest
    return np.where(filled, labels, -1)


def _named(cells: np.ndarray) -> list[list[int]]:
    return [[int(v) for v in one] for one in cells[:NAMED]]


def _listing(cells: np.ndarray) -> str:
    shown = ", ".join(f"({x}, {y}, {z})" for x, y, z in _named(cells))
    more = len(cells) - NAMED
    return shown + (f" and {more} more" if more > 0 else "")


def _finding(check: str, says: str, cells: np.ndarray) -> dict:
    return {
        "check": check,
        "says": says,
        "cells": _named(cells),
        "count": int(len(cells)),
    }


def _pieces(filled: np.ndarray, parts: int) -> tuple[list[dict], dict]:
    """Loose pieces, and pieces held on only by an edge or a corner."""
    found = []
    touching = components(filled, _AROUND)
    groups = [g for g in np.unique(touching) if g >= 0]
    sizes = sorted(
        ((int((touching == g).sum()), g) for g in groups), key=lambda one: -one[0]
    )
    for _, group in sizes[max(1, int(parts)) :]:
        cells = np.argwhere(touching == group)
        found.append(
            _finding(
                "floating",
                f"{len(cells)} cell{'s' if len(cells) != 1 else ''} float free of the "
                f"body: {_listing(cells)}",
                cells,
            )
        )

    faced = components(filled, _FACES)
    for group in groups:
        within = [g for g in np.unique(faced[touching == group]) if g >= 0]
        if len(within) < 2:
            continue
        ordered = sorted(within, key=lambda g: -int((faced == g).sum()))
        for piece in ordered[1:]:
            cells = np.argwhere(faced == piece)
            found.append(
                _finding(
                    "diagonal",
                    f"{len(cells)} cell{'s' if len(cells) != 1 else ''} meet the rest "
                    f"only at an edge or a corner, which reads as broken off: "
                    f"{_listing(cells)}",
                    cells,
                )
            )
    return found, {"parts": len(groups), "pieces": len(np.unique(faced[faced >= 0]))}


def _threads(filled: np.ndarray, longest: int) -> tuple[list[dict], int]:
    """Runs one cell thick, which vanish at a distance.

    A thread cell has at most two face neighbours, and two only on opposite sides: a
    line, never a sheet or a corner of one.
    """
    near = [_shifted(filled, step, False) for step in _FACES]
    count = sum(one.astype(int) for one in near)
    straight = (near[0] & near[1]) | (near[2] & near[3]) | (near[4] & near[5])
    thin = filled & ((count <= 1) | ((count == 2) & straight))
    runs = components(thin, _FACES)
    found, most = [], 0
    for run in [g for g in np.unique(runs) if g >= 0]:
        cells = np.argwhere(runs == run)
        most = max(most, len(cells))
        if len(cells) > int(longest):
            found.append(
                _finding(
                    "thread",
                    f"a thread {len(cells)} cells long and one thick, longer than "
                    f"{int(longest)}: {_listing(cells)}",
                    cells,
                )
            )
    return found, most


def _symmetry(filled: np.ndarray, near: float) -> tuple[list[dict], float]:
    """The share of cells with a partner across the model's middle in x.

    Reported whenever a model is nearly symmetric and not quite, because that is what
    two halves drifting apart looks like.
    """
    total = int(filled.sum())
    partnered = filled & filled[::-1, :, :]
    share = float(partnered.sum()) / total if total else 1.0
    found = []
    if float(near) <= share < 1.0:
        cells = np.argwhere(filled & ~partnered)
        found.append(
            _finding(
                "symmetry",
                f"{len(cells)} cell{'s' if len(cells) != 1 else ''} of a model "
                f"{share:.0%} symmetric in x have no partner across the middle: "
                f"{_listing(cells)}",
                cells,
            )
        )
    return found, round(share, 4)


def check_voxels(
    model: dict,
    *,
    parts: int,
    thread: int,
    budget: int,
    extent: Any,
    near_symmetry: float,
) -> dict:
    """Measure a voxel model, and name the cells behind anything worth a second look.

    `budget` of zero is no ceiling, and an empty `extent` is no target: a game that has
    not decided either is not told it broke a rule nobody wrote.
    """
    if not model.get("count"):
        raise PolyweaveError(
            "post.voxels-empty",
            f"{model.get('name', 'the model')} has no cells in it",
            "check the grid is fine enough for the smallest part, and that nothing "
            "carved the whole shape away",
        )
    filled = _grid(model)
    findings, measured = _pieces(filled, parts)
    threaded, longest = _threads(filled, thread)
    mirrored, share = _symmetry(filled, near_symmetry)
    findings += threaded + mirrored

    if budget and model["count"] > int(budget):
        findings.append(
            {
                "check": "budget",
                "says": f"{model['count']} cells, over the {int(budget)} this project "
                f"can afford",
                "cells": [],
                "count": int(model["count"]),
            }
        )
    size = [n * float(model["cell"]) for n in model["size"]]
    if extent:
        target = [float(v) for v in extent]
        off = [
            axis
            for axis, (have, want) in zip(
                "xyz", zip(size, target, strict=True), strict=True
            )
            if abs(have - want) > float(model["cell"]) + 1e-9
        ]
        if off:
            spans = " by ".join(f"{v:g}" for v in size)
            wants = " by ".join(f"{v:g}" for v in target)
            findings.append(
                {
                    "check": "extent",
                    "says": f"the model is {spans} against a target of {wants}, more "
                    f"than a cell off in {', '.join(off)}",
                    "cells": [],
                    "count": 0,
                }
            )
    return {
        **measured,
        "cells": int(model["count"]),
        "longest_thread": longest,
        "symmetry": share,
        "extent": size,
        "findings": findings,
    }
