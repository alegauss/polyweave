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


SPEC = """asset = "icon"
artefact = "art/icon.png"

[[predicate]]
id      = "tone"
measure = "luma_p99"
region  = "frame"
max     = 0.5
"""


def test_the_items_own_checks_run_and_none_is_said_where_nothing_checks(tree):
    # §PW307: chosen by the item, never by the session.
    asked = revision.ask("art/icon.png", "darker", root=str(tree))["revision"]
    unheld = revision.check(asked, root=str(tree))
    assert unheld["passed"] is None
    assert "nothing checks" in unheld["said"]
    (tree / "docs" / "accept").mkdir(parents=True)
    (tree / "docs" / "accept" / "icon.accept.toml").write_text(SPEC, encoding="utf-8")
    held = revision.check(asked, root=str(tree))
    assert [one["check"] for one in held["checks"]] == ["accept.check"]
    assert held["passed"] is True


def test_a_sessions_settings_refuse_a_verdict_and_check_after_writes(tree):
    asked = revision.ask("art/icon.png", "darker", root=str(tree))["revision"]
    made = revision.settings(asked, root=str(tree))
    assert set(made["permissions"]["deny"]) == set(revision.WITHHELD)
    command = made["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert f"hook revision --revision {asked}" in command


def test_the_hook_denies_a_verdict_and_answers_a_write_to_the_item(tree):
    import subprocess
    import sys

    asked = revision.ask("art/icon.png", "darker", root=str(tree))["revision"]
    denied = revision.hooked(
        {"hook_event_name": "PreToolUse", "tool_name": revision.WITHHELD[0]},
        asked, str(tree),
    )
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    elsewhere = {"hook_event_name": "PostToolUse", "tool_name": "Write",
                 "tool_input": {"file_path": str(tree / "notes.md")}}
    assert revision.hooked(elsewhere, asked, str(tree)) is None
    # Through the command line, as Claude Code runs it.
    event = {"hook_event_name": "PostToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str(tree / "art" / "icon.png")}}
    ran = subprocess.run(
        [sys.executable, "-m", "polyweave", "hook", "revision", "--revision", asked,
         "--root", str(tree)],
        input=json.dumps(event), capture_output=True, text=True, check=True,
    )
    said = json.loads(ran.stdout)["hookSpecificOutput"]["additionalContext"]
    assert said.startswith("The item's own checks after this change")


def test_a_revision_ends_in_a_sitting_and_hears_the_persons_answer(tree):
    # §PW307: the session cannot stop on its own word; the person's answer is read back.
    from polyweave import verdict

    asked = revision.ask("art/icon.png", "darker", root=str(tree))["revision"]
    stopping = {"hook_event_name": "Stop"}
    blocked = revision.hooked(stopping, asked, str(tree))
    assert blocked["decision"] == "block"
    assert "verdict.sitting" in blocked["reason"]
    assert revision.open_(root=str(tree))["revisions"][0]["sitting"] is None

    laid = verdict.sitting(
        {"icon": [{"name": "icon", "new": "art/icon.png"}]}, out="review/s1",
        root=str(tree),
    )
    assert laid
    assert revision.hooked(stopping, asked, str(tree)) is None
    opened = revision.open_(root=str(tree))["revisions"][0]
    assert opened["sitting"] == "review/s1/sitting.json"
    assert opened["answer"] is None
    verdict.record_answer(
        {"choice": "look", "why": "still too bright", "members": []},
        sitting="review/s1/sitting.json", family="icon", root=str(tree),
    )
    answer = revision.open_(root=str(tree))["revisions"][0]["answer"]
    assert (answer["choice"], answer["why"]) == ("look", "still too bright")


def test_a_write_outside_the_item_asks_and_the_close_lists_what_was_reached(tree):
    # §PW309: a change to one item stays inside it, or asks.
    asked = revision.ask("art/icon.png", "darker", root=str(tree))["revision"]

    def before(path):
        return revision.hooked(
            {"hook_event_name": "PreToolUse", "tool_name": "Write",
             "tool_input": {"file_path": path}},
            asked, str(tree),
        )

    assert before(str(tree / "art" / "icon.png")) is None
    assert before(str(tree / ".polyweave" / "marks" / "m.png")) is None
    config = before(str(tree / "polyweave.toml"))
    assert config["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "every item is held to" in config["hookSpecificOutput"][
        "permissionDecisionReason"
    ]
    other = before("game/hud.gd")["hookSpecificOutput"]["permissionDecisionReason"]
    assert "game/hud.gd is not art/icon.png" in other

    revision.hooked(
        {"hook_event_name": "PostToolUse", "tool_name": "Write",
         "tool_input": {"file_path": str(tree / "art" / "icon.png")}},
        asked, str(tree),
    )
    closed = revision.close(asked, withdrawn="enough", root=str(tree))
    assert closed["touched"] == ["art/icon.png"]
    assert closed["waiting"] == []


def test_a_shell_write_outside_the_item_is_found_after_it_and_listed(tree):
    # §PW378: a Bash command names no file the PreToolUse hook could hold to the scope,
    # so `sed -i` on the config went through unseen and the close never listed it.
    (tree / "polyweave.toml").write_text("", encoding="utf-8")
    asked = revision.ask("art/icon.png", "darker", root=str(tree))["revision"]
    made = revision.settings(asked, root=str(tree))
    assert any(one["matcher"] == "Bash" for one in made["hooks"]["PreToolUse"])
    assert any(one["matcher"] == "Bash" for one in made["hooks"]["PostToolUse"])

    def bash(name):
        return revision.hooked(
            {"hook_event_name": name, "tool_name": "Bash", "tool_use_id": "use-7",
             "tool_input": {"command": "sed -i ... polyweave.toml"}},
            asked, str(tree),
        )

    assert bash("PreToolUse") is None
    (tree / "polyweave.toml").write_text("[paths]\nwork = '.polyweave'\n",
                                         encoding="utf-8")
    Image.new("RGBA", (8, 8), (10, 10, 10, 255)).save(tree / "art" / "icon.png")
    (tree / ".polyweave" / "scratch.txt").write_text("the work area", encoding="utf-8")
    said = bash("PostToolUse")["hookSpecificOutput"]["additionalContext"]
    assert "polyweave.toml is the project's config" in said
    assert "Undo it" in said
    found = revision.outside(asked, root=str(tree))["outside"]
    assert [one["file"] for one in found] == ["polyweave.toml"]
    # A command that writes nothing outside says nothing.
    assert bash("PreToolUse") is None
    assert bash("PostToolUse") is None
    closed = revision.close(asked, withdrawn="enough", root=str(tree))
    assert closed["touched"] == ["art/icon.png", "polyweave.toml"]
