"""Buying a mesh from Tripo, behind the same mesh.buy (§PW445).

The service is replaced with the shapes Tripo's v3 reference documents: a create that
answers `data.task_id`, a task read at /tasks/<id> whose `data.output.model_url` is the
mesh, a balance under `data.balance`, and a picture sent up to /files for a
`file_token`. What is tested is that the same ceiling, gate and ledger hold, and CI
spends nothing.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import mesh_buy, picture, purchase
from polyweave.errors import PolyweaveError

GLB = b"glTF" + b"\x00" * 60
PROJECT = (
    '[service.tripo]\nbase = "https://openapi.tripo3d.com/v3"\n'
    'key_env = "POLYWEAVE_TEST_T"\nprices = { "v2.5-20250123" = 20 }\n\n'
    '[budget.tripo]\namount = 60\nexpires = "2099-12-31"\n'
)


class Tripo:
    """A balance, and tasks that finish on the second poll."""

    def __init__(self):
        self.balance, self.sent, self.polls = 200.0, [], 0

    def __call__(self, method, url, key, payload=None):
        if url.endswith("/account/balance"):
            return {"code": 0, "data": {"balance": self.balance, "frozen": 0.0}}
        if method == "POST":
            self.sent.append((url, payload))
            self.balance -= 20.0
            return {"code": 0, "data": {"task_id": "task_abc123"}}
        self.polls += 1
        if self.polls < 2:
            return {"code": 0, "data": {"status": "running", "progress": 50}}
        return {"code": 0, "data": {"task_id": "task_abc123", "status": "success",
                                    "progress": 100,
                                    "output": {"model_url": "https://t/x.glb"}}}


@pytest.fixture
def tripo(tmp_path, monkeypatch):
    (tmp_path / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_T", "tsk")
    fake = Tripo()
    monkeypatch.setattr(mesh_buy, "_json", fake)
    monkeypatch.setattr(mesh_buy, "_uploaded", lambda base, key, source: "file_1")
    monkeypatch.setattr(mesh_buy, "POLL_EVERY", 0)
    monkeypatch.setattr(picture, "_download", lambda link: GLB)
    return fake


def test_a_mesh_from_words_on_tripo_is_bought_measured_and_ledgered(tmp_path, tripo):
    entry = mesh_buy.buy(out="m/drone.glb", prompt="a spiked drone",
                         model="v2.5-20250123", polycount=4000, root=tmp_path)
    url, payload = tripo.sent[0]
    assert url == "https://openapi.tripo3d.com/v3/generation/text-to-model"
    assert payload == {"model_version": "v2.5-20250123", "texture": False,
                       "face_limit": 4000, "prompt": "a spiked drone"}
    assert entry["task_id"] == "tripo:task_abc123" and entry["service"] == "tripo"
    # The two balance readings measured it.
    assert entry["credits"] == 20.0 and entry["measured"] is True
    assert (tmp_path / "m" / "drone.glb").read_bytes() == GLB
    assert purchase.spent(tmp_path, "tripo") == 20.0


def test_a_gated_picture_is_sent_up_first_and_named_by_its_token(tmp_path, tripo):
    def drawn(name, box):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(200, 60, 60, 255))
        image.save(tmp_path / name)

    drawn("outline.png", (14, 44, 114, 84))
    drawn("mote.png", (15, 44, 115, 84))
    assert picture.gate(["mote.png"], "outline.png", root=tmp_path)["chosen"]
    entry = mesh_buy.buy(out="m/mote.glb", picture_path="mote.png",
                         model="v2.5-20250123", root=tmp_path)
    url, payload = tripo.sent[0]
    assert url == "https://openapi.tripo3d.com/v3/generation/image-to-model"
    assert payload["file"] == {"type": "png", "file_token": "file_1"}
    assert "image_url" not in payload
    assert entry["reference"] == "mote.png"


def test_the_ceiling_holds_before_anything_is_sent_up(tmp_path, tripo):
    (tmp_path / C.FILENAME).write_text(PROJECT.replace("amount = 60", "amount = 10"),
                                       encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        mesh_buy.buy(out="m/x.glb", prompt="a cube", model="v2.5-20250123",
                     root=tmp_path)
    assert caught.value.code == "fetch.over-budget"
    assert tripo.sent == []


def test_a_failed_task_is_refused_with_the_service_s_reason(tmp_path, tripo,
                                                           monkeypatch):
    def failing(method, url, key, payload=None):
        if url.endswith("/account/balance"):
            return {"data": {"balance": 100.0}}
        if method == "POST":
            return {"data": {"task_id": "t2"}}
        return {"data": {"status": "failed", "error_message": "prompt rejected"}}

    monkeypatch.setattr(mesh_buy, "_json", failing)
    with pytest.raises(PolyweaveError) as caught:
        mesh_buy.buy(out="m/x.glb", prompt="a cube", model="v2.5-20250123",
                     root=tmp_path)
    assert "prompt rejected" in str(caught.value)
    assert purchase.read(tmp_path) == []
