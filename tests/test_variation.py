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


def preserving(tmp_path):
    """A service that says its edit leaves the unmasked pixels alone (§PW209)."""
    (tmp_path / C.FILENAME).write_text(
        PROJECT.replace("[budget]", "preserves = true\n\n[budget]"), "utf-8"
    )


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
    preserving(tmp_path)
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


# -- reframing an approved picture (§PW181) ------------------------------------------


def reframed(parent, size, at, scale=1.0, touch=None):
    """The parent set into a wider frame with a new border drawn round it."""
    frame = Image.new("RGBA", size, (90, 140, 200, 255))
    placed = (
        parent
        if scale == 1.0
        else parent.resize(
            (round(parent.width * scale), round(parent.height * scale)), Image.LANCZOS
        )
    )
    frame.alpha_composite(placed, at)
    if touch:
        ImageDraw.Draw(frame).rectangle(touch, fill=(10, 200, 10, 255))
    return frame


def solid_parent():
    image = figure()
    ground = Image.new("RGBA", image.size, (255, 255, 255, 255))
    ground.alpha_composite(image)
    return ground


def test_a_reframe_sends_the_frame_and_no_prompt(tmp_path, parent, monkeypatch):
    (tmp_path / C.FILENAME).write_text(
        PROJECT.replace('"remix" = 0.06', '"remix" = 0.06, "reframe" = 0.06'), "utf-8"
    )
    solid_parent().save(tmp_path / "hero.png")
    came_back(monkeypatch, reframed(solid_parent(), (160, 64), (48, 0)))
    variation.vary(
        "hero.png", "wide.png", change="reframe", resolution="1536x640", root=tmp_path
    )
    assert parent["endpoint"].endswith("/v1/ideogram-v3/reframe")
    assert parent["payload"] == {"resolution": "1536x640"}
    found = variation.against_parent("wide.png", root=tmp_path)
    assert found["passed"] is True, found["failed"]
    assert found["placed"]["scale"] == 1.0
    assert (found["placed"]["x"], found["placed"]["y"]) == (48, 0)


def test_a_reframe_that_fitted_the_parent_to_the_frame_is_found(
    tmp_path, parent, monkeypatch
):
    (tmp_path / C.FILENAME).write_text(
        PROJECT.replace('"remix" = 0.06', '"reframe" = 0.06'), "utf-8"
    )
    solid_parent().save(tmp_path / "hero.png")
    came_back(monkeypatch, reframed(solid_parent(), (96, 48), (24, 0), scale=0.75))
    variation.vary(
        "hero.png", "small.png", change="reframe", resolution="96x48", root=tmp_path
    )
    found = variation.against_parent("small.png", root=tmp_path)
    assert found["placed"]["scale"] == 0.75
    assert found["passed"] is True, found["failed"]


def test_a_reframe_that_redrew_the_parent_is_refused(tmp_path, parent, monkeypatch):
    (tmp_path / C.FILENAME).write_text(
        PROJECT.replace('"remix" = 0.06', '"reframe" = 0.06').replace(
            "[budget]", "preserves = true\n\n[budget]"
        ),
        "utf-8",
    )
    solid_parent().save(tmp_path / "hero.png")
    came_back(
        monkeypatch,
        reframed(solid_parent(), (160, 64), (48, 0), touch=(60, 10, 90, 40)),
    )
    variation.vary(
        "hero.png", "wide.png", change="reframe", resolution="1536x640", root=tmp_path
    )
    found = variation.against_parent("wide.png", root=tmp_path)
    assert found["passed"] is False
    assert "redrew what it was asked to keep" in found["failed"][0]


def test_a_reframe_with_no_frame_is_refused_before_anything_is_sent(tmp_path, parent):
    with pytest.raises(PolyweaveError) as caught:
        variation.vary("hero.png", "wide.png", change="reframe", root=tmp_path)
    assert caught.value.code == "fetch.missing-field"
    assert parent == {}


# -- what a person means by kept (§PW209) --------------------------------------------


def _varied(tmp_path, monkeypatch, out, image):
    came_back(monkeypatch, image)
    variation.vary(
        "hero.png", out, "holding a lantern", region="left hand", root=tmp_path
    )


def _accepted(tmp_path, *paths):
    """A sitting of variations, and a person's accept of each on the review page."""
    from polyweave import verdict

    families = {p: [{"name": p, "new": p}] for p in paths}
    sheets = {p: {"sheet": str(tmp_path / p), "members": []} for p in paths}
    verdict._manifest(tmp_path / "review", families, sheets, tmp_path)
    for p in paths:
        verdict.record_answer(
            {
                "choice": "accept",
                "why": "still the hero",
                "members": [{"name": p, "person_accepted": True}],
            },
            sitting="review/sitting.json",
            family=p,
            root=tmp_path,
        )


def test_a_redrawing_service_is_measured_as_kept_and_unjudged_at_first(
    tmp_path, parent, monkeypatch
):
    _varied(
        tmp_path, monkeypatch, "v.png", figure(hand=(60, 60, 200), body=(230, 120, 40))
    )
    found = variation.against_parent("v.png", root=tmp_path)
    assert found["instrument"] == "kept"
    assert "unmasked_delta_e" not in found
    assert found["kept"]["judged"] is False
    assert found["kept"]["floor"].startswith("none: 0 accepted variations")
    assert found["kept"]["look"]["saturation_p95"]["off"] != 0
    assert found["passed"] is True


def test_a_variation_is_held_to_the_spread_of_the_ones_a_person_accepted(
    tmp_path, parent, monkeypatch
):
    _varied(tmp_path, monkeypatch, "a.png", figure(hand=(60, 60, 200)))
    _varied(
        tmp_path, monkeypatch, "b.png", figure(hand=(60, 200, 60), body=(240, 190, 80))
    )
    _accepted(tmp_path, "a.png", "b.png")
    _varied(tmp_path, monkeypatch, "kept.png", figure(hand=(200, 200, 60)))
    kept = variation.against_parent("kept.png", root=tmp_path)
    assert kept["kept"]["judged"] is True and kept["kept"]["accepted"] == 2
    assert kept["passed"] is True, kept["failed"]
    _varied(tmp_path, monkeypatch, "far.png", figure(body=(60, 90, 200), wide=6))
    far = variation.against_parent("far.png", root=tmp_path)
    assert far["passed"] is False
    assert any("the accepted variations moved" in f for f in far["failed"])


def test_a_reframe_by_a_redrawing_service_reports_kept_not_pixels(
    tmp_path, parent, monkeypatch
):
    (tmp_path / C.FILENAME).write_text(
        PROJECT.replace('"remix" = 0.06', '"reframe" = 0.06'), "utf-8"
    )
    solid_parent().save(tmp_path / "hero.png")
    came_back(
        monkeypatch,
        reframed(solid_parent(), (160, 64), (48, 0), touch=(60, 10, 90, 40)),
    )
    variation.vary(
        "hero.png", "wide.png", change="reframe", resolution="1536x640", root=tmp_path
    )
    found = variation.against_parent("wide.png", root=tmp_path)
    assert found["instrument"] == "kept"
    assert found["placed"]["x"] == 48
    assert "held_delta_e" not in found and found["kept"]["judged"] is False
