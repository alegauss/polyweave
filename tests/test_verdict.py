"""One sheet to look at, one call to answer it (§PW109)."""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import accept, loop, verdict

SPEC = """asset = "{name}"

# what the star has to hold
[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"
region  = "frame"
max     = {{ value = 0.37, origin = "margin", measured = 0.3438 }}
"""

#: Flat greys by byte: 200 reads 0.578 in linear luma and 102 reads 0.133.
BRIGHT, DARK = 200, 102


def member(tmp_path, name, byte, *, old=True):
    (tmp_path / "accept").mkdir(exist_ok=True)
    (tmp_path / "renders").mkdir(exist_ok=True)
    spec = tmp_path / "accept" / f"{name}.accept.toml"
    spec.write_text(SPEC.format(name=name), encoding="utf-8")
    Image.new("RGBA", (24, 24), (byte, byte, byte, 255)).save(
        tmp_path / "renders" / f"{name}.png"
    )
    one = {
        "name": name,
        "spec": f"accept/{name}.accept.toml",
        "new": f"renders/{name}.png",
        "shown": [48, 48],
    }
    if old:
        Image.new("RGBA", (24, 24), (DARK, DARK, DARK, 255)).save(
            tmp_path / "renders" / f"{name}.old.png"
        )
        one["old"] = f"renders/{name}.old.png"
    return one


def test_the_sheet_lays_the_family_out_and_says_what_failed(tmp_path):
    family = [member(tmp_path, "star_dim", BRIGHT), member(tmp_path, "star_gold", DARK)]
    found = verdict.sheet(family, out="review/stars.png", root=tmp_path)
    with Image.open(found["sheet"]) as laid:
        assert laid.width >= 2 * 48 and laid.height >= 2 * 48
    dim, gold = found["members"]
    assert not dim["passed"] and gold["passed"]
    assert "a margin put by hand over the measured 0.3438" in dim["failed"][0]
    assert set(found["choices"]) == {"accept", "look", "number"}


def test_a_family_named_in_a_person_s_words_keeps_its_name_and_a_safe_sheet(tmp_path):
    """§PW616: "RK262 card ? refeito" crashed the sitting on Windows."""
    import json

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    one = member(tmp_path, "star_dim", BRIGHT)
    said = verdict.sitting({"RK262 card ? refeito": [one], "mapa: HUD.": [one],
                            "Mapa- HUD": [one], "con": [one]},
                           out="review", root=tmp_path)
    sheets = {name: laid["sheet"].replace("\\", "/").split("/")[-1]
              for name, laid in said["sheets"].items()}
    assert sheets == {"RK262 card ? refeito": "RK262 card _ refeito.png",
                      "mapa: HUD.": "mapa_ HUD.png", "Mapa- HUD": "Mapa- HUD.png",
                      "con": "con_.png"}
    laid = json.loads((tmp_path / "review" / "sitting.json").read_text("utf-8"))
    assert laid["families"]["RK262 card ? refeito"]["sheet"] == (
        "review/RK262 card _ refeito.png")


def test_two_families_one_name_apart_by_case_or_symbol_get_two_sheets():
    taken: set[str] = set()
    assert [verdict.file_stem(one, taken) for one in ("Map?", "map*", "MAP")] == [
        "Map_", "map_-2", "MAP"]


@pytest.mark.parametrize("name", ["", "  ", "...", " . "])
def test_a_family_named_by_nothing_is_refused_before_a_sheet_is_drawn(tmp_path, name):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    one = member(tmp_path, "star_dim", BRIGHT)
    with pytest.raises(PolyweaveError) as refused:
        verdict.sitting({"fine": [one], name: [one]}, out="review", root=tmp_path)
    assert refused.value.code == "verdict.bad-family"
    assert not (tmp_path / "review" / "fine.png").exists()


def _git(tmp_path, *args):
    import subprocess

    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=tmp_path, check=True, capture_output=True)


def test_a_committed_old_picture_is_read_from_git(tmp_path):
    """§PW481: the render overwrote the picture, and the old one lives only in git."""
    import json

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    one = member(tmp_path, "gunship", DARK, old=False)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "renders/gunship.png")
    _git(tmp_path, "commit", "-q", "-m", "the gunship as it shipped")
    committed = (tmp_path / "renders" / "gunship.png").read_bytes()
    Image.new("RGBA", (24, 24), (BRIGHT,) * 3 + (255,)).save(
        tmp_path / "renders" / "gunship.png")  # the new render, in place
    one["old"] = "HEAD:renders/gunship.png"
    laid = verdict.sitting({"gunship": [one]}, out="review/rk143", root=str(tmp_path))
    said = laid["sheets"]["gunship"]["members"][0]
    assert said["old_from"]["rev"] == "HEAD"
    assert said["old_from"]["path"] == "renders/gunship.png"
    sitting = json.loads((tmp_path / "review" / "rk143" / "sitting.json").read_text(
        "utf-8"))
    shown = sitting["families"]["gunship"]["members"][0]
    assert shown["old"].startswith(".polyweave/picture/old/")
    assert (tmp_path / shown["old"]).read_bytes() == committed


