"""Buying a mesh from Rodin, behind the same mesh.buy (§PW446).

The service is replaced with the shapes Hyper3D's v2 API answers: a form-posted task
that answers its `uuid` and `jobs.subscription_key`, a status call listing each job's
`status`, and a download call whose `list` names each file and its url. Rodin
publishes no balance, so the cost is the project's quoted price and not measured.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import mesh_buy, picture, purchase
from polyweave.errors import PolyweaveError

GLB = b"glTF" + b"\x00" * 60
PROJECT = (
    '[service.rodin]\nbase = "https://hyperhuman.deemos.com"\n'
    'key_env = "POLYWEAVE_TEST_R"\nprices = { "Gen-2" = 1.5 }\n\n'
    '[budget.rodin]\namount = 10\nunit = "USD"\nexpires = "2099-12-31"\n'
)


class Rodin:
    """Tasks whose two jobs are done on the second status call."""

    def __init__(self):
        self.forms, self.calls, self.polls = [], [], 0

    def form(self, url, key, fields, files):
        self.forms.append((url, dict(fields), [field for field, _ in files]))
        return {"uuid": "task-9", "jobs": {"uuids": ["j1", "j2"],
                                           "subscription_key": "sub-9"}}

    def json(self, method, url, key, payload=None):
        self.calls.append((url, payload))
        if url.endswith("/api/v2/status"):
            self.polls += 1
            state = "Generating" if self.polls < 2 else "Done"
            return {"jobs": [{"uuid": "j1", "status": "Done"},
                             {"uuid": "j2", "status": state}]}
        return {"list": [{"name": "preview.webp", "url": "https://r/p.webp"},
                         {"name": "base_basic_shaded.glb", "url": "https://r/m.glb"}]}


@pytest.fixture
def rodin(tmp_path, monkeypatch):
    (tmp_path / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_R", "rk")
    fake = Rodin()
    monkeypatch.setattr(mesh_buy, "_form", fake.form)
    monkeypatch.setattr(mesh_buy, "_json", fake.json)
    monkeypatch.setattr(mesh_buy, "POLL_EVERY", 0)
    monkeypatch.setattr(picture, "_download", lambda link: GLB)
    return fake


def test_a_mesh_from_words_on_rodin_is_bought_quoted_and_ledgered(tmp_path, rodin):
    entry = mesh_buy.buy(out="m/drone.glb", prompt="a spiked drone", model="Gen-2",
                         polycount=8000, root=tmp_path)
    url, fields, images = rodin.forms[0]
    assert url == "https://hyperhuman.deemos.com/api/v2/rodin"
    assert fields["tier"] == "Gen-2" and fields["mesh_mode"] == "Quad"
    assert fields["quality_override"] == 8000 and fields["prompt"] == "a spiked drone"
    assert images == []
    assert ("https://hyperhuman.deemos.com/api/v2/download",
            {"task_uuid": "task-9"}) in rodin.calls
    assert entry["task_id"] == "rodin:task-9"
    # No balance to read: the quoted price, said as not measured.
    assert entry["credits"] == 1.5 and entry["measured"] is False
    assert (tmp_path / "m" / "drone.glb").read_bytes() == GLB
    assert purchase.spent(tmp_path, "rodin") == 1.5


def test_a_gated_picture_and_its_views_go_up_as_images(tmp_path, rodin):
    def drawn(name, box):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(200, 60, 60, 255))
        image.save(tmp_path / name)

    for name in ("front", "side"):
        drawn(f"{name}_outline.png", (14, 44, 114, 84))
        drawn(f"{name}.png", (15, 44, 115, 84))
        picture.gate([f"{name}.png"], f"{name}_outline.png", root=tmp_path)
    mesh_buy.buy(out="m/pad.glb", picture_path="front.png", views=["side.png"],
                 model="Gen-2", root=tmp_path)
    _, fields, images = rodin.forms[0]
    assert images == ["images", "images"] and "prompt" not in fields


def test_the_ceiling_holds_before_anything_is_sent(tmp_path, rodin):
    (tmp_path / C.FILENAME).write_text(PROJECT.replace("amount = 10", "amount = 1"),
                                       encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        mesh_buy.buy(out="m/x.glb", prompt="a cube", model="Gen-2", root=tmp_path)
    assert caught.value.code == "fetch.over-budget"
    assert rodin.forms == []
