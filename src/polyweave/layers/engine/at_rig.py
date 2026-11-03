"""A model drawn by the game's own engine at a rig another layer staged (§PW495).

The engine's half of `render.in_game`, answered as the part `engine.draw_at_rig` so the
geometry layer asks for it by name and never imports the engine: a project with
Blender and no Godot keeps its geometry whole.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from polyweave.kernel.errors import PolyweaveError

from . import engine, offscreen

#: The Godot script that draws the model, carried by polyweave rather than the game.
SCRIPT = Path(__file__).parent / "godot" / "model_at_rig.gd"
LINE = re.compile(r"^MODEL_AT_RIG shot=(?P<shot>.+)$", re.MULTILINE)


def draw(mesh: Path, scene: dict, size: tuple[int, int], shot: Path,
         here: Path) -> dict:
    """Import the project, then draw `mesh` as it imports under `scene` to `shot`.

    Answers the route it drew by, or `skipped` and why where no route draws here.
    """
    try:
        route = offscreen.route_for(here)
    except PolyweaveError as refused:
        return {"skipped": refused.message}
    engine._launch([engine.find(here), "--headless", "--import", "--path", str(here)],
                   cwd=here, timeout=600)
    found = offscreen.capture(
        SCRIPT, expect=LINE, root=here, route=route.name, frames=600,
        args=("--", f"model={engine._as_res(mesh, here)}", f"size={size[0]}x{size[1]}",
              f"shot={shot.as_posix()}", f"rig={json.dumps(scene)}"))
    if not shot.is_file():
        raise PolyweaveError(
            "engine.no-signal", f"the game drew no picture of {mesh.name}",
            "read the log for why the scene did not load or draw",
            detail=found.get("why") or found.get("log"))
    return {"route": route.name}
