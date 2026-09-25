"""More than one paid service, each with its own key, schema and ceiling.

§PW162: `[service]` and `[budget]` were Meshy's shape, credits and all, so an image
service billing per picture in dollars had nowhere to live that did not overwrite the
mesh service's. A service is now a named table, and ceilings never pool.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from polyweave import config as C
from polyweave import purchase, schema
from polyweave.errors import PolyweaveError

GLTF = b"glTF" + b"\x00" * 60
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 60
TODAY = date(2026, 9, 22)
TWO = (
    '[service.meshy]\nbase = "https://api.meshy.ai"\n'
    'key_env = "POLYWEAVE_TEST_MESHY"\n\n'
    '[service.ideogram]\nkey_env = "POLYWEAVE_TEST_IDEOGRAM"\n\n'
    '[budget.meshy]\namount = 60\nunit = "credits"\nexpires = "2099-12-31"\n\n'
    '[budget.ideogram]\namount = 2.5\nunit = "USD"\nexpires = "2099-12-31"\n'
)


def project(tmp_path, text):
    (tmp_path / C.FILENAME).write_text(text, encoding="utf-8")
    return tmp_path


def refused(call, *args, **kwargs) -> PolyweaveError:
    with pytest.raises(PolyweaveError) as caught:
        call(*args, **kwargs)
    return caught.value


# -- a service is a named table ------------------------------------------------------


def test_each_named_service_carries_its_own_key_and_schema(tmp_path):
    found = C.load(project(tmp_path, TWO)).services()
    assert sorted(found) == ["ideogram", "meshy"]
    assert found["meshy"]["key_env"] == "POLYWEAVE_TEST_MESHY"
    assert found["meshy"]["base"] == "https://api.meshy.ai"
    # two services never share the file that says what each was proved to accept
    assert found["meshy"]["schema"] != found["ideogram"]["schema"]


def test_a_bare_service_still_reads_as_the_one_it_always_was(tmp_path):
    where = project(
        tmp_path,
        '[service]\nkey_env = "MESHY_API_KEY"\n\n'
        '[budget]\ncredits = 60\nexpires = "2099-12-31"\n',
    )
    config = C.load(where)
    assert list(config.services()) == ["default"]
    assert config.service() == "default"
    assert config.budget(TODAY)["amount"] == 60
    assert purchase.remaining(where, TODAY)["unit"] == "credits"


def test_a_named_ceiling_says_its_unit(tmp_path):
    left = purchase.remaining(project(tmp_path, TWO), TODAY, service="ideogram")
    assert left["unit"] == "USD"
    assert left["declared"] == 2.5
    assert left["spendable"] is True


def test_a_service_with_no_ceiling_of_its_own_may_spend_nothing(tmp_path):
    where = project(tmp_path, "[service.meshy]\n\n[service.ideogram]\n")
    error = refused(purchase.allow, 1, root=where, today=TODAY, service="ideogram")
    assert error.code == "fetch.budget-closed"
    assert "[budget.ideogram] amount" in error.remedy


# -- the declaration is refused where it would be a guess --------------------------


@pytest.mark.parametrize(
    "text",
    [
        # bare keys beside named tables: whose are they?
        '[service]\nkey_env = "X"\n\n[service.meshy]\nbase = "b"\n',
        # a bare ceiling beside named services
        "[service.meshy]\n\n[service.ideogram]\n\n[budget]\ncredits = 5\n",
        # a ceiling for a service nothing declares
        "[service.meshy]\n\n[budget.ideogram]\namount = 5\n",
    ],
)
def test_a_service_declared_two_ways_is_refused(tmp_path, text):
    assert refused(C.load, project(tmp_path, text)).code == "config.services-mixed"


def test_a_bare_ceiling_is_in_credits_and_another_unit_is_a_named_one(tmp_path):
    error = refused(C.load, project(tmp_path, '[budget]\namount = 5\nunit = "USD"\n'))
    assert error.code == "config.unknown-key"


def test_a_misspelt_key_in_a_named_service_is_refused(tmp_path):
    error = refused(C.load, project(tmp_path, '[service.meshy]\nkey_evn = "X"\n'))
    assert error.code == "config.unknown-key"
    assert "service.meshy.key_env" in error.remedy


# -- ceilings never pool -------------------------------------------------------------


def test_a_spend_is_judged_only_against_its_own_services_ceiling(tmp_path):
    where = project(tmp_path, TWO)
    purchase.capture(
        GLTF, out="a.glb", task_id="t_1", credits=55, service="meshy", root=where
    )
    assert purchase.spent(where, "meshy") == 55.0
    assert purchase.spent(where, "ideogram") == 0.0
    # the dollars are untouched by fifty-five credits
    assert purchase.allow(2, root=where, today=TODAY, service="ideogram")["left"] == 2.5
    error = refused(purchase.allow, 10, root=where, today=TODAY, service="meshy")
    assert error.code == "fetch.over-budget"
    assert "[budget.meshy] amount" in error.remedy


def test_naming_no_service_where_there_are_several_is_refused(tmp_path):
    where = project(tmp_path, TWO)
    error = refused(purchase.allow, 1, root=where, today=TODAY)
    assert error.code == "fetch.service-unnamed"
    assert error.as_dict()["allowed"] == ["ideogram", "meshy"]
    assert refused(purchase.remaining, where, TODAY).code == "fetch.service-unnamed"
    assert refused(purchase.spent, where).code == "fetch.service-unnamed"


def test_a_service_nobody_declared_is_refused_with_the_near_one(tmp_path):
    error = refused(
        purchase.allow, 1, root=project(tmp_path, TWO), today=TODAY, service="meshi"
    )
    assert error.code == "fetch.unknown-service"
    assert "meshy" in error.remedy


# -- the ledger entry names its service ---------------------------------------------


def test_the_ledger_entry_names_its_service(tmp_path):
    where = project(tmp_path, TWO)
    entry = purchase.capture(
        PNG, out="p.png", task_id="i_1", credits=0.08, service="ideogram", root=where
    )
    assert entry["service"] == "ideogram"
    assert purchase.read(where)[0]["service"] == "ideogram"


def test_a_bare_projects_entry_names_the_default_service(tmp_path):
    where = project(tmp_path, '[budget]\ncredits = 60\nexpires = "2099-12-31"\n')
    entry = purchase.capture(GLTF, out="a.glb", task_id="t_1", credits=3, root=where)
    assert entry["service"] == "default"


def test_an_entry_from_before_services_had_names_is_charged_to_the_only_one(tmp_path):
    where = project(tmp_path, "[service.meshy]\n\n[budget.meshy]\namount = 60\n")
    (where / "polyweave.purchases.json").write_text(
        json.dumps([{"artefact": "a.glb", "sha256": "x", "credits": 30}]),
        encoding="utf-8",
    )
    assert purchase.spent(where) == 30.0


def test_an_entry_nothing_can_attribute_is_refused_rather_than_guessed(tmp_path):
    where = project(tmp_path, TWO)
    (where / "polyweave.purchases.json").write_text(
        json.dumps([{"artefact": "a.glb", "sha256": "x", "credits": 30}]),
        encoding="utf-8",
    )
    error = refused(purchase.spent, where, "meshy")
    assert error.code == "fetch.ledger-unattributed"
    # held is a question about assets, so it answers, and names what it could not charge
    held = purchase.held(where)
    assert held["unattributed"] == ["a.glb"]
    assert held["against_ceiling"] == {"ideogram": 0.0, "meshy": 0.0}


# -- keys and schemas, by name -------------------------------------------------------


def test_capabilities_reports_each_key_by_name_and_never_by_value(
    tmp_path, monkeypatch
):
    from polyweave.capabilities import capabilities

    monkeypatch.setenv("POLYWEAVE_TEST_MESHY", "sk-never-echoed")
    monkeypatch.delenv("POLYWEAVE_TEST_IDEOGRAM", raising=False)
    found = capabilities(project(tmp_path, TWO), probe=False)
    assert found["services"] == {
        "meshy": {"key_env": "POLYWEAVE_TEST_MESHY", "key_present": True},
        "ideogram": {"key_env": "POLYWEAVE_TEST_IDEOGRAM", "key_present": False},
    }
    assert found["service"] is None
    assert found["budgets"]["ideogram"]["unit"] == "USD"
    assert "sk-never-echoed" not in repr(found)


def test_each_service_learns_its_schema_into_its_own_file(tmp_path):
    where = project(tmp_path, TWO)
    schema.write({"field": {"prompt": {"required": True}}}, where, "ideogram")
    assert schema.read(where, "ideogram")["field"]["prompt"]["required"] is True
    assert schema.read(where, "meshy") == {}
