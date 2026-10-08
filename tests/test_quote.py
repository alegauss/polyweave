"""What a paid call would cost, asked before it runs (§PW308)."""

from __future__ import annotations

import pytest

from polyweave import describe, purchase, revision
from polyweave.errors import PolyweaveError

PROJECT = (
    '[service.ideogram]\nbase = "https://api.ideogram.ai"\n'
    'key_env = "POLYWEAVE_TEST_I"\n'
    'prices = { "4.0" = 0.08, "4.0:QUALITY" = 5.0, "describe" = 0.01, '
    '"edit" = 0.06 }\n\n'
    '[budget.ideogram]\namount = 1.0\nunit = "USD"\nexpires = "2099-12-31"\n'
)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text(PROJECT, encoding="utf-8")
    return tmp_path


def test_the_registry_marks_every_operation_that_spends():
    paid = sorted(o["operation"] for o in describe.describe() if o.get("spends"))
    assert paid == [
        "mesh.buy", "picture.buy", "picture.describe", "picture.vary", "sound.buy",
        "sound.speak",
    ]


def test_a_call_is_priced_as_the_operation_prices_itself(project):
    plain = purchase.quote("picture.buy", {"prompt": "a star"}, root=str(project))
    found = (plain["service"], plain["model"], plain["price"])
    assert found == ("ideogram", "4.0", 0.08)
    assert plain["left"] == 1.0 and plain["after"] == 0.92
    assert plain["affordable"] is True
    assert plain["cheaper"] == "picture.fit"
    dear = purchase.quote(
        "mcp__polyweave__picture_buy", {"rendering_speed": "QUALITY"}, root=str(project)
    )
    assert dear["price"] == 5.0 and dear["affordable"] is False
    assert purchase.quote("picture.describe", {}, root=str(project))["price"] == 0.01
    assert purchase.quote("picture.vary", {}, root=str(project))["price"] == 0.06


def test_a_free_operation_has_no_price(project):
    with pytest.raises(PolyweaveError) as refused:
        purchase.quote("picture.fit", {}, root=str(project))
    assert refused.value.code == "fetch.not-paid"
    assert "picture.buy" in refused.value.as_dict()["allowed"]


def test_a_revision_asks_every_paid_call_and_ties_its_spend(project):
    from PIL import Image

    from polyweave import provenance

    (project / "art").mkdir()
    Image.new("RGBA", (4, 4)).save(project / "art" / "icon.png")
    provenance.write(
        provenance.build("picture", project / "art" / "icon.png", root=project),
        root=project,
    )
    asked = revision.ask("art/icon.png", "warmer", root=str(project))["revision"]
    made = revision.settings(asked, root=str(project))
    assert "mcp__polyweave__picture_buy" in made["permissions"]["ask"]
    assert made["env"] == {"POLYWEAVE_REVISION": asked}
    purchase.append(
        {"service": "ideogram", "credits": 0.08, "revision": asked,
         "artefact": "x.png"},
        root=project,
    )
    closed = revision.close(asked, withdrawn="enough", root=str(project))
    assert closed["spent"] == {"ideogram": 0.08}
