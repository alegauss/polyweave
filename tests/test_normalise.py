"""Putting a fetched mesh into the project's own frame.

§PW20's case: the hammer came back standing upright where the drawing leans it, and two
angles were found by re-rendering until it looked right. Orientation, scale and
origin are mechanical, and this is the arithmetic that does them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polyweave import normalise
from polyweave.errors import PolyweaveError


def box(width=1.0, height=2.0, depth=0.5, *, at=(0.0, 0.0, 0.0), turn=None):
    """A box of stated proportions, optionally moved and rotated off the axes."""
    half = np.array([width, height, depth]) / 2.0
    corners = np.array(
        [
            [x, y, z]
            for x in (-half[0], half[0])
            for y in (-half[1], half[1])
            for z in (-half[2], half[2])
        ]
    )
    # Points on the faces too, so the cloud has variance rather than eight corners.
    dense = np.vstack([corners, corners * 0.5, corners * 0.25])
    if turn is not None:
        dense = dense @ np.asarray(turn, dtype=float).T
    return {"vertices": dense + np.array(at), "faces": [(0, 1, 2)]}


def around_x(degrees):
    a = np.radians(degrees)
    return np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])


def around_z(degrees):
    a = np.radians(degrees)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def cube(width=1.0, height=1.0, depth=1.0, *, at=(0.0, 0.0, 0.0)):
    """A closed box, so there are real faces to project rather than a point cloud."""
    half = np.array([width, height, depth]) / 2.0
    corners = (
        np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]) * half
    )
    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    return {"vertices": corners + np.array(at), "faces": faces}


def draw(where, wide, tall, *, pad=8):
    """A drawing that is one solid rectangle, which is all an outline needs to be."""
    from PIL import Image as PILImage

    canvas = np.zeros((tall + 2 * pad, wide + 2 * pad, 4), dtype=np.uint8)
    canvas[pad : pad + tall, pad : pad + wide] = (255, 255, 255, 255)
    PILImage.fromarray(canvas, "RGBA").save(where)
    return where


# -- the axes are the mesh's own -----------------------------------------------------


def test_the_longest_dimension_comes_first():
    found = normalise.axes(box(width=1.0, height=4.0, depth=0.5)["vertices"])
    # The first axis is the one the cloud varies most in — here, the tall one.
    assert abs(found[0] @ np.array([0.0, 1.0, 0.0])) > 0.99


def test_the_axes_follow_the_mesh_when_it_is_turned():
    turned = box(width=1.0, height=4.0, depth=0.5, turn=around_x(90))
    found = normalise.axes(turned["vertices"])
    # Turned a quarter about x, the long axis now points along z.
    assert abs(found[0] @ np.array([0.0, 0.0, 1.0])) > 0.99


def test_the_frame_is_a_rotation_and_not_a_reflection():
    found = normalise.axes(box()["vertices"])
    assert np.linalg.det(found) == pytest.approx(1.0)


def test_a_flat_mesh_has_no_orientation_to_give():
    flat = np.array([[x, 0.0, z] for x in (-1, 0, 1) for z in (-1, 0, 1)], dtype=float)
    with pytest.raises(PolyweaveError) as caught:
        normalise.axes(flat)
    assert caught.value.code == "mesh.degenerate"


def test_too_few_vertices_determine_nothing():
    with pytest.raises(PolyweaveError) as caught:
        normalise.axes(np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]))
    assert caught.value.code == "mesh.too-few-vertices"


# -- the frame is fixed only up to twenty-four ----------------------------------------


def test_the_axes_leave_twenty_four_ways_round():
    """Which is exactly the ambiguity a reference drawing is for."""
    found = normalise.rotations(normalise.axes(box()["vertices"]))
    assert len(found) == 24
    assert all(np.linalg.det(r) > 0 for r in found)


# -- scale and origin ------------------------------------------------------------------


def test_it_is_scaled_to_the_height_that_was_asked_for():
    found = normalise.normalise(box(width=2.0, height=8.0, depth=1.0), height=1.0)
    assert found["size"][1] == pytest.approx(1.0)
    assert found["scale"] == pytest.approx(0.125)


def test_the_proportions_survive_the_scaling():
    found = normalise.normalise(box(width=2.0, height=8.0, depth=1.0), height=1.0)
    width, height, depth = found["size"]
    assert width / height == pytest.approx(0.25)
    assert depth / height == pytest.approx(0.125)


def test_a_mesh_that_arrives_to_scale_keeps_its_size():
    found = normalise.normalise(box(width=2.0, height=8.0, depth=1.0), height=None)
    assert found["scale"] == 1.0
    assert found["size"][1] == pytest.approx(8.0)


def test_it_stands_on_the_origin_rather_than_straddling_it():
    """§6: the origin is the base of the silhouette, never the centre of the box."""
    found = normalise.normalise(box(at=(7.0, 3.0, -2.0)), height=1.0)
    low, high = found["bounds"]
    assert low[1] == pytest.approx(0.0)  # the ground plane
    assert (low[0] + high[0]) / 2 == pytest.approx(0.0)  # centred across
    assert (low[2] + high[2]) / 2 == pytest.approx(0.0)


def test_wherever_it_arrived_it_lands_in_the_same_place():
    here = normalise.normalise(box(at=(0.0, 0.0, 0.0)))
    far = normalise.normalise(box(at=(100.0, -40.0, 12.0)))
    assert np.allclose(here["bounds"], far["bounds"])


def test_the_footprint_is_the_origin_when_it_is_done():
    found = normalise.normalise(box(at=(5.0, 5.0, 5.0)))
    assert np.allclose(normalise.footprint(found), [0.0, 0.0, 0.0], atol=1e-9)


def test_a_mesh_with_no_height_cannot_be_scaled_to_one():
    flat = {
        "vertices": np.array([[x, 0.0, z] for x in (-1, 1) for z in (-1, 1)] * 3),
        "faces": [],
    }
    with pytest.raises(PolyweaveError) as caught:
        normalise.normalise(flat, height=1.0)
    assert caught.value.code == "mesh.degenerate"


# -- what gets recorded ----------------------------------------------------------------


def test_the_whole_correction_is_one_matrix():
    """So nothing downstream carries a correction angle of its own."""
    found = normalise.normalise(box(at=(3.0, 2.0, 1.0)), height=1.0)
    matrix = normalise.as_matrix(found)
    assert matrix.shape == (4, 4)
    assert matrix[3, 3] == 1.0


def test_the_rotation_that_was_applied_is_recorded():
    turn = around_x(90)
    found = normalise.normalise(box(), rotation=turn, height=1.0)
    assert np.allclose(np.array(found["rotation"]), turn)


def test_no_rotation_records_as_no_rotation():
    found = normalise.normalise(box())
    assert np.allclose(np.array(found["rotation"]), np.eye(3))


# -- which way is forward --------------------------------------------------------------


def test_the_reference_picks_the_orientation_that_matches_it():
    """The hammer, settled by the drawing rather than by two angles found by eye."""
    tall = box(width=0.4, height=4.0, depth=0.4)

    def look(placed):
        # A stand-in for the front render: prefer the candidate that is widest across.
        return float(placed["size"][0])

    found = normalise.choose(tall, look)
    assert found["size"][0] > found["size"][1], "it was laid down to match"
    assert found["tried"] == 24


def test_it_reports_what_it_tried():
    found = normalise.choose(
        box(width=1.0, height=3.0, depth=0.2), lambda p: p["size"][2]
    )
    assert found["tried"] == 24
    assert "score" in found


def test_a_reference_that_settles_nothing_is_said_so_rather_than_guessed():
    """Guessing an orientation is the judgement this does not make."""
    with pytest.raises(PolyweaveError) as caught:
        normalise.choose(box(1.0, 2.0, 0.5), lambda placed: 1.0)
    assert caught.value.code == "mesh.ambiguous-forward"
    assert "judgement" in caught.value.remedy


def test_the_chosen_orientation_is_the_same_one_every_time():
    """A frame that turns on a random seed is not an answer."""
    tall = box(width=0.4, height=4.0, depth=0.4)

    def look(placed):
        return float(placed["size"][0])

    first = normalise.choose(tall, look)
    again = normalise.choose(tall, look)
    assert np.allclose(np.array(first["rotation"]), np.array(again["rotation"]))


def test_the_chosen_orientation_comes_back_already_normalised():
    found = normalise.choose(
        box(width=0.4, height=4.0, depth=0.4), lambda p: float(p["size"][0])
    )
    low, high = found["bounds"]
    assert low[1] == pytest.approx(0.0)
    assert max(high[i] - low[i] for i in range(3)) == pytest.approx(
        found["size"][int(np.argmax(np.array(found["size"])))]
    )


# -- the outline, without a renderer ---------------------------------------------------


def extent(mask):
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    return int(columns[-1] - columns[0] + 1), int(rows[-1] - rows[0] + 1)


def test_a_tall_box_has_a_tall_outline():
    wide, tall = extent(normalise.project(normalise.normalise(cube(1.0, 4.0, 1.0))))
    assert tall > wide * 3


def test_the_same_box_laid_down_has_a_wide_one():
    laid = normalise.normalise(cube(1.0, 4.0, 1.0), rotation=around_z(90))
    wide, tall = extent(normalise.project(laid))
    assert wide > tall * 3


def test_a_face_is_filled_and_not_just_sampled():
    """A rasteriser that leaves pinholes would rank orientations on its own noise."""
    mask = normalise.project(normalise.normalise(cube(1.0, 2.0, 1.0)))
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    inside = mask[rows[0] : rows[-1] + 1, columns[0] : columns[-1] + 1]
    assert inside.all()


def test_an_outline_overlaps_itself_entirely():
    mask = normalise.project(normalise.normalise(cube(1.0, 3.0, 1.0)))
    assert normalise.overlap(mask, mask) == 1.0


def test_two_different_outlines_barely_overlap():
    upright = normalise.project(normalise.normalise(cube(1.0, 4.0, 1.0)))
    laid = normalise.project(
        normalise.normalise(cube(1.0, 4.0, 1.0), rotation=around_z(90))
    )
    assert normalise.overlap(upright, laid) < 0.3


def test_a_projection_is_the_same_every_time():
    subject = normalise.normalise(cube(1.0, 2.5, 0.7))
    assert np.array_equal(normalise.project(subject), normalise.project(subject))


# -- the drawing -----------------------------------------------------------------------


def test_the_drawing_comes_back_on_the_grid_with_its_proportions(tmp_path):
    mask = normalise.drawing(draw(tmp_path / "wide.png", 80, 20), alpha_floor=0.0)
    wide, tall = extent(mask)
    assert wide / tall == pytest.approx(4.0, abs=0.2)
    assert mask.shape == (normalise.GRID, normalise.GRID)


def test_how_the_drawing_was_framed_does_not_change_its_outline(tmp_path):
    tight = normalise.drawing(
        draw(tmp_path / "tight.png", 80, 20, pad=2), alpha_floor=0.0
    )
    loose = normalise.drawing(
        draw(tmp_path / "loose.png", 160, 40, pad=90), alpha_floor=0.0
    )
    assert normalise.overlap(tight, loose) > 0.9


def test_a_drawing_with_nothing_in_it_is_refused(tmp_path):
    from PIL import Image as PILImage

    empty = tmp_path / "empty.png"
    PILImage.fromarray(np.zeros((32, 32, 4), dtype=np.uint8), "RGBA").save(empty)
    with pytest.raises(PolyweaveError) as caught:
        normalise.drawing(empty, alpha_floor=0.0)
    assert caught.value.code == "fetch.no-reference"


# -- the whole of it: the drawing settles which way is forward -------------------------


def test_the_drawing_decides_which_way_round_the_mesh_goes(tmp_path):
    """§PW20's hammer. Two angles found by re-rendering; one drawing already knew."""
    found = normalise.orient(
        cube(1.0, 4.0, 1.0),
        against=draw(tmp_path / "hammer.png", 120, 30),
        alpha_floor=0.0,
    )
    assert found["size"][0] == pytest.approx(4.0, abs=0.1), "the long axis lies across"
    assert found["size"][1] == pytest.approx(1.0)
    assert found["silhouette_iou"] > 0.8
    assert found["tried"] == 24


