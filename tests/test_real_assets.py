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


# -- how far a real subject reaches across a real frame (§PW52) ------------------------


@pytest.mark.parametrize(
    ("named", "mesh"),
    [("hammer", "HAMMER_MESH"), ("plush", "PLUSH_MESH")],
)
def test_a_real_asset_reaches_far_further_across_the_frame_than_the_bar(
    tmp_path, named, mesh
):
    """The measurement `[tolerance] subject_extent` was set from, not a picked number.

    Rendered through the project rig at 128px: the hammer spans 0.578 of the frame and
    the plush body 0.539, at 0.166 and 0.168 coverage. The default is 0.05, an order of
    magnitude below both, and a two-pixel render spans 0.016 — an order of magnitude
    below it in the other direction.

    The bar is asserted loosely here on purpose. What a real asset makes assertable is
    that it clears the floor with room to spare on somebody else's machine; the exact
    figures belong in the comment above `subject_extent`, beside the number they set.
    """
    pytest.importorskip("bpy", reason="rendering needs the renderer")
    from polyweave import config as C
    from polyweave import render
    from polyweave.config import DEFAULTS

    class Quiet:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 128\nfinal_size = 128\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )
    found = render.bake(
        Quiet(),
        model=str(real(globals()[mesh])),
        out=f"{named}.png",
        rung="preview",
        root=tmp_path,
        inline=False,
        cached=False,
    )
    reach = found["asserted"]["subject_extent"]
    bar = DEFAULTS["tolerance"]["subject_extent"]
    assert reach > 5 * bar, f"{named} spans {reach:.4f} against a floor of {bar}"
    # And it is nowhere near filling the frame either, which is why an area floor set
    # from these would still be a guess about the next asset.
    assert found["asserted"]["alpha_coverage"] < 0.5


# -- a ledger somebody else kept, replayed (§PW55) -------------------------------------

MESHY_LOCK = COTTONY / "meshy.lock.json"


def from_meshy(entry: dict) -> dict:
    """One `meshy.lock.json` entry in the plugin's ledger shape.

    The mapping is the caller's on purpose: the service's format is not the plugin's to
    hard-code, and `docs/specs/adoption.md` is where this table is written down. Every
    field on the left is one the lock file already held — nothing here is invented, and
    nothing is asked of the service.

    Two of the five entries are text-to-3D and carry no reference image at all, so
    `image` is read with a default. That is the format's own variance and not a gap:
    a purchase made from words has no drawing, and a `reference` invented for it would
    name a file that never existed.
    """
    asked = entry["request"]
    return {
        "artefact": entry["mesh"],
        "sha256": entry["mesh_sha256"],
        "task_id": entry["task_id"],
        # What it really cost, read from the balance, against what the service declared.
        "credits": float(entry["credits_measured"]),
        "expected_credits": float(entry["consumed_credits"]),
        "surprised": entry["credits_measured"] != entry["consumed_credits"],
        "bought": "mesh",
        "prompt": asked.get("texture_prompt") or asked.get("prompt"),
        "reference": entry.get("image"),
        "at": _stamp(entry["finished_at"]),
    }


