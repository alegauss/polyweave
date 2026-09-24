"""What a side did not measure, said as data (§PW116)."""

from __future__ import annotations

import pytest

from polyweave import loop
from polyweave.errors import PolyweaveError


def made(tmp_path, way, *, seconds, unmeasured=(), renders=0, overruled=False):
    run = loop.start("star", way, root=tmp_path, unmeasured=unmeasured)
    loop.spent(run, seconds=seconds, renders=renders)
    loop.judged(run, tool_passed=True, person_accepted=not overruled)
    return loop.finish(run, root=tmp_path)


def test_a_side_whose_hand_search_was_never_timed_decides_no_speed(tmp_path):
    """The stars: a 3.3 s re-bake, beside the afternoon that nobody timed."""
    made(tmp_path, "before", seconds=3.3, unmeasured=["seconds"])
    made(tmp_path, "after", seconds=8.6)
    found = loop.compare("star", root=tmp_path)
    assert found["unmeasured"] == {"before": ["seconds"], "after": []}
    assert found["verdict"].startswith("inconclusive")
    assert "not reduced" not in found["verdict"]


def test_overruling_still_stands_on_a_partial_side(tmp_path):
    made(tmp_path, "before", seconds=3.3, unmeasured=["seconds"])
    made(tmp_path, "after", seconds=8.6, overruled=True)
    verdict = loop.compare("star", root=tmp_path)["verdict"]
    assert "overruled the tool 1 times" in verdict


def test_a_cost_nobody_counted_cannot_be_said_to_have_moved(tmp_path):
    made(tmp_path, "before", seconds=600, unmeasured=["renders"])
    made(tmp_path, "after", seconds=60, renders=24)
    verdict = loop.compare("star", root=tmp_path)["verdict"]
    assert "went up" not in verdict
    assert "renders went unmeasured on a side" in verdict


def test_only_a_cost_the_ledger_records_can_be_unmeasured(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        loop.start("star", "before", root=tmp_path, unmeasured=["patience"])
    assert refused.value.code == "loop.unknown-measure"
