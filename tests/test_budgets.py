"""A ceiling on the reads every session makes (§PW129).

`describe()` and `capabilities()` are read at the start of a session, so their size is
paid on every one, and each operation registered makes them longer. Each ceiling here is
what was measured when it was set, plus headroom sized to the smallest regression it
has to catch: one more operation of average size, about 630 characters, fails, and a
typo fix does not. A raise is argued beside the number, never made silently.

Characters, not tokens: at the usual four characters a token, 47,500 is about 12,000.
The table prints on a green run too (`pytest -s`), because a figure seen only when the
build breaks goes stale.
"""

from __future__ import annotations

import argparse
import json

import pytest

from polyweave import commands, config, describe, errors, search
from polyweave.accept import Spec
from polyweave.capabilities import capabilities
from polyweave.errors import PolyweaveError

#: describe(): 74 operations measured 46,946. One more average operation is ~630.
#: Raised for asset.brief (§PW131), which took 435 and left 19: 75 measure 47,381.
DESCRIBE = 47_800
#: capabilities(probe=False), which carries describe() and the codes: 54,155, then
#: 54,590 with asset.brief (§PW131).
CAPABILITIES = 55_000
#: The largest refusal: an unknown code, its `allowed` cut to 40 names, 1,154.
ERROR = 1_400
#: One verb's `--help`: render.bake's thirty parameters, 3,847.
HELP_VERB = 4_000
#: The top-level `--help`, naming every verb: 11,346. One more verb line is ~150.
HELP_TOP = 11_600
#: A search's answer over its default budget of 24 samples: 3,739.
SEARCH = 4_000


def _size(value) -> int:
    return len(json.dumps(value, default=str))


def _largest_error() -> int:
    found = 0
    for refuse in (
        lambda: errors.explain("spec.unkown-measure"),
        lambda: config.load(".").get("render.nope"),
    ):
        with pytest.raises(PolyweaveError) as refused:
            refuse()
        found = max(found, _size(refused.value.as_dict()))
    return found


def _helps() -> tuple[int, int]:
    parser = argparse.ArgumentParser(prog="python -m polyweave")
    verbs = parser.add_subparsers(dest="command")
    commands.add_operations(verbs)
    widest = max(len(one.format_help()) for one in verbs.choices.values())
    return widest, len(parser.format_help())


def _search() -> int:
    spec = Spec(
        asset="star",
        rung=None,
        predicates=(),
        search={"exposure": {"min": -1, "max": 1}, "key": {"min": 100, "max": 900}},
    )

    def evaluate(values):
        return {
            "passed": False,
            "score": 0.5,
            "predicates": [
                {"id": "tone", "value": 0.4, "margin": 0.5, "passed": False}
            ],
            "failed": ["tone"],
        }

    return _size(search.search(spec, evaluate, budget=search.BUDGET))


def test_every_session_read_stays_under_its_ceiling(capsys):
    widest, top = _helps()
    measured = {
        "describe()": (_size(describe.describe()), DESCRIBE),
        "capabilities(probe=False)": (_size(capabilities(probe=False)), CAPABILITIES),
        "largest refusal": (_largest_error(), ERROR),
        "widest verb --help": (widest, HELP_VERB),
        "top-level --help": (top, HELP_TOP),
        "search answer, 24 samples": (_search(), SEARCH),
    }
    with capsys.disabled():
        print("\nread                          chars   ceiling")
        for name, (size, ceiling) in measured.items():
            print(f"{name:<28} {size:>7} {ceiling:>9}")
    over = {name: v for name, v in measured.items() if v[0] > v[1]}
    assert not over, f"over budget: {over}; argue a raise beside the constant"


def test_a_long_allowed_list_is_cut_to_the_nearest_names():
    with pytest.raises(PolyweaveError) as refused:
        errors.explain("spec.unkown-measure")
    wire = refused.value.as_dict()
    assert len(wire["allowed"]) == errors.ALLOWED_CAP
    assert wire["allowed_total"] > errors.ALLOWED_CAP
    assert wire["did_you_mean"] == "spec.unknown-measure"
    assert "spec.unknown-measure" in wire["allowed"]
