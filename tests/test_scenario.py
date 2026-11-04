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


PUBLIC = "model_bfl-flux-2-klein-4b"

#: A Starter account: its ceiling counts Scenario's own units, and it trains nothing.
STARTER = f"""[service.scenario]
base = "https://api.cloud.scenario.com"
key_env = "SCENARIO_TEST_KEY"
prices = {{ "{PUBLIC}" = 1 }}

[budget.scenario]
amount = 50
unit = "CU"
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
        self.quote = 1
        # As Scenario declares Flux.2 Klein 4B's inputs (read 2026-11-04).
        self.inputs = [
            {"name": "prompt", "type": "string", "required": {"always": True}},
            {"name": "width", "type": "number", "min": 128, "max": 2048},
            {"name": "height", "type": "number", "min": 128, "max": 2048},
            {"name": "seed", "type": "number"},
        ]

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
        if path == f"models/{PUBLIC}":
            return 200, {"model": {"id": PUBLIC, "inputs": self.inputs}}
        if path == f"generate/custom/{PUBLIC}?dryRun=true":
            return 269, {"creativeUnitsCost": self.quote}
        if path == f"generate/custom/{PUBLIC}":
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


# -- a public model, which needs no training (§PW688) --------------------------------


@pytest.fixture
def starter(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(STARTER, encoding="utf-8")
    monkeypatch.setenv("SCENARIO_TEST_KEY", "k:s")
    fake = Fake()
    monkeypatch.setattr(scenario_adapter, "call", fake)
    monkeypatch.setattr(scenario_adapter, "POLL_EVERY", 0.0)
    monkeypatch.setattr(S, "download", lambda link: png((200, 40, 40, 255)))
    return tmp_path, fake


def drawn(fake) -> dict:
    """The payload of the last drawing sent, which is not a dry run."""
    return [body for method, path, body in fake.sent
            if method == "POST" and path == f"generate/custom/{PUBLIC}"][-1]


def bought_from(root, **over):
    return picture.buy(**{"out": "art/rocket.png", "prompt": "a plush rocket",
                          "model": PUBLIC, "service": "scenario", "root": str(root),
                          **over})


def test_a_public_model_draws_with_no_training_and_its_record_names_it(starter):
    root, fake = starter
    entry = bought_from(root, aspect_ratio="16x9", seed=7)
    payload = drawn(fake)
    # Klein declares width and height, not aspectRatio, so the shape goes as those.
    assert payload == {"prompt": "a plush rocket", "width": 1024, "height": 576,
                       "seed": 7}
    assert ("POST", f"generate/custom/{PUBLIC}?dryRun=true") in [
        (m, p) for m, p, _ in fake.sent]
    details = provenance.read("art/rocket.png", root)["details"]
    assert details["model"] == PUBLIC and details["public"] is True
    assert entry["credits"] == 1
    assert purchase.spent(root, service="scenario") == 1


def test_a_ratio_goes_as_aspect_ratio_where_the_model_declares_that(starter):
    root, fake = starter
    fake.inputs = [{"name": "prompt", "type": "string"},
                   {"name": "aspectRatio", "type": "string",
                    "allowedValues": ["16:9", "1:1", "auto"]}]
    bought_from(root, aspect_ratio="16x9")
    assert drawn(fake) == {"prompt": "a plush rocket", "aspectRatio": "16:9"}
    with pytest.raises(PolyweaveError) as refused:
        bought_from(root, out="art/other.png", aspect_ratio="21x9")
    assert refused.value.code == "fetch.bad-choice"
    assert "16:9" in refused.value.remedy


def test_a_quote_above_the_declared_price_is_refused_before_anything_is_spent(
    starter
):
    root, fake = starter
    fake.quote = 4
    with pytest.raises(PolyweaveError) as refused:
        bought_from(root)
    assert refused.value.code == "picture.quoted-over-price"
    assert f"generate/custom/{PUBLIC}" not in [p for _, p, _ in fake.sent]
    assert purchase.read(root) == []


def test_a_seed_the_model_does_not_declare_is_refused(starter):
    root, fake = starter
    fake.inputs = [{"name": "prompt", "type": "string"}]
    with pytest.raises(PolyweaveError) as refused:
        bought_from(root, seed=3)
    assert refused.value.code == "fetch.unknown-field"
    assert purchase.read(root) == []


def test_a_model_that_draws_nothing_from_words_is_refused(starter):
    root, fake = starter
    fake.inputs = [{"name": "image", "type": "file"}]
    with pytest.raises(PolyweaveError) as refused:
        bought_from(root)
    assert refused.value.code == "fetch.bad-choice"
    assert "txt2img" in refused.value.remedy


# -- a larger picture, bought and recorded against its source (§PW689) ---------------

UPSCALER = "model_upscale-v3"


class Upscaler(Fake):
    """Scenario's routes for an upscaler, which declares an image and a factor."""

    def __init__(self, declared):
        super().__init__()
        self.declared = declared

    def __call__(self, method, url, key, body=None):
        path = url.split("/v1/", 1)[1]
        if path.startswith("models/model_up"):
            self.sent.append((method, path, body))
            return 200, {"model": {"inputs": self.declared}}
        if path.startswith("generate/custom/model_up"):
            self.sent.append((method, path, body))
            if path.endswith("?dryRun=true"):
                return 269, {"creativeUnitsCost": self.quote}
            return 200, {"job": {"jobId": "job_1", "status": "queued"}}
        return super().__call__(method, url, key, body)


