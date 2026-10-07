"""An asset's brief in one read (§PW131)."""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import brief, loop, provenance
from polyweave.errors import PolyweaveError

SHAPE = """name = "crate"
output = "crate"

[params]
size = 4

[voxels]
cell = 1

[[nodes]]
id = "crate"
op = "primitive"
kind = "cube"
size = "size"
"""

SPEC = """asset = "crate"
artefact = "renders/crate.png"

[[predicate]]
id      = "tone"
measure = "luma_p99"
region  = "frame"
max     = { value = 0.37, origin = "margin", measured = 0.34 }
"""


def project(tmp_path):
    (tmp_path / "shapes").mkdir()
    (tmp_path / "shapes" / "crate.toml").write_text(SHAPE, encoding="utf-8")
    (tmp_path / "docs" / "accept").mkdir(parents=True)
    (tmp_path / "docs" / "accept" / "crate.accept.toml").write_text(
        SPEC, encoding="utf-8"
    )
    (tmp_path / "renders").mkdir()
    Image.new("RGBA", (8, 8), (90, 90, 90, 255)).save(
        tmp_path / "renders" / "crate.png"
    )
    provenance.write(
        provenance.build("render", tmp_path / "renders" / "crate.png", root=tmp_path),
        root=tmp_path,
    )
    return tmp_path


def test_one_read_says_where_the_asset_stands(tmp_path):
    root = project(tmp_path)
    run = loop.start("crate", "after", root=root)
    loop.judged(
        run,
        tool_passed=False,
        person_accepted=True,
        check={"predicates": [{"id": "tone", "value": 0.4, "passed": False}]},
    )
    loop.finish(run, root=root)

    found = brief.brief("crate", root=str(root))
    assert found["declaration"]["path"] == "shapes/crate.toml"
    assert found["declaration"]["reads"]
    tone = found["spec"]["predicates"][0]
    assert tone["max"]["origin"] == "margin"
    assert found["artefact"]["matches_record"] is True
    assert found["last_verdict"]["failed"] == ["tone"]
    assert found["last_verdict"]["person_accepted"] is True
    assert len(found["digest"]) == 16


def test_the_digest_moves_when_the_asset_does(tmp_path):
    root = project(tmp_path)
    before = brief.brief("crate", root=str(root))["digest"]
    assert brief.brief("crate", root=str(root))["digest"] == before
    Image.new("RGBA", (8, 8), (200, 90, 90, 255)).save(root / "renders" / "crate.png")
    after = brief.brief("crate", root=str(root))
    assert after["digest"] != before
    assert after["artefact"]["matches_record"] is False


def test_an_asset_nothing_names_is_refused_with_the_ones_that_exist(tmp_path):
    root = project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        brief.brief("crat", root=str(root))
    assert "crat" in refused.value.message


def rendered_from(root, mesh: str, built: str = "assets/crate.glb"):
    """The declaration built into `built`, and the spec's render made from `mesh`."""
    for one in {mesh, built}:
        (root / one).parent.mkdir(parents=True, exist_ok=True)
        (root / one).write_bytes(b"glTF" + one.encode())
    provenance.write(
        provenance.build(
            "mesh",
            root / built,
            root=root,
            inputs=[provenance.source("declaration", "shapes/crate.toml", root)],
        ),
        root=root,
    )
    provenance.write(
        provenance.build(
            "render",
            root / "renders" / "crate.png",
            root=root,
            inputs=[provenance.source("mesh", mesh, root)],
        ),
        root=root,
    )


def test_a_render_of_a_mesh_the_declaration_no_longer_builds_is_said(tmp_path):
    # §PW298: the spec measured the bought mesh while the game drew the voxel build.
    from polyweave import accept

    root = project(tmp_path)
    rendered_from(root, "assets/models/crate.glb")
    found = brief.brief("crate", root=str(root))
    assert found["artefact"]["matches_record"] is True
    assert found["parted"]["rendered_from"] == "assets/models/crate.glb"
    assert found["parted"]["built"] == ["assets/crate.glb"]
    assert found["parted"]["declaration"] == "shapes/crate.toml"
    checked = accept.verify(str(root), under="docs/accept")["specs"][0]
    assert checked["parted"]["rendered_from"] == "assets/models/crate.glb"


def test_a_render_of_the_build_is_not_parted(tmp_path):
    from polyweave import accept

    root = project(tmp_path)
    rendered_from(root, "assets/crate.glb")
    assert brief.brief("crate", root=str(root))["parted"] is None
    assert "parted" not in accept.verify(str(root), under="docs/accept")["specs"][0]


def subject_spec(root, subject: str = "shapes/crate.toml"):
    """The crate's spec, naming its declaration as the model it measures."""
    spec = root / "docs" / "accept" / "crate.accept.toml"
    spec.write_text(f'subject = "{subject}"\n' + SPEC, encoding="utf-8")
    return spec


def test_a_spec_names_its_declarations_build_as_the_model_it_renders(tmp_path):
    # §PW298: render.bake and the search render the build, not a mesh path.
    from polyweave import accept, search

    root = project(tmp_path)
    rendered_from(root, "assets/crate.glb")
    spec = accept.read(subject_spec(root))
    assert spec.subject == "shapes/crate.toml"
    assert accept._subject_model(spec, root) == "assets/crate.glb"
    assert search._subject(spec, None, root) == {"model": "assets/crate.glb"}
    # A model the caller named is the one asked for.
    kept = search._subject(spec, {"model": "other.glb"}, root)
    assert kept == {"model": "other.glb"}


def test_a_spec_holding_its_subject_reads_stale_on_a_render_of_another_mesh(tmp_path):
    from polyweave import accept

    root = project(tmp_path)
    rendered_from(root, "assets/models/crate.glb")
    subject_spec(root)
    found = accept.verify(str(root), under="docs/accept")
    assert found["specs"][0]["status"] == "stale"
    assert found["specs"][0]["parted"]["rendered_from"] == "assets/models/crate.glb"
    assert found["counts"]["stale"] == 1
    assert found["passed"] is False


def test_a_subject_with_no_build_is_refused_with_the_build_to_run(tmp_path):
    from polyweave import accept

    root = project(tmp_path)
    spec = accept.read(subject_spec(root))
    with pytest.raises(PolyweaveError) as refused:
        accept._subject_model(spec, root)
    assert refused.value.code == "spec.subject-unbuilt"
    assert "geometry.build" in str(refused.value.as_dict())


def test_a_subject_that_is_not_a_declaration_is_refused(tmp_path):
    from polyweave import accept

    root = project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        accept.read(subject_spec(root, "assets/crate.glb"))
    assert refused.value.code == "spec.subject-not-declaration"


def test_a_bake_of_a_spec_records_the_build_its_subject_names(tmp_path):
    # §PW298: the render's record names the built mesh, with no path written by hand.
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C
    from polyweave import render

    root = project(tmp_path)
    (root / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )
    rendered_from(root, "assets/models/crate.glb")

    class Quiet:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    render.bake(
        Quiet(),
        out="renders/crate.png",
        spec=str(subject_spec(root)),
        rung="sphere",
        root=str(root),
        inline=False,
    )
    record = provenance.read(root / "renders" / "crate.png", root)
    meshes = [one["path"] for one in record["inputs"] if one["role"] == "mesh"]
    assert meshes == ["assets/crate.glb"]
