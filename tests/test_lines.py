"""A line's tone judged by a person, and a canon of lines (§PW199)."""

from __future__ import annotations

import json

import pytest

from polyweave import review, verdict, words, world
from polyweave.errors import PolyweaveError

WORLD = """\
[entity.ada]
name = "Captain Ada"
kind = "character"

[entity.bo]
name = "Bo"
kind = "character"

[rules]
tone = ["short, warm and often funny", "never a heroic speech"]
"""

ROWS = [
    "HI,Morning. Coffee first.,Bom dia. Café primeiro.,ada",
    "RALLY,We fight for glory!,Lutamos pela glória!,ada",
    "YAWN,Five more minutes.,Mais cinco minutos.,bo",
]


def _project(tmp_path, rows=ROWS, canon=True):
    (tmp_path / "polyweave.toml").write_text(
        '[words]\ntable = "strings.csv"\n'
        + ('canon = "lines.json"\n' if canon else ""),
        encoding="utf-8",
    )
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    (tmp_path / "strings.csv").write_text(
        "keys,en,pt_BR,_speaker\n" + "".join(r + "\n" for r in rows),
        encoding="utf-8",
    )


def _answer(tmp_path, sitting, family, choice, why):
    return review.answer(
        tmp_path,
        {"sitting": sitting, "family": family, "choice": choice, "why": why},
    )


def test_unjudged_lines_are_laid_out_one_family_each_by_speaker(tmp_path):
    _project(tmp_path)
    laid = words.sheet("review/lines", root=str(tmp_path))
    assert laid["lines"] == 3
    assert laid["families"] == ["ada.HI", "ada.RALLY", "bo.YAWN"]
    manifest = json.loads((tmp_path / laid["sitting"]).read_text("utf-8"))
    assert manifest["choices"] == words.LINE_CHOICES
    assert (tmp_path / "review" / "lines" / "ada.HI.png").is_file()
    member = manifest["families"]["bo.YAWN"]["members"][0]
    assert member["text"] == {
        "en": "Five more minutes.",
        "pt_BR": "Mais cinco minutos.",
    }


def test_a_person_s_verdicts_grow_the_canon_and_leave_the_sitting(tmp_path):
    _project(tmp_path)
    sitting = words.sheet("review/lines", root=str(tmp_path))["sitting"]
    _answer(tmp_path, sitting, "ada.HI", "accept", "that is her")
    said = _answer(tmp_path, sitting, "ada.RALLY", "look", "too heroic")
    assert said["members"][0]["line"]["approved"] is False
    kept = words.held(str(tmp_path))
    assert [(k["key"], k["approved"]) for k in kept] == [("HI", True), ("RALLY", False)]
    read = world.read("ada", root=str(tmp_path))
    assert [line["key"] for line in read["lines"]] == ["HI"]
    assert words.check(root=str(tmp_path))["unjudged"] == ["YAWN"]
    again = words.sheet("review/next", root=str(tmp_path))
    assert again["families"] == ["bo.YAWN"]


def test_a_line_whose_text_changed_is_unjudged_again(tmp_path):
    _project(tmp_path)
    sitting = words.sheet("review/lines", root=str(tmp_path))["sitting"]
    _answer(tmp_path, sitting, "ada.HI", "accept", "that is her")
    changed = [ROWS[0].replace("Coffee first", "Tea first"), *ROWS[1:]]
    (tmp_path / "strings.csv").write_text(
        "keys,en,pt_BR,_speaker\n" + "".join(r + "\n" for r in changed), "utf-8"
    )
    assert "HI" in words.check(root=str(tmp_path))["unjudged"]
    # What the person approved is kept as they approved it.
    assert world.read("ada", root=str(tmp_path))["lines"][0]["text"]["en"] == (
        "Morning. Coffee first."
    )


def test_a_line_has_no_bound_for_number_to_move(tmp_path):
    _project(tmp_path)
    sitting = words.sheet("review/lines", root=str(tmp_path))["sitting"]
    with pytest.raises(PolyweaveError) as refused:
        _answer(tmp_path, sitting, "ada.HI", "number", "it is fine")
    assert refused.value.code == "loop.no-failed-bound"
    assert words.held(str(tmp_path)) == []


def test_without_a_canon_there_is_nowhere_to_keep_a_verdict(tmp_path):
    _project(tmp_path, canon=False)
    with pytest.raises(PolyweaveError) as refused:
        words.sheet("review/lines", root=str(tmp_path))
    assert refused.value.code == "words.no-canon"


def test_a_sheet_carries_the_tone_and_the_speaker_s_approved_lines(
    tmp_path, monkeypatch
):
    _project(tmp_path)
    sitting = words.sheet("review/lines", root=str(tmp_path))["sitting"]
    _answer(tmp_path, sitting, "ada.HI", "accept", "that is her")
    drawn = []
    monkeypatch.setattr(words, "_draw", lambda *args: drawn.append(args))
    words.sheet("review/next", root=str(tmp_path))
    _, member, who, tone, shown, _ = drawn[0]
    assert member["line"] == "RALLY" and who == "Captain Ada"
    assert tone == ["short, warm and often funny", "never a heroic speech"]
    assert [one["key"] for one in shown] == ["HI"]


def test_nothing_unjudged_lays_out_nothing(tmp_path):
    _project(tmp_path, rows=ROWS[:1])
    sitting = words.sheet("review/lines", root=str(tmp_path))["sitting"]
    _answer(tmp_path, sitting, "ada.HI", "accept", "that is her")
    assert words.sheet("review/next", root=str(tmp_path))["sitting"] is None
    assert verdict.MANIFEST == "sitting.json"
