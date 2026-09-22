"""What produced an artefact, and the key that identifies the work.

`docs/specs/provenance.md`. The evidence §PW6 rests on is that two runs of one unchanged
scene differed in 29,696 pixels: the record is what makes a difference attributable at
all, and the key is what makes a cache hit safe rather than merely likely.
"""

from __future__ import annotations

import json

import pytest

from polyweave import provenance as P
from polyweave.errors import PolyweaveError


def artefact(tmp_path, name="mascot.png", body=b"\x89PNG-pretend"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def a_record(tmp_path, **over):
    artefact(tmp_path)
    fields = {
        "engine": {"name": "cycles", "version": "4.2.1", "bindings": "bpy 4.2.0"},
        "rung": "final",
        "seed": 20260922,
        "samples": 512,
        "params": {"light": 2.7, "form": 2.5},
        "root": tmp_path,
    }
    fields.update(over)
    return P.build("render", "mascot.png", **fields)


# -- the record ------------------------------------------------------------------


def test_a_record_hashes_the_artefact_it_describes(tmp_path):
    found = a_record(tmp_path)
    assert found["artefact"]["path"] == "mascot.png"
    assert found["artefact"]["bytes"] == len(b"\x89PNG-pretend")
    assert len(found["artefact"]["sha256"]) == 64
    assert found["producer"]["tool"] == "polyweave"


def test_it_carries_what_makes_a_difference_attributable(tmp_path):
    found = a_record(tmp_path)
    assert found["engine"]["version"] == "4.2.1"
    assert found["seed"] == 20260922
    assert found["samples"] == 512
    assert found["params"] == {"light": 2.7, "form": 2.5}
    assert found["produced_at"].endswith("Z")


def test_an_input_is_recorded_by_hash_and_by_role(tmp_path):
    artefact(tmp_path, "meshes/mascot.glb", b"glTF-pretend")
    found = P.source("mesh", "meshes/mascot.glb", root=tmp_path)
    assert found["role"] == "mesh"
    assert found["path"] == "meshes/mascot.glb"  # forward slashes, whatever the OS
    assert len(found["sha256"]) == 64


def test_an_input_that_is_not_there_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        P.source("mesh", "meshes/gone.glb", root=tmp_path)
    assert caught.value.code == "prov.missing-input"


def test_a_record_of_an_artefact_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        P.build("render", "never-written.png", root=tmp_path)
    assert caught.value.code == "prov.missing-artefact"
    assert "paid mesh" in caught.value.remedy


def test_an_unknown_kind_is_refused(tmp_path):
    artefact(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        P.build("sprite", "mascot.png", root=tmp_path)
    assert caught.value.code == "prov.unknown-kind"


def test_a_fetch_carries_its_service_fields_in_the_same_record(tmp_path):
    artefact(tmp_path, "paid.glb", b"glTF")
    found = P.build(
        "fetch",
        "paid.glb",
        extra={"task_id": "t_9f", "prompt_sha256": "ab" * 32, "credits": 30},
        root=tmp_path,
    )
    assert found["credits"] == 30
    assert found["task_id"] == "t_9f"


# -- beside the artefact ---------------------------------------------------------


def test_the_record_is_written_beside_the_artefact(tmp_path):
    written = P.write(a_record(tmp_path), root=tmp_path)
    assert written.name == "mascot.png.prov.json"
    assert written.parent == tmp_path
    assert json.loads(written.read_text())["kind"] == "render"


def test_a_record_is_read_back_by_the_artefact_it_describes(tmp_path):
    P.write(a_record(tmp_path), root=tmp_path)
    assert P.read("mascot.png", root=tmp_path)["seed"] == 20260922
    assert P.read("mascot.png.prov.json", root=tmp_path)["seed"] == 20260922


def test_an_artefact_with_no_record_says_so(tmp_path):
    artefact(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        P.read("mascot.png", root=tmp_path)
    assert caught.value.code == "prov.no-record"


def test_a_record_that_was_edited_into_nonsense_says_so(tmp_path):
    P.write(a_record(tmp_path), root=tmp_path)
    (tmp_path / "mascot.png.prov.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        P.read("mascot.png", root=tmp_path)
    assert caught.value.code == "prov.malformed"


# -- the key ---------------------------------------------------------------------


def test_the_same_work_has_the_same_key(tmp_path):
    assert P.cache_key(a_record(tmp_path)) == P.cache_key(a_record(tmp_path))


def test_what_is_in_the_key_changes_it(tmp_path):
    base = P.cache_key(a_record(tmp_path))
    assert P.cache_key(a_record(tmp_path, seed=1)) != base
    assert P.cache_key(a_record(tmp_path, samples=64)) != base
    assert P.cache_key(a_record(tmp_path, rung="preview")) != base
    assert P.cache_key(a_record(tmp_path, params={"light": 2.8})) != base
    assert (
        P.cache_key(a_record(tmp_path, engine={"name": "eevee", "version": "4.2.1"}))
        != base
    )


def test_what_is_not_in_the_key_leaves_it_alone(tmp_path):
    """When it was made, how long it took, where it landed and what it measured."""
    base = P.cache_key(a_record(tmp_path))
    assert P.cache_key(a_record(tmp_path, produced_at="1999-01-01T00:00:00Z")) == base
    assert P.cache_key(a_record(tmp_path, elapsed_s=999.0)) == base
    assert P.cache_key(a_record(tmp_path, measurements={"saturation_p99": 0.9})) == base


def test_an_artefact_that_changed_does_not_change_its_own_key(tmp_path):
    """The key is over the inputs, not the output; the output is what it identifies."""
    base = P.cache_key(a_record(tmp_path))
    artefact(tmp_path, body=b"a completely different picture")
    assert P.cache_key(a_record(tmp_path)) == base


def test_an_input_that_moved_is_the_same_input(tmp_path):
    artefact(tmp_path, "a/mesh.glb", b"glTF")
    artefact(tmp_path, "b/mesh.glb", b"glTF")
    here = P.source("mesh", "a/mesh.glb", root=tmp_path)
    there = P.source("mesh", "b/mesh.glb", root=tmp_path)
    assert here["path"] != there["path"]
    assert P.cache_key(a_record(tmp_path, inputs=[here])) == P.cache_key(
        a_record(tmp_path, inputs=[there])
    )


def test_an_input_that_changed_is_a_different_input(tmp_path):
    artefact(tmp_path, "mesh.glb", b"glTF one")
    before = P.source("mesh", "mesh.glb", root=tmp_path)
    artefact(tmp_path, "mesh.glb", b"glTF two")
    after = P.source("mesh", "mesh.glb", root=tmp_path)
    assert P.cache_key(a_record(tmp_path, inputs=[before])) != P.cache_key(
        a_record(tmp_path, inputs=[after])
    )


def test_a_float_that_only_differs_in_noise_is_one_key(tmp_path):
    """0.1 and 0.10000000000000001 are one render, and would be two caches."""
    assert P.cache_key(a_record(tmp_path, params={"light": 0.1})) == P.cache_key(
        a_record(tmp_path, params={"light": 0.10000000000000001})
    )


def test_a_float_that_differs_within_six_places_is_two_keys(tmp_path):
    assert P.cache_key(a_record(tmp_path, params={"light": 0.1})) != P.cache_key(
        a_record(tmp_path, params={"light": 0.100001})
    )


def test_the_canonical_form_sorts_keys_and_drops_whitespace():
    assert P.canonical({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert P.canonical({"x": [3, 1, 2]}) == '{"x":[3,1,2]}'  # arrays keep their order


def test_the_key_subset_is_exactly_what_the_spec_names(tmp_path):
    subset = P.key_subset(a_record(tmp_path))
    assert set(subset) == {
        "kind",
        "producer_version",
        "engine_name",
        "engine_version",
        "engine_bindings",
        "engine_view_transform",
        "engine_display_device",
        "rung",
        "seed",
        "samples",
        "inputs",
        "params",
    }


# -- verification ------------------------------------------------------------------


def test_verify_says_a_sound_project_is_sound(tmp_path):
    P.write(a_record(tmp_path), root=tmp_path)
    found = P.verify(tmp_path)
    assert found["sound"] is True
    assert found["ok"] == ["mascot.png"]
    assert found["checked"] == 1


def test_verify_finds_the_artefact_that_was_recorded_and_lost(tmp_path):
    P.write(a_record(tmp_path), root=tmp_path)
    (tmp_path / "mascot.png").unlink()
    found = P.verify(tmp_path)
    assert found["sound"] is False
    assert found["missing"] == [
        {"record": "mascot.png.prov.json", "artefact": "mascot.png"}
    ]


def test_verify_finds_the_artefact_that_is_no_longer_what_it_was(tmp_path):
    P.write(a_record(tmp_path), root=tmp_path)
    (tmp_path / "mascot.png").write_bytes(b"something else entirely")
    found = P.verify(tmp_path)
    assert found["sound"] is False
    assert found["changed"][0]["artefact"] == "mascot.png"
    assert found["changed"][0]["recorded"] != found["changed"][0]["found"]


def test_one_broken_record_does_not_hide_the_next(tmp_path):
    P.write(a_record(tmp_path), root=tmp_path)
    artefact(tmp_path, "second.png", b"another")
    P.write(P.build("render", "second.png", root=tmp_path), root=tmp_path)
    (tmp_path / "mascot.png.prov.json").write_text("{broken", encoding="utf-8")

    found = P.verify(tmp_path)
    assert found["checked"] == 2
    assert found["ok"] == ["second.png"]
    assert len(found["unreadable"]) == 1


def test_verify_walks_the_whole_tree(tmp_path):
    artefact(tmp_path, "deep/under/here.png", b"x")
    P.write(P.build("render", "deep/under/here.png", root=tmp_path), root=tmp_path)
    assert P.verify(tmp_path)["ok"] == ["deep/under/here.png"]


# -- what an assertion measured is what gets recorded --------------------------------


def test_measurements_from_a_check_go_straight_into_the_record(tmp_path):
    """§2's checks return what they measured, so nothing is measured twice."""
    import numpy as np
    from PIL import Image as PILImage

    from polyweave import post

    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[:, :, 3] = 255
    rgba[:, :, 0] = np.arange(8, dtype=np.uint8)[None, :]
    path = tmp_path / "shot.png"
    PILImage.fromarray(rgba, "RGBA").save(path)

    measured = post.check("render", path, size=(8, 8), alpha_floor=0.0)
    record = P.build("render", path, measurements=measured, root=tmp_path)
    assert record["measurements"]["alpha_coverage"] == 1.0
    assert record["measurements"]["size"] == [8, 8]
