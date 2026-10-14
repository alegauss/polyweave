"""Live text in a vector picture, outlined before the engine draws it (§PW453).

A dev.to cover with eighteen `<text>` runs came out of picture.vector with its
background, its mark and not one letter, and the call answered an ordinary success:
ThorVG as Godot builds it draws no text.
"""

from __future__ import annotations

import os
import shutil
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image

from polyweave import provenance, svgtext, vector
from polyweave.errors import PolyweaveError

pytest.importorskip("fontTools", reason="fontTools outlines the text")

SVG = "http://www.w3.org/2000/svg"


def blocky(path):
    """A font whose A and B are filled squares, so a drawn letter is plain to find."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    def square():
        pen = TTGlyphPen(None)
        pen.moveTo((50, 0))
        pen.lineTo((50, 700))
        pen.lineTo((550, 700))
        pen.lineTo((550, 0))
        pen.closePath()
        return pen.glyph()

    names = [".notdef", "space", "A", "B"]
    build = FontBuilder(1000, isTTF=True)
    build.setupGlyphOrder(names)
    build.setupCharacterMap({32: "space", 65: "A", 66: "B"})
    build.setupGlyf({".notdef": square(), "space": TTGlyphPen(None).glyph(),
                     "A": square(), "B": square()})
    build.setupHorizontalMetrics({n: (600, 0) for n in names})
    build.setupHorizontalHeader(ascent=800, descent=-200)
    build.setupNameTable({"familyName": "Blocky Fixture", "styleName": "Regular"})
    build.setupOS2()
    build.setupPost()
    build.save(str(path))
    return path


def drawing(body, width=200):
    return ET.ElementTree(ET.fromstring(
        f'<svg xmlns="{SVG}" width="{width}" height="100" viewBox="0 0 {width} 100">'
        f"{body}</svg>"))


def test_each_run_becomes_its_outlines_in_the_declared_font(tmp_path):
    font = blocky(tmp_path / "blocky.ttf")
    tree = drawing('<g font-family="Blocky Fixture" fill="#f00">'
                   '<text x="10" y="80" font-size="50">AB <tspan fill="#0f0">A'
                   "</tspan></text></g>")
    used = svgtext.outlined(tree, [font])
    assert used == [font]
    root = tree.getroot()
    assert not svgtext.texts(root)
    paths = [p for p in root.iter(f"{{{SVG}}}path")]
    assert len(paths) == 2 and paths[1].get("fill") == "#0f0"


def test_a_character_the_font_lacks_is_refused_by_name(tmp_path):
    font = blocky(tmp_path / "blocky.ttf")
    tree = drawing('<text x="0" y="50" font-family="Blocky Fixture">ABC</text>')
    with pytest.raises(PolyweaveError) as refused:
        svgtext.outlined(tree, [font])
    assert refused.value.code == "compose.text-unoutlined"
    assert "'C'" in refused.value.message


def test_a_font_nowhere_is_refused_naming_the_family(tmp_path):
    tree = drawing('<text x="0" y="50" font-family="No Such Family Anywhere">A</text>')
    with pytest.raises(PolyweaveError) as refused:
        svgtext.outlined(tree, [])
    assert refused.value.code == "compose.text-unoutlined"
    assert "No Such Family Anywhere" in refused.value.message


def test_text_along_a_path_is_refused(tmp_path):
    font = blocky(tmp_path / "blocky.ttf")
    tree = drawing('<path id="arc" d="M0 50 Q100 0 200 50"/>'
                   '<text font-family="Blocky Fixture"><textPath href="#arc">AB'
                   "</textPath></text>")
    with pytest.raises(PolyweaveError) as refused:
        svgtext.outlined(tree, [font])
    assert "follows a path" in refused.value.message


def test_a_drawing_with_no_text_is_left_alone(tmp_path):
    tree = drawing('<rect width="10" height="10"/>')
    assert svgtext.outlined(tree, []) == []


def test_picture_vector_draws_the_letters_and_records_the_font(tmp_path):
    if not (os.environ.get("GODOT") or shutil.which("godot")):
        pytest.skip("no $GODOT on this machine: the engine draws a vector")
    (tmp_path / "fonts").mkdir()
    blocky(tmp_path / "fonts" / "blocky.ttf")
    (tmp_path / "polyweave.toml").write_text(
        '[words]\nfonts = [{ path = "fonts/blocky.ttf" }]\n', encoding="utf-8")
    (tmp_path / "banner.svg").write_text(
        f'<svg xmlns="{SVG}" width="200" height="100" viewBox="0 0 200 100">'
        '<text x="20" y="80" font-family="Blocky Fixture" font-size="60" '
        'fill="#ffffff">AB</text></svg>', encoding="utf-8")
    vector.vector("banner.svg", "banner.png", 200, root=str(tmp_path))
    with Image.open(tmp_path / "banner.png") as picture:
        alpha = np.asarray(picture.convert("RGBA"))[..., 3]
    assert (alpha > 127).mean() > 0.1  # two squares of 30 by 42, on 200 by 100
    record = provenance.read("banner.png", tmp_path)
    assert {"role": "font", "path": "fonts/blocky.ttf"}.items() <= {
        **next(i for i in record["inputs"] if i["role"] == "font")}.items()