def test_the_drawing_can_also_say_upright(tmp_path):
    found = normalise.orient(
        cube(1.0, 4.0, 1.0),
        against=draw(tmp_path / "upright.png", 30, 120),
        alpha_floor=0.0,
    )
    assert found["size"][1] == pytest.approx(1.0)
    assert found["size"][0] == pytest.approx(0.25, abs=0.02), "it stands"
    assert found["silhouette_iou"] > 0.8


def test_the_orientation_it_chose_is_recorded_beside_the_drawing(tmp_path):
    reference = draw(tmp_path / "hammer.png", 120, 30)
    found = normalise.orient(cube(1.0, 4.0, 1.0), against=reference, alpha_floor=0.0)
    assert found["against"] == str(reference)
    assert np.linalg.det(np.array(found["rotation"])) == pytest.approx(1.0)


def test_a_shape_the_drawing_cannot_tell_apart_is_said_so(tmp_path):
    """A cube against a square: every way round matches, and none of them is forward."""
    square = draw(tmp_path / "square.png", 40, 40)
    with pytest.raises(PolyweaveError) as caught:
        normalise.orient(cube(1.0, 1.0, 1.0), against=square, alpha_floor=0.0)
    assert caught.value.code == "mesh.ambiguous-forward"


# -- on arrival ------------------------------------------------------------------------


