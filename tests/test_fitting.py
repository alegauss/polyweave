"""A picture put on the project's grid on arrival (§PW171)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import fitting, provenance
from polyweave.errors import PolyweaveError


def arrived(path, box=(40, 30, 90, 110), fringe=(255, 255, 255)):
    """A gold subject off-centre in a big frame, with a white-tinted soft edge."""
    image = Image.new("RGBA", (160, 160), fringe + (0,))
    pen = ImageDraw.Draw(image)
    left, top, right, bottom = box
    pen.rectangle((left - 1, top - 1, right + 1, bottom + 1), fill=fringe + (120,))
    pen.rectangle(box, fill=(242, 193, 78, 255))
    image.save(path)
    return path.name


def project(tmp_path, **style):
    lines = ["[style]"] + [f"{k} = {v}" for k, v in style.items()]
    (tmp_path / C.FILENAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def test_a_picture_lands_on_its_familys_cell_centred_inside_the_margin(tmp_path):
    where = project(tmp_path, cell="[64, 64]", margin="4")
    found = fitting.fit(arrived(where / "icon.png"), "game/icon.png", root=where)
    with Image.open(where / "game" / "icon.png") as fitted:
        assert fitted.size == (64, 64)
        alpha = np.asarray(fitted)[..., 3]
    rows, columns = np.nonzero(alpha > 5)
    # the subject is taller than wide, so its height fills the cell inside the margin
    assert rows.min() == 4 and rows.max() == 59
    assert abs((columns.min() + columns.max()) / 2 - 31.5) <= 1
    assert found["cell"] == [64, 64] and found["anchor"] == "centre"


def test_what_stands_on_the_ground_sits_on_the_base(tmp_path):
    where = project(tmp_path, cell="[64, 96]", margin="2", anchor='"base"')
    fitting.fit(arrived(where / "tree.png", box=(30, 30, 130, 80)), "t.png", root=where)
    with Image.open(where / "t.png") as fitted:
        alpha = np.asarray(fitted)[..., 3]
    rows, _ = np.nonzero(alpha > 5)
    assert rows.max() == 96 - 2 - 1


def test_the_generators_halo_is_removed_and_measured(tmp_path):
    where = project(tmp_path, cell="[80, 80]")
    found = fitting.fit(arrived(where / "a.png"), "b.png", root=where)
    assert found["halo_delta_e"]["before"] > 10
    assert found["halo_delta_e"]["after"] < found["halo_delta_e"]["before"] / 4


def test_pixel_art_is_never_smoothed_and_keeps_to_its_palette(tmp_path):
    where = project(
        tmp_path, cell="[16, 16]", filter='"pixel"', palette='["#f2c14e", "#000000"]'
    )
    fitting.fit(arrived(where / "a.png"), "b.png", root=where)
    with Image.open(where / "b.png") as fitted:
        pixels = np.asarray(fitted)
    assert set(np.unique(pixels[..., 3])) <= {0, 255}
    solid = pixels[pixels[..., 3] == 255][:, :3]
    assert {tuple(p) for p in solid} <= {(242, 193, 78), (0, 0, 0)}


def test_the_transform_and_the_original_are_on_the_record(tmp_path):
    where = project(tmp_path, cell="[64, 64]")
    fitting.fit(arrived(where / "icon.png"), "fit.png", root=where)
    record = provenance.read("fit.png", root=where)
    assert record["kind"] == "picture"
    assert record["inputs"][0]["path"] == "icon.png"
    assert record["transform"]["trim"] == [39, 29, 92, 112]


def test_a_cell_is_two_whole_numbers_and_an_anchor_is_one_of_two(tmp_path):
    for bad in ({"cell": "[64]"}, {"anchor": '"top"'}):
        with pytest.raises(PolyweaveError) as caught:
            C.load(project(tmp_path, **bad))
        assert caught.value.code == "config.bad-type"
