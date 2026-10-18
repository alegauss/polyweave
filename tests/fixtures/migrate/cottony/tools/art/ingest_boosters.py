"""Bring the two fetched boosters in from their drawings, and say how they came.

    python tools/art/ingest_boosters.py

polyweave §PW80. The hammer and the wand came back from the service needing three
corrections each that bake_model.py found by hand: a scrub of the dark marks the service
painted, a roll of -22 degrees for the hammer, and a fill of 0.72 to make up for the box
the roll widened. This states what each one is for instead of the number it landed on.

- **the lean** is how the drawing holds the object, so the plugin reads it off the drawing
  (`normalise.ingest(against=...)`), with no render spent;
- **the scrub** is the plugin's own pass, asked for per model because a dark line a person
  drew and a shadow the service painted look alike to anything measuring darkness;
- **the size** follows from the drawing too, because the height is taken of the leaned
  silhouette.

The meshes land in .polyweave/boosters/ with their provenance records, and a preview of each
beside them. Nothing here writes to tools/art/3d/ or to the sprites the game loads: whether
the result reads as the old renders did is a person's call. The check is the part a machine
can make: both come in painted, and the hammer's lean is within a degree of the 22 found by
hand.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polyweave
from polyweave import normalise, render
from polyweave.render import blender

ROOT = Path(__file__).resolve().parents[2]
WORK = ".polyweave/boosters"

## the hammer's roll in bake_model.py, found by re-rendering: the number this has to recover
HAND_LEAN = 22.0


class Quiet:
    """A bake reports its stages; a check that bakes two things has nobody to tell."""

    def stage(self, *_, **__):
        pass

    def progress(self, *_, **__):
        pass

    def note(self, *_):
        pass


def painted(mesh: str) -> bool:
    """Whether the written mesh still wears a material that reads an image.

    Read off the file rather than off the bake's answer, because a bake served from the
    cache does not repeat the scrub and so does not say what it found.
    """
    obj = blender.load_mesh(mesh)
    return any(
        node.type == "TEX_IMAGE" and node.image is not None
        for material in obj.data.materials
        if material is not None and material.node_tree is not None
        for node in material.node_tree.nodes
    )


def bring(name: str) -> dict:
    record = normalise.ingest(
        f"tools/art/3d/booster_{name}.glb",
        out=f"{WORK}/{name}.glb",
        against=f"tools/art/3d/booster_{name}.drawn.png",
        root=ROOT,
    )
    render.bake(
        Quiet(),
        out=f"{WORK}/{name}.png",
        model=f"{WORK}/{name}.glb",
        rung="preview",
        azimuth=0.0,
        elevation=0.0,
        scrub=True,
        inline=False,
        root=str(ROOT),
    )
    return {**record, "painted": painted(record["mesh"])}


def main() -> int:
    polyweave.readable()
    found = {name: bring(name) for name in ("hammer", "wand")}
    for name, one in found.items():
        wears = "painted" if one["painted"] else "no texture"
        print(
            f"  {name:<7} leans {one['lean']:+d} deg, iou {one['silhouette_iou']:.3f} "
            f"against its drawing, {wears}"
        )
    holds = abs(abs(found["hammer"]["lean"]) - HAND_LEAN) <= 1.0 and all(
        one["painted"] for one in found.values()
    )
    print(
        "both come in from their drawings, painted, the hammer leaned as found by hand"
        if holds
        else "a booster did not come in the way its drawing holds it"
    )
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main())
