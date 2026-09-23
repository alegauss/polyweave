"""The plugin against artefacts somebody actually made.

§PW48. Every other input this suite has is built in code, which is right for the
arithmetic and wrong for the question "does this work on a real thing". A generated mesh
has the topology a service left it with, a drawing has antialiased edges and a hand's
irregularity, and neither is what a builder in a test produces.

The files and why each is here are in `fixtures/cottony/README.md`. These tests assert
what a real artefact makes assertable and nothing beyond it: a synthetic box is where an
exact number belongs, and this is where "it survived contact" belongs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

COTTONY = Path(__file__).parent / "fixtures" / "cottony"
HAMMER_DRAWING = COTTONY / "booster_hammer.drawn.png"
HAMMER_MESH = COTTONY / "booster_hammer.glb"
PLUSH_MESH = COTTONY / "friend_plush.glb"


def real(path: Path) -> Path:
    """The asset, or a skip where LFS has not fetched it.

    A pointer file is a thing that happened to the checkout, not a thing that is wrong
    with the plugin, so it skips rather than failing with a parse error twelve frames
    down. `git lfs install` then `git lfs pull` is the fix, and the skip says so.
    """
    if not path.is_file():
        pytest.skip(f"{path.name} is not in this checkout")
    if path.read_bytes()[:7] == b"version":
        pytest.skip(f"{path.name} is an LFS pointer; run `git lfs pull`")
    return path


# -- a drawing a person drew ------------------------------------------------------


def test_a_real_drawing_cuts_down_to_the_subject_somebody_drew():
    """Antialiased edges and a hand's irregularity, which a built rectangle has neither
    of — and the alpha floor is what decides where the drawing stops."""
    from polyweave.image import load

    image = load(real(HAMMER_DRAWING))
    assert image.had_alpha, "a drawing meant for a silhouette carries one"
    covered = float(image.subject(0.02).mean())
    assert 0.05 < covered < 0.9, f"a hammer fills some of its frame, not all: {covered}"


def test_the_alpha_floor_moves_the_edge_on_a_real_drawing_and_not_on_a_hard_one():
    """The reason the floor exists: a drawn edge fades and a built one does not."""
    from polyweave.image import load

    image = load(real(HAMMER_DRAWING))
    loose = float(image.subject(0.0).mean())
    tight = float(image.subject(0.5).mean())
    assert loose > tight, "a real edge has pixels between opaque and absent"

    hard = np.zeros((16, 16, 4), dtype=np.uint8)
    hard[4:12, 4:12] = 255
    from polyweave.image import Image

    built = Image(path=None, rgba=hard, had_alpha=True)
    assert built.subject(0.0).mean() == built.subject(0.5).mean(), "nothing in between"


def test_a_real_drawing_traces_to_an_outline_with_corners_in_it(tmp_path):
    """§PW31's tracer against a drawing rather than a generated shape."""
    from polyweave.geometry import outline

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    ring = outline.image(real(HAMMER_DRAWING), root=tmp_path, alpha_floor=0.02)
    assert len(ring) >= 8, "a hammer is not a circle"
    assert len(ring) < 400, "and the simplifier did its job on a per-pixel trace"
    assert np.ptp(ring, axis=0).min() > 0, "it has extent on both axes"


# -- a mesh a service returned ----------------------------------------------------


def test_a_fetched_mesh_reads_back_with_the_topology_it_arrived_with():
    """Not a box: a generated mesh has whatever topology the service left it with."""
    pytest.importorskip("bpy", reason="reading a mesh needs the renderer")
    from polyweave.normalise import read_mesh

    found = read_mesh(real(HAMMER_MESH))
    assert len(found["vertices"]) > 100, "a real mesh, not a primitive"
    assert len(found["faces"]) > 100
    assert np.isfinite(np.asarray(found["vertices"], dtype=float)).all()