@pytest.fixture
def upscaling(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(
        STARTER.replace(f'"{PUBLIC}" = 1', f'"{UPSCALER}" = 10, "model_up-fixed" = 2'),
        encoding="utf-8")
    monkeypatch.setenv("SCENARIO_TEST_KEY", "k:s")
    monkeypatch.setattr(scenario_adapter, "POLL_EVERY", 0.0)
    held = io.BytesIO()
    Image.new("RGB", (64, 36), (200, 40, 40)).save(held, format="PNG")
    monkeypatch.setattr(S, "download", lambda link: held.getvalue())
    (tmp_path / "art").mkdir()
    Image.new("RGB", (32, 18), (90, 120, 160)).save(tmp_path / "art" / "key.png")

    def with_inputs(declared):
        fake = Upscaler(declared)
        monkeypatch.setattr(scenario_adapter, "call", fake)
        return fake

    return tmp_path, with_inputs


def test_an_upscale_is_recorded_against_its_source(upscaling):
    root, with_inputs = upscaling
    fake = with_inputs([{"name": "image", "type": "file"},
                        {"name": "upscaleFactor", "type": "number", "min": 1,
                         "max": 16}])
    entry = scenario.upscale(source="art/key.png", out="art/key@2x.png", factor=2,
                             service="scenario", root=str(root))
    sent = [body for method, path, body in fake.sent
            if path == f"generate/custom/{UPSCALER}"][-1]
    assert sent["image"].startswith("data:image/png;base64,")
    assert sent["upscaleFactor"] == 2
    assert entry["size"] == [64, 36] and entry["credits"] == 10
    record = provenance.read("art/key@2x.png", root)
    assert record["details"]["upscaled"] == {"from": "art/key.png", "size": [32, 18],
                                             "factor": 2}
    assert record["inputs"][0]["role"] == "source"


def test_a_factor_goes_as_the_model_spells_it_or_not_at_all(upscaling):
    root, with_inputs = upscaling
    fake = with_inputs([{"name": "image", "type": "file"},
                        {"name": "upscaleFactor", "type": "string",
                         "allowedValues": ["2x", "4x"]}])
    scenario.upscale(source="art/key.png", out="art/a.png", factor=4,
                     model="model_up-fixed", service="scenario", root=str(root))
    drawn = [body for _, path, body in fake.sent
             if path == "generate/custom/model_up-fixed"][-1]
    assert drawn["upscaleFactor"] == "4x"
    with pytest.raises(PolyweaveError) as refused:
        scenario.upscale(source="art/key.png", out="art/b.png", factor=3,
                         model="model_up-fixed", service="scenario", root=str(root))
    assert refused.value.code == "fetch.bad-choice"
    fixed = with_inputs([{"name": "image", "type": "file"}])
    scenario.upscale(source="art/key.png", out="art/c.png", factor=2,
                     model="model_up-fixed", service="scenario", root=str(root))
    drawn = [body for _, path, body in fixed.sent
             if path == "generate/custom/model_up-fixed"][-1]
    assert set(drawn) == {"image"}


def test_a_model_that_takes_no_image_enlarges_nothing(upscaling):
    root, with_inputs = upscaling
    with_inputs([{"name": "prompt", "type": "string"}])
    with pytest.raises(PolyweaveError) as refused:
        scenario.upscale(source="art/key.png", out="art/d.png", service="scenario",
                         root=str(root))
    assert refused.value.code == "fetch.bad-choice"
    assert purchase.read(root) == []


def test_a_failed_training_is_owed(project):
    root, fake = project
    fake.status = "failed"
    with pytest.raises(PolyweaveError):
        scenario.train(family="heroes", root=str(root))
    assert purchase.spent(root, service="scenario") == 5.0
