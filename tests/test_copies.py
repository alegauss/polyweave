"""A picture's derived copies, cut from a declared table and recorded (§PW585).

Cottony's site script called a copy stale past a mean and a percentile tuned by hand,
because nothing recorded what each copy was made from. Here the record does.
"""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture.copies import copies

TABLE = """into = "site/assets"
quality = 88

[[copy]]
source = "art/logo.png"
out = "logo.webp"
side = 40

[[copy]]
source = "art/promo.png"
out = "og.jpg"
box = [10, 20, 90, 60]
quality = 80

[[copy]]
source = "art/logo.png"
out = "favicon.png"
side = 16
"""


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "art").mkdir()
    logo = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
    logo.paste((200, 40, 40, 255), (10, 10, 90, 40))
    logo.save(tmp_path / "art" / "logo.png")
    Image.new("RGB", (120, 80), (30, 90, 200)).save(tmp_path / "art" / "promo.png")
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "assets.copies.toml").write_text(TABLE, encoding="utf-8")
    return tmp_path


def cut(tree):
    return copies("site/assets.copies.toml", root=str(tree))


def test_every_row_is_cut_encoded_by_its_extension_and_recorded(tree):
    answer = cut(tree)
    rows = {one["out"]: one for one in answer["written"]}
    assert list(rows) == ["site/assets/logo.webp", "site/assets/og.jpg",
                          "site/assets/favicon.png"]
    assert rows["site/assets/logo.webp"]["size"] == [40, 20]
    assert rows["site/assets/og.jpg"]["size"] == [80, 40]
    assert rows["site/assets/favicon.png"]["size"] == [16, 8]
    with Image.open(tree / "site" / "assets" / "og.jpg") as og:
        assert og.format == "JPEG"
    record = provenance.read(tree / "site" / "assets" / "logo.webp", tree)
    assert {one["path"] for one in record["inputs"]} == {
        "art/logo.png", "site/assets.copies.toml"}
    assert record["params"]["side"] == 40 and record["params"]["quality"] == 88
    assert provenance.outdated(str(tree))["outdated"] == []


def test_a_copy_is_outdated_once_its_source_moves_and_only_its_own(tree):
    cut(tree)
    Image.new("RGB", (120, 80), (220, 220, 30)).save(tree / "art" / "promo.png")
    stale = provenance.outdated(str(tree))["outdated"]
    assert [one["artefact"] for one in stale] == ["site/assets/og.jpg"]
    assert stale[0]["moved"] == ["art/promo.png"]
    cut(tree)
    assert provenance.outdated(str(tree))["sound"] is True


def test_a_missing_source_is_refused_before_anything_is_written(tree):
    (tree / "art" / "promo.png").unlink()
    with pytest.raises(PolyweaveError) as refused:
        cut(tree)
    assert refused.value.code == "copies.missing-source"
    assert "art/promo.png" in refused.value.message
    assert not (tree / "site" / "assets").exists()


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (("[[copy]]", "colour = 1\n\n[[copy]]"), "colour"),
        (('out = "og.jpg"', 'out = "og.gif"'), "og.gif"),
        (("side = 40", 'side = "big"'), "'big'"),
        (("box = [10, 20, 90, 60]", "box = [90, 20, 10, 60]"), "[90, 20, 10, 60]"),
    ],
)
def test_a_table_that_cannot_be_cut_is_refused_with_what_it_takes(tree, change, named):
    table = tree / "site" / "assets.copies.toml"
    table.write_text(TABLE.replace(*change, 1), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        cut(tree)
    assert refused.value.code == "copies.bad-table"
    assert named in refused.value.message
    assert not (tree / "site" / "assets").exists()


def test_a_jpeg_of_a_source_with_transparency_is_refused(tree):
    table = tree / "site" / "assets.copies.toml"
    table.write_text(TABLE.replace('out = "logo.webp"', 'out = "logo.jpg"'), "utf-8")
    with pytest.raises(PolyweaveError) as refused:
        cut(tree)
    assert refused.value.code == "copies.no-alpha"


# -- a copy held to a byte bound, and owing what its source owes (§PW658) -------------


def noisy(tree):
    import numpy as np

    pixels = np.random.default_rng(7).integers(0, 255, (300, 300, 3), dtype=np.uint8)
    Image.fromarray(pixels, "RGB").save(tree / "art" / "photo.png")


def bounded(tree, out: str, bound: int | None):
    row = f'[[copy]]\nsource = "art/photo.png"\nout = "{out}"\nquality = 90\n'
    if bound is not None:
        row += f"max_bytes = {bound}\n"
    (tree / "site" / "photo.copies.toml").write_text(f'into = "site/assets"\n\n{row}',
                                                     encoding="utf-8")
    return copies("site/photo.copies.toml", root=str(tree))


def test_a_webp_steps_its_quality_down_until_it_fits_its_bound(tree):
    # Shio's package allows 300 KB a picture, and its PNGs were 6.8 MB each.
    noisy(tree)
    whole = bounded(tree, "photo.webp", None)["written"][0]["bytes"]
    [made] = bounded(tree, "photo.webp", int(whole * 0.7))["written"]
    assert made["bytes"] <= int(whole * 0.7)
    assert made["quality"] < 90
    record = provenance.read("site/assets/photo.webp", root=str(tree))
    assert record["params"]["max_bytes"] == int(whole * 0.7)


def test_a_png_over_its_bound_is_refused_and_not_left(tree):
    noisy(tree)
    with pytest.raises(PolyweaveError) as refused:
        bounded(tree, "photo.png", 1000)
    assert refused.value.code == "copies.over-bytes"
    assert not (tree / "site" / "assets" / "photo.png").exists()


def test_a_copy_owes_what_the_picture_it_was_cut_from_owes(tree):
    noisy(tree)
    provenance.write(provenance.build(
        "picture", tree / "art" / "photo.png",
        engine={"name": "ideogram", "tier": "free"},
        extra={"credit": "Pictures by Ideogram"}, root=tree), tree)
    bounded(tree, "photo.webp", None)
    said = provenance.credits(root=str(tree))
    [owed] = said["owed"]
    assert "site/assets/photo.webp" in owed["files"]
    free = {one["file"]: one for one in said["non_commercial"]}
    assert free["site/assets/photo.webp"]["via"] == "art/photo.png"