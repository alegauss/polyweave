"""The model a bake drew, drawn again by the game's own engine at the same rig (§PW495).

A finish accepted on a sitting reaches the game as the `.tres` a build wrote beside its
mesh, imported in place of glTF's own materials (§PW570). Whether the game then draws
what was judged is a question only a picture answers: `render.in_game` reads a bake's
record (its mesh and its rig), sets the same camera, the same three lights and the same
world in the game's project, draws the imported model there and sets the two pictures
side by side.

The rig is the bake's own arithmetic (`rig.camera_for`, `rig.lights_for`), so where the
camera stands and where the lights are cannot drift. What cannot be carried exactly is
the light itself: the bake's area lights are Cycles' watts and Godot has no area light,
so each becomes an omni light falling off by the inverse square at `LIGHT_SCALE` of its
watts. How far apart the two pictures may be and still agree is a person's tolerance,
never this function's, so it answers how far apart they are and gives a verdict only
against a tolerance the caller passes.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Annotated

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

from .rig import Rig, camera_for, lights_for

#: The Godot script that draws the model, carried by polyweave rather than the game.
SCRIPT = (Path(__file__).resolve().parents[2] / "engine" / "godot" / "model_at_rig.gd")
LINE = re.compile(r"^MODEL_AT_RIG shot=(?P<shot>.+)$", re.MULTILINE)

#: An omni light's energy per watt of the bake's area light. A Lambertian emitter of P
#: watts gives P / (pi d^2) of irradiance at d, and a diffuse surface sends a pi-th of
#: it back, where Godot's omni light of energy e at the inverse square sends e / d^2:
#: so 1 / pi^2. On a grey cone at the default rig the game's median light came out
#: 1.07 of the bake's (2026-11-03, Godot 4.7.1 on OpenGL); `light_scale` corrects it.
LIGHT_SCALE = 1.0 / math.pi ** 2

#: The world colour Blender gives a new world, linear 0.0509, as sRGB: the one every
#: bake with no `ambient_colour` was lit by.
BLENDER_WORLD = "#404040"

#: The rig fields a bake records that this reads.
_RIG = ("azimuth", "elevation", "margin", "focal_mm", "key", "fill", "rim",
        "light_distance", "ambient", "ambient_colour", "exposure", "transparent")


def _not_a_bake(bake: str, why: str) -> PolyweaveError:
    return PolyweaveError(
        "render.not-a-bake", f"{bake} {why}",
        "bake the model with render.bake, perspective and in its own materials, and "
        "name that picture", given=bake)


def _read_bake(bake: str, here: Path) -> tuple[Path, Rig, dict]:
    """The bake's mesh, its rig and its record, or why it cannot be drawn again."""
    try:
        record = provenance.read(bake, root=here)
    except PolyweaveError:
        record = None
    if not record or record.get("kind") != "render":
        raise _not_a_bake(bake, "has no bake record beside it")
    params = record.get("params", {})
    differs = [name for name in ("covers", "prepare", "material", "after")
               if params.get(name)]
    if differs:
        raise _not_a_bake(bake, f"was drawn with {', '.join(differs)}, so the game's "
                          "model is not what it shows")
    meshes = [one for one in record.get("inputs", []) if one.get("role") == "mesh"]
    if not meshes:
        raise _not_a_bake(bake, "was drawn from no mesh: the sphere rung draws none")
    mesh = here / meshes[0]["path"]
    if mesh.suffix.lower() != ".glb" or not mesh.is_file():
        raise _not_a_bake(bake, f"was drawn from {meshes[0]['path']}, which is no .glb "
                          "on disk")
    rig = Rig().with_(**{name: params[name] for name in _RIG if name in params})
    return mesh, rig, record


def _staged(rig: Rig, lo, hi, size: tuple[int, int], light_scale: float) -> dict:
    """The scene the game draws, in its own axes: the bake's camera, its three lights as
    omni lights, its world and its film, as the script takes them."""
    camera = camera_for(rig, lo, hi)
    wide, tall = size
    lights = [{"location": list(one["location"]),
               "energy": one["energy"] * LIGHT_SCALE * light_scale,
               "range": camera["radius"] * rig.light_distance * 4.0}
              for one in lights_for(rig, lo, hi)]
    return {
        "camera": {"location": list(camera["location"]),
                   "look_at": list(camera["look_at"]),
                   # Blender fits its sensor to the frame's longer side.
                   "fov_deg": math.degrees(rig.fov),
                   "keep": "width" if wide >= tall else "height"},
        "lights": lights,
        "ambient": {"colour": rig.ambient_colour or BLENDER_WORLD,
                    "energy": rig.ambient},
        "exposure": rig.exposure,
        "transparent": rig.transparent,
    }