def test_an_old_git_does_not_hold_or_a_missing_picture_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    one = member(tmp_path, "gunship", DARK, old=False)
    _git(tmp_path, "init", "-q")
    with pytest.raises(PolyweaveError) as refused:
        verdict.sitting({"gunship": [{**one, "old": "HEAD:renders/gunship.png"}]},
                        out="review/x", root=str(tmp_path))
    assert refused.value.code == "verdict.no-old"
    with pytest.raises(PolyweaveError) as refused:
        verdict.sheet([{**one, "old": "renders/none.png"}], out="review/x.png",
                      root=str(tmp_path))
    assert refused.value.code == "verdict.bad-member"
    assert "renders/none.png" in refused.value.message


def test_a_bare_path_is_read_as_the_picture_it_names(tmp_path):
    """§PW261: a family of paths is the commonest first guess at a member."""
    member(tmp_path, "citadel", DARK, old=False)
    found = verdict.sheet(["renders/citadel.png"], out="review/c.png", root=tmp_path)
    # Nothing measured it, so it neither passes nor fails: it is unheld (§PW338).
    assert found["members"] == [
        {"name": "citadel", "passed": None, "checked": False, "failed": []}
    ]
    assert found["choices"] == verdict.UNHELD_CHOICES


@pytest.mark.parametrize(
    ("members", "said"),
    [
        ([7], "member 0 is a int"),
        ([{"new": "renders/x.png"}], "member 0 has no name"),
        (["renders/x.png", {"name": "y"}], "member 1 has no new"),
    ],
)
def test_a_member_that_is_not_one_is_refused_with_its_index(tmp_path, members, said):
    with pytest.raises(PolyweaveError) as refused:
        verdict.sitting({"f": members}, out="review", root=tmp_path)
    assert refused.value.code == "verdict.bad-member"
    assert said in refused.value.message


def test_the_number_is_wrong_moves_the_bound_to_what_a_person_accepted(tmp_path):
    family = [member(tmp_path, "star_dim", BRIGHT), member(tmp_path, "star_gold", DARK)]
    run = loop.start("stars", "after", root=tmp_path)
    said = verdict.judge(
        family,
        "number",
        "same star at size",
        root=tmp_path,
        run=run,
        when="2026-09-24",
    )
    assert said["members"][0]["rewritten"] == ["no-hot-facet:max"]
    assert said["members"][1]["rewritten"] == []
    (p,) = accept.read(tmp_path / "accept" / "star_dim.accept.toml").predicates
    assert p.maximum >= p.origins["max"]["measured"] > 0.37
    assert p.origins["max"]["origin"] == "person"
    assert p.origins["max"]["date"] == "2026-09-24"
    assert p.origins["max"]["why"] == "same star at size"
    text = (tmp_path / "accept" / "star_dim.accept.toml").read_text(encoding="utf-8")
    assert "# what the star has to hold" in text
    # The star now passes the bound the person set, and both verdicts are in the run.
    again = verdict.sheet(family, out="review/again.png", root=tmp_path)
    assert all(one["passed"] for one in again["members"])
    assert [v["person_accepted"] for v in run["verdicts"]] == [True, True]
    assert run["verdicts"][0]["predicates"][0]["passed"] is False


def test_the_look_is_wrong_leaves_the_spec_and_blames_what_was_named(tmp_path):
    family = [member(tmp_path, "star_gold", DARK)]
    before = (tmp_path / "accept" / "star_gold.accept.toml").read_text(encoding="utf-8")
    run = loop.start("stars", "after", root=tmp_path)
    said = verdict.judge(
        family, "look", "too dull", root=tmp_path, run=run, named=["no-hot-facet"]
    )
    assert said["members"][0]["named"] == ["no-hot-facet"]
    after = (tmp_path / "accept" / "star_gold.accept.toml").read_text(encoding="utf-8")
    assert after == before
    loop.finish(run, root=tmp_path)
    (one,) = [b for b in loop.bounds(tmp_path) if b.get("id")]
    assert one["loose"] == [pytest.approx(0.133, abs=1e-3)]


def test_a_verdict_with_no_run_open_says_it_was_not_recorded(tmp_path):
    said = verdict.judge(
        [member(tmp_path, "star_gold", DARK)], "accept", "fine", root=tmp_path
    )
    assert said["ledger"].startswith("not recorded")


@pytest.mark.parametrize(
    ("choice", "why", "code"),
    [
        ("maybe", "hmm", "loop.unknown-choice"),
        ("accept", " ", "loop.no-reason"),
        ("number", "fine", "loop.no-failed-bound"),
    ],
)
def test_a_verdict_that_cannot_be_carried_is_refused(tmp_path, choice, why, code):
    family = [member(tmp_path, "star_gold", DARK)]
    with pytest.raises(PolyweaveError) as refused:
        verdict.judge(family, choice, why, root=tmp_path)
    assert refused.value.code == code


