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


# -- kinds told apart by sample crops (§PW404) --------------------------------------

PULSE = (150, 245, 255)  # the lander's cyan flaring, past its colour's tolerance


def shapes(tmp_path, frames=4, every=0.5):
    """Three cyan blocks and three cyan orbs drifting right, one block flaring on every
    other frame, and a crop of each shape kept as its kind's sample."""
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    folder = tmp_path / ".polyweave" / "references" / "shapes"
    folder.mkdir(parents=True)
    listed = []
    for n in range(frames):
        at = n * every
        image = Image.new("RGB", (1280, 720), (8, 8, 20))
        draw = ImageDraw.Draw(image)
        for row in range(3):
            x, y = 200 + 40 * at, 150 + 150 * row
            flare = row == 0 and n % 2 == 1
            draw.rectangle((x - 20, y - 20, x + 20, y + 20),
                           fill=PULSE if flare else CYAN)
            draw.ellipse((x + 380, y - 20, x + 420, y + 20), fill=CYAN)
        if n == 0:
            (tmp_path / "samples").mkdir()
            image.crop((180, 280, 221, 321)).save(tmp_path / "samples" / "block.png")
            image.crop((580, 280, 621, 321)).save(tmp_path / "samples" / "orb.png")
        name = f"t{int(at * 1000):08d}.png"
        image.save(folder / name)
        listed.append({"ms": int(at * 1000), "file": name})
    (folder / "frames.json").write_text(json.dumps({"frames": listed}),
                                        encoding="utf-8")
    return ".polyweave/references/shapes"


SHAPED = {"block": {"colour": "#3fe8ff", "size": [800, 3000],
                    "samples": ["samples/block.png"]},
          "orb": {"colour": "#3fe8ff", "size": [800, 3000],
                  "samples": ["samples/orb.png"]}}


def test_two_kinds_of_one_colour_are_told_apart_by_their_samples(tmp_path):
    made = reference_objects.objects(shapes(tmp_path), SHAPED, root=str(tmp_path))
    counted = {(g["kind"], g["count"]) for g in made["groups"]}
    assert counted == {("block", 3), ("orb", 3)}


def test_by_colour_alone_the_two_kinds_are_one(tmp_path):
    alike = {name: {k: v for k, v in kind.items() if k != "samples"}
             for name, kind in SHAPED.items()}
    made = reference_objects.objects(shapes(tmp_path), alike, root=str(tmp_path))
    written = json.loads((tmp_path / made["objects"]).read_text("utf-8"))
    # Every shape is counted once as a block and once as an orb.
    assert written["per_frame"][0]["count"] == 12


def test_a_kind_with_samples_keeps_what_its_colour_alone_loses(tmp_path):
    folder = shapes(tmp_path)
    plain = {"block": {"colour": "#3fe8ff", "size": [1400, 3000]}}
    lost = reference_objects.objects(folder, plain, root=str(tmp_path))
    written = json.loads((tmp_path / lost["objects"]).read_text("utf-8"))
    # The flaring block drops out on the frames it flares.
    assert [one["count"] for one in written["per_frame"]] == [3, 2, 3, 2]
    sampled = {"block": {**plain["block"], "samples": ["samples/block.png"]}}
    kept = reference_objects.objects(folder, sampled, root=str(tmp_path))
    written = json.loads((tmp_path / kept["objects"]).read_text("utf-8"))
    assert [one["count"] for one in written["per_frame"]] == [3, 3, 3, 3]
    assert {(g["kind"], g["count"]) for g in kept["groups"]} == {("block", 3)}


def test_each_sample_is_recorded_with_its_digest(tmp_path):
    made = reference_objects.objects(shapes(tmp_path), SHAPED, root=str(tmp_path))
    record = provenance.read(made["objects"], root=str(tmp_path))
    samples = [one for one in record["inputs"] if one["role"] == "sample"]
    assert [one["path"] for one in samples] == ["samples/block.png", "samples/orb.png"]
    assert all(one["sha256"] for one in samples)
    assert record["params"]["kinds"]["orb"]["samples"] == ["samples/orb.png"]


@pytest.mark.parametrize("kind", [{"samples": []}, {"samples": ["samples/none.png"]},
                                  {"samples": ["samples/orb.png"], "match": 0}])
def test_samples_that_mean_nothing_are_refused(tmp_path, kind):
    folder = shapes(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        reference_objects.objects(folder, {"orb": {"colour": "#3fe8ff", **kind}},
                                  root=str(tmp_path))
    assert refused.value.code == "capture.bad-kinds"


def test_frames_that_are_not_there_are_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        reference_objects.objects("nowhere", KINDS, root=str(tmp_path))
    assert refused.value.code == "capture.no-reference-frames"
