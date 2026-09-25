"""Buying a mesh, from words or from a picture the gate passed (§PW183).

The service is replaced: requests are recorded, and the answers are the shapes Meshy's
reference documents, so what is tested is the ceiling, the gate, the balance readings
and the ledger.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import mesh_buy, picture, purchase
from polyweave.errors import PolyweaveError

GLB = b"glTF" + b"\x00" * 60
PROJECT = (
    '[service.meshy]\nbase = "https://api.meshy.ai"\nkey_env = "POLYWEAVE_TEST_M"\n'
    'prices = { "meshy-6-lite" = 5, "meshy-6" = 20 }\n\n'
    '[budget.meshy]\namount = 60\nexpires = "2099-12-31"\n'
)


class Meshy:
    """A balance, and tasks that finish on the second poll."""

    def __init__(self):
        self.balance, self.sent, self.polls = 100.0, [], 0

    def __call__(self, method, url, key, payload=None):
        if url.endswith("/openapi/v1/balance"):
            return {"balance": self.balance}
        if method == "POST":
            self.sent.append((url, payload))
            self.balance -= 5.0
            return {"result": "task-1"}
        self.polls += 1
        if self.polls < 2:
            return {"status": "IN_PROGRESS", "progress": 40}
        return {"status": "SUCCEEDED", "model_urls": {"glb": "https://m/x.glb"}}


@pytest.fixture
def meshy(tmp_path, monkeypatch):
    (tmp_path / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_M", "msy")
    fake = Meshy()
    monkeypatch.setattr(mesh_buy, "_json", fake)
    monkeypatch.setattr(mesh_buy, "POLL_EVERY", 0)
    monkeypatch.setattr(picture, "_download", lambda link: GLB)
    return fake


def refused(**how) -> PolyweaveError:
    with pytest.raises(PolyweaveError) as caught:
        mesh_buy.buy(**how)
    return caught.value


def test_a_mesh_from_words_is_measured_by_two_balance_readings(tmp_path, meshy):
    entry = mesh_buy.buy(out="m/drone.glb", prompt="a spiked drone", root=tmp_path)
    url, payload = meshy.sent[0]
    assert url == "https://api.meshy.ai/openapi/v2/text-to-3d"
    assert payload["mode"] == "preview" and payload["ai_model"] == "meshy-6-lite"
    assert entry["task_id"] == "meshy:task-1" and entry["service"] == "meshy"
    assert entry["credits"] == 5.0 and entry["measured"] is True
    assert (tmp_path / "m" / "drone.glb").read_bytes() == GLB
    assert purchase.spent(tmp_path, "meshy") == 5.0


def test_a_picture_the_gate_never_passed_is_refused(tmp_path, meshy):
    Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(tmp_path / "mote.png")
    error = refused(out="m.glb", picture_path="mote.png", root=tmp_path)
    assert error.code == "fetch.picture-ungated"
    assert meshy.sent == []


def test_a_mesh_from_a_gated_picture_sends_it_and_names_it(tmp_path, meshy):
    def drawn(name, box):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(200, 60, 60, 255))
        image.save(tmp_path / name)

    drawn("outline.png", (14, 44, 114, 84))
    drawn("mote.png", (15, 44, 115, 84))
    assert picture.gate(["mote.png"], "outline.png", root=tmp_path)["chosen"]
    entry = mesh_buy.buy(out="m/mote.glb", picture_path="mote.png", root=tmp_path)
    url, payload = meshy.sent[0]
    assert url == "https://api.meshy.ai/openapi/v1/image-to-3d"
    assert payload["image_url"].startswith("data:image/png;base64,")
    assert payload["should_texture"] is False
    assert entry["reference"] == "mote.png"


def test_a_picture_changed_since_the_gate_is_refused(tmp_path, meshy):
    def drawn(name, box):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(200, 60, 60, 255))
        image.save(tmp_path / name)

    drawn("outline.png", (14, 44, 114, 84))
    drawn("mote.png", (15, 44, 115, 84))
    picture.gate(["mote.png"], "outline.png", root=tmp_path)
    drawn("mote.png", (44, 8, 84, 120))
    assert refused(out="m.glb", picture_path="mote.png", root=tmp_path).code == (
        "fetch.picture-ungated"
    )


def test_a_model_with_no_price_is_refused_before_anything_is_sent(tmp_path, meshy):
    error = refused(out="m.glb", prompt="x", model="meshy-7.1", root=tmp_path)
    assert error.code == "fetch.unpriced" and meshy.sent == []


def test_a_failed_task_ledgers_nothing(tmp_path, meshy, monkeypatch):
    def failing(method, url, key, payload=None):
        if url.endswith("/balance"):
            return {"balance": 100.0}
        if method == "POST":
            return {"result": "t"}
        return {"status": "FAILED", "task_error": {"message": "bad prompt"}}

    monkeypatch.setattr(mesh_buy, "_json", failing)
    error = refused(out="m.glb", prompt="x", root=tmp_path)
    assert "bad prompt" in error.message
    assert purchase.read(tmp_path) == []


def test_buying_a_mesh_is_a_fetch_job():
    from polyweave.describe import describe

    found = next(one for one in describe() if one["operation"] == "mesh.buy")
    assert found["kind"] == "fetch"
    assert "report" not in [one["name"] for one in found["parameters"]]


def test_json_is_a_code_on_refusal(monkeypatch):
    import io
    import urllib.error

    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 402, "no", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    with pytest.raises(PolyweaveError) as caught:
        mesh_buy._json("POST", "https://api.meshy.ai/x", "k", {})
    assert caught.value.code == "fetch.over-budget"
    assert json.dumps({}) == "{}"
