"""A sitting laid out in the wrong folder, moved with its answers (§PW436).

Met in Spinhold: the pilot's lines sitting landed at the project root and was moved by
hand, `answers.jsonl` was missed, and 23 answers named a sitting that was gone.
"""

from __future__ import annotations

import json

import pytest

from polyweave import review, verdict
from polyweave.errors import PolyweaveError
from test_verdict_answer import member


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    verdict.sitting(
        {"stars": [member(tmp_path, "star_dim", 200)],
         "moons": [member(tmp_path, "moon_dim", 180)]},
        out="pilot_lines", root=tmp_path,
    )
    return tmp_path


def test_a_moved_sitting_keeps_its_answers_at_its_new_path(project):
    verdict.answer("pilot_lines", "accept", "both right", root=str(project))
    said = verdict.move("pilot_lines", "art/review/pilot_lines", root=str(project))
    landed = "art/review/pilot_lines/sitting.json"
    assert said == {**said, "from": "pilot_lines/sitting.json", "to": landed,
                    "answers": 2}
    assert not (project / "pilot_lines").exists()
    manifest = json.loads((project / landed).read_text("utf-8"))
    assert all(one["sheet"].startswith("art/review/pilot_lines/")
               for one in manifest["families"].values())
    assert [one["manifest"] for one in review.sittings(project)] == [landed]
    # The answers file only grew: the two answers and one move.
    lines = (project / ".polyweave" / "answers.jsonl").read_text("utf-8").splitlines()
    assert len(lines) == 3 and "moved" in json.loads(lines[-1])
    kept = verdict.answers(root=str(project))["answers"]
    assert sorted(one["family"] for one in kept) == ["moons", "stars"]
    assert {one["sitting"] for one in kept} == {landed}
    # Answered at its new path, so a verdict asked again there skips both families.
    again = verdict.answer("art/review/pilot_lines", "accept", "again",
                           root=str(project))
    assert again["skipped"] == ["stars", "moons"]


def test_a_sitting_moved_twice_is_followed_to_where_it_is(project):
    verdict.answer("pilot_lines", "accept", "ok", family="stars", root=str(project))
    verdict.move("pilot_lines", "art/one", root=str(project))
    verdict.move("art/one", "art/review/two", root=str(project))
    assert {one["sitting"] for one in verdict.answers(root=str(project))["answers"]} \
        == {"art/review/two/sitting.json"}


@pytest.mark.parametrize("to", ["art/taken", "../elsewhere", "pilot_lines/inner"])
def test_a_move_where_it_cannot_go_is_refused_and_nothing_moves(project, to):
    (project / "art" / "taken").mkdir(parents=True)
    with pytest.raises(PolyweaveError) as refused:
        verdict.move("pilot_lines", to, root=str(project))
    assert refused.value.code == "verdict.bad-move"
    assert (project / "pilot_lines" / "sitting.json").is_file()


def test_a_sitting_never_laid_out_is_refused(project):
    with pytest.raises(PolyweaveError) as refused:
        verdict.move("art/none", "art/review/none", root=str(project))
    assert refused.value.code == "loop.unknown-sitting"
