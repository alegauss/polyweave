"""A reference video's fixed places, declared once, and its minimap read (§PW380).

Resogun's radar strip is the only place its video shows what spawns off camera and on
which side, and at a few dozen pixels a contact sheet guesses it. These frames are drawn
here: a 200 by 20 radar holding the player at its middle, one enemy a quarter of the way
round to the left, and one almost at the right end, which on a strip whose ends meet is
to the player's right.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image, ImageDraw

from polyweave import provenance, reference_regions
from polyweave.config import load
from polyweave.errors import PolyweaveError

DECLARED = """\
[reference.resogun]
size = [400, 200]
regions = { radar = [100, 10, 300, 30], score = [10, 170, 90, 195] }
minimap = "radar"
map = "strip"
player = "#00ff00"
blips = { enemy = "#ff0000" }
"""


def film(tmp_path, size=(400, 200), declared=DECLARED):
    (tmp_path / "polyweave.toml").write_text(declared, encoding="utf-8")
    folder = tmp_path / ".polyweave" / "references" / "clip"
    folder.mkdir(parents=True)
    listed = []
    for n in range(3):
        image = Image.new("RGB", size, (10, 10, 30))
        draw = ImageDraw.Draw(image)
        draw.rectangle((198, 18, 201, 21), fill=(0, 255, 0))  # the player, u = 0.5
        draw.rectangle((148, 18, 151, 21), fill=(255, 0, 0))  # u = 0.25
        draw.rectangle((288 - n, 18, 291 - n, 21), fill=(255, 0, 0))  # u ~ 0.95
        name = f"t{n * 500:08d}.png"
        image.save(folder / name)
        listed.append({"ms": n * 500, "file": name})
    (folder / "frames.json").write_text(json.dumps({"frames": listed}),
                                        encoding="utf-8")
    return ".polyweave/references/clip"


def test_a_minimap_s_blips_are_placed_round_the_strip_from_the_player(tmp_path):
    made = reference_regions.minimap(film(tmp_path), root=str(tmp_path))
    assert made["player_unseen"] == 0 and made["blips"] == 6
    written = json.loads((tmp_path / made["minimap"]).read_text("utf-8"))
    first = written["read"][0]
    assert first["player"]["u"] == pytest.approx(0.5, abs=0.02)
    by_angle = sorted(first["blips"], key=lambda b: b["angle"])
    assert by_angle[0]["angle"] == pytest.approx(90, abs=4)
    assert by_angle[0]["side"] == "left"
    assert by_angle[0]["from_player"] == pytest.approx(-90, abs=4)
    # Almost at the right end of a strip whose ends meet: to the player's right.
    assert by_angle[1]["side"] == "right"
    assert first["sides"] == {"enemy:left": 1, "enemy:right": 1}
    record = provenance.read(made["minimap"], root=str(tmp_path))
    assert record["params"]["region"] == "radar"


def test_each_region_is_laid_out_enlarged_on_its_own_sheet(tmp_path):
    made = reference_regions.regions(film(tmp_path), scale=3, root=str(tmp_path))
    assert set(made["regions"]) == {"radar", "score"}
    with Image.open(tmp_path / made["regions"]["radar"][0]) as sheet:
        # A strip four times wider than it is tall is stacked one to a row.
        assert sheet.size == (200 * 3, 20 * 3 * 3)


def test_frames_of_another_size_are_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        reference_regions.minimap(film(tmp_path, size=(800, 400)), root=str(tmp_path))
    assert refused.value.code == "capture.wrong-size"


def test_a_reference_not_declared_is_refused_with_those_that_are(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        reference_regions.regions(film(tmp_path), reference="defender",
                                  root=str(tmp_path))
    assert refused.value.code == "capture.unknown-reference"


@pytest.mark.parametrize(
    "line",
    ['regions = { radar = [100, 10, 500, 30] }',
     'regions = { radar = [100, 10, 300] }',
     'minimap = "nowhere"',
     'blips = { enemy = "red" }'],
)
def test_a_region_or_blip_that_means_nothing_is_refused(tmp_path, line):
    key = line.split(" ")[0]
    kept = [one for one in DECLARED.splitlines() if not one.startswith(key + " ")]
    (tmp_path / "polyweave.toml").write_text("\n".join([*kept, line]) + "\n",
                                             encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        load(tmp_path).references()
    assert refused.value.code == "config.bad-type"
