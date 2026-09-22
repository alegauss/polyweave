"""Checking a shape against the drawing that asked for it, before paying for it.

§PW16's case: a wide low cap on a short stem was sent, a tall dome on a long stem came
back, and thirty credits had already gone. The check that would have caught it costs
nothing, and this is it.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import shape
from polyweave.errors import PolyweaveError


def project(tmp_path, text=""):
    (tmp_path / "polyweave.toml").write_text(text, encoding="utf-8")
    return tmp_path


def drawing(tmp_path, name, *, rows, columns, size=64):
    """A silhouette as a drawing gives one: coverage and nothing else."""
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[rows, columns, 3] = 255
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def wide_low_cap(tmp_path, name="cap.png"):
    return drawing(tmp_path, name, rows=slice(40, 64), columns=slice(8, 56))


def tall_dome(tmp_path, name="dome.png"):
    return drawing(tmp_path, name, rows=slice(8, 64), columns=slice(24, 40))


# -- the case this line exists for --------------------------------------------------


def test_the_tall_dome_is_rejected_against_the_wide_low_cap(tmp_path):
    """Thirty credits, caught for nothing."""
    where = project(tmp_path)
    found = shape.check(tall_dome(where), against=wide_low_cap(where), root=where)
    assert found["holds"] is False
    assert found["silhouette_iou"] < 0.3
    assert "under a bar of" in found["why"]


def test_a_shape_that_matches_holds(tmp_path):
    where = project(tmp_path)
    asked = wide_low_cap(where)
    came_back = drawing(where, "back.png", rows=slice(40, 64), columns=slice(8, 56))
    found = shape.check(came_back, against=asked, root=where)
    assert found["holds"] is True
    assert found["silhouette_iou"] == 1.0


def test_a_rejection_carries_the_picture_and_the_drawing(tmp_path):
    """ "It came back wrong" is not actionable; a file somebody can open is."""
    where = project(tmp_path)
    came_back = tall_dome(where)
    asked = wide_low_cap(where)
    with pytest.raises(PolyweaveError) as caught:
        shape.require(came_back, against=asked, root=where)
    assert caught.value.code == "fetch.shape-rejected"
    assert str(came_back) in caught.value.remedy
    assert str(asked) in caught.value.remedy
    assert "px" in caught.value.remedy


def test_a_shape_that_holds_passes_the_gate(tmp_path):
    where = project(tmp_path)
    asked = wide_low_cap(where)
    assert shape.require(asked, against=asked, root=where)["holds"] is True


# -- the bar is the project's --------------------------------------------------------


def test_the_threshold_comes_from_the_project(tmp_path):
    where = project(tmp_path, "[tolerance]\nsilhouette_iou = 0.2\n")
    found = shape.check(tall_dome(where), against=wide_low_cap(where), root=where)
    assert found["threshold"] == 0.2
    assert found["holds"] is True  # a laxer bar lets the same shape through


def test_a_caller_may_state_its_own_bar(tmp_path):
    where = project(tmp_path)
    found = shape.check(
        tall_dome(where), against=wide_low_cap(where), root=where, threshold=0.1
    )
    assert found["threshold"] == 0.1


# -- what else it reports --------------------------------------------------------------


def test_it_reports_how_the_shape_differs_not_only_that_it_does(tmp_path):
    where = project(tmp_path)
    found = shape.check(tall_dome(where), against=wide_low_cap(where), root=where)
    assert found["centroid_offset"] > 0
    assert found["bbox_delta"] > 0


def test_a_preview_is_checked_without_rendering_anything(tmp_path):
    """Where the service offers a preview, that is the cheapest place to find out."""
    where = project(tmp_path)
    found = shape.check(tall_dome(where), against=wide_low_cap(where), root=where)
    assert found["rendered"] is False


def test_a_drawing_that_is_not_there_is_refused(tmp_path):
    where = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        shape.check(tall_dome(where), against="nothing/here.png", root=where)
    assert caught.value.code == "fetch.no-reference"


def test_a_reference_of_another_size_still_compares(tmp_path):
    """A render and a drawing of different sizes are normalised before comparing."""
    where = project(tmp_path)
    big = drawing(where, "big.png", rows=slice(32, 64), columns=slice(0, 64), size=64)
    small = drawing(
        where, "small.png", rows=slice(8, 16), columns=slice(0, 16), size=16
    )
    assert shape.check(big, against=small, root=where)["holds"] is True


def test_a_mesh_is_recognised_from_a_picture():
    assert shape.is_mesh("a.glb") is True
    assert shape.is_mesh("a.gltf") is True
    assert shape.is_mesh("a.png") is False


# -- against a real mesh ---------------------------------------------------------------


def test_a_returned_mesh_is_rendered_front_on_and_checked(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    import bpy

    from polyweave import config as C

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 48\nfinal_size = 48\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n\n"
        "[tolerance]\nsilhouette_iou = 0.6\n",
        encoding="utf-8",
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=2.0, vertices=48)
    mesh = tmp_path / "shape.glb"
    bpy.ops.export_scene.gltf(filepath=str(mesh), export_format="GLB")

    # The mesh against its own silhouette holds, whatever the cone happens to look like.
    first = shape.check(mesh, against=wide_low_cap(tmp_path), root=tmp_path)
    assert first["rendered"] is True
    assert (tmp_path / ".polyweave" / "shape" / "front.png").is_file()

    itself = shape.check(
        first["picture"], against=first["picture"], root=tmp_path, threshold=0.99
    )
    assert itself["holds"] is True
    assert itself["silhouette_iou"] == 1.0
