"""A purchase ledger kept as a table by name, as an adopting project's lock is (§PW457).

Cottony points `[paths] purchases` at its Meshy lock, a JSON object keyed by asset name,
and reading it as a list answered its five keys where entries were meant.
"""

from __future__ import annotations

import json

import pytest

from polyweave import purchase
from polyweave.errors import PolyweaveError

LOCK = {
    "booster_hammer": {
        "consumed_credits": 30,
        "credits_measured": 30,
        "finished_at": 1789659976551,
        "image": "tools/art/3d/booster_hammer.drawn.png",
        "mesh": "tools/art/3d/booster_hammer.glb",
        "mesh_bytes": 8184632,
        "mesh_sha256": "72" * 32,
        "request": {"ai_model": "meshy-7", "texture_prompt": "a candy mallet"},
        "task_id": "01a0b009",
    },
    "mascot": {
        "consumed_credits": 20,
        "mesh": "tools/art/3d/mascot.glb",
        "mesh_sha256": "ab" * 32,
        "task_id": "01a0b00a",
    },
}


def lock(tmp_path, held):
    (tmp_path / "polyweave.toml").write_text(
        '[paths]\npurchases = "tools/art/3d/meshy.lock.json"\n', encoding="utf-8")
    where = tmp_path / "tools" / "art" / "3d"
    where.mkdir(parents=True)
    (where / "meshy.lock.json").write_text(json.dumps(held), encoding="utf-8")
    return tmp_path


def test_a_ledger_by_name_reads_as_one_entry_per_name(tmp_path):
    held = purchase.read(lock(tmp_path, LOCK))
    assert [one["name"] for one in held] == ["booster_hammer", "mascot"]
    hammer = held[0]
    assert hammer["artefact"] == "tools/art/3d/booster_hammer.glb"
    assert hammer["sha256"] == "72" * 32 and hammer["task_id"] == "01a0b009"
    assert hammer["credits"] == 30.0 and hammer["measured"] is True
    assert hammer["adopted"] is True
    assert hammer["at"].startswith("2026-") and hammer["at"].endswith("Z")
    assert held[1]["credits"] == 20.0 and held[1]["measured"] is False


def test_an_adopted_ledger_charges_no_ceiling(tmp_path):
    assert purchase.spent(lock(tmp_path, LOCK)) == 0.0


def test_a_ledger_by_name_is_not_rewritten_by_a_buy(tmp_path):
    root = lock(tmp_path, LOCK)
    with pytest.raises(PolyweaveError) as refused:
        purchase.capture(b"glTF" + b"\x00" * 60, out="a.glb", task_id="t1", credits=1,
                         root=root)
    assert refused.value.code == "fetch.ledger-by-name"
    held = json.loads((root / "tools/art/3d/meshy.lock.json").read_text("utf-8"))
    assert held == LOCK


@pytest.mark.parametrize("shape", ['"a bare string"', "12", '{"mascot": "a name"}'])
def test_a_ledger_in_neither_shape_is_refused(tmp_path, shape):
    root = lock(tmp_path, {})
    (root / "tools/art/3d/meshy.lock.json").write_text(shape, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        purchase.read(root)
    assert refused.value.code == "fetch.ledger-malformed"
    assert "keyed by name" in refused.value.as_dict()["remedy"]
