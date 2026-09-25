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
    'key_env = "POLYWEAVE_TEST_I"\n'
    'prices = { "4.0" = 0.08, "4.0:QUALITY" = 5.0, "3.0" = 0.06, '
    '"describe" = 0.01 }\n\n'
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

    def send(self, endpoint, key, payload, files=None):
        self.sent.append((endpoint, key, dict(payload)))
        self.files = files
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

    proved = {"required": False, "proved": True, "choices": []}
    schema.write(
        {"field": {"prompt": {"required": True}, "seed": proved}}, tmp_path, "ideogram"
    )
    entry = buy(tmp_path, out="refs/b.png", model="3.0", transparent=False, seed=7)
    assert entry["credits"] == 0.06
    endpoint, _, payload = service.sent[1]
    assert endpoint == "https://api.ideogram.ai/v1/ideogram-v3/generate"
    assert payload == {"prompt": "a plush booster", "seed": 7}


def test_a_spend_past_the_ceiling_never_reaches_the_service(tmp_path, service):
    error = refused(tmp_path, rendering_speed="QUALITY")
    assert error.code == "fetch.over-budget"
    assert service.sent == []
    assert purchase.read(tmp_path) == []


# -- a price that says it was quoted (§PW164) ----------------------------------------


def test_a_picture_is_priced_from_the_table_and_says_it_was_quoted(tmp_path, service):
    entry = buy(tmp_path)
    assert entry["credits"] == 0.08
    assert entry["measured"] is False
    left = purchase.remaining(tmp_path, service="ideogram")
    assert left["spent"] == left["quoted"] == 0.08
    assert purchase.held(tmp_path)["quoted"] == {"ideogram": 0.08, "meshy": 0.0}


def test_a_model_and_speed_with_no_price_is_refused_rather_than_free(tmp_path, service):
    error = refused(tmp_path, rendering_speed="TURBO")
    assert error.code == "fetch.unpriced"
    assert "'4.0:TURBO'" in error.message
    assert service.sent == []


def test_an_answer_with_more_pictures_is_charged_for_each(tmp_path, service):
    service.answer = {**ANSWER, "data": ANSWER["data"] * 3}
    assert buy(tmp_path)["credits"] == 0.24


def test_a_price_that_is_not_a_positive_number_is_refused(tmp_path):
    from polyweave import config

    (tmp_path / "polyweave.toml").write_text(
        '[service.ideogram]\nprices = { "4.0" = 0 }\n', encoding="utf-8"
    )
    with pytest.raises(PolyweaveError) as caught:
        config.load(tmp_path)
    assert caught.value.code == "config.bad-type"


def test_a_cost_read_off_two_balances_is_measured(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[budget]\ncredits = 60\nexpires = "2099-12-31"\n', encoding="utf-8"
    )
    entry = purchase.capture(
        PNG,
        out="a.glb",
        task_id="t",
        credits=30,
        balance_before=100.0,
        balance_after=70.0,
        root=tmp_path,
    )
    assert entry["measured"] is True
    assert purchase.remaining(tmp_path)["quoted"] == 0.0


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


# -- a quote is not trusted forever --------------------------------------------------


def _bought_at(tmp_path, service, at, out):
    entry = buy(tmp_path, out=out)
    ledger = purchase.read(tmp_path)
    ledger[-1]["at"] = at
    purchase.where(tmp_path).write_text(json.dumps(ledger), encoding="utf-8")
    return entry


def test_a_usage_row_turns_a_quote_into_what_was_billed(tmp_path, service):
    _bought_at(tmp_path, service, "2026-09-22T10:00:05Z", "a.png")
    found = purchase.reconcile(
        [{"at": "2026-09-22T10:00:00Z", "cost": 0.1, "count": 1}],
        service="ideogram",
        root=tmp_path,
    )
    assert found["surprised"] == ["a.png"]
    entry = purchase.read(tmp_path)[0]
    assert entry["credits"] == 0.1
    assert entry["expected_credits"] == 0.08
    assert entry["measured"] is True
    assert purchase.remaining(tmp_path, service="ideogram")["quoted"] == 0.0


def test_a_billed_row_with_no_entry_is_named(tmp_path, service):
    _bought_at(tmp_path, service, "2026-09-22T10:00:05Z", "a.png")
    found = purchase.reconcile(
        [
            {"at": "2026-09-22T10:00:00Z", "cost": 0.08},
            {"at": "2026-09-22T12:00:00Z", "cost": 0.08},
        ],
        service="ideogram",
        root=tmp_path,
    )
    assert found["surprised"] == []
    assert [r["at"] for r in found["unmatched_rows"]] == ["2026-09-22T12:00:00Z"]
    assert found["still_quoted"] == []


def test_a_row_far_from_every_entry_matches_none(tmp_path, service):
    _bought_at(tmp_path, service, "2026-09-22T10:00:00Z", "a.png")
    found = purchase.reconcile(
        [{"at": "2026-09-23T10:00:00Z", "cost": 0.08}],
        service="ideogram",
        root=tmp_path,
    )
    assert found["matched"] == []
    assert found["still_quoted"] == ["a.png"]


# -- a picture its record can make again (§PW165) -----------------------------------

STRUCTURED = {
    "high_level_description": "a plush booster on its own",
    "compositional_deconstruction": {"background": "none", "elements": []},
}


def test_a_structured_prompt_is_sent_as_written_and_kept(tmp_path, service):
    buy(tmp_path, prompt=None, json_prompt=STRUCTURED)
    _, _, payload = service.sent[0]
    assert json.loads(payload["json_prompt"]) == STRUCTURED
    assert "text_prompt" not in payload
    record = provenance.read("refs/booster.png", root=tmp_path)
    assert record["details"]["json_prompt"] == STRUCTURED


def test_the_prompt_the_service_drew_from_is_recorded_beside_the_one_sent(
    tmp_path, service
):
    entry = buy(tmp_path)
    assert entry["prompt"] == "a plush booster"
    record = provenance.read("refs/booster.png", root=tmp_path)
    assert record["details"]["returned_prompt"] == "a plush booster, rewritten"
    assert record["details"]["seed"] == 42


def test_a_seed_nothing_proved_the_service_reads_is_refused(tmp_path, service):
    assert refused(tmp_path, seed=7).code == "fetch.seed-unproved"
    assert service.sent == []


@pytest.mark.parametrize(
    ("over", "code"),
    [
        ({"prompt": None}, "fetch.missing-field"),
        ({"json_prompt": STRUCTURED}, "fetch.missing-field"),
        (
            {"prompt": None, "json_prompt": STRUCTURED, "model": "3.0"},
            "fetch.unknown-field",
        ),
    ],
)
def test_one_prompt_and_only_the_kind_the_model_reads(tmp_path, service, over, code):
    assert refused(tmp_path, **over).code == code


def test_an_approved_picture_is_described_into_a_file_beside_it(tmp_path, service):
    buy(tmp_path)
    service.answer = {"json_prompt": STRUCTURED}
    entry = picture.describe_picture(
        "refs/booster.png", service="ideogram", root=tmp_path
    )
    beside = tmp_path / "refs" / "booster.prompt.json"
    assert json.loads(beside.read_text(encoding="utf-8")) == STRUCTURED
    assert entry["bought"] == "description"
    assert entry["credits"] == 0.01
    assert service.sent[-1][0] == "https://api.ideogram.ai/v1/ideogram-v4/describe"
    assert service.files["image_file"][1] == PNG
    record = provenance.read("refs/booster.prompt.json", root=tmp_path)
    assert record["inputs"][0]["path"] == "refs/booster.png"
