"""A capture held to its concept painting, region by region (§PW477)."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from polyweave import provenance
from polyweave.errors import PolyweaveError
from polyweave.reference_concept import concept

CONCEPT = """\
painting = "design/screen.png"

[region.header]
painting = [0, 0, 200, 60]
capture  = [0, 0, 300, 90]

[region.board]
painting = [20, 100, 160, 160]
capture  = [30, 150, 240, 240]
"""


def scene(size, header, board, *, stripes=True):
    """A screen: a header band, and a board with a pattern in it."""
    w, h = size
    picture = Image.new("RGB", size, (40, 30, 60))
    pen = ImageDraw.Draw(picture)
    pen.rectangle((0, 0, w, h * 0.2), fill=header)
    x0, y0, side = w * 0.1, h * 0.333, w * 0.8
    pen.rectangle((x0, y0, x0 + side, y0 + side), fill=board)
    if stripes:
        for k in range(4):
            top = y0 + side * k / 4
            pen.rectangle((x0, top, x0 + side, top + side / 8), fill=(250, 240, 200))
    return picture


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "design").mkdir()
    (tmp_path / "shots").mkdir()
    scene((200, 300), (220, 80, 120), (60, 140, 200)).save(
        tmp_path / "design" / "screen.png")
    (tmp_path / "design" / "screen.concept.toml").write_text(CONCEPT, encoding="utf-8")
    return tmp_path


def test_a_faithful_capture_at_another_size_reads_as_the_painting(project):
    scene((300, 450), (220, 80, 120), (60, 140, 200)).save(project / "shots" / "a.png")
    found = concept("design/screen.concept.toml", "shots/a.png", out="shots/sheets",
                    root=str(project))
    header, board = found["regions"]["header"], found["regions"]["board"]
    assert header["palette_delta_e"] < 3
    assert board["palette_delta_e"] < 3
    assert board["structure"] > 0.8
    assert board["luma_p50_ratio"] == pytest.approx(1.0, abs=0.1)
    assert board["edge_density"]["ratio"] == pytest.approx(1.0, abs=0.35)
    sheet = project / board["sheet"]
    assert sheet.is_file()
    record = provenance.read(str(sheet), root=project)
    assert {i["role"] for i in record["inputs"]} == {"reference", "capture"}
    assert record["params"]["region"] == "board"


def test_a_capture_that_drifted_says_where_and_how(project):
    # The header lost its pink, and the board lost its stripes.
    scene((300, 450), (120, 120, 120), (60, 140, 200), stripes=False).save(
        project / "shots" / "b.png")
    found = concept("design/screen.concept.toml", "shots/b.png", root=str(project))
    header, board = found["regions"]["header"], found["regions"]["board"]
    assert header["palette_delta_e"] > 10
    assert header["saturation_p90_ratio"] < 0.3
    assert board["edge_density"]["ratio"] < 0.3
    assert board["structure"] < 0.6
    assert "sheet" not in board


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("capture  = [0, 0, 300, 90]", "capture  = [0, 0, 900, 90]"), "runs off"),
        (("capture  = [0, 0, 300, 90]", ""), "capture is None"),
        (('painting = "design/screen.png"', 'painting = "design/none.png"'),
         "no painting"),
        (("[region.board]", "[region.board]\nscale = 2"), "rectangles only"),
    ],
)
def test_a_concept_that_cannot_be_held_is_refused(project, change, said):
    scene((300, 450), (220, 80, 120), (60, 140, 200)).save(project / "shots" / "a.png")
    path = project / "design" / "screen.concept.toml"
    path.write_text(CONCEPT.replace(*change), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        concept("design/screen.concept.toml", "shots/a.png", root=str(project))
    assert refused.value.code == "capture.bad-concept"
    assert said in refused.value.message + refused.value.remedy