def test_a_mesh_arrives_and_is_stored_in_the_project_s_frame(tmp_path):
    pytest.importorskip("bpy")
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(1.0, 4.0, 1.0)), tmp_path / "raw.glb")
    record = normalise.ingest(
        source, out=tmp_path / "kept.glb", against=draw(tmp_path / "ref.png", 120, 30)
    )
    assert Path(record["mesh"]).is_file()
    assert record["size"][0] == pytest.approx(4.0, abs=0.2)
    assert record["size"][1] == pytest.approx(1.0, abs=0.05)
    assert record["faces"] >= 6


def test_what_was_applied_is_recorded_so_nothing_downstream_repeats_it(tmp_path):
    pytest.importorskip("bpy")
    from polyweave.normalise import write_mesh

    source = write_mesh(
        normalise.normalise(cube(2.0, 8.0, 2.0), height=None), tmp_path / "raw.glb"
    )
    record = normalise.ingest(source, out=tmp_path / "kept.glb")
    assert record["scale"] == pytest.approx(0.125, rel=0.01)
    assert np.array(record["matrix"]).shape == (4, 4)
    assert record["source"] == str(source)


def painted(where):
    """A quad a service might return: UVs, and a colour that is only a texture."""
    import bpy

    from polyweave.render import blender

    blender.reset()
    bpy.ops.mesh.primitive_plane_add(size=2.0)
    quad = bpy.context.active_object
    quad.scale = (1.0, 3.0, 1.0)
    quad.rotation_euler = (1.5707963, 0.0, 0.0)  # standing, so it has a height to scale
    picture = bpy.data.images.new("paint", 4, 4)
    picture.pixels = [0.9, 0.3, 0.1, 1.0] * 16
    picture.pack()
    paint = bpy.data.materials.new("paint")
    paint.use_nodes = True
    texture = paint.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = picture
    shader = paint.node_tree.nodes["Principled BSDF"]
    paint.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    quad.data.materials.append(paint)
    bpy.ops.export_scene.gltf(filepath=str(where), use_selection=False)
    return where


