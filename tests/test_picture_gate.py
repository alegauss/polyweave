"""The silhouette settled on the picture, before a mesh is bought (§PW168)."""

from __future__ import annotations

import json

from PIL import Image, ImageDraw

from polyweave import config as C
from polyweave import picture


def drawn(path, box, fill=(242, 193, 78), size=128, ground=(0, 0, 0, 0)):
    image = Image.new("RGBA", (size, size), ground)
    ImageDraw.Draw(image).ellipse(box, fill=fill + (255,))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path.name


WIDE = (14, 44, 114, 84)  # the wide low cap that was asked for
TALL = (44, 8, 84, 120)  # the tall dome that came back


def project(tmp_path, text=""):
    (tmp_path / C.FILENAME).write_text(text, encoding="utf-8")
    drawn(tmp_path / "outline.png", WIDE)
    return tmp_path


def test_a_picture_matching_the_outline_is_chosen(tmp_path):
    where = project(tmp_path)
    drawn(where / "a.png", (15, 44, 115, 84))  # one pixel right: IoU 0.975
    drawn(where / "b.png", TALL)
    found = picture.gate(["a.png", "b.png"], "outline.png", root=where)
    assert found["chosen"] == "a.png"
    passed = {one["picture"]: one["passed"] for one in found["candidates"]}
    assert passed == {"a.png": True, "b.png": False}


def test_of_several_that_pass_the_highest_iou_goes_forward(tmp_path):
    where = project(tmp_path)
    # framed alike, a shift is nothing and a change of proportion is the difference
    drawn(where / "near.png", (14, 44, 114, 85))  # a pixel taller: IoU about 0.976
    drawn(where / "nearer.png", (20, 10, 120, 50))  # the same shape, elsewhere
    found = picture.gate(["near.png", "nearer.png"], "outline.png", root=where)
    assert found["chosen"] == "nearer.png"
    assert found["why"] == "the highest silhouette IoU of those that passed"


def test_a_failure_is_written_beside_the_picture_to_correct_the_next_prompt(tmp_path):
    where = project(tmp_path)
    drawn(where / "dome.png", TALL)
    found = picture.gate(["dome.png"], "outline.png", root=where)
    assert found["chosen"] is None
    written = json.loads((where / "dome.gate.json").read_text(encoding="utf-8"))
    assert written["passed"] is False
    assert "centroid" in written["failed"][0]
    assert "prompt" in written


def test_a_photograph_and_a_subject_off_the_frame_are_refused(tmp_path):
    where = project(tmp_path)
    drawn(where / "photo.png", WIDE, ground=(255, 255, 255, 255))
    drawn(where / "cut.png", (-30, 44, 70, 84))
    found = picture.gate(["photo.png", "cut.png"], "outline.png", root=where)
    photo, cut = found["candidates"]
    assert any("not a drawing" in f for f in photo["failed"])
    assert any("runs off the left" in f for f in cut["failed"])


def test_a_picture_that_drifted_from_the_canon_does_not_pass(tmp_path):
    where = project(tmp_path, '[style]\ncanon = "canon"\npalette = ["#f2c14e"]\n')
    entries = []
    for i, box in enumerate([WIDE, (14, 44, 115, 84)]):
        drawn(where / "canon" / f"c{i}.png", box)
        entries.append({"picture": f"c{i}.png", "sha256": str(i)})
    (where / "canon" / "canon.json").write_text(json.dumps(entries), "utf-8")
    drawn(where / "blue.png", WIDE, fill=(40, 90, 230))
    found = picture.gate(["blue.png"], "outline.png", root=where)
    one = found["candidates"][0]
    assert one["passed"] is False
    assert any(f.startswith("palette_delta_e_p95 drifted") for f in one["failed"])


def test_the_same_shape_anywhere_in_any_frame_passes(tmp_path):
    """§PW194: framing is the service's choice, and the silhouette is the shape."""
    where = project(tmp_path)
    # four times the size, off-centre in a bigger frame
    drawn(where / "big.png", (50, 150, 450, 310), size=512)
    found = picture.gate(["big.png"], "outline.png", root=where)
    assert found["chosen"] == "big.png"
    assert found["candidates"][0]["silhouette_iou"] > 0.97
