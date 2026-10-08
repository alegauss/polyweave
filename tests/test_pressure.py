"""A wave timeline's threat per second, from events the game writes (§PW330).

The timelines are small enough to work out by hand: what enters, what is alive when
every enemy dies as it lands and when none dies before its wave ends, and the gaps.
"""

from __future__ import annotations

import json

import pytest

from polyweave import pressure, provenance
from polyweave.errors import PolyweaveError

#: Two drones at 0 s in a wave ending at 4 s, a heavy at 1.5 s ending at 3 s, and a
#: lone drone at 9 s ending at 10 s.
WAVES = [
    {"second": 0, "kind": "drone", "weight": 1, "until": 4},
    {"second": 0, "kind": "drone", "weight": 1, "until": 4},
    {"second": 1.5, "kind": "heavy", "weight": 3, "until": 3},
    {"second": 9, "kind": "drone", "weight": 1, "until": 10},
]


def test_threat_enters_and_lives_in_both_bounding_cases(tmp_path):
    said = pressure.pressure(WAVES, warp=1.0, root=str(tmp_path))
    assert said["seconds"] == 10
    assert said["entering"][:3] == [2.0, 3.0, 0.0]
    # Nothing killed: both drones all of 0-4 s, the heavy from 1.5 s to 3 s.
    assert said["alive_slow"][:5] == [2.0, 3.5, 5.0, 2.0, 0.0]
    # Killed as they land, one second after spawning.
    assert said["alive_fast"][:3] == [2.0, 1.5, 1.5]
    assert said["total"] == 6.0 and said["peak_slow"] == 5.0


def test_the_gaps_with_nothing_to_shoot_are_named_past_the_window(tmp_path):
    said = pressure.pressure(WAVES, warp=1.0, window=2.5, root=str(tmp_path))
    assert said["gaps"] == [[1.0, 1.5], [2.5, 9.0]]
    assert said["longest_gap"] == 6.5
    assert said["past_window"] == [[2.5, 9.0]]


def test_a_change_is_read_beside_the_timeline_before_it(tmp_path):
    (tmp_path / "before.json").write_text(json.dumps(WAVES), encoding="utf-8")
    filled = WAVES + [{"second": 5, "kind": "drone", "weight": 1, "until": 7}]
    (tmp_path / "after.json").write_text(json.dumps({"events": filled}), "utf-8")
    said = pressure.pressure(file="after.json", compare_file="before.json", warp=1.0,
                             out="pressure/phase1.json", root=str(tmp_path))
    assert said["change"] == {"total": 1.0, "peak_slow": 0.0, "longest_gap": -3.5}
    record = provenance.read(said["out"], root=tmp_path)
    assert [one["role"] for one in record["inputs"]] == ["events", "events"]


@pytest.mark.parametrize("events", [
    [],
    [{"kind": "drone"}],
    [{"second": 3, "until": 1}],
])
def test_a_timeline_that_cannot_be_read_is_refused(tmp_path, events):
    with pytest.raises(PolyweaveError) as refused:
        pressure.pressure(events, root=str(tmp_path))
    assert refused.value.code == "spec.no-targets"
