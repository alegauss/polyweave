"""An artefact another project made, brought in with a record of where from (§PW325).

The sibling is a real git repository in a temporary folder, so the record's project,
path and commit are the ones git reports.
"""

from __future__ import annotations

import subprocess

import pytest

from polyweave import provenance
from polyweave.errors import PolyweaveError


def git(where, *argv):
    return subprocess.run(["git", "-C", str(where), *argv], capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.fixture
def studio(tmp_path):
    """Cottony, holding the studio badge every game borrows."""
    sibling = tmp_path / "cottony"
    (sibling / "brand").mkdir(parents=True)
    (sibling / "brand" / "badge.png").write_bytes(b"\x89PNG badge v1")
    git(sibling, "init", "-q")
    git(sibling, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git(sibling, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "badge")
    game = tmp_path / "game"
    game.mkdir()
    return sibling, game


def test_a_borrowed_file_records_its_project_path_and_commit(studio):
    sibling, game = studio
    found = provenance.borrow(str(sibling / "brand" / "badge.png"), "ui/badge.png",
                              root=str(game))
    assert (game / "ui" / "badge.png").read_bytes() == b"\x89PNG badge v1"
    taken = found["borrowed"]
    assert taken["path"] == "brand/badge.png"
    assert taken["commit"] == git(sibling, "rev-parse", "HEAD")
    assert taken["uncommitted"] is False
    record = provenance.read("ui/badge.png", root=game)
    assert record["kind"] == "borrow"
    assert record["inputs"][0]["role"] == "borrowed"


def test_a_source_that_moves_on_makes_every_borrower_outdated(studio):
    sibling, game = studio
    provenance.borrow(str(sibling / "brand" / "badge.png"), "ui/badge.png",
                      root=str(game))
    assert provenance.outdated(root=str(game))["outdated"] == []
    (sibling / "brand" / "badge.png").write_bytes(b"\x89PNG badge v2")
    stale = provenance.outdated(root=str(game))["outdated"]
    assert [one["artefact"] for one in stale] == ["ui/badge.png"]
    # Borrowing again takes it as it is now, and says it is not committed yet.
    again = provenance.borrow(str(sibling / "brand" / "badge.png"), "ui/badge.png",
                              root=str(game))
    assert again["borrowed"]["uncommitted"] is True
    assert provenance.outdated(root=str(game))["outdated"] == []


def test_a_file_of_this_project_can_be_borrowed_too(tmp_path):
    (tmp_path / "art").mkdir()
    (tmp_path / "art" / "logo.png").write_bytes(b"logo")
    found = provenance.borrow("art/logo.png", "game/ui/logo.png", root=str(tmp_path))
    assert found["artefact"] == "game/ui/logo.png"


@pytest.mark.parametrize("path, out", [("nowhere.png", "ui/x.png"),
                                       ("art/logo.png", "art/logo.png")])
def test_a_borrow_with_nothing_to_take_is_refused(tmp_path, path, out):
    (tmp_path / "art").mkdir()
    (tmp_path / "art" / "logo.png").write_bytes(b"logo")
    with pytest.raises(PolyweaveError) as refused:
        provenance.borrow(path, out, root=str(tmp_path))
    assert refused.value.code == "prov.missing-input"