def test_what_a_service_painted_comes_through_ingest(tmp_path):
    """§PW90: the fetched hammer came out the right way round, the right size, white."""
    bpy = pytest.importorskip("bpy")
    from polyweave.render import blender

    source = painted(tmp_path / "raw.glb")
    record = normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)
    obj = blender.load_mesh(record["mesh"])
    assert obj.data.uv_layers, "the coordinates the paint is laid on"
    fed = [
        node
        for material in obj.data.materials
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE" and node.image is not None
    ]
    assert fed, "and a material still reading its image"
    assert bpy.data.images


def test_the_file_written_is_where_the_maths_put_it(tmp_path):
    """Moved in place rather than rebuilt, so the two have to agree."""
    pytest.importorskip("bpy")
    from polyweave.normalise import read_mesh

    source = painted(tmp_path / "raw.glb")
    record = normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)
    back = np.asarray(read_mesh(record["mesh"])["vertices"], dtype=float)
    size = back.max(axis=0) - back.min(axis=0)
    assert size == pytest.approx(np.array(record["size"]), abs=1e-4)
    assert back[:, 1].min() == pytest.approx(0.0, abs=1e-4), "standing on the ground"


# -- and what it derived is recorded beside it (§PW46) ---------------------------------


def test_the_normalised_mesh_carries_a_record_of_its_own(tmp_path):
    """The ledger holds the bytes that arrived; the project loads this one."""
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(2.0, 8.0, 2.0)), tmp_path / "raw.glb")
    found = normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)

    written = provenance.read("kept.glb", root=tmp_path)
    assert written["kind"] == "mesh"
    assert Path(found["provenance"]).is_file()
    assert written["artefact"]["path"] == "kept.glb"


def test_the_parent_is_named_by_hash_so_a_mesh_that_moved_is_the_same_parent(tmp_path):
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(2.0, 8.0, 2.0)), tmp_path / "raw.glb")
    normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)

    parent = provenance.read("kept.glb", root=tmp_path)["inputs"][0]
    assert parent["role"] == "mesh"
    assert parent["sha256"] == provenance.sha256_of(source)[0]
    assert parent["path"] == "raw.glb"


