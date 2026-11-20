"""A thumbnail held to its title and to the size a feed shows it at (§PW699)."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store.thumbnail import thumbnail

TITLE = "30 mil merges por dia: o Git não aguentou e a Anthropic..."


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    picture = Image.new("RGB", (1280, 720), (20, 20, 20))
    pen = ImageDraw.Draw(picture)
    # A tall white line on black, a small one, and one grey on grey.
    for x in range(100, 700, 40):
        pen.rectangle((x, 100, x + 20, 220), fill=(250, 250, 250))
    for x in range(100, 400, 20):
        pen.rectangle((x, 400, x + 10, 440), fill=(250, 250, 250))
    pen.rectangle((100, 500, 700, 620), fill=(120, 120, 120))
    for x in range(100, 700, 40):
        pen.rectangle((x, 500, x + 20, 620), fill=(135, 135, 135))
    picture.save(tmp_path / "thumb.png")
    return tmp_path


def test_a_thumbnail_repeating_its_title_is_named_word_by_word(project):
    said = thumbnail("thumb.png", TITLE, texts=["O Git não aguentou",
                                                "30 mil merges por dia"],
                     language="pt-BR", root=str(project))
    assert said["passed"] is False
    assert said["words"] == 9
    assert set(said["shared"]) == {"30", "mil", "merges", "dia", "git", "aguentou"}
    assert any("past 6" in one for one in said["failed"])
    assert all(one.get("unmeasured") for one in said["lines"])


def test_a_thumbnail_that_adds_to_its_title_passes_on_words(project):
    said = thumbnail("thumb.png", TITLE, texts=["Monorepo quebrou"],
                     language="pt-BR", root=str(project))
    assert said["shared"] == [] and said["passed"] is True


def test_each_line_is_measured_at_feed_size(project):
    said = thumbnail("thumb.png", TITLE, texts=[
        {"text": "Tall", "box": [100, 100, 700, 220]},
        {"text": "small", "box": [100, 400, 400, 440]},
        {"text": "faint", "box": [100, 500, 700, 620]},
    ], root=str(project))
    tall, small, faint = said["lines"]
    assert tall["passed"] is True and tall["height_px"] == pytest.approx(15.8, abs=0.2)
    assert small["passed"] is False and small["height_px"] < 8
    assert faint["passed"] is False and faint["contrast"] < 3
    assert said["passed"] is False and len(said["failed"]) == 2


def test_a_missing_thumbnail_is_refused(project):
    with pytest.raises(PolyweaveError) as refused:
        thumbnail("none.png", TITLE, texts=[], root=str(project))
    assert refused.value.code == "store.no-thumbnail"


def test_the_passing_variants_are_laid_for_a_person_and_the_rest_say_why(project):
    from polyweave.layers.store.thumbnail import thumbnails

    drawn = (project / "thumb.png").read_bytes()
    for name in ("a", "b", "c", "d"):
        (project / f"{name}.png").write_bytes(drawn)
    said = thumbnails([
        {"picture": "a.png", "texts": ["O Git não aguentou"]},
        {"picture": "b.png", "texts": ["Monorepo quebrou"]},
        {"picture": "c.png", "texts": ["Fila de espera"]},
        {"picture": "d.png", "texts": ["Quem pagou a conta"]},
    ], TITLE, language="pt-BR", keep=2, out="review/thumbs", root=str(project))
    assert said["laid"] == ["b.png", "c.png"]
    rest = {one["picture"]: one["why"] for one in said["rest"]}
    assert set(rest) == {"a.png", "d.png"}
    assert "repeats" in rest["a.png"]
    assert "past the 2 laid out" in rest["d.png"]
    assert said["sitting"]
    assert (project / "review" / "thumbs" / "thumbnail.png").is_file()


def test_no_passing_variant_lays_nothing(project):
    from polyweave.layers.store.thumbnail import thumbnails

    said = thumbnails([{"picture": "thumb.png", "texts": ["o Git não aguentou"]}],
                      TITLE, language="pt-BR", root=str(project))
    assert said["laid"] == [] and said["sitting"] is None
