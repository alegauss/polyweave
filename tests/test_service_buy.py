"""A paid provider is an adapter, and one buy spends through it (§PW516)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from polyweave.kernel import config as C
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import mesh_buy
from polyweave.services import purchase
from polyweave.services import service as S

PROJECT = (
    '[service.bells]\nbase = "https://bells.example"\nkey_env = "POLYWEAVE_TEST_B"\n'
    'prices = { "bronze" = 4 }\n\n'
    '[budget.bells]\namount = 10\nexpires = "2099-12-31"\n'
)


class Bells:
    """A provider whose tasks finish on the second ask, charging what it was quoted."""

    def __init__(self, *, balance=True):
        self.money, self.submitted, self.asked = 100.0, [], 0
        self.service = S.Service(
            name="bells", media=("sound",), hosts=("bells.example",),
            submit=self.submit, poll=self.poll, fetch=self.fetch,
            balance=self.balance if balance else None, details={"metal": "bronze"},
        )

    def submit(self, order):
        self.submitted.append(order.asked)
        self.money -= 4.0
        return "peal-1"

    def poll(self, order, task, report):
        def ask():
            self.asked += 1
            done = self.asked > 1
            return S.Asked(state="done" if done else "ringing", found={"task": task},
                           said="ringing")

        return S.waited(task, ask, report)

    def fetch(self, order, finished):
        return b"RIFF" + b"\x00" * 40

    def balance(self, base, key):
        return self.money


def _order(root, **asked) -> S.Order:
    return S.Order(service="bells", base="https://bells.example", key="k", price=4.0,
                   asked={"route": "text", **asked}, root=root,
                   kept={"out": "bell.wav", "bought": "sound", "prompt": "a bell"})


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    monkeypatch.setattr(S, "POLL_EVERY", 0)
    return tmp_path


def test_a_purchase_is_allowed_submitted_polled_fetched_and_ledgered(project):
    bells = Bells()
    entry = S.buy(bells.service, _order(project, prompt="a bell"))
    assert bells.submitted == [{"route": "text", "prompt": "a bell"}]
    assert entry["task_id"] == "bells:peal-1" and entry["service"] == "bells"
    assert entry["measured"] is True and entry["credits"] == 4.0
    assert [one["task_id"] for one in purchase.read(project)] == ["bells:peal-1"]
    assert (project / "bell.wav").read_bytes().startswith(b"RIFF")


def test_a_purchase_past_the_ceiling_is_refused_before_anything_is_sent(project):
    bells = Bells()
    S.buy(bells.service, _order(project))
    S.buy(bells.service, _order(project))
    with pytest.raises(PolyweaveError) as refused:
        S.buy(bells.service, _order(project))
    assert refused.value.code == "fetch.over-budget"
    assert len(bells.submitted) == 2


def test_a_provider_with_no_balance_records_its_quote_as_not_measured(project):
    entry = S.buy(Bells(balance=False).service, _order(project))
    assert entry["measured"] is False and entry["credits"] == 4.0


def test_each_mesh_provider_is_an_adapter_found_by_its_host():
    assert {"meshy", "tripo", "rodin"} <= set(S.providers())
    assert S.provider("https://openapi.tripo3d.com/v3", "mesh", "meshy").name == "tripo"
    assert S.provider("https://hyperhuman.deemos.com", "mesh", "meshy").name == "rodin"
    assert S.provider("https://api.meshy.ai", "mesh", "meshy").name == "meshy"


def test_the_mesh_domain_neither_allows_nor_speaks_http_itself():
    source = Path(mesh_buy.__file__).read_text(encoding="utf-8")
    called = {
        f"{node.func.value.id}.{node.func.attr}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
    }
    assert "purchase.allow" not in called and "purchase.capture" not in called
    assert "urllib" not in source and "client.send" not in source
