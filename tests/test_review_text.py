"""A sitting that explains itself, in the project's language (§PW287).

Starship's owner opened the trails sitting and could not tell what they were voting on.
Every kind of sitting now carries a title, a summary and each choice with what it leads
to, from one catalog per language beside the page.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from polyweave import review, review_text, verdict
from polyweave.errors import PolyweaveError


def test_every_catalog_holds_the_same_words():
    """A key the Portuguese catalog lacks would show the key itself to the person."""
    english = review_text.catalog("en")
    assert "pt-BR" in review_text.languages()
    for speaks in review_text.languages():
        other = review_text.catalog(speaks)
        assert set(other["page"]) == set(english["page"]), speaks
        assert set(other["kinds"]) == set(english["kinds"]), speaks
        for kind, text in english["kinds"].items():
            assert set(other["kinds"][kind]) == set(text), (speaks, kind)
            assert set(other["kinds"][kind]["choices"]) == set(text["choices"])


def test_a_sitting_says_what_it_is_and_what_each_choice_leads_to(tmp_path):
    (tmp_path / "polyweave.toml").write_text('[review]\nlanguage = "pt-BR"\n', "utf-8")
    (tmp_path / "a.png").write_bytes(b"")
    families = {"trail": [{"name": "trail", "new": "a.png", "passed": True}]}
    sheets = {"trail": {"sheet": str(tmp_path / "a.png"), "members": []}}
    verdict._manifest(tmp_path / "review", families, sheets, tmp_path, kind="effect",
                      about="Compare com o que você aprovou.",
                      abouts={"trail": "O rastro da nave."})
    manifest = json.loads((tmp_path / "review" / "sitting.json").read_text("utf-8"))
    assert manifest["language"] == "pt-BR"
    assert manifest["title"] == "Efeitos visuais para aprovar"
    assert manifest["about"].endswith("Compare com o que você aprovou.")
    assert manifest["choices"]["accept"]["label"] == "Aceitar"
    assert manifest["choices"]["look"]["then"]
    assert manifest["legend"]["reach"]
    assert manifest["families"]["trail"]["about"] == "O rastro da nave."


def test_a_language_with_no_catalog_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text('[review]\nlanguage = "xx"\n', "utf-8")
    with pytest.raises(PolyweaveError) as refused:
        review_text.language(tmp_path)
    assert refused.value.code == "config.bad-language"


def test_the_page_reads_its_own_words_from_the_catalog(tmp_path):
    (tmp_path / "polyweave.toml").write_text('[review]\nlanguage = "pt-BR"\n', "utf-8")
    served = review.server(tmp_path)
    threading.Thread(target=served.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{served.server_address[1]}"
        with urllib.request.urlopen(base + "/locales/pt-BR.json") as answer:
            assert json.load(answer)["page"]["record"] == "Registrar minha decisão"
        with urllib.request.urlopen(base + "/api/state") as answer:
            assert json.load(answer)["language"] == "pt-BR"
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/locales/..%2Fpage.js")
    finally:
        served.shutdown()


# The page is the decision screen the window draws (§PW403): these hold its sources, in
# gui/packages, and the bundle built from them that the page serves.


def screen(path):
    return (Path(__file__).parents[1] / "gui" / "packages" / path).read_text("utf-8")


def test_the_page_holds_still_while_a_person_answers():
    """§PW289: a whole redraw between two clicks replaced the button pressed."""
    decide = screen("ui/src/Decide.tsx")
    # The files are read again only while no card holds a choice, a word or a box.
    assert "if (busy.current.size === 0) void read()" in decide
    assert "onHold(card, Boolean(picked || why.trim() || marked))" in decide
    # An answer reads the files once more; a card keeps its own state, keyed by name.
    assert "<Card key={name}" in decide


def test_an_older_sitting_is_read_through_the_catalog():
    """§PW293: sittings laid out before PW287 kept their choices as English strings."""
    assert "words.kinds[kind]?.choices?.[word]" in screen("core/src/desk.ts")
    # Every choice key an older sitting carries is one the catalog can answer for.
    for kind in ("look", "effect", "line", "sound"):
        assert {"accept", "look"} <= set(review_text.kind(kind, "pt-BR")["choices"])


def test_a_summary_reads_as_a_legend_and_each_sitting_stands_apart():
    """§PW295: the summary's choices looked like buttons, and sittings ran together."""
    decide = screen("ui/src/Decide.tsx")
    start = decide.index("<ul data-how")
    how = decide[start:decide.index("</ul>", start)]
    # A list of what each choice means, never a button.
    assert "<li" in how
    assert "<Button" not in how
    assert "<section data-sitting" in decide


def test_no_sentence_a_person_reads_is_kept_in_the_page_s_code():
    """The page takes every word from the catalog, so its script names only keys."""
    script = (Path(review.SCREEN) / "review.js").read_text(encoding="utf-8")
    for sentence in ("Record this verdict", "Registrar", "Pick one choice"):
        assert sentence not in script
