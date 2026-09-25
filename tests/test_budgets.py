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
#: Raised for measure.digest (§PW141), a bake's two hashes readable off any picture
#: by path: 48,154, with headroom under one more operation. Then 48,709 with cost.read
#: (§PW143) and port.run's `fresh` (§PW144), 49,694 with motion.bake (§PW160).
#: 50,895 with `service` on six purchase and schema operations (§PW162): no operation
#: was added, and a call that has to name its balance cannot do it without the field.
#: 52,311 with picture.buy (§PW163), a whole paid call and so wider than the average,
#: then 53,672 with purchase.reconcile (§PW164) and picture.describe (§PW165),
#: then 54,332 with style.read and picture.buy's `family` (§PW166), then 55,585
#: with style.drift (§PW167) and picture.gate (§PW168), 56,301 with picture.letters
#: (§PW169), 58,365 with picture.vary and picture.against_parent (§PW170), 59,062
#: with picture.fit (§PW171), 60,557 with verdict.answers (§PW173) and
#: shape.turntable (§PW176).
DESCRIBE = 61_200
#: capabilities(probe=False), which carries describe() and the codes: 54,155, then
#: 54,590 with asset.brief (§PW131), then 55,225 with measure.digest (§PW141), then
#: 55,803 with cost.read, its code and `fresh` (§PW143, §PW144), then 56,825 with
#: motion.bake and rig.no-mesh (§PW160), then 58,501 with `service`, its three
#: refusals and the per-service keys and ceilings (§PW162), then 60,039 with
#: picture.buy and its five refusals (§PW163), then 61,418 with reconcile, describe,
#: fetch.unpriced and fetch.seed-unproved (§PW164, §PW165), then 62,247 with
#: style.read and the style area's four codes (§PW166), then 62,817 with style.drift
#: and style.no-subject (§PW167), then 63,520 with picture.gate (§PW168), then
#: 64,354 with picture.letters, the OCR probe and fetch.ocr-failed (§PW169), then
#: 66,456 with picture.vary, picture.against_parent and their two codes (§PW170),
#: then 67,153 with picture.fit (§PW171), then 68,672 with verdict.answers,
#: loop.unknown-sitting and shape.turntable (§PW173, §PW176).
CAPABILITIES = 69_300
#: The largest refusal: an unknown code, its `allowed` cut to 40 names, 1,154.
ERROR = 1_400
#: One verb's `--help`: render.bake's thirty parameters, 3,847.
HELP_VERB = 4_000
#: The top-level `--help`, naming every verb: 11,346. One more verb line is ~150.
#: 11,792 once measure.digest is a verb (§PW141), 11,933 with cost.read (§PW143),
#: 12,066 with motion.bake (§PW160), 12,216 with sound.measure (§PW113), 12,385
#: with picture.buy (§PW163), 12,712 with purchase.reconcile and picture.describe
#: (§PW164, §PW165), 13,013 with style.read and style.drift (§PW166, §PW167), 13,327
#: with picture.gate and picture.letters (§PW168, §PW169), 13,664 with picture.vary
#: and picture.against_parent (§PW170), 13,968 with picture.fit, the review verb and
#: verdict.answers (§PW171, §PW172, §PW173).
HELP_TOP = 14_300
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