def test_the_transform_is_in_the_record_so_the_chain_can_be_followed(tmp_path):
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(
        normalise.normalise(cube(2.0, 8.0, 2.0), height=None), tmp_path / "raw.glb"
    )
    found = normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)

    params = provenance.read("kept.glb", root=tmp_path)["params"]
    assert params["scale"] == pytest.approx(found["scale"])
    assert np.array(params["matrix"]).shape == (4, 4)
    assert params["offset"] == found["offset"]


def test_a_normalisation_has_no_engine_seed_or_sampler_and_says_so_by_absence(tmp_path):
    """One vocabulary, with what does not apply absent rather than null: a record
    carrying four nulls claims it has them and they are unknown, which is not true."""
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(2.0, 8.0, 2.0)), tmp_path / "raw.glb")
    normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)

    written = provenance.read("kept.glb", root=tmp_path)
    assert not {"engine", "rung", "seed", "samples"} & set(written)
    assert {"artefact", "kind", "inputs", "params", "producer"} <= set(written)


def test_one_mesh_normalised_twice_leaves_two_records_naming_one_parent(tmp_path):
    """Which is a fact. Two files and no records is a question nobody can answer."""
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(1.0, 4.0, 1.0)), tmp_path / "raw.glb")
    normalise.ingest(
        source,
        out=tmp_path / "wide.glb",
        against=draw(tmp_path / "wide.png", 120, 30),
        root=tmp_path,
    )
    normalise.ingest(
        source,
        out=tmp_path / "tall.glb",
        against=draw(tmp_path / "tall.png", 30, 120),
        root=tmp_path,
    )
    parents = {
        provenance.read(n, root=tmp_path)["inputs"][0]["sha256"]
        for n in ("wide.glb", "tall.glb")
    }
    assert len(parents) == 1, "two records, one parent"


def test_verify_no_longer_reads_the_derived_mesh_as_unrecorded(tmp_path):
    """The whole point: the mesh the project loads stops being invisible to verify."""
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    (tmp_path / "polyweave.toml").write_text(
        "[paths]\nmeshes = 'assets/3d'\n", encoding="utf-8"
    )
    (tmp_path / "assets" / "3d").mkdir(parents=True)
    source = write_mesh(
        normalise.normalise(cube(2.0, 8.0, 2.0)), tmp_path / "assets" / "3d" / "raw.glb"
    )
    provenance.write(provenance.build("fetch", source, root=tmp_path), root=tmp_path)
    normalise.ingest(source, out=tmp_path / "assets" / "3d" / "kept.glb", root=tmp_path)
    assert provenance.unrecorded(tmp_path) == []


def test_a_mesh_oriented_against_a_drawing_records_the_bars_it_was_judged_by(tmp_path):
    """The silhouette IoU beside it is a number until something says against what."""
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(1.0, 4.0, 1.0)), tmp_path / "raw.glb")
    normalise.ingest(
        source,
        out=tmp_path / "kept.glb",
        against=draw(tmp_path / "ref.png", 120, 30),
        root=tmp_path,
    )
    written = provenance.read("kept.glb", root=tmp_path)
    assert written["tolerances"]["alpha_floor"] == pytest.approx(0.02)
    assert set(written["tolerances"]) == {
        "alpha_floor",
        "render_noise",
        "silhouette_iou",
        "delta_e",
        "background_delta_e",
        "subject_coverage",
        "subject_extent",
    }
    assert provenance.remeasure(written, written["tolerances"]) == []


def test_the_floor_recorded_is_the_one_that_decided_the_mask(tmp_path):
    """Not what the project would decide today, which is the whole point (§PW51)."""
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(1.0, 4.0, 1.0)), tmp_path / "raw.glb")
    normalise.ingest(
        source,
        out=tmp_path / "kept.glb",
        against=draw(tmp_path / "ref.png", 120, 30),
        alpha_floor=0.25,
        root=tmp_path,
    )
    written = provenance.read("kept.glb", root=tmp_path)
    assert written["tolerances"]["alpha_floor"] == pytest.approx(0.25)


def test_a_mesh_with_no_drawing_measured_nothing_against_a_bar(tmp_path):
    pytest.importorskip("bpy")
    from polyweave import provenance
    from polyweave.normalise import write_mesh

    source = write_mesh(normalise.normalise(cube(2.0, 8.0, 2.0)), tmp_path / "raw.glb")
    normalise.ingest(source, out=tmp_path / "kept.glb", root=tmp_path)
    assert "tolerances" not in provenance.read("kept.glb", root=tmp_path)
