"""The claim is about the second change, not the first bake (§PW114)."""

from __future__ import annotations

import pytest

from polyweave import loop
from polyweave.errors import PolyweaveError


def made(tmp_path, way, *, seconds, change=None, person_minutes=0.0, renders=0):
    run = loop.start("star", way, root=tmp_path, change=change)
    loop.spent(run, seconds=seconds, person_minutes=person_minutes, renders=renders)
    loop.judged(run, tool_passed=True, person_accepted=True)
    return loop.finish(run, root=tmp_path)


def ported(tmp_path):
    """The stars as the ledger saw them: a re-bake beats a search on the first port."""
    made(tmp_path, "before", seconds=3.3)
    made(tmp_path, "after", seconds=8.6)


def test_a_change_to_an_asset_not_yet_ported_is_refused(tmp_path):
    made(tmp_path, "before", seconds=3.3)
    with pytest.raises(PolyweaveError) as refused:
        loop.start("star", "before", root=tmp_path, change="palette hue")
    assert refused.value.code == "loop.not-ported"


def test_a_change_is_compared_on_its_own_runs(tmp_path):
    ported(tmp_path)
    made(tmp_path, "before", seconds=5400.0, change="palette hue", person_minutes=90)
    made(tmp_path, "after", seconds=40.0, change="palette hue", renders=24)
    first = loop.compare("star", root=tmp_path)
    assert first["event"] == "the first port"
    assert "not reduced" in first["verdict"]
    after_hue = loop.compare("star", root=tmp_path, change="palette hue")
    assert after_hue["event"] == "after palette hue"
    assert after_hue["before"]["person_minutes"] == 90
    assert after_hue["changed"]["person_minutes"]["delta"] == -90
    assert "faster" in after_hue["verdict"]
    assert after_hue["changes"] == ["palette hue"]


def test_a_change_whose_baseline_came_second_is_refused(tmp_path):
    ported(tmp_path)
    made(tmp_path, "after", seconds=40.0, change="samples")
    with pytest.raises(PolyweaveError) as refused:
        loop.start("star", "before", root=tmp_path, change="samples")
    assert refused.value.code == "loop.baseline-too-late"
    assert "after 'samples'" in refused.value.message


def test_a_baseline_for_another_change_is_still_fine(tmp_path):
    ported(tmp_path)
    made(tmp_path, "after", seconds=40.0, change="samples")
    assert loop.start("star", "before", root=tmp_path, change="blender 5.3")


def test_a_person_spending_more_is_a_cost_that_moved(tmp_path):
    ported(tmp_path)
    made(tmp_path, "before", seconds=600.0, change="hue", person_minutes=5)
    made(tmp_path, "after", seconds=60.0, change="hue", person_minutes=8)
    found = loop.compare("star", root=tmp_path, change="hue")
    assert "person_minutes went up" in found["verdict"]


def test_a_change_with_one_side_is_not_a_measurement(tmp_path):
    ported(tmp_path)
    made(tmp_path, "before", seconds=600.0, change="hue")
    with pytest.raises(PolyweaveError) as refused:
        loop.compare("star", root=tmp_path, change="hue")
    assert refused.value.code == "loop.nothing-to-compare"
    assert "after 'hue'" in refused.value.message
