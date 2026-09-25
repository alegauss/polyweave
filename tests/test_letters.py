"""Reading the letters back (§PW169).

No OCR engine is installed where these run, so the reading is replaced: what is tested
is what the plugin does with what an engine reads, and what it says when there is none.
"""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import config as C
from polyweave import picture


@pytest.fixture
def titled(tmp_path):
    (tmp_path / C.FILENAME).write_text(
        '[capture]\nlocale = "pt_BR"\n', encoding="utf-8"
    )
    Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(tmp_path / "title.png")
    return tmp_path


def engine(monkeypatch, read):
    monkeypatch.setattr("shutil.which", lambda name: "/bin/tesseract")
    seen = {}

    def reader(found, path, language):
        seen["language"] = language
        return read

    monkeypatch.setattr(picture, "_read_letters", reader)
    return seen


def test_lettering_read_back_as_asked_passes(titled, monkeypatch):
    seen = engine(monkeypatch, "  Coração\nde   PELÚCIA \n")
    found = picture.letters("title.png", ["coração", "de pelúcia"], root=titled)
    assert found["checked"] is True
    assert found["passed"] is True
    # the project's locale decides the reader's language
    assert seen["language"] == "por"


def test_a_dropped_accent_is_the_defect_and_is_never_folded_away(titled, monkeypatch):
    engine(monkeypatch, "Coracao\n")
    found = picture.letters("title.png", ["Coração"], root=titled)
    assert found["passed"] is False
    assert found["texts"] == [{"asked": "Coração", "read": "coracao", "passed": False}]


def test_no_engine_is_a_stated_gap_and_never_a_pass(titled, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    found = picture.letters("title.png", ["Coração"], root=titled)
    assert found["checked"] is False
    assert found["passed"] is None
    assert "unchecked, which is not a pass" in found["why"]


def test_the_lettering_is_read_off_the_record_by_default(titled, monkeypatch):
    from polyweave import provenance

    record = provenance.build(
        "fetch",
        titled / "title.png",
        extra={
            "details": {
                "json_prompt": {
                    "compositional_deconstruction": {
                        "elements": [
                            {"type": "obj", "desc": "a heart"},
                            {"type": "text", "text": "Amor"},
                        ]
                    }
                }
            }
        },
        root=titled,
    )
    provenance.write(record, root=titled)
    engine(monkeypatch, "amor")
    found = picture.letters("title.png", root=titled)
    assert [one["asked"] for one in found["texts"]] == ["Amor"]
    assert found["passed"] is True


def test_a_picture_with_no_lettering_declared_has_nothing_to_check(titled):
    found = picture.letters("title.png", root=titled)
    assert found["checked"] is False
    assert found["why"] == "no lettering was declared for this picture"


def test_the_gate_refuses_a_picture_whose_lettering_came_back_wrong(
    tmp_path, monkeypatch
):
    from PIL import ImageDraw

    (tmp_path / C.FILENAME).write_text("", encoding="utf-8")
    for name in ("outline.png", "sign.png"):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((14, 44, 114, 84), fill=(200, 60, 60, 255))
        image.save(tmp_path / name)
    engine(monkeypatch, "Cafe")
    monkeypatch.setattr(picture, "_declared_text", lambda path, here: ["Café"])
    found = picture.gate(["sign.png"], "outline.png", root=tmp_path)
    assert found["chosen"] is None
    assert found["candidates"][0]["failed"] == [
        "lettering: asked for 'Café', read 'cafe'"
    ]
