"""The credits kit and the file it reads, written from the records (§PW350).

provenance.credits writes the file and says when it no longer matches the records, so
an asset recorded after the last build cannot ship uncredited; the kit's proof shows
every credit a record owes on the screen, where $GODOT is set.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from polyweave import kits, provenance


@pytest.fixture
def game(tmp_path):
    here = tmp_path / "game"
    shutil.copytree(kits.KITS / "credits" / "fixture", here)
    return here


def test_a_borrowed_file_carries_the_credit_its_licence_requires(game):
    said = provenance.borrow("source/mark.png", "art/again.png", licence="CC-BY-4.0",
                             credit="Mark by Ana Lima, CC BY 4.0", root=str(game))
    record = provenance.read("art/again.png", game)
    assert said["credit"] == record["credit"] == "Mark by Ana Lima, CC BY 4.0"
    assert record["licence"] == "CC-BY-4.0"


def test_the_credits_file_is_fresh_until_a_record_owes_a_new_credit(game):
    held = provenance.credits(root=str(game), out="credits.json", check=True)
    assert held["fresh"] is True
    assert [c["credit"] for c in held["owed"]] == ["Badge by Studio Norte, CC BY 4.0"]
    assert held["people"][0] == {"name": "Ana Lima", "role": "Art"}
    provenance.borrow("source/mark.png", "art/late.png", credit="Late by Rui Sato",
                      root=str(game))
    stale = provenance.credits(root=str(game), out="credits.json", check=True)
    assert stale["fresh"] is False
    assert stale["missing"] == ["Late by Rui Sato"]
    assert "Late by Rui Sato" in stale["why"]
    wrote = provenance.credits(root=str(game), out="credits.json")
    assert wrote["wrote"] == "credits.json"
    assert provenance.credits(root=str(game), out="credits.json", check=True)["fresh"]


def test_a_missing_credits_file_is_not_fresh(game):
    (game / "credits.json").unlink()
    said = provenance.credits(root=str(game), out="credits.json", check=True)
    assert said["fresh"] is False
    assert "provenance.credits out=" in said["why"]


def test_the_credits_kit_lands_and_proves_in_its_fixture(game):
    said = kits.install("credits", root=str(game))
    assert said["declared"] == {}
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "change", "said"), [
    ("credits.json", "drop-owed", "is owed a credit the screen does not show"),
    ("addons/polyweave/credits/credits.gd",
     (" or event is InputEventJoypadButton:", ":"),
     "InputEventJoypadButton press did not end the credits"),
    ("addons/polyweave/credits/credits.gd",
     ("_offset += rate * delta", "_offset += rate * delta * 3"), "the screen scrolled"),
])
def test_a_broken_credits_screen_fails_the_proof_by_name(game, where, change, said):
    kits.install("credits", root=str(game))
    target = game / where
    if change == "drop-owed":
        held = json.loads(target.read_text(encoding="utf-8"))
        held["owed"] = []
        target.write_text(json.dumps(held), encoding="utf-8")
    else:
        text = target.read_text(encoding="utf-8")
        assert change[0] in text
        target.write_text(text.replace(*change), encoding="utf-8")
    [found] = kits._scripts(["credits"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]
