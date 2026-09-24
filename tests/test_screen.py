"""The same bar, on the screen the player sees (§PW112)."""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import accept, capture, cli, provenance
from polyweave.errors import PolyweaveError

#: Flat greys by byte: 200 reads 0.578 in linear luma and 102 reads 0.133.
BRIGHT, DARK = 200, 102

SPEC = """asset = "star"
artefact = "sprites/star.png"
screen = {{ capture = "captures/title.png", region = "{region}" }}

[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"
region  = "frame"
max     = 0.37
"""


def project(tmp_path, *, baked, on_screen, region="star"):
    """A dark bake, and a capture where the star is drawn in `on_screen`'s grey."""
    (tmp_path / "docs" / "accept").mkdir(parents=True)
    (tmp_path / "docs" / "accept" / "star.accept.toml").write_text(
        SPEC.format(region=region), encoding="utf-8"
    )
    (tmp_path / "sprites").mkdir()
    Image.new("RGBA", (16, 16), (baked, baked, baked, 255)).save(
        tmp_path / "sprites" / "star.png"
    )
    (tmp_path / "captures").mkdir()
    shot = Image.new("RGB", (64, 32), (20, 20, 20))
    shot.paste((on_screen,) * 3, (40, 8, 56, 24))
    shot.save(tmp_path / "captures" / "title.png")
    record = provenance.build(
        "capture",
        tmp_path / "captures" / "title.png",
        extra={"regions": {"star": [40, 8, 56, 24]}},
        root=tmp_path,
    )
    provenance.write(record, root=tmp_path)
    return tmp_path


def test_a_capture_script_says_where_it_drew_each_thing():
    log = "frame 12\nregion: star_dim=412,96,508,192\nregion: cloud=0,0,10,10\n"
    assert capture.regions(log) == {
        "star_dim": [412, 96, 508, 192],
        "cloud": [0, 0, 10, 10],
    }


def test_the_spec_is_checked_on_the_rectangle_the_capture_named(tmp_path):
    root = project(tmp_path, baked=DARK, on_screen=DARK)
    spec = accept.read(root / "docs" / "accept" / "star.accept.toml")
    found = accept.check_screen(spec, root=root)
    assert found["passed"]
    assert found["screen"]["box"] == [40, 8, 56, 24]
    assert found["predicates"][0]["value"] == pytest.approx(0.133, abs=1e-3)


def test_a_star_that_passes_baked_and_fails_on_screen_is_said(tmp_path):
    root = project(tmp_path, baked=DARK, on_screen=BRIGHT)
    (one,) = accept.verify(root)["specs"]
    assert one["baked"] == "passed"
    assert one["screen"]["status"] == "failed"
    assert one["status"] == "failed"
    assert "the engine draws it differently" in one["disagree"]


def test_the_command_prints_the_screen_answer(tmp_path, capsys):
    root = project(tmp_path, baked=DARK, on_screen=BRIGHT)
    assert cli.main(["verify", "--root", str(root)]) == 1
    printed = capsys.readouterr().out
    assert "on screen: no-hot-facet" in printed
    assert "draws it differently" in printed


def test_a_region_the_capture_never_printed_is_refused_with_the_ones_it_did(tmp_path):
    root = project(tmp_path, baked=DARK, on_screen=DARK, region="moon")
    spec = accept.read(root / "docs" / "accept" / "star.accept.toml")
    with pytest.raises(PolyweaveError) as refused:
        accept.check_screen(spec, root=root)
    assert refused.value.code == "spec.no-screen"
    assert "star" in refused.value.remedy
    (one,) = accept.verify(root)["specs"]
    assert one["screen"]["status"] == "refused"
    assert one["status"] == "refused"


@pytest.mark.parametrize(
    "screen",
    ["captures/title.png", {"capture": "c.png"}, {"capture": "c.png", "region": 3}],
)
def test_a_screen_that_does_not_say_where_is_refused(screen):
    with pytest.raises(PolyweaveError) as refused:
        accept.parse(
            {
                "asset": "star",
                "screen": screen,
                "predicate": [{"id": "a", "measure": "luma_p99", "max": 1.0}],
            }
        )
    assert refused.value.code == "spec.unknown-field"
