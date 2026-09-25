"""A variation measured against its parent (§PW170).

The service is replaced: it returns whatever picture the test says the edit came back
as, so what is tested is the lineage and what is measured against it.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import picture, provenance, variation
from polyweave.errors import PolyweaveError

PROJECT = (
    '[service]\nbase = "https://api.ideogram.ai"\nkey_env = "POLYWEAVE_TEST_I"\n'
    'prices = { "edit" = 0.06, "remix" = 0.06 }\n\n'
    '[budget]\ncredits = 60\nexpires = "2099-12-31"\n'
)
DESCRIBED = {
    "compositional_deconstruction": {
        "elements": [
            {"type": "obj", "desc": "the left hand", "bbox": [500, 0, 1000, 500]},
            {"type": "obj", "desc": "a round body", "bbox": [0, 0, 1000, 1000]},
        ]
    }
}


def figure(hand=(200, 60, 60), body=(242, 193, 78), wide=0):
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    pen.ellipse((8 - wide, 8, 56 + wide, 56), fill=body + (255,))
    pen.rectangle((4, 40, 28, 60), fill=hand + (255,))  # inside the left-hand box
    return image


def png(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def parent(tmp_path, monkeypatch):
    (tmp_path / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_I", "sk")
    figure().save(tmp_path / "hero.png")
    (tmp_path / "hero.prompt.json").write_text(json.dumps(DESCRIBED), "utf-8")
    sent = {}

    def send(endpoint, key, payload, files=None):
        sent.update(endpoint=endpoint, payload=payload, files=files)
        answer = {"created": "t", "data": [{"seed": 3, "url": "https://p/v.png"}]}
        return 200, json.dumps(answer).encode()

    monkeypatch.setattr(picture, "_send", send)
    return sent


def came_back(monkeypatch, image):
    monkeypatch.setattr(picture, "_download", lambda link: png(image))


def test_a_variation_records_its_parent_and_its_mask(tmp_path, parent, monkeypatch):
    came_back(monkeypatch, figure(hand=(60, 60, 200)))
    entry = variation.vary(
        "hero.png",
        "hero_lantern.png",
        "holding a lantern",
        region="left hand",
        root=tmp_path,
    )
    assert parent["endpoint"].endswith("/v1/ideogram-v3/inpaint")
    assert set(parent["files"]) == {"image", "mask"}
    assert entry["credits"] == 0.06
    record = provenance.read("hero_lantern.png", root=tmp_path)
    assert record["details"]["parent"]["path"] == "hero.png"
    assert record["details"]["mask"] == "hero_lantern.mask.png"
    # the parent is an input, so a replaced parent names this variation
    assert record["inputs"][0]["path"] == "hero.png"
    with Image.open(tmp_path / "hero_lantern.mask.png") as mask:
        assert mask.getpixel((10, 50)) == 0 and mask.getpixel((50, 10)) == 255


def test_an_edit_that_kept_everything_outside_its_mask_passes(
    tmp_path, parent, monkeypatch
):
    came_back(monkeypatch, figure(hand=(60, 60, 200)))
    variation.vary(
        "hero.png", "v.png", "holding a lantern", region="left hand", root=tmp_path
    )
    found = variation.against_parent("v.png", root=tmp_path)
    assert found["passed"] is True, found["failed"]


def test_an_edit_that_redrew_what_it_was_not_asked_to_is_refused(
    tmp_path, parent, monkeypatch
):
    came_back(monkeypatch, figure(hand=(60, 60, 200), body=(230, 120, 40), wide=4))
    variation.vary(
        "hero.png", "v.png", "holding a lantern", region="left hand", root=tmp_path
    )
    found = variation.against_parent("v.png", root=tmp_path)
    assert found["passed"] is False
    assert any("redrew what it was not asked to" in f for f in found["failed"])


def test_a_region_must_name_exactly_one_described_element(tmp_path, parent):
    with pytest.raises(PolyweaveError) as caught:
        variation.vary("hero.png", "v.png", "x", region="a", root=tmp_path)
    assert caught.value.code == "fetch.no-region"
    assert parent == {}


def test_a_remix_sends_its_strength_and_no_mask(tmp_path, parent, monkeypatch):
    came_back(monkeypatch, figure())
    variation.vary(
        "hero.png", "r.png", "in winter", change="remix", strength=70, root=tmp_path
    )
    assert parent["endpoint"].endswith("/v1/ideogram-v3/remix")
    assert parent["payload"]["image_weight"] == 70
    assert set(parent["files"]) == {"image"}


def test_a_picture_with_no_parent_has_nothing_to_hold_it_against(tmp_path, parent):
    provenance.write(
        provenance.build("fetch", tmp_path / "hero.png", root=tmp_path), root=tmp_path
    )
    with pytest.raises(PolyweaveError) as caught:
        variation.against_parent("hero.png", root=tmp_path)
    assert caught.value.code == "fetch.no-parent"
