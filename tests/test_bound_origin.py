"""A bound that says where its number came from (§PW106)."""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import accept
from polyweave.errors import PolyweaveError


def spec(bound):
    return accept.parse(
        {
            "asset": "star_dim",
            "predicate": [
                {
                    "id": "no-hot-facet",
                    "measure": "luma_p99",
                    "region": "frame",
                    "max": bound,
                }
            ],
        }
    )


#: Flat greys by the byte they are drawn in. Luma is measured linear, so byte 200 reads
#: 0.578 and byte 102 reads 0.133: one well over a ceiling of 0.37 and one well under.
BRIGHT, DARK = 200, 102


def grey(tmp_path, byte):
    """A flat picture in one grey, so every luma statistic of it is the same."""
    Image.new("RGBA", (16, 16), (byte, byte, byte, 255)).save(tmp_path / "grey.png")
    return tmp_path / "grey.png"


def test_a_bare_number_is_still_a_bound():
    p = spec(0.37).predicates[0]
    assert p.maximum == 0.37
    assert p.origins == {}


def test_a_bound_can_say_it_is_a_margin_over_what_was_measured():
    p = spec({"value": 0.37, "origin": "margin", "measured": 0.3438}).predicates[0]
    assert p.maximum == 0.37
    assert p.origins == {"max": {"origin": "margin", "measured": 0.3438}}
    assert p.as_dict()["max"] == {"value": 0.37, "origin": "margin", "measured": 0.3438}


@pytest.mark.parametrize(
    ("bound", "code"),
    [
        ({"value": 0.37, "origin": "hunch"}, "spec.bad-origin"),
        ({"value": 0.37}, "spec.bad-origin"),
        ({"value": 0.37, "origin": "person", "who": "me"}, "spec.unknown-field"),
        ({"origin": "person"}, "spec.bad-bound"),
    ],
)
def test_a_bound_that_cannot_say_where_it_came_from_is_refused(bound, code):
    with pytest.raises(PolyweaveError) as refused:
        spec(bound)
    assert refused.value.code == code


def test_a_miss_on_a_margin_says_the_number_may_be_wrong(tmp_path):
    guessed = spec({"value": 0.37, "origin": "margin", "measured": 0.3438})
    found = accept.check(guessed, grey(tmp_path, BRIGHT), root=tmp_path)
    result = found["predicates"][0]
    assert not found["passed"]
    assert result["bound"] == {"side": "max", "origin": "margin", "measured": 0.3438}
    assert "a margin put by hand over the measured 0.3438" in result["why"]
    assert "the number may be what is wrong" in result["why"]
    assert found["guessed"] == ["no-hot-facet"]


def test_a_miss_on_a_persons_bound_says_the_look_moved(tmp_path):
    agreed = spec({"value": 0.37, "origin": "person", "date": "2026-09-24"})
    found = accept.check(agreed, grey(tmp_path, BRIGHT), root=tmp_path)
    assert (
        "a person agreed on 2026-09-24: the look moved" in found["predicates"][0]["why"]
    )
    assert found["guessed"] == []


def test_a_pass_names_its_bound_and_says_nothing_else(tmp_path):
    agreed = spec({"value": 0.41, "origin": "person", "date": "2026-09-24"})
    found = accept.check(agreed, grey(tmp_path, DARK), root=tmp_path)
    result = found["predicates"][0]
    assert found["passed"]
    assert result["bound"]["origin"] == "person"
    assert "why" not in result