def _apart(game: np.ndarray, bake: np.ndarray) -> dict:
    """How the two pictures differ: the silhouettes' overlap, and inside both, the
    game's median light against the bake's and the mean colour difference."""
    shown_g, shown_b = game[..., 3] > 127, bake[..., 3] > 127
    union = int((shown_g | shown_b).sum())
    both = shown_g & shown_b
    iou = float(both.sum()) / union if union else 1.0
    out = {"silhouette_iou": round(iou, 4)}
    if both.any():
        weights = np.array([0.2126, 0.7152, 0.0722])
        g = game[..., :3][both].astype(np.float64)
        b = bake[..., :3][both].astype(np.float64)
        out["light_ratio"] = round(float(np.median(g @ weights))
                                   / max(float(np.median(b @ weights)), 1e-6), 4)
        out["colour_apart"] = round(float(np.sqrt(((g - b) ** 2).sum(axis=1)).mean())
                                    / (math.sqrt(3) * 255.0), 4)
    return out


@operation("render.in_game", kind="capture")
def in_game(
    bake: Annotated[str, Param("a picture render.bake drew, under the project")],
    *,
    light_scale: Annotated[
        float, Param("the game's light against the derived match, 1 as derived",
                     lo=0.0)
    ] = 1.0,
    tolerance: Annotated[
        float, Param("the colour distance a person accepts, 0 to 1; 0 gives no verdict",
                     lo=0.0, hi=1.0)
    ] = 0.0,
    root: Annotated[str, Param("the game's project, holding project.godot")] = ".",
) -> dict:
    """Draw a baked model again in the game's own engine, at the bake's rig.

    Reads the bake's record for its .glb and rig, draws the model as the game imports
    it (its written .tres materials) under the same camera, lights and world, and
    writes `<bake>.game.png` recorded beside the bake, with a sheet of the two for a
    person. Answers the silhouettes' overlap, the light ratio and the colour distance;
    `agrees` only against a `tolerance` a person set.
    """
    from PIL import Image

    from polyweave.layers.engine import engine, offscreen
    from polyweave.loop import verdict

    config = load(root)
    here = config.root
    if not (here / "project.godot").is_file():
        raise PolyweaveError(
            "render.no-game", f"{here} holds no project.godot to draw the model in",
            "run it from the game's project, where the mesh is imported", given=root)
    picture = here / bake
    mesh, rig, _ = _read_bake(bake, here)
    from polyweave.layers.geometry import cost

    lo, hi = cost.bounds(mesh)
    with Image.open(picture) as opened:
        baked = np.asarray(opened.convert("RGBA"))
    size = (baked.shape[1], baked.shape[0])
    scene = _staged(rig, lo, hi, size, light_scale)
    shot = picture.with_name(picture.stem + ".game.png")
    try:
        route = offscreen.route_for(here)
    except PolyweaveError as refused:
        return {"ok": None, "skipped": refused.message,
                "says": "skipped: no route draws real pixels on this machine"}
    import json

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
    with Image.open(shot) as opened:
        drawn = np.asarray(opened.convert("RGBA"))
    measured = _apart(drawn, baked)
    provenance.write(provenance.build(
        "capture", shot, engine={"name": "godot", "route": route.name},
        inputs=[provenance.source("bake", picture, root=here),
                provenance.source("mesh", mesh, root=here)],
        params={"light_scale": light_scale, "staged": scene},
        root=here,
    ), root=here)
    sheet = provenance.relative(verdict.sheet(
        [{"name": mesh.stem, "old": provenance.relative(picture, here),
          "new": provenance.relative(shot, here)}],
        out=provenance.relative(picture.with_name(picture.stem + ".game.sheet.png"),
                                here),
        root=str(here))["sheet"], here)
    agrees = (None if not tolerance else
              measured.get("colour_apart", 1.0) <= tolerance
              and measured["silhouette_iou"] >= 1.0 - tolerance)
    return {
        "game": provenance.relative(shot, here),
        "sheet": sheet,
        "route": route.name,
        **measured,
        "agrees": agrees,
        "says": (f"the game's {mesh.name} overlaps the bake's silhouette by "
                 f"{measured['silhouette_iou']:.0%}"
                 + (f", its light {measured['light_ratio']:.2f} of the bake's and "
                    f"its colour {measured['colour_apart']:.3f} apart"
                    if "light_ratio" in measured else "")
                 + ("; a person judges the sheet" if agrees is None else
                    "; within the tolerance" if agrees else
                    "; outside the tolerance")),
    }
