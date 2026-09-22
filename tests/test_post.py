"""§2 of the tool surface: every operation asserts its own output.

The three silent failures §PW2 is drawn from each have a test here — the bevelled
boolean that returns nothing, the render that came out blank, and the download that
stopped early.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import post
from polyweave.errors import PolyweaveError

# -- meshes --------------------------------------------------------------------

CUBE_VERTS = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
]  # fmt: skip
CUBE_FACES = [
    (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
    (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
]  # fmt: skip


def cube():
    return {"vertices": CUBE_VERTS, "faces": CUBE_FACES}


def test_a_mesh_with_faces_passes_and_reports_its_bounds():
    measured = post.check("mesh", cube())
    assert measured["faces"] == 6
    assert measured["vertices"] == 8
    assert measured["bounds"] == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]


def test_an_empty_mesh_is_an_error_not_a_warning():
    with pytest.raises(PolyweaveError) as caught:
        post.check("mesh", {"vertices": [], "faces": []})
    assert caught.value.code == "post.mesh-empty"


def test_a_nan_vertex_is_named_before_anything_renders_it():
    verts = list(CUBE_VERTS)
    verts[2] = (float("nan"), 1, 0)
    with pytest.raises(PolyweaveError) as caught:
        post.check("mesh", {"vertices": verts, "faces": CUBE_FACES})
    assert caught.value.code == "post.mesh-nan"
    assert "1 of 8" in caught.value.message


def test_an_infinite_vertex_leaves_the_mesh_with_no_bounds():
    verts = list(CUBE_VERTS)
    verts[5] = (float("inf"), 0, 1)
    with pytest.raises(PolyweaveError) as caught:
        post.check("mesh", {"vertices": verts, "faces": CUBE_FACES})
    assert caught.value.code == "post.mesh-unbounded"


def test_a_mesh_is_read_off_an_object_a_mapping_or_a_pair():
    class Mesh:
        vertices = CUBE_VERTS
        faces = CUBE_FACES

    assert post.check("mesh", Mesh())["faces"] == 6
    assert post.check("mesh", cube())["faces"] == 6
    assert post.check("mesh", (CUBE_VERTS, CUBE_FACES))["faces"] == 6


def test_something_that_is_not_a_mesh_says_so():
    with pytest.raises(PolyweaveError) as caught:
        post.check("mesh", 7)
    assert caught.value.code == "post.not-a-mesh"


# -- the boolean that cost a render --------------------------------------------


def test_a_boolean_that_emptied_names_the_bevel():
    """§PW2: 2402 faces for one cut, 0 for the same cut after a bevel, no error."""
    empty = {"vertices": [], "faces": []}
    with pytest.raises(PolyweaveError) as caught:
        post.check("boolean", empty, operands=(2402, 96))
    assert caught.value.code == "post.boolean-empty"
    assert "2402 and 96" in caught.value.message
    assert "bevel" in caught.value.remedy.lower()


def test_a_boolean_of_two_empty_operands_is_only_an_empty_mesh():
    """Nothing in, nothing out is not the bevel bug, so it keeps the plainer code."""
    empty = {"vertices": [], "faces": []}
    with pytest.raises(PolyweaveError) as caught:
        post.check("boolean", empty, operands=(0, 96))
    assert caught.value.code == "post.mesh-empty"


def test_a_boolean_that_produced_faces_reports_its_operands():
    measured = post.check("boolean", cube(), operands=(cube(), cube()))
    assert measured["faces"] == 6
    assert measured["operands"] == [6, 6]


def test_a_boolean_needs_exactly_two_operands():
    with pytest.raises(PolyweaveError) as caught:
        post.check("boolean", cube(), operands=(6, 6, 6))
    assert caught.value.code == "post.bad-operands"


# -- the expensive one is opt-in -----------------------------------------------


def test_manifold_does_not_run_unless_it_is_asked_for():
    open_box = {"vertices": CUBE_VERTS, "faces": CUBE_FACES[:-1]}
    post.check("mesh", open_box)  # cheap checks alone: a hole is not their business
    with pytest.raises(PolyweaveError) as caught:
        post.check("mesh", open_box, optional=("manifold",))
    assert caught.value.code == "post.mesh-non-manifold"


def test_manifold_passes_on_a_closed_mesh():
    measured = post.check("mesh", cube(), optional=("manifold",))
    assert measured["manifold"] is True
    assert measured["edges"] == 12


def test_an_unknown_optional_check_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        post.check("mesh", cube(), optional=("watertight",))
    assert caught.value.code == "post.unknown-check"
    assert "manifold" in caught.value.remedy


def test_an_optional_check_that_does_not_apply_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        post.check(
            "render", _png(tmp_path, "a.png"), optional=("manifold",), alpha_floor=0.0
        )
    assert caught.value.code == "post.check-misapplied"


# -- pictures ------------------------------------------------------------------


def _png(tmp_path, name, *, size=(8, 8), fill=None, alpha=255):
    rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    rgba[:, :, 3] = alpha
    if fill is None:
        # A gradient, so the image is not uniform.
        rgba[:, :, 0] = np.arange(size[0], dtype=np.uint8)[None, :]
        rgba[:, :, 1] = 128
    else:
        rgba[:, :, :3] = fill
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def test_a_render_with_content_passes_and_reports_its_size(tmp_path):
    measured = post.check(
        "render", _png(tmp_path, "r.png", size=(16, 9)), alpha_floor=0.0
    )
    assert measured["size"] == [16, 9]
    assert measured["alpha_coverage"] == 1.0


def test_a_render_of_one_flat_colour_is_refused(tmp_path):
    path = _png(tmp_path, "flat.png", fill=(17, 17, 17))
    with pytest.raises(PolyweaveError) as caught:
        post.check("render", path, alpha_floor=0.0)
    assert caught.value.code == "post.render-uniform"
    assert "#111111" in caught.value.message
    assert "allow_uniform" in caught.value.remedy


def test_a_fully_transparent_render_is_refused(tmp_path):
    path = _png(tmp_path, "gone.png", alpha=0)
    with pytest.raises(PolyweaveError) as caught:
        post.check("render", path, alpha_floor=0.0)
    assert caught.value.code == "post.render-transparent"


def test_the_wrong_dimensions_are_refused_against_what_was_asked_for(tmp_path):
    path = _png(tmp_path, "small.png", size=(8, 8))
    with pytest.raises(PolyweaveError) as caught:
        post.check("render", path, size=(512, 512), alpha_floor=0.0)
    assert caught.value.code == "post.render-size"
    assert "8x8" in caught.value.message


def test_a_flat_texture_is_allowed_when_the_caller_says_so(tmp_path):
    path = _png(tmp_path, "albedo.png", fill=(200, 30, 30))
    with pytest.raises(PolyweaveError):
        post.check("texture", path, alpha_floor=0.0)
    assert post.check("texture", path, allow_uniform=True, alpha_floor=0.0)["size"] == [
        8,
        8,
    ]


def test_a_subject_is_the_pixels_above_the_alpha_floor(tmp_path):
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[:2, :, 3] = 255
    rgba[:2, :, 0] = np.arange(4, dtype=np.uint8)[None, :]
    path = tmp_path / "half.png"
    PILImage.fromarray(rgba, "RGBA").save(path)
    assert post.check("render", path, alpha_floor=0.0)["alpha_coverage"] == 0.5


def test_a_capture_that_was_never_written_says_which_path(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        post.check("capture", tmp_path / "never.png", alpha_floor=0.0)
    assert caught.value.code == "post.file-missing"
    assert "never.png" in caught.value.message


def test_a_capture_that_is_not_an_image_is_not_a_capture(tmp_path):
    path = tmp_path / "shot.png"
    path.write_text("Godot printed this instead", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        post.check("capture", path, alpha_floor=0.0)
    assert caught.value.code == "post.not-an-image"


def test_a_blank_capture_is_still_a_capture(tmp_path):
    """A loading screen is a legitimate screenshot, unlike a blank render."""
    measured = post.check(
        "capture", _png(tmp_path, "load.png", fill=(0, 0, 0)), alpha_floor=0.0
    )
    assert measured["size"] == [8, 8]


# -- downloads -----------------------------------------------------------------


def test_a_download_records_its_digest(tmp_path):
    path = tmp_path / "mesh.glb"
    path.write_bytes(b"glTF" * 64)
    measured = post.check("download", path, declared_length=256)
    assert measured["bytes"] == 256
    assert len(measured["sha256"]) == 64


def test_a_truncated_download_is_refused_against_the_declared_length(tmp_path):
    path = tmp_path / "mesh.glb"
    path.write_bytes(b"glTF" * 10)
    with pytest.raises(PolyweaveError) as caught:
        post.check("download", path, declared_length=256)
    assert caught.value.code == "post.download-length"
    assert "216 bytes early" in caught.value.remedy


def test_a_download_that_does_not_hash_as_promised_is_refused(tmp_path):
    path = tmp_path / "mesh.glb"
    path.write_bytes(b"glTF")
    with pytest.raises(PolyweaveError) as caught:
        post.check("download", path, sha256="0" * 64)
    assert caught.value.code == "post.download-digest"


def test_bytes_in_hand_are_checked_without_a_file():
    measured = post.check("download", b"glTF", declared_length=4)
    assert measured["bytes"] == 4


def test_a_download_that_never_started_says_so(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        post.check("download", tmp_path / "nothing.glb", declared_length=1)
    assert caught.value.code == "post.file-missing"


# -- the surface itself --------------------------------------------------------


def test_an_unknown_output_kind_names_the_ones_that_exist():
    with pytest.raises(PolyweaveError) as caught:
        post.check("sprite", None)
    assert caught.value.code == "post.unknown-output"
    assert "render" in caught.value.remedy


def test_an_unknown_expectation_is_refused_rather_than_dropped(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        post.check("render", _png(tmp_path, "r.png"), sixe=(8, 8), alpha_floor=0.0)
    assert caught.value.code == "post.unknown-field"
    assert "sixe" in caught.value.message
    assert "size" in caught.value.remedy


# -- a tolerance has one home (§PW40) ------------------------------------------


def test_a_check_that_needs_a_tolerance_and_is_given_none_is_refused(tmp_path):
    """It used to default to zero while the config declared 0.02, so a caller who
    forgot measured the background as part of the subject and got an answer."""
    for kind in ("render", "texture", "field", "capture"):
        with pytest.raises(PolyweaveError) as caught:
            post.check(kind, _png(tmp_path, f"{kind}.png"))
        assert caught.value.code == "post.tolerance-unstated"
        assert "alpha_floor" in caught.value.message


def test_a_check_that_needs_no_tolerance_does_not_ask_for_one():
    """A mesh has no alpha, so requiring a floor of it would be ceremony."""
    assert post.check("mesh", cube())["faces"] == 6


def test_the_floor_the_caller_states_is_the_floor_that_is_used(tmp_path):
    """Half the frame is opaque, so the two floors disagree about the coverage."""
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[:2, :, 3] = 255
    rgba[2:, :, 3] = 3  # faint, and above zero
    rgba[:, :, 0] = np.arange(4, dtype=np.uint8)[None, :]
    path = tmp_path / "faint.png"
    PILImage.fromarray(rgba, "RGBA").save(path)

    assert post.check("render", path, alpha_floor=0.0)["alpha_coverage"] == 1.0
    assert post.check("render", path, alpha_floor=0.02)["alpha_coverage"] == 0.5


def test_the_project_is_where_the_number_lives(tmp_path):
    """One home, resolved together, so an operation cannot pick up a stale sibling."""
    from polyweave import config

    (tmp_path / "polyweave.toml").write_text(
        "[tolerance]\nalpha_floor = 0.5\n", encoding="utf-8"
    )
    found = config.load(tmp_path).tolerances()
    assert found.alpha_floor == 0.5
    assert found.delta_e == 2.0, "and the rest keep the defaults, in the same object"
    assert set(found.as_dict()) == {
        "alpha_floor",
        "render_noise",
        "silhouette_iou",
        "delta_e",
        "background_delta_e",
        "subject_coverage",
    }


# -- a field, which is a texture that has to know what it is for (§PW38) --------


def _field(tmp_path, name, *, levels=256, size=(64, 1), bits=8):
    """A one-row ramp holding exactly `levels` distinct values.

    A staircase and a gradient are the same picture at this size; the difference is how
    many steps it takes to climb, which is the only thing this check measures.
    """
    top = (1 << bits) - 1
    steps = np.linspace(0, top, size[0])
    quantised = np.round(steps / top * (levels - 1)) / (levels - 1) * top
    row = quantised.astype(np.uint16 if bits == 16 else np.uint8)
    samples = np.tile(row, (size[1], 1))
    path = tmp_path / name
    PILImage.fromarray(samples).save(path)
    return path


def test_a_field_that_kept_its_gradient_passes_and_says_how_many_levels(tmp_path):
    measured = post.check(
        "field", _field(tmp_path, "h.png"), levels=60, alpha_floor=0.0
    )
    assert measured["levels"] == 64, "one per pixel of a 64-wide ramp"
    assert measured["bits"] == 8


def test_a_gradient_that_came_back_a_staircase_is_refused(tmp_path):
    """The third silent failure: still a gradient, still not uniform, still the right
    size, and every other assertion here passes it."""
    flat = _field(tmp_path, "stairs.png", levels=4)
    post.check("texture", flat, alpha_floor=0.0)  # the other checks see nothing wrong

    with pytest.raises(PolyweaveError) as caught:
        post.check("field", flat, levels=64, alpha_floor=0.0)
    assert caught.value.code == "post.field-quantised"
    assert "4 distinct values" in caught.value.message


def test_the_same_image_is_fine_as_a_texture_and_broken_as_a_field(tmp_path):
    """Nothing in the file says which it is, so the caller declares it."""
    flat = _field(tmp_path, "forty.png", levels=40)
    assert post.check("texture", flat, alpha_floor=0.0)["size"] == [64, 1]
    with pytest.raises(PolyweaveError):
        post.check("field", flat, levels=200, alpha_floor=0.0)


def test_a_file_written_too_shallow_is_a_different_failure_from_a_flattened_one(
    tmp_path,
):
    """Their remedies point at different code: the renderer, or a buffer after it."""
    with pytest.raises(PolyweaveError) as caught:
        post.check("field", _field(tmp_path, "eight.png"), bits=16, alpha_floor=0.0)
    assert caught.value.code == "post.field-shallow"
    assert "8 bits per channel" in caught.value.message


def test_a_deep_file_holding_too_little_blames_the_buffer_and_not_the_renderer(
    tmp_path,
):
    deep = _field(tmp_path, "deep.png", levels=8, size=(256, 1), bits=16)
    measured_bits = post.check("field", deep, alpha_floor=0.0)["bits"]
    assert measured_bits == 16, "the file's own depth, not the working array's"

    with pytest.raises(PolyweaveError) as caught:
        post.check("field", deep, bits=16, levels=1000, alpha_floor=0.0)
    assert caught.value.code == "post.field-quantised"
    assert "buffer" in caught.value.remedy


def test_the_depth_is_read_off_the_file_and_not_off_the_loaded_array(tmp_path):
    """`Image` holds every picture as RGBA bytes, so measuring it would measure the
    conversion rather than what was written."""
    deep = _field(tmp_path, "sixteen.png", levels=4096, size=(256, 1), bits=16)
    levels = post.check("field", deep, alpha_floor=0.0)["levels"]
    assert levels > 255, "beyond what a byte could hold"


def test_a_field_reports_a_level_count_per_channel(tmp_path):
    """A field packed into three channels is three signals, and the flattest broke."""
    rgb = np.zeros((1, 64, 3), dtype=np.uint8)
    rgb[:, :, 0] = np.arange(64, dtype=np.uint8)
    rgb[:, :, 1] = 7
    rgb[:, :, 2] = np.arange(64, dtype=np.uint8) // 2
    path = tmp_path / "packed.png"
    PILImage.fromarray(rgb, "RGB").save(path)

    measured = post.check("field", path, alpha_floor=0.0)
    assert measured["levels_per_channel"] == [64, 1, 32]
    assert measured["levels"] == 1, "the flattest is what the check is about"


def test_a_field_takes_no_argument_a_texture_takes_and_it_does_not(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        post.check(
            "field", _field(tmp_path, "u.png"), allow_uniform=True, alpha_floor=0.0
        )
    assert caught.value.code == "post.unknown-field"
    assert "levels" in caught.value.remedy


def test_every_code_is_namespaced_and_carries_a_remedy(tmp_path):
    """§3: a code is part of the contract, and an error names the door it closes."""
    failures = [
        lambda: post.check("mesh", {"vertices": [], "faces": []}),
        lambda: post.check("boolean", {"vertices": [], "faces": []}, operands=(9, 9)),
        lambda: post.check(
            "render", _png(tmp_path, "f.png", fill=(1, 1, 1)), alpha_floor=0.0
        ),
        lambda: post.check("download", b"x", declared_length=9),
        lambda: post.check("capture", tmp_path / "no.png", alpha_floor=0.0),
    ]
    for failing in failures:
        with pytest.raises(PolyweaveError) as caught:
            failing()
        assert caught.value.code.startswith("post.")
        assert caught.value.remedy
        assert "Traceback" not in caught.value.message
