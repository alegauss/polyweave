"""Write the three booster objects as meshes polyweave can render, at the board's scale.

    python tools/art/export_boosters.py
    python -m polyweave port.run --family tools/art/boosters.family.toml

The boosters are the family off `bake_model.py`'s rig whose hand-tuning was never light
(polyweave PW80). The hammer and the wand were fetched from their drawings, and each needed
corrections found by re-rendering: the hammer came back standing where its drawing leans it,
so bake_model rolled it -22 degrees and widened its fill to keep the drawing's size. Here
both come in through polyweave's `normalise.ingest` against the drawing they were fetched
from, which finds which way round each faces and how far it leans (PW90, PW91): 22 degrees
for the hammer, the number bake_model held, without anyone stating it.

The ball is built, not fetched (ball_model.py says why), so it is written as ball_model
builds it, wearing its swirl.

Each mesh is scaled so its frame is the 200 px slot the well is composed in, at the board's
112 px/unit the plugin holds every asset to, as export_props.py does for the props: the
object spans the share of that frame its drawing does, as bake_model framed it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy  # isort: skip

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bake_model as B
import ball_model
from polyweave import normalise

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / ".polyweave" / "boosters"
PX = 200
CELL = 112.0

## the share of the frame each object spans, as bake_model framed it. The hammer's 0.72
## was taken off the box round its rolled bounding box's corners, which is wider than the
## hammer, so what it spans in the shipped render is 0.595 of the frame: that is the share
## here, measured on its leaned mesh's own extent
FILLS = {"hammer": 0.595, "wand": 0.62, "shuffle": 0.54}
FETCHED = ("hammer", "wand")


def ingest(name: str) -> Path:
    """The fetched mesh, turned and leaned to stand as its drawing does."""
    out = WORK / f"{name}.ingested.glb"
    normalise.ingest(
        f"tools/art/3d/booster_{name}.glb",
        out=out.relative_to(ROOT).as_posix(),
        against=f"tools/art/3d/booster_{name}.drawn.png",
        origin="centre",
        root=ROOT,
    )
    return out


def export(name: str) -> Path:
    """Write one booster's mesh, scaled to its frame at the board's scale."""
    if name in FETCHED:
        B.load(ingest(name))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        ball_model.build()
    obj = B.single_mesh()
    low, high = B.bounds(obj)
    span = high - low
    factor = (PX / CELL) / (max(span.x, span.z) / FILLS[name])
    obj.scale = [factor * s for s in obj.scale]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    out = WORK / f"{name}.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB")
    return out


def main() -> None:
    for name in FILLS:
        print(f"  {export(name).relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
