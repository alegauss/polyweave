"""How a voxel model breaks, worked out when it is built, not on the kill frame (§PW99).

A game breaking a model one cell at a time spawns a piece per cell, and one working out
the pieces at runtime pays for it on the frame the player is watching. Both answers are
geometry the build already holds, so it writes them down:

- **fragments**: connected groups of cells within a size range, each with its cells,
  centre and mass, so a game spawns one piece per fragment;
- **depth**: each cell's distance in cells from the surface, which is the order damage
  takes — a hit chips the outermost cells nearest it first.

**A fragment keeps to one material and one node where it can**, so a cockpit flies off
whole rather than half glass and half hull. Cells are grouped into those regions first
and fragments grow inside them.

**Deterministic from the seed.** The same model with the same seed always breaks the
same way, so a test can say where, and a game can replay a death.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from ..errors import PolyweaveError

__all__ = ["depths", "plan", "settings"]

_FACES = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def settings(stated: Any) -> tuple[int, int, int]:
    """A `[voxels.fracture]` table's smallest and largest fragment, and its seed."""
    stated = dict(stated or {})
    size = stated.get("size")
    try:
        smallest, largest = (int(v) for v in size)
        ok = 1 <= smallest <= largest and all(float(v).is_integer() for v in size)
    except (TypeError, ValueError):
        ok = False
    if not ok:
        raise PolyweaveError(
            "geom.bad-fracture",
            f"a fracture size of {size!r} names no fragment that can exist",
            "write size = [smallest, largest] in cells, with 1 <= smallest <= largest",
        )
    return smallest, largest, int(stated.get("seed", 0))


def _neighbours(at: tuple, where: dict) -> list[int]:
    x, y, z = at
    return [
        where[(x + dx, y + dy, z + dz)]
        for dx, dy, dz in _FACES
        if (x + dx, y + dy, z + dz) in where
    ]


def depths(cells: list[tuple]) -> list[int]:
    """Each cell's distance from the surface, in face steps; the outermost are 1."""
    where = {at: index for index, at in enumerate(cells)}
    depth = [0] * len(cells)
    queue: deque[int] = deque()
    for index, at in enumerate(cells):
        if len(_neighbours(at, where)) < len(_FACES):
            depth[index] = 1
            queue.append(index)
    while queue:
        one = queue.popleft()
        for other in _neighbours(cells[one], where):
            if not depth[other]:
                depth[other] = depth[one] + 1
                queue.append(other)
    return depth


def _regions(cells: list[tuple], keys: list) -> list[list[int]]:
    """Connected groups of cells that share a key: one material, one node."""
    where = {at: index for index, at in enumerate(cells)}
    seen = [False] * len(cells)
    out = []
    for start in range(len(cells)):
        if seen[start]:
            continue
        seen[start], group, queue = True, [], deque([start])
        while queue:
            one = queue.popleft()
            group.append(one)
            for other in _neighbours(cells[one], where):
                if not seen[other] and keys[other] == keys[start]:
                    seen[other] = True
                    queue.append(other)
        out.append(group)
    return out


def _grow(
    region: list[int], cells: list[tuple], smallest: int, largest: int, rng
) -> list:
    """Fragments inside one region, each grown from a seed to a size drawn in range."""
    inside = {cells[i]: i for i in region}
    free = set(region)
    fragments = []
    for seed in (region[i] for i in rng.permutation(len(region))):
        if seed not in free:
            continue
        target = int(rng.integers(smallest, largest + 1))
        grown, queue = [], deque([seed])
        free.discard(seed)
        while queue and len(grown) < target:
            one = queue.popleft()
            grown.append(one)
            for other in sorted(_neighbours(cells[one], inside)):
                if other in free and len(grown) + len(queue) < target:
                    free.discard(other)
                    queue.append(other)
        free.update(queue)  # grown past the target: what was queued goes back
        fragments.append(grown)
    return _merged(fragments, cells, smallest, largest)


def _merged(fragments: list, cells: list[tuple], smallest: int, largest: int) -> list:
    """Fragments under the smallest size joined to a neighbour where that still fits."""
    owner = {}
    for number, fragment in enumerate(fragments):
        for one in fragment:
            owner[cells[one]] = number
    alive = dict(enumerate(fragments))
    for number in sorted(alive, key=lambda n: len(alive[n])):
        if number not in alive or len(alive[number]) >= smallest:
            continue
        touching = {
            owner[neighbour]
            for one in alive[number]
            for neighbour in _around(cells[one])
            if neighbour in owner and owner[neighbour] != number
        }
        fits = sorted(
            (len(alive[n]), n)
            for n in touching
            if n in alive and len(alive[n]) + len(alive[number]) <= largest
        )
        if not fits:
            continue
        into = fits[0][1]
        alive[into] = alive[into] + alive.pop(number)
        for one in alive[into]:
            owner[cells[one]] = into
    return [alive[n] for n in sorted(alive)]


def _around(at: tuple) -> list[tuple]:
    x, y, z = at
    return [(x + dx, y + dy, z + dz) for dx, dy, dz in _FACES]


def plan(model: dict, stated: Any) -> dict:
    """The fragments a model breaks into, and each cell's depth (`[voxels.fracture]`).

    Adds `fragment` and `depth` columns to the model's cells, beside the five it has,
    and returns the fragments: their cells as indices into those columns, their centre
    in the model's own units and their mass in cells.
    """
    smallest, largest, seed = settings(stated)
    found = model["cells"]
    cells = list(zip(found["x"], found["y"], found["z"], strict=True))
    keys = list(zip(found["palette"], found["node"], strict=True))
    rng = np.random.default_rng(seed)

    fragments = []
    for region in _regions(cells, keys):
        # A region that fits in one fragment is one, so a cockpit flies off whole rather
        # than in whatever sizes the draw happened to pick.
        if len(region) <= largest:
            fragments.append(region)
            continue
        fragments += _grow(region, cells, smallest, largest, rng)
    fragments.sort(key=lambda fragment: min(fragment))

    size, origin = float(model["cell"]), np.asarray(model["origin"], dtype=float)
    which = [0] * len(cells)
    listed = []
    for number, fragment in enumerate(fragments):
        members = sorted(fragment)
        for one in members:
            which[one] = number
        middle = np.asarray([cells[one] for one in members], dtype=float).mean(axis=0)
        listed.append(
            {
                "cells": members,
                "centre": [round(float(v), 6) for v in origin + (middle + 0.5) * size],
                "mass": len(members),
                "palette": int(found["palette"][members[0]]),
            }
        )
    found["fragment"] = which
    found["depth"] = depths(cells)
    sizes = [one["mass"] for one in listed]
    return {
        "size": [smallest, largest],
        "seed": seed,
        "fragments": listed,
        "count": len(listed),
        "mean": round(float(np.mean(sizes)), 3) if sizes else 0.0,
        "deepest": max(found["depth"], default=0),
    }
