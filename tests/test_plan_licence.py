"""The licence a plan grants, kept for every paid service (§PW448).

A generator's licence depends on the plan the key belongs to: Tripo's free tier and
ElevenLabs' free plan are non-commercial. The plan is kept on the record by the one call
every buy goes through, so a new adapter cannot forget it, and a sold game's release
check refuses a part its plan does not license.
"""

from __future__ import annotations

from polyweave import provenance, purchase
from polyweave.driving import release_checked

GLTF = b"glTF" + b"\x00" * 60

TRIPO = """[project]
sells = {sells}

[service.tripo]
base = "https://api.tripo3d.ai"
key_env = "TRIPO_API_KEY"
plan = "{plan}"
"""


def bought(tmp_path, *, plan="free", sells="true", engine=None):
    (tmp_path / "polyweave.toml").write_text(TRIPO.format(plan=plan, sells=sells),
                                             encoding="utf-8")
    purchase.capture(GLTF, out="art/drone.glb", task_id="tripo:t1", credits=20,
                     engine=engine or {"name": "tripo", "model": "v3.0"},
                     service="tripo", root=tmp_path)
    return provenance.read("art/drone.glb", tmp_path)


def test_the_declared_plan_is_kept_on_the_record(tmp_path):
    engine = bought(tmp_path)["engine"]
    assert engine["plan"] == "free" and engine["commercial"] is False
    assert bought(tmp_path, plan="pro")["engine"]["commercial"] is True


def test_a_plan_the_service_reported_wins_over_the_declared_one(tmp_path):
    engine = bought(tmp_path, plan="pro",
                    engine={"name": "tripo", "model": "v3.0", "tier": "free"})["engine"]
    assert engine["plan"] == "free" and engine["commercial"] is False


def test_an_unstated_plan_says_nothing_it_does_not_know(tmp_path):
    engine = bought(tmp_path, plan="")["engine"]
    assert "plan" not in engine and "commercial" not in engine
    assert release_checked(root=str(tmp_path))["ok"]


def test_a_sold_game_refuses_a_part_its_plan_licenses_non_commercially(tmp_path):
    bought(tmp_path)
    said = release_checked(root=str(tmp_path))
    assert not said["ok"]
    found = said["findings"][0]
    assert found["code"] == "game.part-not-licensed"
    assert found["at"] == "art/drone.glb"
    assert "tripo" in found["why"] and "free" in found["why"]
    assert provenance.credits(root=str(tmp_path))["non_commercial"] == [
        {"file": "art/drone.glb", "service": "tripo", "tier": "free"}]


def test_a_game_given_away_ships_it(tmp_path):
    bought(tmp_path, sells="false")
    assert release_checked(root=str(tmp_path))["ok"]
