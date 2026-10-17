"""The worlds offered on one tier of a route, held level (§PW385).

Spinhold made its shift a chart of worlds, tiers in order and a choice of worlds on
each, and one arcade score table is only fair while every world on a tier is worth the
same threat and saves the same number of Holders. It checked that in its own
dev/pressure.gd; this is the check made once.
"""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import pressure


def world(threat, holders, start=0.0):
    events = [{"second": start + i, "kind": "lander", "weight": threat / 4, "until": 30}
              for i in range(4)]
    events += [{"second": start + 10 + i, "kind": "gleaner", "weight": 0.0, "until": 30}
               for i in range(holders)]
    return events


def test_a_tier_whose_worlds_match_is_level():
    found = pressure.level([{"city": world(20, 3)}, {"quilt": world(20, 3),
                                                     "waist": world(21, 3)}],
                           count="gleaner")
    assert found["level"] is True
    assert found["tiers"][1]["worlds"]["waist"]["off_by"] == pytest.approx(0.05)
    assert found["tiers"][1]["worlds"]["quilt"]["count"] == 3


def test_a_world_off_the_band_or_saving_another_count_is_named():
    found = pressure.level([{"quilt": world(20, 3), "waist": world(26, 2)}],
                           count="gleaner", band=0.1)
    assert found["level"] is False
    what = {one["what"]: one for one in found["unlevel"]}
    assert what["threat"]["world"] == "waist"
    assert what["threat"]["off_by"] == pytest.approx(0.3)
    assert (what["gleaner"]["count"], what["gleaner"]["reference_count"]) == (2, 3)


def test_strict_refuses_as_a_gate_naming_the_world_and_the_share(tmp_path):
    (tmp_path / "waves").mkdir()
    (tmp_path / "waves" / "quilt.json").write_text(json.dumps(world(20, 3)),
                                                   encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        pressure.level([{"quilt": "waves/quilt.json", "waist": world(30, 3)}],
                       strict=True, root=str(tmp_path))
    assert refused.value.code == "spec.unlevel-tier"
    assert "waist totals 30" in refused.value.message
    assert "50% off a band of 10%" in refused.value.message


def test_tiers_that_are_not_tiers_are_refused():
    with pytest.raises(PolyweaveError) as refused:
        pressure.level([[]])
    assert refused.value.code == "spec.no-targets"
