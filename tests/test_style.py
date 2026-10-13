"""A style declared once, and a canon only a person grows (§PW166)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import config as C
from polyweave import picture, style, verdict
from polyweave.errors import PolyweaveError

SPEC = """asset = "{name}"

[[predicate]]
id      = "dim"
measure = "luma_p99"
region  = "frame"
max     = {{ value = 0.9, origin = "margin", measured = 0.5 }}
"""

STYLES = (
    '[style.characters]\ncanon = "art/canon/characters"\n'
    'palette = ["#f2c14e", "#3a2e39"]\n'
    'skeleton = { medium = "flat vector", lighting = "soft" }\n\n'
    '[style.icons]\ncanon = "art/canon/icons"\npalette = ["#ffffff"]\n'
)
STRUCTURED = {
    "high_level_description": "a plush booster",
    "compositional_deconstruction": {"background": "none", "elements": []},
    "style_description": {"medium": "oil painting", "aesthetics": "cosy"},
}


def project(tmp_path, text):
    (tmp_path / C.FILENAME).write_text(text, encoding="utf-8")
    return tmp_path


def refused(call, *args, **kwargs) -> PolyweaveError:
    with pytest.raises(PolyweaveError) as caught:
        call(*args, **kwargs)
    return caught.value


# -- declared once, per family -------------------------------------------------------


def test_each_family_declares_its_own_look(tmp_path):
    found = C.load(project(tmp_path, STYLES)).styles()
    assert sorted(found) == ["characters", "icons"]
    assert found["icons"]["palette"] == ["#ffffff"]
    assert found["characters"]["canon"].endswith("characters")


def test_a_bare_style_is_one_family(tmp_path):
    where = project(tmp_path, '[style]\npalette = ["#000000"]\n')
    family, declared = C.load(where).style()
    assert family == "default"
    assert declared["palette"] == ["#000000"]
    assert declared["canon"] == "" and declared["skeleton"] == {}


def test_a_palette_colour_is_a_value_not_a_name(tmp_path):
    error = refused(C.load, project(tmp_path, '[style]\npalette = ["gold"]\n'))
    assert error.code == "config.bad-type"


def test_naming_no_family_among_several_is_refused(tmp_path):
    config = C.load(project(tmp_path, STYLES))
    assert refused(config.style).code == "style.family-unnamed"
    assert refused(config.style, "icon").code == "style.unknown-family"


def test_the_skeleton_wins_and_the_palette_is_the_familys():
    composed = style.compose(
        STRUCTURED,
        {"skeleton": {"medium": "flat vector"}, "palette": ["#f2c14e"]},
    )
    described = composed["style_description"]
    assert described["medium"] == "flat vector"
    assert described["aesthetics"] == "cosy"  # what the skeleton leaves unsaid
    assert described["color_palette"] == ["#f2c14e"]
    assert STRUCTURED["style_description"]["medium"] == "oil painting"  # not mutated


# -- every picture carries it --------------------------------------------------------


@pytest.fixture
def service(tmp_path, monkeypatch):
    project(
        tmp_path,
        '[service]\nbase = "https://api.ideogram.ai"\nkey_env = "POLYWEAVE_TEST_I"\n'
        'prices = { "4.0" = 0.08 }\n\n'
        '[budget]\ncredits = 60\nexpires = "2099-12-31"\n\n' + STYLES,
    )
    monkeypatch.setenv("POLYWEAVE_TEST_I", "sk")
    sent = []

    def send(endpoint, key, payload, files=None):
        sent.append(payload)
        answer = {"created": "x", "data": [{"seed": 1, "url": "https://p/x.png"}]}
        return 200, json.dumps(answer).encode()

    monkeypatch.setattr(picture, "_send", send)
    monkeypatch.setattr(picture, "_download", lambda link: b"\x89PNG" + b"\0" * 60)
    return sent


def test_a_bought_picture_carries_its_familys_style(tmp_path, service):
    picture.buy(out="p.png", json_prompt=STRUCTURED, family="characters", root=tmp_path)
    sent = json.loads(service[0]["json_prompt"])
    assert sent["style_description"]["medium"] == "flat vector"
    assert sent["style_description"]["color_palette"] == ["#f2c14e", "#3a2e39"]


def test_a_text_prompt_has_nowhere_to_carry_a_style(tmp_path, service):
    error = refused(
        picture.buy, out="p.png", prompt="a booster", family="icons", root=tmp_path
    )
    assert error.code == "style.needs-structure"
    assert service == []


# -- canon pictures as style references (§PW180) ---------------------------------------


@pytest.fixture
def referenced(tmp_path, monkeypatch):
    """A family that sends two canon pictures as style references, on 3.0."""
    project(
        tmp_path,
        '[service]\nbase = "https://api.ideogram.ai"\nkey_env = "POLYWEAVE_TEST_I"\n'
        'prices = { "4.0" = 0.08, "3.0" = 0.06 }\n\n'
        '[budget]\ncredits = 60\nexpires = "2099-12-31"\n\n'
        '[style.characters]\ncanon = "art/canon/characters"\n'
        'palette = ["#f2c14e", "#3a2e39"]\n'
        'skeleton = { medium = "flat vector", lighting = "soft" }\n'
        'references = ["ada.png", "bo.png"]\n',
    )
    canon = tmp_path / "art" / "canon" / "characters"
    canon.mkdir(parents=True)
    for name, byte in (("ada.png", 200), ("bo.png", 90)):
        Image.new("RGBA", (8, 8), (byte, byte, byte, 255)).save(canon / name)
    monkeypatch.setenv("POLYWEAVE_TEST_I", "sk")
    sent = []

    def send(endpoint, key, payload, files=None):
        sent.append({"endpoint": endpoint, "payload": payload, "files": files})
        answer = {"created": "x", "data": [{"seed": 1, "url": "https://p/x.png"}]}
        return 200, json.dumps(answer).encode()

    monkeypatch.setattr(picture, "_send", send)
    monkeypatch.setattr(picture, "_download", lambda link: b"\x89PNG" + b"\0" * 60)
    return sent


def test_a_family_with_references_sends_its_canon_pictures_on_3(tmp_path, referenced):
    entry = picture.buy(out="p.png", prompt="Ada waving", model="3.0",
                        family="characters", root=tmp_path)
    [call] = referenced
    assert call["endpoint"].endswith("/v1/ideogram-v3/generate-transparent")
    assert [(f, name) for f, (name, _, _) in call["files"]] == [
        ("style_reference_images", "ada.png"), ("style_reference_images", "bo.png")]
    # A text prompt carries the skeleton and the palette in words.
    assert call["payload"]["prompt"] == (
        "Ada waving. Style: lighting soft; medium flat vector. "
        "Palette: #f2c14e, #3a2e39.")
    record = json.loads((tmp_path / "p.png.prov.json").read_text(encoding="utf-8"))
    held = record["details"]["references"]
    assert [one["picture"] for one in held] == ["ada.png", "bo.png"]
    assert all(len(one["sha256"]) == 64 for one in held)
    assert entry["credits"] == 0.06


def test_a_family_with_references_is_refused_where_they_would_be_dropped(
    tmp_path, referenced
):
    error = refused(picture.buy, out="p.png", prompt="Ada", family="characters",
                    root=tmp_path)
    assert error.code == "style.references-need-3"
    assert error.call["arguments"]["model"] == "3.0"
    error = refused(picture.buy, out="p.png", json_prompt=STRUCTURED, model="3.0",
                    family="characters", root=tmp_path)
    assert error.code == "style.references-take-text"
    assert referenced == []


def test_a_reference_the_canon_does_not_hold_is_named(tmp_path, referenced):
    (tmp_path / "art" / "canon" / "characters" / "bo.png").unlink()
    error = refused(picture.buy, out="p.png", prompt="Ada", model="3.0",
                    family="characters", root=tmp_path)
    assert error.code == "style.no-reference"
    assert "bo.png" in error.message
    assert referenced == []


# -- the canon grows only by a person's verdict --------------------------------------


def member(tmp_path, name, canon):
    (tmp_path / "accept").mkdir(exist_ok=True)
    (tmp_path / "art").mkdir(exist_ok=True)
    (tmp_path / "accept" / f"{name}.accept.toml").write_text(
        SPEC.format(name=name), encoding="utf-8"
    )
    Image.new("RGBA", (16, 16), (120, 120, 120, 255)).save(
        tmp_path / "art" / f"{name}.png"
    )
    (tmp_path / "art" / f"{name}.prompt.json").write_text("{}", encoding="utf-8")
    return {
        "name": name,
        "spec": f"accept/{name}.accept.toml",
        "new": f"art/{name}.png",
        "canon": canon,
    }


def test_an_accepted_picture_joins_its_canon_with_the_verdict(tmp_path):
    project(tmp_path, STYLES)
    said = verdict.judge(
        [member(tmp_path, "booster", "characters")],
        "accept",
        "that is the booster",
        root=tmp_path,
        when="2026-09-25",
    )
    joined = said["members"][0]["canon"]
    assert joined["verdict"] == {
        "choice": "accept",
        "why": "that is the booster",
        "when": "2026-09-25",
    }
    canon = tmp_path / "art" / "canon" / "characters"
    assert (canon / "booster.png").is_file()
    assert (canon / "booster.prompt.json").is_file()
    assert style.read("characters", root=tmp_path)["admitted"] == [joined]


def test_a_rejected_look_joins_no_canon(tmp_path):
    project(tmp_path, STYLES)
    said = verdict.judge(
        [member(tmp_path, "booster", "characters")], "look", "wrong ears", root=tmp_path
    )
    assert said["members"][0]["canon"] is None
    assert style.read("characters", root=tmp_path)["admitted"] == []


def test_admitting_one_picture_twice_is_a_no_op(tmp_path):
    project(tmp_path, STYLES)
    one = member(tmp_path, "booster", "characters")
    for _ in range(2):
        verdict.judge([one], "accept", "yes", root=tmp_path)
    assert len(style.read("characters", root=tmp_path)["admitted"]) == 1


def test_a_family_with_no_canon_directory_refuses_to_admit(tmp_path):
    project(tmp_path, '[style]\npalette = ["#000000"]\n')
    error = refused(
        verdict.judge, [member(tmp_path, "b", "default")], "accept", "ok", root=tmp_path
    )
    assert error.code == "style.no-canon"


def test_nothing_but_a_verdict_can_add_to_a_canon():
    """`admit` is not an operation, so no caller reaches it by name."""
    from polyweave.describe import describe

    names = {one["operation"] for one in describe()}
    assert {"style.read", "style.drift"} <= names
    assert "style.admit" not in names
