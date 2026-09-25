"""A clip baked by name, to the animation and the sheet a game plays (§PW160).

A clip's own document was already operations: created, read, keyed, retimed and written
by name. What turns it into something a game plays was not. Fitting the skeleton,
weighting it, compiling the animation and baking the sheet each take a mesh and a fitted
rig as objects in memory, which a JSON call cannot carry, so a GDScript project still
needed a Python script for motion and for nothing else.

So one operation takes the three files by name, the shape `port.run` took for a family:
the clip, the mesh and the body plan. It fits, weights, compiles and bakes, and answers
with the paths written and `sprites.matched`'s verdict on the pair. The fit's numbers
(pull, influences, falloff) and the sheet's (fps, frames, trim, columns) come from the
project's `[rig]` and `[sprites]`, as they do for a script.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from .describe import Param, operation
from .errors import PolyweaveError
from .render.ladder import RUNGS


@operation("motion.bake", produces="render", kind="bake", injects=("report",))
def bake(
    report,
    clip: Annotated[str, Param("the clip file, as a path under the project")],
    mesh: Annotated[str, Param("the mesh the clip moves, a .glb under the project")],
    out: Annotated[
        str, Param("where to write, without a suffix: <out>.glb and <out>.png")
    ],
    *,
    plan: Annotated[
        str, Param("the body plan to fit; the project's [rig] plan if unset")
    ] = "",
    rung: Annotated[
        str, Param("the rung the sheet's frames render at", choices=RUNGS)
    ] = "preview",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Fit, weight, compile and bake one clip on one mesh, by name."""
    from . import clip as C
    from . import skeleton, sprites
    from .normalise import read_mesh

    here = Path(root).resolve()
    subject = C.read(clip, root=str(here))
    body_file = Path(mesh) if Path(mesh).is_absolute() else here / mesh
    if not body_file.is_file():
        raise PolyweaveError(
            "rig.no-mesh",
            f"there is no mesh at {body_file} for {subject['name']} to move",
            "name the .glb the clip is for, as a path under the project",
        )
    report.stage("building", note="fitting the skeleton to the mesh")
    body = read_mesh(body_file)
    rig = skeleton.fit(body, named=plan, root=str(here))
    bound = skeleton.weights(body, rig, root=str(here))

    report.stage("rendering", note=f"{subject['name']}: the animation and the sheet")
    where = Path(out) if Path(out).is_absolute() else here / out
    where.parent.mkdir(parents=True, exist_ok=True)
    found = sprites.both(
        subject, body, rig, bound, out=where, root=str(here), rung=rung
    )
    verdict = sprites.matched(found["animation"], found["sprites"], root=str(here))
    return {
        "clip": subject["name"],
        "plan": rig.get("plan"),
        "animation": str(found["animation"]["artefact"]),
        "sheet": str(found["sprites"]["sheet"]),
        "atlas": str(found["sprites"]["atlas"]),
        "matched": verdict["matched"],
        "why": verdict["why"],
    }
