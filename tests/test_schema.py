"""What the service accepts, learned once and kept.

§PW19's trap is that an unknown field is dropped in silence, so a field that passes
validation proves nothing. The fake service below behaves exactly that way, which is
what makes these tests about the real problem rather than about a mock.
"""

from __future__ import annotations

import pytest

from polyweave import schema
from polyweave.errors import PolyweaveError


def project(tmp_path, text=""):
    (tmp_path / "polyweave.toml").write_text(text, encoding="utf-8")
    return tmp_path


class Service:
    """A service that behaves the way the real one does.

    It requires two fields, enumerates one of them, and **drops anything it does not
    recognise without a word** — which is the whole difficulty.
    """

    REQUIRED = ("prompt", "art_style")
    CHOICES = {
        "art_style": ["realistic", "sculpture"],
        "topology": ["quad", "triangle"],
    }

    def __init__(self):
        self.seen = []
        self.charged = 0.0

    def __call__(self, payload):
        self.seen.append(dict(payload))
        reads = set(self.CHOICES) | set(self.REQUIRED)
        known = {k: v for k, v in payload.items() if k in reads}
        missing = [f for f in self.REQUIRED if f not in known]
        if missing:
            return {
                "ok": False,
                "message": f"missing: {', '.join(missing)}",
                "fields": missing,
            }
        bad = [
            k
            for k, v in known.items()
            if k in self.CHOICES and v not in self.CHOICES[k]
        ]
        if bad:
            return {
                "ok": False,
                "message": f"invalid value for {bad[0]}",
                "fields": bad,
                "choices": {k: self.CHOICES[k] for k in bad},
            }
        self.charged += 30.0  # only a valid payload ever enqueues, and only that costs
        return {"ok": True, "message": "queued"}


# -- learning ------------------------------------------------------------------------


def test_the_required_fields_come_from_an_empty_payload(tmp_path):
    where = project(tmp_path)
    found = schema.learn(Service(), ["art_style", "topology"], root=where)
    assert found["field"]["prompt"]["required"] is True
    assert found["field"]["art_style"]["required"] is True
    assert found["field"]["topology"]["required"] is False


def test_an_impossible_value_makes_the_service_print_what_it_accepts(tmp_path):
    where = project(tmp_path)
    found = schema.learn(
        Service(), ["art_style", "topology"], base={"prompt": "a cap"}, root=where
    )
    assert found["field"]["art_style"]["choices"] == ["realistic", "sculpture"]
    assert found["field"]["topology"]["choices"] == ["quad", "triangle"]


def test_every_probe_carries_the_control_field(tmp_path):
    """Only an invalid value proves a field is read, so the control rides along."""
    service = Service()
    schema.learn(service, ["art_style"], root=project(tmp_path))
    assert all(schema.CONTROL in payload for payload in service.seen)


def test_the_control_shows_that_unknown_fields_are_dropped(tmp_path):
    """Which is the fact that makes a passing field worthless as evidence."""
    found = schema.learn(Service(), ["art_style"], root=project(tmp_path))
    assert found["drops_unknown"] is True
    assert found["control"] == schema.CONTROL


def test_only_a_refused_value_marks_a_field_proved(tmp_path):
    where = project(tmp_path)
    found = schema.learn(
        Service(),
        ["art_style", "topology", "invented"],
        base={"prompt": "a cap"},
        root=where,
    )
    assert schema.proved(found) == ["art_style", "topology"]
    # `invented` was dropped in silence, which proves nothing about it either way.
    assert "invented" not in schema.proved(found)
    # `prompt` is required and free text, so no value can be invalid and nothing here
    # proves the service reads it. The schema says so rather than pretending.
    assert found["field"]["prompt"]["required"] is True
    assert found["field"]["prompt"]["proved"] is False


def test_the_probing_never_enqueues_anything(tmp_path):
    """A request the server refuses never starts a task, so a rejection is free."""
    service = Service()
    schema.learn(service, ["art_style", "topology"], root=project(tmp_path))
    assert service.charged == 0.0