def test_the_hammer_arrives_upright_and_the_drawing_says_it_leans(tmp_path):
    """§PW20's case, with both halves of it real: the mesh came back standing up and the
    drawing already knew which way round it goes."""
    pytest.importorskip("bpy", reason="orienting a mesh needs the renderer")
    from polyweave import normalise

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    found = normalise.ingest(
        real(HAMMER_MESH),
        out=tmp_path / "hammer.glb",
        against=real(HAMMER_DRAWING),
        root=tmp_path,
    )
    assert Path(found["mesh"]).is_file()
    # 0.4343 across 24 orientations, measured. Worth writing down because the synthetic
    # tests clear 0.8 on a box against its own outline: a real drawing agrees with a
    # real mesh far less closely than a built pair does, and a threshold picked from
    # those would have called this a failure to orient rather than a match.
    assert found["tried"] == 24, "chosen against alternatives, not assumed"
    assert found["silhouette_iou"] > 0.3, "the drawing and the mesh are one object"


def test_a_normalised_real_mesh_is_recorded_like_any_other(tmp_path):
    """§PW46 against 8 MB of real mesh rather than a cube of stated proportions."""
    pytest.importorskip("bpy", reason="normalising a mesh needs the renderer")
    from polyweave import normalise, provenance

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    normalise.ingest(real(HAMMER_MESH), out=tmp_path / "hammer.glb", root=tmp_path)
    written = provenance.read("hammer.glb", root=tmp_path)
    assert written["inputs"][0]["sha256"] == provenance.sha256_of(HAMMER_MESH)[0]


def test_a_real_plush_body_takes_a_skeleton(tmp_path):
    """§PW26 against a mesh whose limbs are where somebody modelled them, rather than
    where the plan assumed they would be."""
    pytest.importorskip("bpy", reason="fitting a skeleton needs the renderer")
    from polyweave import skeleton
    from polyweave.normalise import read_mesh

    body = read_mesh(real(PLUSH_MESH))
    fitted = skeleton.fit(body, named="plush", root=str(tmp_path))
    assert fitted["joints"], "a plush plan put bones somewhere in it"
    inside = np.asarray([j["at"] for j in fitted["joints"]], dtype=float)
    lo = np.asarray(body["vertices"], dtype=float).min(axis=0)
    hi = np.asarray(body["vertices"], dtype=float).max(axis=0)
    span = hi - lo
    assert (inside >= lo - span * 0.2).all(), "no joint is far outside the body"
    assert (inside <= hi + span * 0.2).all()


# -- shading the service painted into the texture (§PW49) -------------------------


def test_the_hammers_texture_has_painted_shading_in_it():
    """The claim the line rests on, measured rather than repeated: ordinary detail on
    this 4096-square sheet reaches 0.062 and the marks reach 0.372."""
    pytest.importorskip("bpy", reason="reading a texture needs the renderer")
    import bpy

    from polyweave import texture

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(real(HAMMER_MESH)))
    image = bpy.data.images["Image_0"]
    pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(
        image.size[1], image.size[0], -1
    )
    found = texture.marks(pixels)
    assert found["darkest"] > 0.3, "marks far darker than their surroundings"
    assert 0.0005 < found["fraction"] < 0.02, f"a few, not a flattening: {found}"


def test_scrubbing_the_hammer_lifts_the_marks_and_leaves_the_rest():
    pytest.importorskip("bpy", reason="scrubbing a texture needs the renderer")
    import bpy

    from polyweave import texture

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(real(HAMMER_MESH)))
    image = bpy.data.images["Image_0"]
    pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(
        image.size[1], image.size[0], -1
    )
    cleaned, found = texture.scrub(pixels)
    assert cleaned.mean() > pixels.mean(), "the marks were lifted, so it is lighter"
    changed = float((np.abs(cleaned - pixels) > 1e-6).any(axis=2).mean())
    assert changed == pytest.approx(found["fraction"], abs=0.001)
    assert changed < 0.02, "and the other 98% of the sheet is untouched"
