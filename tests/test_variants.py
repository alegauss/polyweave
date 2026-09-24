"""A family of models in one document (§PW103)."""

from __future__ import annotations

import json

import pytest

from polyweave import cli
from polyweave import geometry as G
from polyweave.errors import PolyweaveError

SHIP = """name = "ship"
output = "hull"

[params]
span = 4

[materials.hull]
colour = "#808080"

[voxels]
cell = 1

[[nodes]]
id = "hull"
op = "plate"
rect = [0, 0, "span", 2]
depth = 1
material = "hull"

[variants.scout]
span = 2

[variants.boss]
span = 8

[variants.boss.materials.hull]
colour = "#C03030"
glow = 1.5
"""


def shipped(tmp_path, body=SHIP):
    (tmp_path / "ship.toml").write_text(body, encoding="utf-8")
    return G.read("ship.toml", root=tmp_path)


def test_a_variant_is_the_document_with_its_overrides(tmp_path):
    document = shipped(tmp_path)
    assert G.variants(document) == ["boss", "scout"]
    boss = G.variant(document, "boss")
    assert boss["name"] == "ship_boss"
    assert boss["params"]["span"] == 8
    assert boss["materials"]["hull"] == {"colour": "#C03030", "glow": 1.5}
    assert "variants" not in boss
    # and the document it came from is untouched
    assert document["params"]["span"] == 4
    assert document["materials"]["hull"] == {"colour": "#808080"}


@pytest.mark.parametrize(
    "extra",
    [
        "[variants.odd]\nspam = 3\n",
        '[variants.odd.materials.glass]\ncolour = "#FFFFFF"\n',
    ],
)
def test_a_variant_setting_what_the_shape_lacks_is_refused(tmp_path, extra):
    document = shipped(tmp_path, SHIP + "\n" + extra)
    with pytest.raises(PolyweaveError) as refused:
        G.variant(document, "odd")
    assert refused.value.code == "geom.unknown-name"


def test_a_variant_nobody_declared_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        G.variant(shipped(tmp_path), "titan")
    assert refused.value.code == "geom.unknown-name"


def test_a_build_writes_every_member_and_reads_them_side_by_side(tmp_path, capsys):
    shipped(tmp_path)
    status = cli.main(["build", "ship.toml", "--root", str(tmp_path), "--json"])
    answer = json.loads(capsys.readouterr().out)
    assert status == 0
    assert [one["name"] for one in answer["members"]] == [
        "ship",
        "ship_boss",
        "ship_scout",
    ]
    spans = [
        one["says"].split(" by ")[0].rsplit(" ", 1)[1] for one in answer["members"]
    ]
    assert spans == ["4", "8", "2"]
    for name in ("ship", "ship_boss", "ship_scout"):
        assert (tmp_path / f"{name}.voxels.json").is_file()
    boss = json.loads((tmp_path / "ship_boss.voxels.json").read_text(encoding="utf-8"))
    assert boss["palette"][0]["colour"] == "#C03030"


def test_the_printed_readback_names_each_member(tmp_path, capsys):
    shipped(tmp_path)
    cli.main(["build", "ship.toml", "--root", str(tmp_path)])
    printed = capsys.readouterr().out
    assert "  ship_boss:" in printed
    assert "    = a voxel model 8 by 2 by 1" in printed
