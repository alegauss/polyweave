"""A baked model drawn again by the game's own engine at the bake's rig (§PW495).

The rig's arithmetic, the comparison and the refusals are checked everywhere. The draw
itself needs Blender for the bake and `$GODOT` for the game.
"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

from polyweave.kernel import config as C
from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry.render import in_game
from polyweave.layers.geometry.render.rig import Rig, as_params, camera_for, lights_for


def test_the_game_is_staged_at_the_bakes_own_rig():
    rig = Rig().with_(azimuth=20.0, key=300.0, ambient_colour="#102030")
    lo, hi = (-1.0, 0.0, -1.0), (1.0, 2.0, 1.0)
    scene = in_game._staged(rig, lo, hi, (128, 128), light_scale=2.0)
    camera = camera_for(rig, lo, hi)
    assert scene["camera"]["location"] == pytest.approx(list(camera["location"]))
    assert scene["camera"]["look_at"] == pytest.approx(list(camera["look_at"]))
    # Blender's 36 mm sensor across the frame's longer side, as Godot's width-kept fov.
    assert scene["camera"]["fov_deg"] == pytest.approx(
        math.degrees(2 * math.atan(36 / (2 * rig.focal_mm))))
    assert scene["camera"]["keep"] == "width"
    assert in_game._staged(rig, lo, hi, (64, 128), 1.0)["camera"]["keep"] == "height"
    lights = lights_for(rig, lo, hi)
    assert [one["location"] for one in scene["lights"]] == [
        pytest.approx(list(one["location"])) for one in lights]
    assert scene["lights"][0]["energy"] == pytest.approx(
        lights[0]["energy"] * in_game.LIGHT_SCALE * 2.0)
    assert scene["ambient"] == {"colour": "#102030", "energy": rig.ambient}
    # A bake with no world colour was lit by Blender's own.
    assert in_game._staged(Rig(), lo, hi, (8, 8), 1.0)["ambient"]["colour"] == "#404040"


def _picture(shown, colour, size=32):
    out = np.zeros((size, size, 4), np.uint8)
    out[shown] = (*colour, 255)
    return out


def test_two_pictures_are_set_apart_by_silhouette_light_and_colour():
    body = np.zeros((32, 32), bool)
    body[8:24, 8:24] = True
    lit = _picture(body, (200, 100, 50))
    same = in_game._apart(lit, lit)
    assert same == {"silhouette_iou": 1.0, "light_ratio": 1.0, "colour_apart": 0.0}
    darker = in_game._apart(_picture(body, (100, 50, 25)), lit)
    assert darker["light_ratio"] == pytest.approx(0.5, abs=0.01)
    assert darker["colour_apart"] > 0
    half = body.copy()
    half[16:, :] = False
    assert in_game._apart(_picture(half, (1, 1, 1)),
                          _picture(body, (1, 1, 1)))["silhouette_iou"] == 0.5


@pytest.fixture
def game(tmp_path):
    (tmp_path / C.FILENAME).write_text("", encoding="utf-8")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "cone.glb").write_bytes(b"glTF")
    (tmp_path / "bake.png").write_bytes(b"png")
    return tmp_path


def _recorded(root, inputs=("mesh",), **params):
    provenance.write(provenance.build(
        "render", root / "bake.png",
        inputs=[provenance.source(role, root / "cone.glb", root=root)
                for role in inputs],
        params={**as_params(Rig()), **params}, root=root), root=root)


@pytest.mark.parametrize("why", ["no record", "covers", "prepare", "no mesh"])
def test_a_picture_that_is_no_bake_of_the_games_model_is_refused(game, why):
    if why == "covers":
        _recorded(game, covers=[2, 2])
    elif why == "prepare":
        _recorded(game, prepare=[{"step": "fill"}])
    elif why == "no mesh":
        _recorded(game, inputs=())
    with pytest.raises(PolyweaveError) as refused:
        in_game.in_game("bake.png", root=str(game))
    assert refused.value.code == "render.not-a-bake"


def test_a_folder_with_no_game_is_refused(game):
    (game / "project.godot").unlink()
    with pytest.raises(PolyweaveError) as refused:
        in_game.in_game("bake.png", root=str(game))
    assert refused.value.code == "render.no-game"


def test_the_game_draws_the_baked_model_where_the_bake_did(tmp_path):
    """Blender bakes a cone; Godot draws it again from the bake's record alone."""
    pytest.importorskip("bpy")
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    import bpy

    from polyweave.layers.geometry import render

    (tmp_path / C.FILENAME).write_text(
        "[render]\nfinal_size = 96\nsamples = { sphere = 4, preview = 4, final = 16 }\n"
        "seed = 11\n", encoding="utf-8")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=2.0, vertices=64)
    (tmp_path / "assets").mkdir()
    bpy.ops.export_scene.gltf(filepath=str(tmp_path / "assets" / "cone.glb"),
                              export_format="GLB")

    class Quiet:
        def stage(self, *_, **__):
            pass

        def progress(self, *_, **__):
            pass

        def note(self, *_):
            pass

    render.bake(Quiet(), out="bake.png", rung="final", model="assets/cone.glb",
                root=str(tmp_path))
    drawn = in_game.in_game("bake.png", root=str(tmp_path))
    if drawn.get("skipped"):
        pytest.skip(drawn["skipped"])
    assert drawn["game"] == "bake.game.png"
    # The camera is the bake's: the cone stands in the same place at the same size.
    assert drawn["silhouette_iou"] >= 0.9, drawn
    assert drawn["light_ratio"] > 0 and drawn["agrees"] is None
    assert drawn["sheet"] == "bake.game.sheet.png"
    assert (tmp_path / drawn["sheet"]).is_file()
    record = provenance.read("bake.game.png", root=str(tmp_path))
    assert {one["role"] for one in record["inputs"]} == {"bake", "mesh"}