def test_the_balance_either_side_is_the_proof_it_was_free(tmp_path):
    service = Service()
    found = schema.learn(
        service,
        ["art_style"],
        root=project(tmp_path),
        balance=lambda: 100.0 - service.charged,
    )
    assert found["credits"] == 0.0


# -- kept ------------------------------------------------------------------------------


def test_the_schema_is_written_where_the_project_says(tmp_path):
    where = project(tmp_path, '[service]\nschema = "docs/service.toml"\n')
    schema.learn(Service(), ["art_style"], root=where)
    assert (where / "docs" / "service.toml").is_file()


def test_a_written_schema_reads_back(tmp_path):
    where = project(tmp_path)
    written = schema.learn(
        Service(), ["art_style"], base={"prompt": "a cap"}, root=where
    )
    read = schema.read(where)
    assert read["field"]["art_style"]["choices"] == ["realistic", "sculpture"]
    assert read["drops_unknown"] is True
    assert read["learned_at"] == written["learned_at"]


def test_the_file_says_what_proved_means(tmp_path):
    """A person reads and corrects this file, so it explains itself."""
    where = project(tmp_path)
    schema.learn(Service(), ["art_style"], root=where)
    text = schema.where(where).read_text(encoding="utf-8")
    assert "dropped in silence" in text


def test_a_schema_edited_into_nonsense_says_so(tmp_path):
    where = project(tmp_path)
    schema.learn(Service(), ["art_style"], root=where)
    schema.where(where).write_text("[field\n", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        schema.read(where)
    assert caught.value.code == "fetch.schema-malformed"


# -- checked before it is sent ---------------------------------------------------------


def learned(tmp_path):
    where = project(tmp_path)
    return where, schema.learn(
        Service(), ["art_style", "topology"], base={"prompt": "a cap"}, root=where
    )


def test_a_payload_the_service_accepts_passes(tmp_path):
    where, known = learned(tmp_path)
    payload = {"prompt": "a wide low cap", "art_style": "sculpture"}
    assert schema.validate(payload, root=where) == payload


def test_a_typo_is_a_local_refusal_rather_than_a_silent_no_op(tmp_path):
    """The whole point: the service would have dropped it and said nothing."""
    where, known = learned(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        schema.validate(
            {"prompt": "a cap", "art_style": "sculpture", "art_stlye": "x"}, root=where
        )
    assert caught.value.code == "fetch.unknown-field"
    assert "dropped in silence" in caught.value.remedy


def test_a_missing_required_field_is_caught_here(tmp_path):
    where, known = learned(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        schema.validate({"prompt": "a cap"}, root=where)
    assert caught.value.code == "fetch.missing-field"
    assert "art_style" in caught.value.message


def test_a_value_outside_the_proved_set_is_caught_here(tmp_path):
    where, known = learned(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        schema.validate({"prompt": "a cap", "art_style": "painterly"}, root=where)
    assert caught.value.code == "fetch.bad-choice"
    assert "realistic" in caught.value.remedy


def test_a_project_that_has_not_learned_yet_says_so(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        schema.validate({"prompt": "a cap"}, root=project(tmp_path))
    assert caught.value.code == "fetch.no-schema"
    assert "learn it once" in caught.value.remedy


def test_relearning_is_one_call(tmp_path):
    """Re-learning after the service changes, instead of an afternoon."""
    where, first = learned(tmp_path)

    class Changed(Service):
        CHOICES = {"art_style": ["realistic", "painterly"], "topology": ["quad"]}

    again = schema.learn(
        Changed(), ["art_style", "topology"], base={"prompt": "a cap"}, root=where
    )
    assert again["field"]["art_style"]["choices"] == ["realistic", "painterly"]
    assert schema.read(where)["field"]["art_style"]["choices"] == [
        "realistic",
        "painterly",
    ]
