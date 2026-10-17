"""What the records say polyweave did, per asset and in total (§PW444).

A read, never an estimate: each figure is a sum over a file the project keeps, and
names that file.
"""

from __future__ import annotations

import json

from polyweave.loop import loop


def made(tmp_path, asset, way, *, renders, seconds, credits=0, passed=True,
         accepted=True):
    one = loop.start(asset, way, root=tmp_path)
    loop.spent(one, renders=renders, seconds=seconds, credits=credits, calls=1,
               root=tmp_path)
    loop.judged(one, tool_passed=passed, person_accepted=accepted, why="looked",
                root=tmp_path)
    return loop.finish(one, root=tmp_path)


def test_each_asset_s_ways_and_verdicts_are_totalled_and_named_by_their_file(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    made(tmp_path, "tray", "before", renders=4, seconds=120.0)
    made(tmp_path, "tray", "after", renders=9, seconds=30.0, credits=2, passed=False)
    made(tmp_path, "stars", "after", renders=28, seconds=8.6)
    said = loop.report(root=str(tmp_path))
    tray = next(one for one in said["assets"] if one["asset"] == "tray")
    assert tray["ways"]["after"]["made"]["renders"] == 9
    assert tray["ways"]["after"]["made"]["rounds"] == 1
    # The tool refused what the person accepted: one overruling verdict.
    assert tray["ways"]["after"]["verdicts"] == {"given": 1, "accepted": 1,
                                                 "overruled": 1}
    assert tray["compare"]["seconds"]["delta"] == -90.0
    assert tray["compare"]["renders"]["times"] == 2.25
    stars = next(one for one in said["assets"] if one["asset"] == "stars")
    # One way only: nothing is compared, rather than compared against a guess.
    assert "compare" not in stars and "before" not in stars["ways"]
    assert said["totals"]["renders"] == 41
    ledger = json.loads((tmp_path / said["totals"]["from"]).read_text("utf-8"))
    assert len(ledger["runs"]) == 3
    # Nothing was bought or gated, so neither is said.
    assert "bought" not in said and "gate" not in said


def test_a_project_with_no_records_reports_nothing_and_says_so(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    said = loop.report(root=str(tmp_path))
    assert said["assets"] == [] and said["totals"]["runs"] == 0
