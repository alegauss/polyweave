"""A verdict a person gave in conversation, answering a sitting by name (§PW375).

Met in Spinhold: the owner said "está tudo certo, pode continuar" of four open sittings,
and carrying it took reading each manifest and a throwaway driver calling the page's own
write. One call does it now, and the ledger takes it as it takes a click.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import describe, verdict
from polyweave.errors import PolyweaveError

SPEC = """asset = "{name}"

[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"
region  = "frame"
max     = {{ value = 0.37, origin = "margin", measured = 0.3438 }}
"""


def member(tmp_path, name, byte):
    (tmp_path / "accept").mkdir(exist_ok=True)
    (tmp_path / "renders").mkdir(exist_ok=True)
    (tmp_path / "accept" / f"{name}.accept.toml").write_text(
        SPEC.format(name=name), encoding="utf-8")
    Image.new("RGBA", (24, 24), (byte, byte, byte, 255)).save(
        tmp_path / "renders" / f"{name}.png")
    return {"name": name, "spec": f"accept/{name}.accept.toml",
            "new": f"renders/{name}.png"}


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    verdict.sitting(
        {"stars": [member(tmp_path, "star_dim", 200)],
         "moons": [member(tmp_path, "moon_dim", 180)]},
        out="art/review/title", root=tmp_path,
    )
    return tmp_path


def answered(root):
    path = root / ".polyweave" / "answers.jsonl"
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def test_every_family_of_a_sitting_is_answered_by_its_folder(project):
    said = verdict.answer("art/review/title", "accept", "está tudo certo",
                          root=str(project))
    assert said["sitting"] == "art/review/title/sitting.json"
    assert sorted(one["family"] for one in said["answered"]) == ["moons", "stars"]
    lines = answered(project)
    assert sorted(one["family"] for one in lines) == ["moons", "stars"]
    # The person's words as given, as a click on the page would have kept them.
    assert {one["why"] for one in lines} == {"está tudo certo"}


def test_one_family_is_answered_alone_and_the_others_are_left(project):
    said = verdict.answer("art/review/title/sitting.json", "accept",
                          "the star is right", family="stars", root=str(project))
    assert [one["family"] for one in said["answered"]] == ["stars"]
    assert [one["family"] for one in answered(project)] == ["stars"]


def test_a_family_already_answered_is_skipped_and_named(project):
    verdict.answer("art/review/title", "accept", "the star is right", family="stars",
                   root=str(project))
    said = verdict.answer("art/review/title", "accept", "all of it", root=str(project))
    assert [one["family"] for one in said["answered"]] == ["moons"]
    assert said["skipped"] == ["stars"]
    assert len(answered(project)) == 2


def test_the_answers_an_agent_resumes_from_include_it(project):
    verdict.answer("art/review/title", "accept", "ok", root=str(project))
    assert len(verdict.answers(root=str(project))["answers"]) == 2


@pytest.mark.parametrize(
    ("sitting", "family", "code"),
    [("art/review/elsewhere", "", "loop.unknown-sitting"),
     ("art/review/title", "suns", "loop.unknown-sitting")],
)
def test_a_sitting_or_family_not_laid_out_is_refused(project, sitting, family, code):
    with pytest.raises(PolyweaveError) as refused:
        verdict.answer(sitting, "accept", "yes", family=family, root=str(project))
    assert refused.value.code == code
    assert not (project / ".polyweave" / "answers.jsonl").exists()


def test_a_verdict_carried_from_chat_needs_the_person_s_words(project):
    with pytest.raises(PolyweaveError) as refused:
        verdict.answer("art/review/title", "accept", "  ", root=str(project))
    assert refused.value.code == "loop.no-reason"


def test_it_is_an_operation_an_agent_can_find():
    assert describe.for_target("polyweave.verdict:answer") == "verdict.answer"
