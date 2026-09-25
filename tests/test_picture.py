"""Buying a picture through the same doors a mesh goes through (§PW163).

Nothing here reaches the service: the transport is replaced, so every test is about
what the client does before and after a request, which is where the money is.
"""

from __future__ import annotations

import json

import pytest

from polyweave import picture, provenance, purchase, schema
from polyweave.errors import PolyweaveError

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 60
PROJECT = (
    '[service.meshy]\nbase = "https://api.meshy.ai"\nkey_env = "POLYWEAVE_TEST_M"\n\n'
    '[service.ideogram]\nbase = "https://api.ideogram.ai"\n'
    'key_env = "POLYWEAVE_TEST_I"\n\n'
    '[budget.meshy]\namount = 60\nexpires = "2099-12-31"\n\n'
    '[budget.ideogram]\namount = 1.0\nunit = "USD"\nexpires = "2099-12-31"\n'
)
ANSWER = {
    "created": "2026-09-22T10:00:00Z",
    "data": [
        {
            "prompt": "a plush booster, rewritten",
            "resolution": "1024x1024",
            "is_image_safe": True,
            "seed": 42,
            "url": "https://ideogram.example/p.png",
        }
    ],
}


class Service:
    """What the service would do, and a record of what was asked of it."""

    def __init__(self, status=200, answer=ANSWER):
        self.status, self.answer, self.sent = status, answer, []

    def send(self, endpoint, key, payload):
        self.sent.append((endpoint, key, dict(payload)))
        body = (
            self.answer if isinstance(self.answer, bytes) else json.dumps(self.answer)
        )
        return self.status, body if isinstance(body, bytes) else body.encode()


@pytest.fixture
def service(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_I", "sk-picture")
    fake = Service()
    monkeypatch.setattr(picture, "_send", fake.send)
    monkeypatch.setattr(picture, "_download", lambda link: PNG)
    return fake


def buy(tmp_path, **over):
    fields = {
        "prompt": "a plush booster",
        "out": "refs/booster.png",
        "cost": 0.08,
        "service": "ideogram",
        "root": tmp_path,
    }
    fields.update(over)
    return picture.buy(**fields)


def refused(tmp_path, **over) -> PolyweaveError:
    with pytest.raises(PolyweaveError) as caught:
        buy(tmp_path, **over)
    return caught.value


# -- the doors, in order -------------------------------------------------------------


def test_a_bought_picture_lands_hashed_recorded_and_ledgered(tmp_path, service):
    entry = buy(tmp_path)
    assert (tmp_path / "refs" / "booster.png").read_bytes() == PNG
    assert entry["bought"] == "image"
    assert entry["service"] == "ideogram"
    assert entry["credits"] == 0.08
    assert purchase.read(tmp_path) == [entry]
    record = provenance.read("refs/booster.png", root=tmp_path)
    assert record["details"]["resolution"] == "1024x1024"
    assert record["details"]["model"] == "4.0"


def test_it_is_charged_to_its_own_services_ceiling(tmp_path, service):
    buy(tmp_path)
    assert purchase.spent(tmp_path, "ideogram") == 0.08
    assert purchase.spent(tmp_path, "meshy") == 0.0


def test_the_transparent_endpoint_is_the_default_and_the_prompt_field_is_the_models(
    tmp_path, service
):
    buy(tmp_path)
    endpoint, key, payload = service.sent[0]
    assert endpoint == "https://api.ideogram.ai/v1/ideogram-v4/generate-transparent"
    assert key == "sk-picture"
    assert payload == {"text_prompt": "a plush booster"}

    buy(tmp_path, out="refs/b.png", model="3.0", transparent=False, seed=7)
    endpoint, _, payload = service.sent[1]
    assert endpoint == "https://api.ideogram.ai/v1/ideogram-v3/generate"
    assert payload == {"prompt": "a plush booster", "seed": 7}


def test_a_spend_past_the_ceiling_never_reaches_the_service(tmp_path, service):
    error = refused(tmp_path, cost=5.0)
    assert error.code == "fetch.over-budget"
    assert service.sent == []
    assert purchase.read(tmp_path) == []


def test_a_picture_asked_for_at_no_cost_is_refused(tmp_path, service):
    assert refused(tmp_path, cost=0).code == "fetch.cost-unstated"
    assert service.sent == []


def test_a_payload_the_learned_schema_refuses_is_never_sent(tmp_path, service):
    schema.write(
        {"field": {"prompt": {"required": True, "proved": False, "choices": []}}},
        tmp_path,
        "ideogram",
    )
    # 4.0 spells it text_prompt, and a schema learned from 3.0 says otherwise
    assert refused(tmp_path).code == "fetch.unknown-field"
    assert service.sent == []


def test_an_unset_key_is_refused_before_anything_is_sent(
    tmp_path, service, monkeypatch
):
    monkeypatch.delenv("POLYWEAVE_TEST_I")
    error = refused(tmp_path)
    assert error.code == "fetch.service-unconfigured"
    assert "POLYWEAVE_TEST_I" in error.message
    assert service.sent == []


# -- the service's refusals are codes ------------------------------------------------


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (422, "fetch.prompt-refused"),
        (429, "fetch.rate-limited"),
        (401, "fetch.service-error"),
    ],
)
def test_a_refusal_is_a_code_and_ledgers_nothing(tmp_path, service, status, code):
    service.status, service.answer = status, {"detail": "no"}
    assert refused(tmp_path).code == code
    assert purchase.read(tmp_path) == []


def test_an_answer_marked_unsafe_with_no_picture_is_a_refused_prompt(tmp_path, service):
    service.answer = {"created": "x", "data": [{"is_image_safe": False, "url": None}]}
    assert refused(tmp_path).code == "fetch.prompt-refused"
    assert purchase.read(tmp_path) == []


def test_the_client_never_holds_more_calls_open_than_the_account_allows():
    assert picture._inflight._value == picture.INFLIGHT == 10
