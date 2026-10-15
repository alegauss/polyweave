"""A verdict only a person can give (§PW443).

An accept called as a tool lands only with the code the review page shows for the
sitting, which the page's server issues and keeps; the page's own write needs none.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import person, review, server, verdict
from polyweave.cli import command_line
from polyweave.commands import run

SPEC = """asset = "{name}"

[[predicate]]
id      = "tone"
measure = "luma_p99"
region  = "frame"
max     = 0.99
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


SITTING = "art/review/title/sitting.json"


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.delenv(person.SURFACE, raising=False)
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    verdict.sitting({"stars": [member(tmp_path, "star_dim", 120)]},
                    out="art/review/title", root=tmp_path)
    return tmp_path


def tool(name, **arguments):
    said = server.call(name, arguments)
    return said["isError"], said["structuredContent"]


def stars(root):
    return [member(root, "star_dim", 120)]


def test_an_agent_cannot_accept_its_own_look_through_the_tool(project):
    refused, said = tool("verdict_judge", members=stars(project), choice="accept",
                         why="looks right to me", root=str(project))
    assert refused
    assert said["refused"]["code"] == "verdict.not-the-person"
    assert "review page" in said["refused"]["remedy"]
    assert not (project / ".polyweave" / "answers.jsonl").exists()


def test_a_wrong_code_is_refused_and_named(project):
    person.issue(project, SITTING)
    refused, said = tool("verdict_answer", sitting="art/review/title", choice="accept",
                         why="ok", code="ZZZZZ", root=str(project))
    assert refused
    assert "'ZZZZZ' is not" in said["refused"]["message"]


def test_the_code_the_page_shows_lets_the_person_s_yes_land(project):
    code = person.issue(project, SITTING)
    refused, said = tool("verdict_answer", sitting="art/review/title", choice="accept",
                         why="está certo", code=code.lower(), root=str(project))
    assert not refused, said
    assert [one["family"] for one in said["answered"]] == ["stars"]


def test_judge_takes_the_code_of_a_sitting_laying_out_its_members(project):
    code = person.issue(project, SITTING)
    refused, _ = tool("verdict_judge", members=stars(project), choice="accept",
                      why="ok", code=code, root=str(project))
    assert not refused
    other = person.issue(project, person.PAGE)
    refused, _ = tool("verdict_judge", members=stars(project), choice="accept",
                      why="ok", code=other, root=str(project))
    assert refused


def test_a_rejection_needs_no_code(project):
    refused, said = tool("verdict_judge", members=stars(project), choice="look",
                         why="too dark", root=str(project))
    assert not refused, said


def test_the_page_s_own_write_needs_no_code(project):
    said = review.answer(project, {"sitting": SITTING, "family": "stars",
                                   "choice": "accept", "why": "certo"})
    assert said["choice"] == "accept"


def test_review_answer_as_a_tool_needs_the_code_in_its_body(project):
    body = {"sitting": SITTING, "family": "stars", "choice": "accept", "why": "ok"}
    refused, _ = tool("review_answer", body=body, root=str(project))
    assert refused
    code = person.issue(project, SITTING)
    refused, said = tool("review_answer", body={**body, "code": code},
                         root=str(project))
    assert not refused, said


def test_promote_needs_the_code_above_the_page_s_lanes(project):
    refused, said = tool("verdict_promote", gate="g1", picture="p.png", why="ok",
                         root=str(project))
    assert refused
    assert said["refused"]["code"] == "verdict.not-the-person"


def test_a_window_s_own_server_is_the_person_s_surface(project, monkeypatch):
    monkeypatch.setenv(person.SURFACE, "window")
    refused, said = tool("verdict_judge", members=stars(project), choice="accept",
                         why="ok", root=str(project))
    assert not refused, said


def test_the_command_line_holds_the_same_door(project, capsys):
    stated = command_line().parse_args([
        "verdict.answer", "--sitting", "art/review/title", "--choice", "accept",
        "--why", "ok", "--root", str(project)])
    assert run(stated) == 1
    assert "verdict.not-the-person" in capsys.readouterr().err


def test_a_sitting_says_the_address_the_page_opens_it_at(tmp_path):
    """§PW459: a link to one sitting, which a screenshot and a person can both open."""
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    said = verdict.sitting({"stars": [member(tmp_path, "star_dim", 120)]},
                           out="art/review/title", root=tmp_path)
    assert said["manifest"] == SITTING
    assert said["page"] == "/?sitting=art%2Freview%2Ftitle%2Fsitting.json"
    assert said["page"] in said["says"]
    lines = review.waiting_at(tmp_path, "http://127.0.0.1:8765")
    assert lines == [f"  1 to answer: http://127.0.0.1:8765{said['page']}"]
    review.answer(tmp_path, {"sitting": SITTING, "family": "stars",
                             "choice": "accept", "why": "certo"})
    assert review.waiting_at(tmp_path, "http://127.0.0.1:8765") == []


def test_only_a_digest_of_a_code_is_on_disk(project):
    code = person.issue(project, SITTING)
    kept = (project / ".polyweave" / person.DIGESTS).read_text("utf-8")
    assert code not in kept
    assert json.loads(kept)[SITTING] != code