def _stamp(epoch_ms: int) -> str:
    from datetime import UTC, datetime

    return (
        datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def test_a_real_lock_file_maps_onto_the_ledger_without_inventing_a_field():
    import json

    lock = json.loads(real(MESHY_LOCK).read_text(encoding="utf-8"))
    assert len(lock) == 5, "five meshes, bought once each"
    for name, entry in lock.items():
        mapped = from_meshy(entry)
        assert mapped["task_id"], name
        assert len(mapped["sha256"]) == 64, name
        assert mapped["credits"] > 0, name
        # Every purchase says what was asked for, in words or in a drawing. Neither is
        # required on its own: `mascot` was bought untextured, so its empty texture
        # prompt is correct and the reference is the whole ask, and `friend_plush` came
        # from words with no drawing at all.
        assert mapped["prompt"] or mapped["reference"], name
    assert sum(from_meshy(e)["credits"] for e in lock.values()) == 130.0
    # Not one of the five was charged differently from what the service declared, which
    # is the only form of that claim anybody can check.
    assert not any(from_meshy(e)["surprised"] for e in lock.values())
    assert {e["mode"] for e in lock.values()} == {"image-to-3d", "text-to-3d"}


def test_the_hashes_a_lock_file_recorded_are_asked_about_for_the_first_time(tmp_path):
    """§PW55's case. A lock file records a hash and nothing ever compares it.

    Two of the five meshes are in this repository, which is what makes the question
    answerable here at all. The other three stay in Cottony and come back `missing` —
    which is the right answer about this tree and not a claim about theirs.
    """
    import json
    import shutil

    from polyweave import purchase

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    lock = json.loads(real(MESHY_LOCK).read_text(encoding="utf-8"))

    here = []
    for entry in lock.values():
        mapped = from_meshy(entry)
        copied = COTTONY / Path(mapped["artefact"]).name
        if copied.is_file() and copied.read_bytes()[:7] != b"version":
            (tmp_path / mapped["artefact"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(copied, tmp_path / mapped["artefact"])
            here.append(Path(mapped["artefact"]).name)

    found = purchase.adopt([from_meshy(e) for e in lock.values()], root=tmp_path)
    adopted = {Path(e["artefact"]).name for e in found["adopted"]}
    assert adopted == set(here), "every mesh that is here still hashes to its entry"
    assert found["changed"] == [], "and not one of them has moved since it was bought"
    assert len(found["missing"]) == 5 - len(here)
    # The credits stay out of this project's ceiling: they were spent before it had one.
    assert purchase.spent(tmp_path) == 0.0
    assert purchase.held(tmp_path)["credits"] == found["credits"]


# -- the motion a game actually ships (§PW58) ------------------------------------------

SETTLE = COTTONY / "friend_cloud.png"
SETTLE_LEAN = COTTONY / "friend_cloud_lean.png"

#: Cottony's whole motion surface, as `bake_model.py` declares it: the same mesh pressed
#: to this share of its height and re-rendered, because a scaled sprite squashes its own
#: highlight and its own shadow with it.
SQUASH = 0.93


def _box(path):
    """The subject's box in a real render, as the sheet's own trim would find it."""
    from polyweave.image import load as load_image

    mask = load_image(path).subject(0.02)
    rows = np.nonzero(np.any(mask, axis=1))[0]
    cols = np.nonzero(np.any(mask, axis=0))[0]
    return {
        "wide": int(cols[-1] - cols[0] + 1),
        "tall": int(rows[-1] - rows[0] + 1),
        "bottom": int(rows[-1]),
    }


def test_the_settle_a_game_ships_is_the_squash_its_constants_declare():
    """The declared constant, recovered from the pixels that were shipped.

    Not a restatement of `squash = 0.93`: these two PNGs are what the game loads, and
    the ratio of their silhouettes is measured off them. It lands on 0.93 because the
    frame really was re-rendered at that height rather than scaled afterwards.
    """
    standing, leaning = _box(real(SETTLE)), _box(real(SETTLE_LEAN))
    assert leaning["tall"] / standing["tall"] == pytest.approx(SQUASH, abs=0.005)
    assert leaning["wide"] > standing["wide"], "it spreads sideways as it presses down"
    # And it settles onto the same ground line, which is what makes the crossfade read
    # as a toy settling rather than as two toys.
    assert leaning["bottom"] == standing["bottom"]


def test_a_games_own_settle_pair_lays_out_as_one_sheet(tmp_path):
    """§PW58's sheet half, against the frames a game ships rather than built ones.

    Cottony has no sheet and no atlas: `hud.gd` crossfades between two loose PNGs that
    `Art.sprite` loads separately. This is what the pair becomes when something lays it
    out — one image and an index a machine can read.
    """
    import json

    from polyweave import clip as C
    from polyweave import sprites

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    settle = C.clip(
        "settle",
        0.4,
        channels={"root": {"scale": [(0.0, [1, 1, 1]), (0.2, [1.04, SQUASH, 1.04])]}},
    )
    rendered = [
        {"artefact": str(real(SETTLE)), "at": 0.0, "frame": 0},
        {"artefact": str(real(SETTLE_LEAN)), "at": 0.2, "frame": 1},
    ]
    found = sprites.sheet(settle, rendered, out=tmp_path / "settle.png", root=tmp_path)

    assert found["columns"] * found["rows"] >= 2
    assert len(found["frames"]) == 2
    # One cell size for both, and it is the union of the two silhouettes — a frame
    # trimmed to its own outline is a sprite that jitters on its own axis.
    standing, leaning = _box(real(SETTLE)), _box(real(SETTLE_LEAN))
    assert found["cell"] == [
        max(standing["wide"], leaning["wide"]),
        max(standing["tall"], leaning["tall"]),
    ]
    assert {tuple(one["rect"][2:]) for one in found["frames"]} == {tuple(found["cell"])}
    # The trim is doing real work: a 360 square render is mostly empty margin.
    assert found["cell"][0] < 360
    assert found["cell"][1] < 360
    assert Path(found["sheet"]).is_file()
    written = json.loads(Path(found["atlas"]).read_text(encoding="utf-8"))
    assert written["clip"] == "settle"


def test_the_sheet_and_the_animation_agree_on_which_clip_they_are(tmp_path):
    """The whole claim of §PW29, asked over a real pair."""
    from polyweave import clip as C
    from polyweave import sprites

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    settle = C.clip(
        "settle",
        0.4,
        channels={"root": {"scale": [(0.0, [1, 1, 1]), (0.2, [1.04, SQUASH, 1.04])]}},
    )
    found = sprites.sheet(
        settle,
        [{"artefact": str(real(SETTLE)), "at": 0.0, "frame": 0}],
        out=tmp_path / "settle.png",
        root=tmp_path,
    )
    mine = {"clip_sha256": found["clip_sha256"]}
    assert sprites.matched(mine, found, root=tmp_path)["matched"] is True

    # A different settle is a different digest, so the two stop claiming to be one clip.
    other = C.clip(
        "settle",
        0.4,
        channels={"root": {"scale": [(0.0, [1, 1, 1]), (0.2, [1, 0.8, 1])]}},
    )
    theirs = {"clip_sha256": C._digest(C.as_toml(other))}
    assert sprites.matched(theirs, found, root=tmp_path)["matched"] is False
