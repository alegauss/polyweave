"""A paid provider is an adapter, and one buy spends through it (§PW516)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from polyweave.kernel import config as C
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import mesh_buy
from polyweave.layers.picture import picture, scenario, variation
from polyweave.layers.sound import sound_buy
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
            submit=self.submit, poll=self.poll, deliver=self.deliver,
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

    def deliver(self, order, task, finished):
        return S.Delivery(task=task, body=b"RIFF" + b"\x00" * 40,
                          details={"peals": 3})

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


def test_a_request_the_provider_refused_owes_nothing(project):
    bells = Bells()

    def refused(order):
        raise PolyweaveError("fetch.prompt-refused", "no bells", "ask for another")

    with pytest.raises(PolyweaveError):
        S.buy(S.Service(**{**vars(bells.service), "submit": refused}), _order(project))
    assert purchase.owed(project) == []


def test_a_task_taken_and_never_finished_stays_owed_against_the_ceiling(project):
    bells = Bells()

    def cracked(order, task, report):
        raise PolyweaveError("fetch.service-error", "the bell cracked", "ask again")

    with pytest.raises(PolyweaveError):
        S.buy(S.Service(**{**vars(bells.service), "poll": cracked}), _order(project))
    [owed] = purchase.owed(project)
    assert owed["credits"] == 4.0 and owed["service"] == "bells"
    assert purchase.read(project) == []
    assert purchase.remaining(str(project), service="bells")["left"] == 6.0


def test_a_link_that_cannot_be_read_is_owed_with_it_for_collecting(
    project, monkeypatch
):
    bells = Bells()

    def linked(order, task, finished):
        return S.Delivery(task=task, link="https://bells.example/peal.wav")

    def unread(link):
        raise PolyweaveError("fetch.service-error", "gone", "again")

    monkeypatch.setattr(S, "download", unread)
    with pytest.raises(PolyweaveError) as refused:
        S.buy(S.Service(**{**vars(bells.service), "deliver": linked}), _order(project))
    assert refused.value.code == "fetch.nothing-arrived"
    [owed] = purchase.owed(project)
    assert owed["task_id"] == "bells:peal-1"
    assert owed["link"] == "https://bells.example/peal.wav"
    monkeypatch.setattr(S, "download", lambda link: b"RIFF" + b"\x00" * 40)
    entry = S.delivered(owed["link"], owed["capture"], project)
    assert entry["task_id"] == "bells:peal-1" and purchase.owed(project) == []


def test_each_mesh_provider_is_an_adapter_found_by_its_host():
    assert {"meshy", "tripo", "rodin"} <= set(S.providers())
    assert S.provider("https://openapi.tripo3d.com/v3", "mesh", "meshy").name == "tripo"
    assert S.provider("https://hyperhuman.deemos.com", "mesh", "meshy").name == "rodin"
    assert S.provider("https://api.meshy.ai", "mesh", "meshy").name == "meshy"


#: What only `buy` may call: the ceiling, the owed list and the ledger's capture.
SPENDING = {"purchase.allow", "purchase.allow_priced", "purchase.capture",
            "purchase.owe", "purchase.settle"}


def test_no_layer_spends_except_through_buy():
    import polyweave.layers

    spent = []
    for path in Path(polyweave.layers.__path__[0]).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and f"{node.func.value.id}.{node.func.attr}" in SPENDING):
                spent.append(f"{path.name}:{node.lineno} {node.func.attr}")
    assert spent == []


@pytest.mark.parametrize("module", [mesh_buy, picture, variation, scenario, sound_buy],
                         ids=lambda module: module.__name__.rsplit(".", 1)[-1])
def test_a_paid_domain_speaks_no_http_itself(module):
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "urllib.request" not in source and "client.send" not in source


def test_each_paid_provider_is_an_adapter():
    assert set(S.providers()) == {"meshy", "tripo", "rodin", "ideogram", "scenario",
                                  "elevenlabs"}


def test_the_domain_shapes_the_bytes_before_they_are_kept(project):
    def shaped(body, details):
        return b"RIFF-shaped" + body[4:], {**details, "shaped": True}

    order = S.Order(**{**vars(_order(project)), "shaped": shaped})
    S.buy(Bells().service, order)
    assert (project / "bell.wav").read_bytes().startswith(b"RIFF-shaped")
    record = __import__("polyweave.kernel.provenance", fromlist=["read"]).read(
        "bell.wav", project)
    assert record["details"]["shaped"] is True


def _peals(order, task, finished):
    return S.Delivery(task=task, reported=3.0, engine={"tier": "free"}, parts=tuple(
        S.Part(task=f"{task}-{i}", body=b"RIFF" + bytes([i]) * 40, out=f"p{i}.wav")
        for i in (1, 2, 3)))


def test_one_call_delivering_several_parts_splits_its_charge(project):
    bells = Bells(balance=False)
    entries = S.buy(S.Service(**{**vars(bells.service), "deliver": _peals}),
                    _order(project))
    assert [one["task_id"] for one in entries] == [
        "bells:peal-1-1", "bells:peal-1-2", "bells:peal-1-3"]
    assert [one["credits"] for one in entries] == [1.0, 1.0, 1.0]
    assert purchase.owed(project) == []


def test_parts_split_what_the_balance_measured_never_charge_it_on_each(project):
    entries = S.buy(S.Service(**{**vars(Bells().service), "deliver": _peals}),
                    _order(project))
    assert sum(one["credits"] for one in entries) == pytest.approx(4.0, abs=1e-5)
