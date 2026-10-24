"""A capture held to its concept painting, region by region (§PW477)."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.reference.reference_concept import concept

CONCEPT = """\
painting = "design/screen.png"

[region.header]
painting = [0, 0, 200, 60]
capture  = [0, 0, 300, 90]

[region.board]
painting = [20, 100, 160, 160]
capture  = [30, 150, 240, 240]
"""


def scene(size, header, board, *, stripes=True, low=0):
    """A screen: a header band, and a board with a pattern in it, `low` pixels down."""
    w, h = size
    picture = Image.new("RGB", size, (40, 30, 60))
    pen = ImageDraw.Draw(picture)
    pen.rectangle((0, 0, w, h * 0.2), fill=header)
    x0, y0, side = w * 0.1, h * 0.333 + low, w * 0.8
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
    assert board["geometry"]["moved"] is False
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


def test_a_region_that_sits_low_says_so_as_geometry(project):
    """§PW477: a board 30 px low is a move, not a colour difference."""
    scene((300, 450), (220, 80, 120), (60, 140, 200), low=30).save(
        project / "shots" / "low.png")
    found = concept("design/screen.concept.toml", "shots/low.png", root=str(project))
    geometry = found["regions"]["board"]["geometry"]
    assert geometry["moved"] is True
    assert geometry["offset"][1] == pytest.approx(30, abs=4)
    assert abs(geometry["offset"][0]) <= 4
    assert geometry["scale"] == 1.0


def test_a_region_flush_with_the_captures_far_edges_is_measured(tmp_path):
    """§PW619: Cottony's sky below the boosters, a search that slides to the capture's
    bottom edge at a scale whose copy rounds down (1920 x 0.853 is 1638.4, kept as
    1638), is measured rather than crashing the placement search."""
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    scene((1024, 1536), (220, 80, 120), (60, 140, 200)).save(tmp_path / "screen.png")
    scene((1080, 1920), (220, 80, 120), (60, 140, 200)).save(tmp_path / "shot.png")
    (tmp_path / "screen.concept.toml").write_text(
        'painting = "screen.png"\n\n[region.below]\n'
        'painting = [0, 1430, 1024, 106]\ncapture  = [0, 1600, 600, 318]\n',
        encoding="utf-8")
    found = concept("screen.concept.toml", "shot.png", root=str(tmp_path))
    assert "geometry" in found["regions"]["below"]


SPEC = """\
asset = "screen"

[[predicate]]
id      = "board-holds-its-stripes"
measure = "concept_structure"
concept = "design/screen.concept.toml"
region  = "board"
min     = 0.8

[[predicate]]
id      = "board-sits-where-painted"
measure = "concept_offset"
concept = "design/screen.concept.toml"
region  = "board"
max     = 6
"""


def test_a_spec_holds_a_capture_to_a_region_of_the_painting(project):
    """§PW477: a predicate a search can aim at the painting with."""
    from polyweave.loop import accept

    (project / "screen.accept.toml").write_text(SPEC, encoding="utf-8")
    spec = accept.read("screen.accept.toml", project)
    scene((300, 450), (220, 80, 120), (60, 140, 200)).save(project / "shots" / "a.png")
    held = accept.check(spec, project / "shots" / "a.png", root=project)
    assert held["passed"], held["failed"]
    scene((300, 450), (220, 80, 120), (60, 140, 200), stripes=False, low=30).save(
        project / "shots" / "b.png")
    drifted = accept.check(spec, project / "shots" / "b.png", root=project)
    assert set(drifted["failed"]) == {"board-holds-its-stripes",
                                      "board-sits-where-painted"}
    # A margin below one on each, which is what a search climbs.
    assert all(p["margin"] < 1 for p in drifted["predicates"])


def test_a_target_a_share_of_the_way_to_the_painting_is_written_as_its_number(project):
    """§PW620: half the way there means something where 1.0 is the painting."""
    from polyweave.loop import accept, verdict

    (project / "screen.accept.toml").write_text(SPEC, encoding="utf-8")
    # A board a shade off the painting's, its structure just under 1.
    scene((300, 450), (220, 80, 120), (90, 120, 180)).save(project / "shots" / "a.png")
    one = {"name": "screen", "spec": "screen.accept.toml", "new": "shots/a.png"}
    today = next(p["value"] for p in accept.check(
        accept.read("screen.accept.toml", project), project / "shots" / "a.png",
        root=project)["predicates"] if p["id"] == "board-holds-its-stripes")
    said = verdict.target([one], {"board-holds-its-stripes": {"toward": 0.5}},
                          "closer to the painting", root=project)
    reach = round(today + 0.5 * (1.0 - today), 4)
    assert said["members"][0]["targets"] == {"board-holds-its-stripes": {"min": reach}}
    held = {p.id: p for p in accept.read("screen.accept.toml", project).predicates}
    assert held["board-holds-its-stripes"].origins["min"]["target"] is True


def test_a_concept_predicate_naming_no_region_it_declares_is_refused(project):
    from polyweave.loop import accept

    body = SPEC.replace('region  = "board"\nmin', 'region  = "footer"\nmin')
    (project / "screen.accept.toml").write_text(body, encoding="utf-8")
    scene((300, 450), (220, 80, 120), (60, 140, 200)).save(project / "shots" / "a.png")
    with pytest.raises(PolyweaveError) as refused:
        accept.check(accept.read("screen.accept.toml", project),
                     project / "shots" / "a.png", root=project)
    assert refused.value.code == "capture.bad-concept"
    assert set(refused.value.as_dict()["allowed"]) == {"header", "board"}


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
