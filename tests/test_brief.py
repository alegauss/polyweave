"""An asset's brief in one read (§PW131)."""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import brief, loop, provenance
from polyweave.errors import PolyweaveError

SHAPE = """name = "crate"
output = "crate"

[params]
size = 4

[voxels]
cell = 1

[[nodes]]
id = "crate"
op = "primitive"
kind = "cube"
size = "size"
"""

SPEC = """asset = "crate"
artefact = "renders/crate.png"

[[predicate]]
id      = "tone"
measure = "luma_p99"
region  = "frame"
max     = { value = 0.37, origin = "margin", measured = 0.34 }
"""


def project(tmp_path):
    (tmp_path / "shapes").mkdir()
    (tmp_path / "shapes" / "crate.toml").write_text(SHAPE, encoding="utf-8")
    (tmp_path / "docs" / "accept").mkdir(parents=True)
    (tmp_path / "docs" / "accept" / "crate.accept.toml").write_text(
        SPEC, encoding="utf-8"
    )
    (tmp_path / "renders").mkdir()
    Image.new("RGBA", (8, 8), (90, 90, 90, 255)).save(
        tmp_path / "renders" / "crate.png"
    )
    provenance.write(
        provenance.build("render", tmp_path / "renders" / "crate.png", root=tmp_path),
        root=tmp_path,
    )
    return tmp_path


def test_one_read_says_where_the_asset_stands(tmp_path):
    root = project(tmp_path)
    run = loop.start("crate", "after", root=root)
    loop.judged(
        run,
        tool_passed=False,
        person_accepted=True,
        check={"predicates": [{"id": "tone", "value": 0.4, "passed": False}]},
    )
    loop.finish(run, root=root)

    found = brief.brief("crate", root=str(root))
    assert found["declaration"]["path"] == "shapes/crate.toml"
    assert found["declaration"]["reads"]
    tone = found["spec"]["predicates"][0]
    assert tone["max"]["origin"] == "margin"
    assert found["artefact"]["matches_record"] is True
    assert found["last_verdict"]["failed"] == ["tone"]
    assert found["last_verdict"]["person_accepted"] is True
    assert len(found["digest"]) == 16


def test_the_digest_moves_when_the_asset_does(tmp_path):
    root = project(tmp_path)
    before = brief.brief("crate", root=str(root))["digest"]
    assert brief.brief("crate", root=str(root))["digest"] == before
    Image.new("RGBA", (8, 8), (200, 90, 90, 255)).save(root / "renders" / "crate.png")
    after = brief.brief("crate", root=str(root))
    assert after["digest"] != before
    assert after["artefact"]["matches_record"] is False


def test_an_asset_nothing_names_is_refused_with_the_ones_that_exist(tmp_path):
    root = project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        brief.brief("crat", root=str(root))
    assert "crat" in refused.value.message