CONCEPT = """asset = "{name}"

[[predicate]]
id      = "near-painting"
measure = "luma_p99"
region  = "frame"
min     = {{ value = 0.1, origin = "measured", measured = 0.133 }}
max     = 0.9
"""


def test_a_person_s_target_is_written_past_the_look_and_fails_until_reached(tmp_path):
    """§PW620: a region far from its painting needs a goal a person set."""
    one = member(tmp_path, "board", DARK)
    spec = tmp_path / "accept" / "board.accept.toml"
    spec.write_text(CONCEPT.format(name="board"), encoding="utf-8")
    run = loop.start("board", "after", root=tmp_path)
    said = verdict.target([one], {"board": 0.4}, "closer to the painting",
                          root=tmp_path, run=run, when="2026-10-24")
    assert said["members"] == [{"name": "board", "written": ["near-painting:min"],
                                "targets": {"near-painting": {"min": 0.4}}}]
    (p,) = accept.read(spec).predicates
    assert (p.minimum, p.maximum) == (0.4, 0.9)
    assert p.origins["min"] == {
        "origin": "person", "measured": pytest.approx(0.133, abs=1e-3),
        "date": "2026-10-24", "why": "closer to the painting", "target": True}
    found = accept.check(accept.read(spec), tmp_path / one["new"], root=tmp_path)
    assert not found["passed"]
    assert "has not reached its min, a target a person set 2026-10-24" in (
        found["predicates"][0]["why"])
    assert [v["person_accepted"] for v in run["verdicts"]] == [False]


@pytest.mark.parametrize(
    ("byte", "targets", "said"),
    [
        (BRIGHT, {"no-hot-facet": 0.4}, "would loosen it"),
        (DARK, {"no-hot-facet": 0.5}, "has no min"),
        (DARK, {"star_gold": "dark"}, "a target is a number"),
        (DARK, {}, "no target was named"),
        (DARK, {"no-hot-facet": {"toward": 0.5}}, "declares no value where it is"),
        (DARK, {"no-hot-facet": {"toward": 2}}, "a share of the way"),
    ],
)
def test_a_target_that_is_no_bar_to_reach_is_refused(tmp_path, byte, targets, said):
    one = member(tmp_path, "star_gold", byte)
    before = (tmp_path / "accept" / "star_gold.accept.toml").read_text("utf-8")
    with pytest.raises(PolyweaveError) as refused:
        verdict.target([one], targets, "hmm", root=tmp_path)
    assert refused.value.code == "loop.bad-target"
    assert said in refused.value.message
    assert (tmp_path / "accept" / "star_gold.accept.toml").read_text("utf-8") == before


def test_a_target_naming_nothing_a_member_carries_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        verdict.target([member(tmp_path, "star_gold", DARK)], {"glow": 0.1}, "hmm",
                       root=tmp_path)
    assert refused.value.code == "loop.unknown-predicate"


def test_naming_a_predicate_no_member_carries_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        verdict.judge(
            [member(tmp_path, "star_gold", DARK)],
            "look",
            "dull",
            root=tmp_path,
            named=["no-hot-facets"],
        )
    assert refused.value.code == "loop.unknown-predicate"


def test_the_choices_fit_on_a_sheet_of_small_members(tmp_path):
    """§PW182: a sheet of narrow pictures cut its choice lines off at the edge."""
    from PIL import ImageDraw

    family = [member(tmp_path, "star_dim", BRIGHT, old=False)]
    found = verdict.sheet(family, out="review/small.png", root=tmp_path)
    with Image.open(found["sheet"]) as laid:
        width = laid.width
    pen = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    widest = max(pen.textlength(f"{w}: {m}") for w, m in verdict.CHOICES.items())
    assert width >= widest


def test_a_member_nothing_holds_is_unheld_not_passed(tmp_path):
    """§PW338: a screen with no spec read as held by a spec that agreed."""
    member(tmp_path, "citadel", DARK, old=False)
    plain = {"name": "citadel", "new": "renders/citadel.png"}
    found = verdict.sheet([plain], out="review/c.png", root=tmp_path)
    [said] = found["members"]
    assert said["passed"] is None and said["checked"] is False
    assert "the spec agrees" not in found["choices"]["accept"]
    assert "number" not in found["choices"]


def test_a_family_with_one_held_member_keeps_the_spec_choices(tmp_path):
    held = member(tmp_path, "star_gold", DARK)
    member(tmp_path, "citadel", DARK, old=False)
    plain = {"name": "citadel", "new": "renders/citadel.png"}
    found = verdict.sheet([held, plain], out="review/c.png", root=tmp_path)
    assert [one["checked"] for one in found["members"]] == [True, False]
    assert set(found["choices"]) == {"accept", "look", "number"}


def test_a_gates_own_refusal_still_fails_a_member_with_no_spec(tmp_path):
    member(tmp_path, "citadel", DARK, old=False)
    refused = {"name": "citadel", "new": "renders/citadel.png", "passed": False}
    [said] = verdict.sheet([refused], out="review/c.png", root=tmp_path)["members"]
    assert said["passed"] is False and said["checked"] is True
