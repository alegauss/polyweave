"""A change a person asks for is a record, not a chat line (§PW301)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import provenance, revision
from polyweave.errors import PolyweaveError


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "art").mkdir()
    Image.new("RGBA", (8, 8), (90, 90, 90, 255)).save(tmp_path / "art" / "icon.png")
    provenance.write(
        provenance.build("picture", tmp_path / "art" / "icon.png", root=tmp_path),
        root=tmp_path,
    )
    Image.new("L", (8, 8), 255).save(tmp_path / "art" / "rim.mask.png")
    return tmp_path


def test_a_request_is_kept_against_what_the_person_was_looking_at(tree):
    asked = revision.ask(
        "art/icon.png", "a warmer rim", mask="art/rim.mask.png", root=str(tree)
    )
    assert asked["event"] == "asked"
    assert asked["item"] == "art/icon.png"
    assert asked["mask"] == "art/rim.mask.png"
    assert len(asked["digest"]) == 16
    kept = (tree / ".polyweave" / "revisions.jsonl").read_text("utf-8").splitlines()
    assert json.loads(kept[0])["words"] == "a warmer rim"

    opened = revision.open_(root=str(tree))["revisions"]
    assert [one["revision"] for one in opened] == [asked["revision"]]
    assert opened[0]["moved"] is False
    assert opened[0]["brief"]["item"]["id"] == "art/icon.png"


def test_an_item_that_moved_since_the_request_says_so(tree):
    revision.ask("art/icon.png", "a warmer rim", root=str(tree))
    Image.new("RGBA", (8, 8), (200, 90, 90, 255)).save(tree / "art" / "icon.png")
    provenance.write(
        provenance.build("picture", tree / "art" / "icon.png", root=tree), root=tree
    )
    assert revision.open_(root=str(tree))["revisions"][0]["moved"] is True


def test_a_revision_closes_on_a_run_and_a_sitting_or_as_withdrawn(tree):
    first = revision.ask("art/icon.png", "a warmer rim", root=str(tree))["revision"]
    second = revision.ask("art/icon.png", "thinner outline", root=str(tree))["revision"]
    closed = revision.close(first, run="abc123", sitting="icons", root=str(tree))
    assert closed["run"] == "abc123"
    assert "verdict" not in closed
    revision.close(second, withdrawn="the person changed their mind", root=str(tree))
    assert revision.open_(root=str(tree))["revisions"] == []
    with pytest.raises(PolyweaveError) as refused:
        revision.close(first, withdrawn="again", root=str(tree))
    assert refused.value.code == "review.not-open"
    assert "already closed" in refused.value.message


@pytest.mark.parametrize(
    "how",
    [{}, {"run": "abc123"}, {"run": "a", "sitting": "s", "withdrawn": "both"}],
)
def test_a_close_with_neither_an_answer_nor_a_reason_is_refused(tree, how):
    asked = revision.ask("art/icon.png", "a warmer rim", root=str(tree))["revision"]
    with pytest.raises(PolyweaveError) as refused:
        revision.close(asked, root=str(tree), **how)
    assert refused.value.code == "review.unanswered"


def test_a_request_about_nothing_listed_is_refused_with_the_items(tree):
    with pytest.raises(PolyweaveError) as refused:
        revision.ask("art/icon", "warmer", root=str(tree))
    assert refused.value.code == "review.unknown-item"
    assert "art/icon.png" in refused.value.as_dict()["allowed"]


def test_a_span_must_be_a_stretch_of_time(tree):
    with pytest.raises(PolyweaveError) as refused:
        revision.ask("art/icon.png", "later", span=[2.0, 1.0], root=str(tree))
    assert refused.value.code == "review.bad-span"
    asked = revision.ask("art/icon.png", "here", span=[1, 2.5], root=str(tree))
    assert asked["span"] == [1.0, 2.5]


def test_each_turn_is_kept_on_its_revision_in_order(tree):
    # §PW306: the request and how it was talked through travel together.
    asked = revision.ask("art/icon.png", "a warmer rim", root=str(tree))["revision"]
    revision.turn(asked, "keep the outline", root=str(tree))
    revision.turn(asked, "Warmed the rim; outline kept.", by="session", root=str(tree))
    turns = revision.open_(root=str(tree))["revisions"][0]["turns"]
    assert [(t["by"], t["text"]) for t in turns] == [
        ("person", "keep the outline"),
        ("session", "Warmed the rim; outline kept."),
    ]
    revision.close(asked, withdrawn="done another way", root=str(tree))
    with pytest.raises(PolyweaveError) as refused:
        revision.turn(asked, "too late", root=str(tree))
    assert refused.value.code == "review.not-open"
