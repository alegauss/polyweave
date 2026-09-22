"""A budget approved once, spent against a ledger.

§PW18: the rule that an agent may not spend on its own judgement is right, and enforcing
it by asking at every fetch stops a session five times to buy five meshes. What the rule
actually constrains is the ceiling.
"""

from __future__ import annotations

from datetime import date

import pytest

from polyweave import purchase
from polyweave.errors import PolyweaveError

GLTF = b"glTF" + b"\x00" * 60
LIVE = '[budget]\ncredits = 60\nexpires = "2099-12-31"\n'
TODAY = date(2026, 9, 22)


def project(tmp_path, text=""):
    (tmp_path / "polyweave.toml").write_text(text, encoding="utf-8")
    return tmp_path


def bought(tmp_path, **over):
    fields = {"out": "a.glb", "task_id": "t_1", "credits": 30, "root": tmp_path}
    fields.update(over)
    return purchase.capture(GLTF, **fields)


# -- the ceiling is the thing approved ---------------------------------------------


def test_a_live_budget_leaves_what_it_declared(tmp_path):
    left = purchase.remaining(project(tmp_path, LIVE), TODAY)
    assert left["declared"] == 60.0
    assert left["spent"] == 0
    assert left["left"] == 60.0
    assert left["spendable"] is True


def test_what_is_left_falls_as_it_is_spent(tmp_path):
    where = project(tmp_path, LIVE)
    bought(where, out="a.glb", task_id="t_1", credits=30)
    left = purchase.remaining(where, TODAY)
    assert left["spent"] == 30.0
    assert left["left"] == 30.0


def test_a_spend_inside_the_ceiling_is_allowed_without_asking(tmp_path):
    where = project(tmp_path, LIVE)
    assert purchase.allow(30, root=where, today=TODAY)["left"] == 60.0


def test_a_spend_past_the_ceiling_is_refused(tmp_path):
    where = project(tmp_path, LIVE)
    bought(where, out="a.glb", task_id="t_1", credits=50)
    with pytest.raises(PolyweaveError) as caught:
        purchase.allow(30, root=where, today=TODAY)
    assert caught.value.code == "fetch.over-budget"
    assert "10.0 credits left" in caught.value.message
    assert "above 80" in caught.value.remedy


def test_a_budget_nobody_set_permits_nothing(tmp_path):
    """The absence of a ceiling is never read as permission."""
    where = project(tmp_path)
    assert purchase.remaining(where, TODAY)["spendable"] is False
    with pytest.raises(PolyweaveError) as caught:
        purchase.allow(1, root=where, today=TODAY)
    assert caught.value.code == "fetch.budget-closed"
    assert "never read as permission" in caught.value.remedy


def test_an_expired_budget_permits_nothing(tmp_path):
    where = project(tmp_path, '[budget]\ncredits = 60\nexpires = "2020-01-01"\n')
    with pytest.raises(PolyweaveError) as caught:
        purchase.allow(1, root=where, today=TODAY)
    assert caught.value.code == "fetch.budget-closed"
    assert "expired" in caught.value.message


def test_a_budget_spent_to_the_last_credit_permits_nothing(tmp_path):
    where = project(tmp_path, LIVE)
    bought(where, out="a.glb", task_id="t_1", credits=60)
    assert purchase.remaining(where, TODAY)["spendable"] is False
    with pytest.raises(PolyweaveError) as caught:
        purchase.allow(1, root=where, today=TODAY)
    assert caught.value.code == "fetch.budget-closed"
    assert "used up" in caught.value.message


# -- what a call really cost --------------------------------------------------------


def test_the_cost_is_the_difference_between_two_readings(tmp_path):
    """Not what the caller believed it would cost."""
    where = project(tmp_path, LIVE)
    entry = bought(where, credits=30, balance_before=100.0, balance_after=72.0)
    assert entry["credits"] == 28.0
    assert entry["expected_credits"] == 30.0
    assert entry["balance_before"] == 100.0
    assert entry["balance_after"] == 72.0


def test_a_cost_that_was_not_what_was_expected_is_flagged(tmp_path):
    where = project(tmp_path, LIVE)
    surprised = bought(where, credits=30, balance_before=100.0, balance_after=50.0)
    assert surprised["surprised"] is True
    assert surprised["credits"] == 50.0


def test_a_cost_that_matched_is_not_flagged(tmp_path):
    where = project(tmp_path, LIVE)
    entry = bought(where, credits=30, balance_before=100.0, balance_after=70.0)
    assert entry["surprised"] is False


def test_a_call_claimed_to_be_free_is_verifiable(tmp_path):
    """Which is what makes the free-probe technique checkable rather than asserted."""
    where = project(tmp_path, LIVE)
    entry = bought(where, credits=0, balance_before=100.0, balance_after=100.0)
    assert entry["credits"] == 0.0
    assert entry["surprised"] is False
    assert purchase.spent(where) == 0.0


def test_the_measured_cost_is_what_counts_against_the_ceiling(tmp_path):
    where = project(tmp_path, LIVE)
    bought(where, credits=1, balance_before=100.0, balance_after=45.0)
    assert purchase.spent(where) == 55.0
    assert purchase.remaining(where, TODAY)["left"] == 5.0


def test_without_two_readings_the_expected_cost_is_recorded(tmp_path):
    where = project(tmp_path, LIVE)
    entry = bought(where, credits=30)
    assert entry["credits"] == 30.0
    assert entry["balance_before"] is None
    assert entry["surprised"] is False


# -- the ledger is the artefact a person reviews --------------------------------------


def test_the_record_beside_the_artefact_carries_the_same_numbers(tmp_path):
    from polyweave import provenance

    where = project(tmp_path, LIVE)
    bought(where, credits=30, balance_before=100.0, balance_after=72.0)
    record = provenance.read("a.glb", root=where)
    assert record["credits"] == 28.0
    assert record["balance_before"] == 100.0


def test_a_review_reads_every_spend_in_order(tmp_path):
    where = project(tmp_path, LIVE)
    bought(where, out="a.glb", task_id="t_1", credits=10)
    bought(where, out="b.glb", task_id="t_2", credits=20)
    held = purchase.read(where)
    assert [e["task_id"] for e in held] == ["t_1", "t_2"]
    assert purchase.spent(where) == 30.0
