"""One sheet to look at, one call to answer it (§PW109)."""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import accept, loop, verdict
from polyweave.errors import PolyweaveError

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
