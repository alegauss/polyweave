"""A picture bought from a model trained on the family's canon (§PW450).

Scenario is stood in for by a fake answering its v1 routes, so nothing is spent: the
test is that training and drawing go through the ceiling, the ledger and the record
like any purchase, and that a member admitted after training reads as outdated.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import picture, scenario, style
from polyweave.services import purchase
from polyweave.services import scenario as scenario_adapter
from polyweave.services import service as S

PROJECT = """[style.heroes]
canon = "art/canon/heroes"

[service.scenario]
base = "https://api.cloud.scenario.com"
key_env = "SCENARIO_TEST_KEY"
prices = { "flux.2-dev-lora:train" = 5.0, "flux.2-dev-lora" = 0.2 }

[budget.scenario]
amount = 20.0
unit = "USD"
expires = "2099-12-31"
"""


def png(colour) -> bytes:
    held = io.BytesIO()
    Image.new("RGBA", (32, 32), colour).save(held, format="PNG")
    return held.getvalue()


class Fake:
    """Scenario's routes as the docs give them, answering at once."""

    def __init__(self):
        self.sent: list[tuple[str, str, dict | None]] = []
        self.status = "trained"

    def __call__(self, method, url, key, body=None):
        assert key == "k:s"
        path = url.split("/v1/", 1)[1]
        self.sent.append((method, path, body))
        if method == "POST" and path == "models":
            return 200, {"model": {"id": "model_1", "status": "draft"}}
        if path.startswith("models/model_1/training-images"):
            return 200, {"trainingImage": {"id": "t"}}
        if path == "models/model_1/train":
            return 200, {"model": {"status": "training"}, "job": {"jobId": "job_t"}}
        if path == "models/model_1":
            return 200, {"model": {"id": "model_1", "status": self.status}}
        if path.startswith("generate/custom/model_1"):
            return 200, {"job": {"jobId": "job_1", "status": "queued"}}
        if path == "jobs/job_1":
            return 200, {"job": {"status": "success",
                                 "metadata": {"assetIds": ["asset_1"]}}}
        if path == "assets/asset_1":
            return 200, {"asset": {"url": "https://cdn.example/asset_1.png"}}
        return 404, {"error": path}


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("SCENARIO_TEST_KEY", "k:s")
    fake = Fake()
    monkeypatch.setattr(scenario_adapter, "call", fake)
    monkeypatch.setattr(scenario_adapter, "POLL_EVERY", 0.0)
    monkeypatch.setattr(S, "download", lambda link: png((200, 40, 40, 255)))
    (tmp_path / "studies").mkdir()
    for index in range(5):
        study = tmp_path / "studies" / f"hero_{index}.png"
        study.write_bytes(png((180 + index, 30, 30, 255)))
        style.admit(f"studies/hero_{index}.png", family="heroes", why="on model",
                    choice="accept", root=tmp_path)
    return tmp_path, fake


def test_the_canon_trains_a_model_within_the_ceiling(project):
    root, fake = project
    said = scenario.train(family="heroes", root=str(root))
    assert said["model"] == "model_1" and said["members"] == 5
    sent = [(m, p) for m, p, _ in fake.sent]
    assert sent[0] == ("POST", "models")
    assert sent.count(("POST", "models/model_1/training-images")) == 5
    assert ("PUT", "models/model_1/train") in sent
    assert fake.sent[1][2]["data"].startswith("data:image/png;base64,")
    trained = root / "art/canon/heroes/scenario.model.json"
    kept = json.loads(trained.read_text("utf-8"))
    assert kept["model"] == "model_1" and len(kept["members"]) == 5
    assert purchase.spent(root, service="scenario") == 5.0


def test_a_picture_drawn_from_it_names_the_model_and_its_members(project):
    root, _ = project
    scenario.train(family="heroes", root=str(root))
    entry = picture.buy(out="art/hero_new.png", prompt="the hero, waving",
                        family="heroes", service="scenario", root=str(root))
    assert entry["task_id"] == "scenario:job_1"
    record = provenance.read("art/hero_new.png", root)
    assert record["details"]["model"] == "model_1"
    assert len(record["details"]["members"]) == 5
    assert record["inputs"][0]["role"] == "model"
    assert purchase.spent(root, service="scenario") == 5.2
    assert "outdated" not in entry


def test_a_member_admitted_after_training_reads_as_outdated(project):
    root, _ = project
    scenario.train(family="heroes", root=str(root))
    late = root / "studies" / "hero_late.png"
    late.write_bytes(png((10, 200, 10, 255)))
    style.admit("studies/hero_late.png", family="heroes", why="joined later",
                choice="accept", root=root)
    entry = picture.buy(out="art/hero_two.png", prompt="the hero, running",
                        family="heroes", service="scenario", root=str(root))
    assert entry["outdated"] == ["hero_late.png"]


def test_a_canon_too_small_is_refused_before_anything_is_spent(project):
    root, fake = project
    (root / "polyweave.toml").write_text(
        PROJECT.replace("art/canon/heroes", "art/canon/empty"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        scenario.train(family="heroes", root=str(root))
    assert refused.value.code == "style.too-few-to-train"
    assert fake.sent == []


def test_drawing_before_training_is_refused_with_the_door(project):
    root, fake = project
    with pytest.raises(PolyweaveError) as refused:
        picture.buy(out="art/x.png", prompt="x", family="heroes", service="scenario",
                    root=str(root))
    assert refused.value.code == "style.untrained"
    assert fake.sent == []


def test_a_training_over_the_ceiling_is_refused_before_sending(project):
    root, fake = project
    poorer = PROJECT.replace("amount = 20.0", "amount = 2.0")
    (root / "polyweave.toml").write_text(poorer, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        scenario.train(family="heroes", root=str(root))
    assert refused.value.code == "fetch.over-budget"
    assert fake.sent == []


def test_a_failed_training_is_owed(project):
    root, fake = project
    fake.status = "failed"
    with pytest.raises(PolyweaveError):
        scenario.train(family="heroes", root=str(root))
    assert purchase.spent(root, service="scenario") == 5.0
