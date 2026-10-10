"""A camera move declared as a clip and built into a camera the game plays (Â§PW372).

Starship's opening kept its shots in the game's own JSON, set by eye. The scene built
here is played by the engine itself where there is one, and has to frame what the
declaration's own arithmetic says it frames.
"""

from __future__ import annotations

import math
import os
import re
import tomllib
from pathlib import Path

import pytest

from polyweave import camera, describe, engine, project, provenance
from polyweave.errors import PolyweaveError

OPENING = """\
name = "opening"
easing = "sine"
fov = 50

[[shot]]
anchor = "ship"
from = [0, 2, 10]
to = [4, 2, 10]
look = [0, 2, 0]
look_to = [4, 2, 0]
hold = 1.0

[[shot]]
from = [0, 12, 30]
look = [0, 0, 0]
fov = 35
hold = 0.5
ease = "linear"
mark = "citadel"
"""


def clip_file(tmp_path, body: str = OPENING) -> str:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "cinema").mkdir(exist_ok=True)
    (tmp_path / "cinema" / "opening.camera.toml").write_text(body, encoding="utf-8")
    return "cinema/opening.camera.toml"


def test_a_camera_clip_is_built_as_a_scene_with_its_record(tmp_path):
    made = camera.build(clip_file(tmp_path), root=str(tmp_path))
    assert made["file"] == "cinema/opening.tscn"
    text = (tmp_path / "cinema" / "opening.tscn").read_text("utf-8")
    assert '[node name="opening" type="Camera3D"]' in text
    assert '"mark": "citadel"' in text and '"ease": "sine"' in text
    record = provenance.read("cinema/opening.tscn", root=str(tmp_path))
    assert record["kind"] == "camera"
    assert record["inputs"][0]["path"] == "cinema/opening.camera.toml"
    assert record["measurements"]["shots"] == 2


def test_what_a_clip_measures_is_worked_out_from_its_declaration(tmp_path):
    made = camera.build(clip_file(tmp_path), root=str(tmp_path))
    assert made["duration"] == pytest.approx(1.5)
    assert (made["shortest_hold"], made["longest_hold"]) == (0.5, 1.0)
    assert made["anchors"] == ["", "ship"] and made["marks"] == ["", "citadel"]


def test_a_shot_takes_the_clip_s_easing_and_fov_where_it_says_none():
    clip = camera.checked({"name": "a", "easing": "ease", "fov": 70,
                           "shot": [{"from": [0, 0, 1], "look": [0, 0, 0], "hold": 1}]})
    shot = clip["shots"][0]
    assert (shot["ease"], shot["fov"], shot["to"], shot["look_to"]) == (
        "ease", 70.0, [0.0, 0.0, 1.0], [0.0, 0.0, 0.0])


def test_the_camera_at_a_moment_drifts_on_its_shot_s_easing(tmp_path):
    clip = camera.checked(tomllib.loads(OPENING))
    # Half way through a sine drift is half way along it.
    mid = camera.at(clip, 0.5)
    assert mid["shot"] == 0 and mid["from"] == pytest.approx([2.0, 2.0, 10.0])
    quarter = camera.at(clip, 0.25)
    assert quarter["from"][0] == pytest.approx(4 * (0.5 - 0.5 * math.cos(math.pi / 4)))
    assert camera.at(clip, 1.2)["mark"] == "citadel"
    assert camera.at(clip, 1.5) is None and camera.at(clip, -0.1) is None


def test_reduced_motion_holds_each_shot_at_its_start():
    clip = camera.checked(tomllib.loads(OPENING))
    assert camera.at(clip, 0.9, still=True)["from"] == [0.0, 2.0, 10.0]


@pytest.mark.parametrize(
    "body",
    [
        'name = "a"\n',
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\n',
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\nhold = 0\n',
        'name = "a"\n[[shot]]\nfrom = [0, 1]\nlook = [0, 0, 0]\nhold = 1\n',
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\nhold = 1\nfov = 0\n',
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\nhold = 1\n'
        'ease = "bounce"\n',
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 1]\nhold = 1\n',
        'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\nhold = 1\n'
        'to = [0, 0, 0]\n',
        'name = "a b"\n[[shot]]\nfrom = [0, 0, 1]\nlook = [0, 0, 0]\nhold = 1\n',
    ],
)
def test_a_clip_that_means_nothing_is_refused_with_a_code(tmp_path, body):
    with pytest.raises(PolyweaveError) as refused:
        camera.build(clip_file(tmp_path, body), root=str(tmp_path))
    assert refused.value.code == "clip.bad-camera"


