"""Graphics presets found by search, the best look that fits each budget (§PW367).

The grid and the choice run anywhere; a search needs $GODOT and a route that draws.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers import kits
from polyweave.layers.engine import offscreen, presets


def test_an_upscaler_is_tried_only_below_full_scale():
    found = presets.combinations({"scale": [1.0, 0.5], "scaler": ["bilinear", "fsr"]})
    assert found == [{"scale": 1.0, "scaler": "bilinear"},
                     {"scale": 0.5, "scaler": "bilinear"},
                     {"scale": 0.5, "scaler": "fsr"}]


RUNS = [
    {"settings": {"scale": 1.0}, "p95_ms": 12.0, "loss": 0.0, "shot": "a.png"},
    {"settings": {"scale": 0.75}, "p95_ms": 8.0, "loss": 0.02, "shot": "b.png"},
    {"settings": {"scale": 0.5}, "p95_ms": 5.0, "loss": 0.09, "shot": "c.png"},
]


def test_each_preset_takes_the_least_loss_that_fits_and_lossy_ones_go_to_a_person():
    chosen, lossy = presets.choose(RUNS, {"ultra": 20, "high": 10, "low": 6, "none": 1})
    assert chosen["ultra"]["settings"] == {"scale": 1.0}
    assert chosen["high"]["settings"] == {"scale": 0.75}
    assert chosen["low"]["settings"] == {"scale": 0.5}
    assert chosen["none"] == {"budget_ms": 1.0, "fits": False, "cheapest_ms": 5.0}
    assert [one["name"] for one in lossy] == ["high", "low"]


def test_a_search_with_no_budget_is_refused_by_name(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        presets.preset_search("res://main.tscn", budgets={}, root=str(tmp_path))
    assert caught.value.code == "engine.no-budget"


def test_a_machine_with_nothing_that_draws_is_skipped_and_said(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")

    def nothing(*_, **__):
        raise PolyweaveError("engine.no-offscreen-route",
                             "no route draws real pixels on this machine", "use one")

    monkeypatch.setattr(offscreen, "route_for", nothing)
    found = presets.preset_search("res://main.tscn", budgets={"low": 33},
                                  root=str(tmp_path))
    assert found["ok"] is None
    assert "no route draws" in found["skipped"]


def test_the_sheet_of_lossy_presets_is_named_in_the_answer(tmp_path, monkeypatch):
    """§PW677: the sheet was written and the answer's `sheet` was always null."""
    from types import SimpleNamespace

    from PIL import Image

    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(offscreen, "route_for",
                        lambda *_, **__: SimpleNamespace(name="stub"))

    def captured(script, *, args, **how):
        said = dict(arg.split("=", 1) for arg in args if "=" in arg)
        scale = float(json.loads(said["settings"])["scale"])
        Image.new("RGB", (32, 32), (int(200 * scale), 40, 40)).save(said["shot"])
        log = tmp_path / f"run-{scale}.log"
        log.write_text(f"PRESET p95_ms={10.0 * scale} p99_ms={12.0 * scale}\n",
                       encoding="utf-8")
        return {"log": str(log)}

    monkeypatch.setattr(offscreen, "capture", captured)
    found = presets.preset_search("res://main.tscn", budgets={"low": 6.0},
                                  grid={"scale": [1.0, 0.5]}, root=str(tmp_path))
    assert found["sheet"] and (tmp_path / found["sheet"]).is_file()
    assert not found["sheet"].startswith(str(tmp_path))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_search_runs_every_combination_and_prices_each_feature(tmp_path):
    try:
        offscreen.route_for(tmp_path)
    except PolyweaveError as refused:
        pytest.skip(refused.message)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "graphics" / "fixture", game)
    (game / "polyweave.toml").write_text("", encoding="utf-8")
    found = presets.preset_search(
        "res://main.tscn", budgets={"any": 1000, "never": 0.0001},
        grid={"scale": [1.0, 0.5], "msaa": [4, 0]}, frames=30, root=str(game))
    assert found["runs"] == 4
    assert found["reference"]["settings"] == {"scale": 1.0, "msaa": 4}
    assert found["presets"]["any"]["fits"] is True
    assert found["presets"]["never"]["fits"] is False
    assert set(found["costs_ms"]) == {"scale", "msaa"}
    assert found["dearest"] in ("scale", "msaa")
