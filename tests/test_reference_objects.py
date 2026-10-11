"""What moves in a reference video's frames, counted and followed (Â§PW379).

Spinhold's agent counted twenty small enemies by eye on every contact sheet, and a
miscount reached the sheet the owner reviews. These frames are drawn here, so what is in
them is known: a line of three cyan objects drifting right, one cyan object flying off
the right edge, one magenta object that vanishes mid-screen, and a ring of six.
"""

from __future__ import annotations

import json
import math

import pytest
from PIL import Image, ImageDraw

from polyweave import provenance, reference_objects
from polyweave.errors import PolyweaveError

CYAN, MAGENTA = (63, 232, 255), (255, 61, 203)
KINDS = {"lander": {"colour": "#3fe8ff", "size": [40, 400]},
         "mutant": {"colour": "#ff3dcb", "size": [40, 400]}}


def square(draw, x, y, colour, half=6):
    draw.rectangle((x - half, y - half, x + half, y + half), fill=colour)


def film(tmp_path, frames=6, every=0.5):
    """Frames at `every` seconds, as reference.frames lays them out."""
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    folder = tmp_path / ".polyweave" / "references" / "clip"
    folder.mkdir(parents=True)
    listed = []
    for n in range(frames):
        at = n * every
        image = Image.new("RGB", (1280, 720), (8, 8, 20))
        draw = ImageDraw.Draw(image)
        for row in range(3):  # a line, drifting right together
            square(draw, 200 + 40 * at, 200 + 60 * row, CYAN)
        square(draw, 1000 + 160 * at, 600, CYAN)  # leaves by the right edge
        if at < 1.2:  # destroyed mid-screen
            square(draw, 640, 360 + 20 * at, MAGENTA)
        if at >= 1.0:  # a ring of six born at one second
            for k in range(6):
                angle = 2 * math.pi * k / 6
                square(draw, 900 + 80 * math.cos(angle), 250 + 80 * math.sin(angle),
                       CYAN)
        name = f"t{int(at * 1000):08d}.png"
        image.save(folder / name)
        listed.append({"ms": int(at * 1000), "file": name})
    (folder / "frames.json").write_text(json.dumps({"frames": listed}),
                                        encoding="utf-8")
    return ".polyweave/references/clip"


def test_objects_are_counted_followed_and_grouped(tmp_path):
    made = reference_objects.objects(film(tmp_path), KINDS, root=str(tmp_path))
    written = json.loads((tmp_path / made["objects"]).read_text("utf-8"))
    groups = {(g["kind"], g["born"], g["count"]): g for g in written["groups"]}
    line = groups[("lander", 0.0, 3)]
    assert line["formation"] == "line"
    assert line["ended"] == {"left": 0, "gone": 0, "alive": 3}
    assert groups[("lander", 1.0, 6)]["formation"] == "ring"
    assert groups[("mutant", 0.0, 1)]["ended"]["gone"] == 1
    leaver = groups[("lander", 0.0, 1)]
    assert leaver["ended"]["left"] == 1
    assert written["per_frame"][0]["count"] == 5
    # The line and the ring; the leaver is off the frame and the mutant gone.
    assert written["per_frame"][-1]["count"] == 9


def test_a_track_s_path_is_in_the_video_s_own_pixels(tmp_path):
    made = reference_objects.objects(film(tmp_path), KINDS, root=str(tmp_path))
    written = json.loads((tmp_path / made["objects"]).read_text("utf-8"))
    first = written["tracks"][0]
    assert first["path"][0][1:] == pytest.approx([200, 200], abs=3)
    assert first["path"][-1][1:] == pytest.approx([300, 200], abs=3)


def test_the_counts_are_recorded_and_drawn_on_a_sheet(tmp_path):
    made = reference_objects.objects(film(tmp_path), KINDS, root=str(tmp_path))
    record = provenance.read(made["objects"], root=str(tmp_path))
    assert record["params"]["kinds"]["lander"]["colour"] == "#3fe8ff"
    assert record["inputs"][0]["path"].endswith("frames.json")
    assert made["sheets"] and (tmp_path / made["sheets"][0]).is_file()


def test_an_area_leaves_out_what_is_outside_the_play(tmp_path):
    made = reference_objects.objects(film(tmp_path), KINDS, area=[0, 0, 700, 720],
                                     root=str(tmp_path))
    kinds = {(g["kind"], g["count"]) for g in made["groups"]}
    assert ("lander", 6) not in kinds and ("lander", 3) in kinds


@pytest.mark.parametrize(
    "kinds",
    [{}, {"a": {"colour": "cyan"}}, {"a": {"colour": "#00ffff", "size": [10, 2]}},
     {"a": {"colour": "#00ffff", "tolerance": 2}}],
)
def test_a_kind_that_means_nothing_is_refused(tmp_path, kinds):
    with pytest.raises(PolyweaveError) as refused:
        reference_objects.objects(film(tmp_path), kinds, root=str(tmp_path))
    assert refused.value.code == "capture.bad-kinds"


def test_frames_that_are_not_there_are_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        reference_objects.objects("nowhere", KINDS, root=str(tmp_path))
    assert refused.value.code == "capture.no-reference-frames"