def test_a_misspelled_key_is_answered_with_its_nearest(tmp_path):
    body = 'name = "a"\n[[shot]]\nfrom = [0, 0, 1]\nlok = [0, 0, 0]\nhold = 1\n'
    with pytest.raises(PolyweaveError) as refused:
        camera.build(clip_file(tmp_path, body), root=str(tmp_path))
    assert "shot 1" in refused.value.message and "'look'" in refused.value.remedy


@pytest.mark.parametrize("body", [None, "[[shot\n"])
def test_a_missing_or_broken_file_is_refused(tmp_path, body):
    source = clip_file(tmp_path, body or OPENING)
    if body is None:
        source = "cinema/elsewhere.camera.toml"
    with pytest.raises(PolyweaveError) as refused:
        camera.build(source, root=str(tmp_path))
    assert refused.value.code == "clip.no-camera"


def test_the_scene_is_listed_as_a_clip_in_the_inventory(tmp_path):
    camera.build(clip_file(tmp_path), root=str(tmp_path))
    rows = project.inventory(str(tmp_path), kind="clip")["items"]
    assert [(r["id"], r["declaration"]) for r in rows] == [
        ("cinema/opening.tscn", "cinema/opening.camera.toml")]


def test_it_is_an_operation_an_agent_can_find():
    assert describe.for_target("polyweave.camera:build") == "clip.camera"
    params = {p["name"] for p in describe.describe("clip.camera")["parameters"]}
    assert params == {"source", "out", "root"}


PLAYS = """extends SceneTree

var ship := Node3D.new()
var cam: Camera3D

func _initialize() -> void:
\tship.position = Vector3(100, 0, 0)
\troot.add_child(ship)
\tcam = load("res://cinema/opening.tscn").instantiate()
\troot.add_child(cam)

func _process(_delta: float) -> bool:
\tcam.anchors = {"ship": ship}
\tvar cuts := []
\tcam.cut.connect(func(index: int, mark: String) -> void:
\t\tcuts.append("%d:%s" % [index, mark]))
\tfor at in [0.25, 0.5, 1.2]:
\t\tcam.seek(at)
\t\tvar ahead := -cam.global_transform.basis.z
\t\tprint("camera: at=%.2f pos=%.4f,%.4f,%.4f ahead=%.4f,%.4f,%.4f fov=%.1f" % [at,
\t\t\tcam.global_position.x, cam.global_position.y, cam.global_position.z,
\t\t\tahead.x, ahead.y, ahead.z, cam.fov])
\tcam.still = true
\tcam.seek(0.9)
\tprint("camera: still x=%.4f" % cam.global_position.x)
\tcam.place = func(anchor: String, at: Vector3) -> Vector3: return at * 2.0
\tcam.seek(1.2)
\tprint("camera: placed y=%.4f" % cam.global_position.y)
\tprint("camera: cuts=%s length=%.2f" % [",".join(cuts), cam.length()])
\treturn true
"""


def test_the_engine_plays_the_clip_as_its_declaration_says(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    camera.build(clip_file(tmp_path), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="camera"\n', encoding="utf-8")
    (tmp_path / "plays.gd").write_text(PLAYS, encoding="utf-8")
    ran = engine.run("plays.gd", expect=r"^camera: cuts", root=tmp_path, headless=True)
    assert ran["ok"] is True, ran
    said = Path(ran["log"]).read_text("utf-8")
    clip = camera.checked(tomllib.loads(OPENING))
    shots = re.findall(
        r"at=([\d.]+) pos=([-\d.,]+) ahead=([-\d.,]+) fov=([\d.]+)", said)
    assert len(shots) == 3, said
    for at, pos, ahead, fov in shots:
        expected = camera.at(clip, float(at))
        offset = [100.0, 0.0, 0.0] if expected["anchor"] == "ship" else [0.0, 0.0, 0.0]
        eye = [a + b for a, b in zip(expected["from"], offset, strict=True)]
        look = [a + b for a, b in zip(expected["look"], offset, strict=True)]
        facing = [b - a for a, b in zip(eye, look, strict=True)]
        norm = math.sqrt(sum(v * v for v in facing))
        assert [float(v) for v in pos.split(",")] == pytest.approx(eye, abs=1e-3)
        assert [float(v) for v in ahead.split(",")] == pytest.approx(
            [v / norm for v in facing], abs=1e-3)
        assert float(fov) == pytest.approx(expected["fov"])
    assert "still x=100.0000" in said
    assert "placed y=24.0000" in said
    # Seeking back into the first shot and on again is two more cuts.
    assert "cuts=0:,1:citadel,0:,1:citadel length=1.50" in said
