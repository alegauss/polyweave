"""Search the plugin's rig for the four progress stars, and say whether it holds on all four.

    python tools/art/search_stars.py

The stars are the first family off `bake_model.py`'s hand-found rig (polyweave §PW76). Their
geometry is `star.toml`, built by the plugin rather than by `star_model.py`, and what a render
of each has to be is `docs/design/accept/star_*.accept.toml`, read off the sprites the old rig
shipped. Every render lands under `.polyweave/stars/` first, beside the search's trace and its
contact sheet, and only a rig that holds on all four is baked into `docs/design/art/ui/`, over
the sprites `bake_model.py` used to write there. A person looked at that rig's four beside the
shipped ones on 2026-09-24 and accepted them, which is what moved the dim's ceiling.

**Searched on one, checked on three.** The rig is fitted to the 96 px gold alone and then
rendered, unchanged, for the dim one and the two 192 px ones. One geometry in two hues at two
sizes is the point of starting here: a rig that only passes the sprite it was fitted to has
been fitted, and one that passes all four has found the look.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import polyweave
from polyweave import accept, geometry, search, trace
from polyweave.geometry import build

ROOT = Path(__file__).resolve().parents[2]
WORK = ".polyweave/stars"
CELL = 112.0

## the one the search fits, then the three it has to hold on without being searched
FITTED = ("star_gold", "#FFC43F", 96)
HELD = (
    ("star_dim", "#C7B49A", 96),
    ("star_gold_big", "#FFC43F", 192),
    ("star_dim_big", "#C7B49A", 192),
)

## what the search is not allowed to turn. Square on the front, as the sprite is drawn; no rim,
## because a lit edge is what rule 2 forbids on candy; no fill, because the ambient is doing the
## work the old rig's fill did; and the exposure held, because it only rescales the ambient.
FIXED = {"azimuth": 0.0, "elevation": 0.0, "rim": 0.0, "fill": 0.0, "exposure": 1.0}

BUDGET = 60


def fixed(colour: str, px: int, *, cached: bool = True) -> dict:
    """Everything a render of one sprite states that the search leaves alone."""
    return {
        **FIXED,
        "cached": cached,
        "model": f"{WORK}/star-{px}.glb",
        "covers": [px / CELL, px / CELL],
        "pixels_per_unit": CELL,
        "material": {"colour": colour, "roughness": 0.22},
    }


def spec(name: str) -> accept.Spec:
    return accept.read(f"docs/design/accept/{name}.accept.toml", root=ROOT)


def line(name: str, found: dict) -> str:
    verdict = "holds" if found["passed"] else "misses " + ", ".join(found["failed"])
    return f"  {name:<14} {verdict}"


def run(*, cached: bool = True) -> dict:
    """Fit, check, and bake if it holds. What it spent comes back for the loop ledger."""
    declared = geometry.read("tools/art/star.toml", root=ROOT)
    for px in sorted({px for _, _, px in (FITTED, *HELD)}):
        build.write(declared, f"{WORK}/star-{px}.glb", root=ROOT, px=px)

    name, colour, px = FITTED
    started = time.monotonic()
    found = search.search(
        spec(name),
        search.renderer(
            spec(name), out=f"{WORK}/{name}.png", root=ROOT, fixed=fixed(colour, px, cached=cached)
        ),
        budget=BUDGET,
        points=5,
    )
    trace.write(found, out=f"{WORK}/trace", spec=spec(name), root=ROOT)
    rig = ", ".join(f"{k} {v:g}" for k, v in sorted(found["best"].items()))
    print(f"search: {rig} after {found['spent']} renders, {time.monotonic() - started:.1f}s")
    print(f"  {found['stopped']}")
    print(line(name, found))
    renders = found["spent"]

    held = True
    for name, colour, px in HELD:
        check = search.renderer(
            spec(name), out=f"{WORK}/{name}.png", root=ROOT, fixed=fixed(colour, px, cached=cached)
        )
        verdict = check(found["best"])
        renders += 1
        held = held and verdict["passed"]
        print(line(name, verdict))
    print("the rig holds on all four" if held else "the rig was fitted, not found")

    ## Baked from the same request each one was checked at, so the cache hands back the picture
    ## that passed rather than rendering a fresh one, and checked again where it lands.
    if held:
        for name, colour, px in (FITTED, *HELD):
            bake = search.renderer(
                spec(name), out=f"docs/design/art/ui/{name}.png", root=ROOT, fixed=fixed(colour, px)
            )
            held = held and bake(found["best"])["passed"]
        print("baked into docs/design/art/ui/" if held else "a baked sprite missed its spec")
    return {"held": held, "renders": renders, "seconds": time.monotonic() - started, "rig": found["best"]}


def main() -> int:
    polyweave.readable()
    return 0 if run()["held"] else 1


if __name__ == "__main__":
    sys.exit(main())
