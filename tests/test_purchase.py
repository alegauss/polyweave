"""Taking delivery of something that was paid for.

§PW17's case: the service deletes a task's assets seventy-two hours after it completes,
one run recorded the settings it had proved and not the mesh, and the mesh is gone.
Thirty credits spent for a receipt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from polyweave import provenance, purchase
from polyweave.errors import PolyweaveError

GLTF = b"glTF" + b"\x00" * 60


def project(tmp_path, text=""):
    (tmp_path / "polyweave.toml").write_text(text, encoding="utf-8")
    return tmp_path


def drawing(tmp_path, name="cap.png"):
    path = tmp_path / name
    path.write_bytes(b"\x89PNG-pretend")
    return path


def bought(tmp_path, **over):
    fields = {
        "out": "assets/cap.glb",
        "task_id": "t_9f3a",
        "credits": 30,
        "prompt": "a wide low cap on a short stem",
        "root": tmp_path,
    }
    fields.update(over)
    return purchase.capture(GLTF, **fields)


# -- the file outlives the service -----------------------------------------------------


def test_the_bytes_land_before_anything_is_written_down(tmp_path):
    where = project(tmp_path)
    entry = bought(where)
    assert (where / "assets" / "cap.glb").read_bytes() == GLTF
    assert entry["sha256"]
    assert entry["bytes"] == len(GLTF)


def test_a_record_is_written_beside_the_artefact(tmp_path):
    where = project(tmp_path)
    bought(where)
    record = provenance.read("assets/cap.glb", root=where)
    assert record["kind"] == "fetch"
    assert record["task_id"] == "t_9f3a"
    assert record["credits"] == 30.0
    assert record["prompt"] == "a wide low cap on a short stem"


def test_the_ledger_names_what_was_paid_for(tmp_path):
    where = project(tmp_path)
    entry = bought(where)
    held = purchase.read(where)
    assert held == [entry]
    assert held[0]["artefact"] == "assets/cap.glb"
    assert held[0]["at"].endswith("Z")


def test_the_ledger_lives_in_the_tree_and_is_committed(tmp_path):
    """A paid mesh and its record are one artefact, and both belong in the repo."""
    where = project(tmp_path)
    bought(where)
    assert purchase.where(where) == (where / "polyweave.purchases.json").resolve()
    assert purchase.where(where).is_file()


def test_the_project_may_say_where_its_ledger_lives(tmp_path):
    where = project(tmp_path, '[paths]\npurchases = "docs/bought.json"\n')
    bought(where)
    assert (where / "docs" / "bought.json").is_file()


# -- the ledger never over-claims ------------------------------------------------------


def test_nothing_is_ledgered_when_the_delivery_fails(tmp_path):
    """No window where a session believes an asset is safe because a ledger says so."""
    where = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.capture(
            GLTF,
            out="assets/short.glb",
            task_id="t_1",
            credits=30,
            declared_length=999,
            root=where,
        )
    assert caught.value.code == "post.download-length"
    assert purchase.read(where) == []


def test_nothing_is_ledgered_without_a_task_id(tmp_path):
    where = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.capture(GLTF, out="a.glb", task_id="", root=where)
    assert caught.value.code == "fetch.no-task"
    assert purchase.read(where) == []


def test_a_transfer_that_never_arrived_is_refused(tmp_path):
    where = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.capture(where / "never.glb", out="a.glb", task_id="t_1", root=where)
    assert caught.value.code == "fetch.nothing-arrived"


def test_something_that_is_not_bought_here_is_refused(tmp_path):
    where = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.capture(GLTF, out="a.glb", task_id="t_1", bought="song", root=where)
    assert caught.value.code == "fetch.unknown-purchase"


def test_a_digest_that_does_not_match_stops_the_purchase(tmp_path):
    where = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.capture(GLTF, out="a.glb", task_id="t_1", sha256="0" * 64, root=where)
    assert caught.value.code == "post.download-digest"
    assert purchase.read(where) == []


# -- keyed off the local file ----------------------------------------------------------


def test_a_purchase_is_found_by_its_hash_not_its_remote_id(tmp_path):
    """The remote id is the one that stops existing."""
    where = project(tmp_path)
    entry = bought(where)
    assert purchase.find(entry["sha256"], root=where) == entry
    assert purchase.find("0" * 64, root=where) is None


def test_the_reference_that_asked_for_it_is_recorded(tmp_path):
    where = project(tmp_path)
    bought(where, reference=drawing(where))
    record = provenance.read("assets/cap.glb", root=where)
    assert record["reference"] == "cap.png"
    assert record["inputs"][0]["role"] == "reference"


def test_what_a_project_has_spent_is_answerable(tmp_path):
    where = project(tmp_path)
    bought(where, out="a.glb", task_id="t_1", credits=30)
    bought(where, out="b.glb", task_id="t_2", credits=12.5)
    assert purchase.spent(where) == 42.5
    assert len(purchase.read(where)) == 2


# -- is it all still here --------------------------------------------------------------


def test_a_sound_project_is_sound(tmp_path):
    where = project(tmp_path)
    bought(where)
    found = purchase.held(where)
    assert found["sound"] is True
    assert found["credits"] == 30.0
    assert found["present"] == ["assets/cap.glb"]


def test_a_paid_mesh_that_went_missing_is_named_with_what_it_cost(tmp_path):
    """The question §PW17 says nothing could answer."""
    where = project(tmp_path)
    bought(where)
    (where / "assets" / "cap.glb").unlink()

    found = purchase.held(where)
    assert found["sound"] is False
    assert found["missing"][0]["task_id"] == "t_9f3a"
    assert found["lost_credits"] == 30.0


def test_a_paid_mesh_that_is_no_longer_what_it_was_is_named(tmp_path):
    where = project(tmp_path)
    bought(where)
    (where / "assets" / "cap.glb").write_bytes(b"something else entirely")
    found = purchase.held(where)
    assert found["sound"] is False
    assert found["changed"][0]["artefact"] == "assets/cap.glb"


def test_a_ledger_edited_into_nonsense_says_so(tmp_path):
    where = project(tmp_path)
    bought(where)
    purchase.where(where).write_text("{not a ledger", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        purchase.read(where)
    assert caught.value.code == "fetch.ledger-malformed"
    assert "version control" in caught.value.remedy


def test_a_project_that_has_bought_nothing_reads_as_empty(tmp_path):
    where = project(tmp_path)
    assert purchase.read(where) == []
    assert purchase.spent(where) == 0
    assert purchase.held(where)["sound"] is True


def test_the_ledger_survives_being_written_twice(tmp_path):
    where = project(tmp_path)
    bought(where, out="a.glb", task_id="t_1")
    bought(where, out="b.glb", task_id="t_2")
    held = json.loads(purchase.where(where).read_text(encoding="utf-8"))
    assert [e["task_id"] for e in held] == ["t_1", "t_2"]


# -- a ledger somebody else kept, replayed into this one (§PW55) -----------------------


def a_mesh(root, name="bought.glb", body=b"glTF-pretend"):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path, hashlib.sha256(body).hexdigest()


def an_entry(root, **over):
    path, digest = a_mesh(root, over.pop("name", "bought.glb"))
    return {
        "artefact": path.name,
        "sha256": digest,
        "task_id": "t_01",
        "credits": 30.0,
        "prompt": "a candy mallet",
        **over,
    }


def test_an_entry_whose_file_is_there_and_unchanged_is_adopted(tmp_path):
    project(tmp_path)
    found = purchase.adopt([an_entry(tmp_path)], root=tmp_path)
    assert [e["artefact"] for e in found["adopted"]] == ["bought.glb"]
    assert found["credits"] == 30.0
    assert found["sound"] is True
    assert purchase.read(tmp_path)[0]["task_id"] == "t_01"


def test_an_entry_naming_a_file_that_is_gone_never_enters_the_ledger(tmp_path):
    """The ledger is written last so it can never claim an asset that is not there."""
    project(tmp_path)
    entry = {**an_entry(tmp_path), "artefact": "never-landed.glb"}
    found = purchase.adopt([entry], root=tmp_path)
    assert found["adopted"] == []
    assert found["missing"][0]["artefact"] == "never-landed.glb"
    assert found["sound"] is False
    assert purchase.read(tmp_path) == []


def test_an_entry_whose_mesh_moved_is_reported_with_both_hashes(tmp_path):
    """The question a lock file was written to answer and nothing ever asked."""
    project(tmp_path)
    entry = an_entry(tmp_path)
    (tmp_path / "bought.glb").write_bytes(b"a different mesh entirely")
    found = purchase.adopt([entry], root=tmp_path)
    assert found["adopted"] == []
    assert found["changed"][0]["recorded"] == entry["sha256"]
    assert found["changed"][0]["found"] != entry["sha256"]
    assert purchase.read(tmp_path) == []


def test_adopting_twice_changes_nothing(tmp_path):
    project(tmp_path)
    entry = an_entry(tmp_path)
    purchase.adopt([entry], root=tmp_path)
    again = purchase.adopt([entry], root=tmp_path)
    assert again["adopted"] == []
    assert again["already"][0]["task_id"] == "t_01"
    assert len(purchase.read(tmp_path)) == 1


def test_a_replayed_spend_does_not_eat_a_ceiling_set_afterwards(tmp_path):
    """It was gone before this project had a ceiling; charging it would refuse work."""
    project(tmp_path, '[budget]\ncredits = 50\nexpires = "2099-12-31"\n')
    purchase.adopt([an_entry(tmp_path)], root=tmp_path)
    assert purchase.spent(tmp_path) == 0.0
    assert purchase.remaining(tmp_path)["left"] == 50
    # But it is still an asset, and `held` counts every credit that was ever paid.
    assert purchase.held(tmp_path)["credits"] == 30.0
    assert purchase.held(tmp_path)["against_ceiling"] == 0.0
    assert purchase.held(tmp_path)["sound"] is True


def test_an_adopted_mesh_gets_a_record_beside_it(tmp_path):
    """Everything downstream keys off the record and the hash, not the remote id."""
    from polyweave import provenance

    project(tmp_path)
    purchase.adopt([an_entry(tmp_path)], root=tmp_path)
    written = provenance.read("bought.glb", root=tmp_path)
    assert written["kind"] == "fetch"
    assert written["task_id"] == "t_01"
    assert written["adopted"] is True


def test_a_record_somebody_already_wrote_is_left_alone(tmp_path):
    from polyweave import provenance

    project(tmp_path)
    entry = an_entry(tmp_path)
    mine = provenance.build("fetch", "bought.glb", extra={"mine": True}, root=tmp_path)
    provenance.write(mine, root=tmp_path)
    purchase.adopt([entry], root=tmp_path)
    assert provenance.read("bought.glb", root=tmp_path)["mine"] is True


def test_an_entry_with_no_task_id_is_a_mapping_error_and_stops_the_call(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.adopt([{**an_entry(tmp_path), "task_id": ""}], root=tmp_path)
    assert caught.value.code == "fetch.no-task"


def test_an_entry_with_no_hash_is_refused_because_everything_keys_off_it(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        purchase.adopt([{**an_entry(tmp_path), "sha256": ""}], root=tmp_path)
    assert caught.value.code == "fetch.ledger-malformed"
