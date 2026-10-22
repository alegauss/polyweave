"""A camera move declared as a clip and built into a camera the game plays (§PW372).

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

from polyweave.kernel import describe, provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import engine
from polyweave.layers.motion import camera
from polyweave.surface import project

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
    assert describe.for_target("polyweave.layers.motion.camera:build") == "clip.camera"
    params = {p["name"] for p in describe.describe("clip.camera")["parameters"]}
    assert params == {"source", "out", "root"}


def test_each_shot_is_framed_in_the_game_and_laid_out_to_judge(tmp_path, monkeypatch):
    """clip.shots pins each shot, lets a frame pass, saves the screen, lets the pin
    go, and lays the shots out as one sitting (§PW372)."""
    from PIL import Image

    from polyweave.layers.engine import driving

    source = clip_file(tmp_path)
    sent = []

    def set_value(session, *, path, prop, value, root):
        sent.append(("set", path, prop, value))

    def stepped(session, *, frames, root):
        sent.append(("step", frames))

    def shot(session, *, out, root):
        sent.append(("shot", Path(out).name))
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 18), (40, 40, 60)).save(out)

    monkeypatch.setattr(driving, "set_value", set_value)
    monkeypatch.setattr(driving, "stepped", stepped)
    monkeypatch.setattr(driving, "shot", shot)
    said = camera.shots(source, session="g1", camera="/root/Main/Camera",
                        out="art/review/opening", root=str(tmp_path))
    assert [one["at"] for one in said["shots"]] == [0.5, 1.25]
    assert said["shots"][1]["mark"] == "citadel"
    assert sent == [
        ("set", "/root/Main/Camera", "pinned", "0.5"), ("step", 2),
        ("shot", "opening-1.png"),
        ("set", "/root/Main/Camera", "pinned", "1.25"), ("step", 2),
        ("shot", "opening-2.png"),
        ("set", "/root/Main/Camera", "pinned", "-1"),
    ]
    assert (tmp_path / "art/review/opening/opening.png").is_file()
    assert said["sitting"].endswith("sitting.json")
    assert said["page"].startswith("/?sitting=")


def test_one_call_opens_the_game_where_the_clip_plays_and_closes_it(
        tmp_path, monkeypatch):
    """Spinhold reached each world's cutscene by calling its campaign's private methods,
    where its own --world flag would do (§PW553)."""
    from PIL import Image

    from polyweave.layers.engine import driving

    sent = []
    monkeypatch.setattr(driving, "opened", lambda root, **said: (
        sent.append(("open", said["display"], said["args"])) or {"session": "g9"}))
    monkeypatch.setattr(driving, "waited", lambda session, **said: (
        sent.append(("wait", said["node"])) or {"met": True}))
    monkeypatch.setattr(driving, "set_value", lambda session, **said: None)
    monkeypatch.setattr(driving, "stepped", lambda session, **said: None)
    monkeypatch.setattr(driving, "closed", lambda session, **said: sent.append(
        ("close", session)))

    def shot(session, *, out, root):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 18), (40, 40, 60)).save(out)

    monkeypatch.setattr(driving, "shot", shot)
    said = camera.shots(clip_file(tmp_path), camera="/root/World/Camera",
                        args=["--world=quilt"], out="art/review/quilt",
                        root=str(tmp_path))
    assert len(said["shots"]) == 2
    assert sent == [("open", True, ["--world=quilt"]), ("wait", "/root/World/Camera"),
                    ("close", "g9")]


def test_a_camera_the_opened_game_never_made_is_refused_and_the_game_closed(
        tmp_path, monkeypatch):
    from polyweave.layers.engine import driving

    closed = []
    monkeypatch.setattr(driving, "opened", lambda root, **said: {"session": "g9"})
    monkeypatch.setattr(driving, "waited", lambda session, **said: {"met": False})
    monkeypatch.setattr(driving, "closed",
                        lambda session, **said: closed.append(session))
    with pytest.raises(PolyweaveError) as refused:
        camera.shots(clip_file(tmp_path), camera="Camera", out="o",
                     args=["--world=nowhere"], root=str(tmp_path))
    assert refused.value.code == "clip.camera-absent"
    assert closed == ["g9"]


def test_the_pin_is_let_go_when_a_shot_fails(tmp_path, monkeypatch):
    from polyweave.layers.engine import driving

    sent = []
    monkeypatch.setattr(driving, "set_value",
                        lambda session, **said: sent.append(said["value"]))
    monkeypatch.setattr(driving, "stepped", lambda session, **said: None)

    def broken(session, **said):
        raise PolyweaveError("driver.shot-not-written", "headless", "open with display")

    monkeypatch.setattr(driving, "shot", broken)
    with pytest.raises(PolyweaveError):
        camera.shots(clip_file(tmp_path), session="g1", camera="Camera", out="o",
                     root=str(tmp_path))
    assert sent == ["0.5", "-1"]


def test_a_clip_the_game_is_not_playing_is_stood_up_and_framed(tmp_path, monkeypatch):
    """§PW591: Spinhold builds a world's camera only in a cutscene a map dive starts."""
    from PIL import Image

    from polyweave.layers.engine import driving

    sent = []

    def send(session, cmd, *, root, **fields):
        sent.append((cmd, fields["scene"], fields["names"], fields["anchors"]))
        return {"result": {"path": "/root/Main/opening"}}

    monkeypatch.setattr(driving, "opened", lambda root, **said: {"session": "g9"})
    monkeypatch.setattr(driving, "send", send)
    monkeypatch.setattr(driving, "set_value", lambda session, **said: None)
    monkeypatch.setattr(driving, "called", lambda session, **said: sent.append(
        ("seek", said["path"], said["args"])))
    monkeypatch.setattr(driving, "stepped", lambda session, **said: None)
    monkeypatch.setattr(driving, "closed", lambda session, **said: sent.append(
        ("close", session)))

    def shot(session, *, out, root):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 18), (40, 40, 60)).save(out)

    monkeypatch.setattr(driving, "shot", shot)
    said = camera.shots(clip_file(tmp_path), clip="cinema/opening.tscn",
                        anchors={"ship": "World/Ship"}, args=["--world=waist"],
                        out="art/review/waist", root=str(tmp_path))
    assert len(said["shots"]) == 2
    assert sent == [
        ("clip_camera", "res://cinema/opening.tscn", ["ship"], {"ship": "World/Ship"}),
        ("seek", "/root/Main/opening", [0.5]), ("seek", "/root/Main/opening", [1.25]),
        ("close", "g9"),
    ]


def _framing(monkeypatch, sent):
    """A game that frames whatever it is asked to, and says what it was asked."""
    from PIL import Image

    from polyweave.layers.engine import driving

    def shot(session, *, out, root):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 18), (40, 40, 60)).save(out)
        return {"environment": {"resolution": "32x18", "locale": "en"}}

    monkeypatch.setattr(driving, "opened", lambda root, **said: (
        sent.append(("open", said)) or {"session": "g9"}))
    monkeypatch.setattr(driving, "send", lambda session, cmd, **said: {
        "result": {"path": "/root/Main/opening"}})
    monkeypatch.setattr(driving, "set_value", lambda session, **said: sent.append(
        ("set", said["path"], said["prop"], said["value"])))
    monkeypatch.setattr(driving, "called", lambda session, **said: None)
    monkeypatch.setattr(driving, "stepped", lambda session, **said: None)
    monkeypatch.setattr(driving, "closed", lambda session, **said: sent.append(
        ("close", session)))
    monkeypatch.setattr(driving, "shot", shot)


def test_each_shot_is_recorded_and_a_kept_one_lands_at_its_path(tmp_path, monkeypatch):
    """§PW597: Spinhold borrowed a world picture from its work area, with no record of
    the clip that framed it, and hid its HUD by hand first."""
    sent = []
    _framing(monkeypatch, sent)
    said = camera.shots(clip_file(tmp_path), clip="cinema/opening.tscn",
                        args=["--world=waist"], out=".polyweave/waist",
                        keep={"2": "assets/ui/worlds/waist.png"}, hide=["Main/Hud"],
                        root=str(tmp_path))
    assert said["shots"][1]["kept"] == "assets/ui/worlds/waist.png"
    assert len(said["records"]) == 3
    record = provenance.read("assets/ui/worlds/waist.png", root=str(tmp_path))
    assert record["kind"] == "shot" and record["params"]["shot"] == 2
    assert record["inputs"][0]["path"] == "cinema/opening.camera.toml"
    assert record["call"]["clip"] == "cinema/opening.tscn"
    assert record["call"]["hide"] == ["Main/Hud"]
    assert record["call"]["environment"] == {"resolution": "32x18", "locale": "en"}
    assert ("set", "Main/Hud", "visible", "false") in sent
    assert sent[-2:] == [("set", "Main/Hud", "visible", "true"), ("close", "g9")]


def test_a_kept_shot_is_framed_again_from_its_record(tmp_path, monkeypatch):
    from polyweave.layers.engine import capture

    sent = []
    _framing(monkeypatch, sent)
    camera.shots(clip_file(tmp_path), clip="cinema/opening.tscn", out=".polyweave/w",
                 keep={"1": "assets/ui/worlds/waist.png"}, root=str(tmp_path))
    sent.clear()
    again = capture.taken_again("assets/ui/worlds/waist.png",
                                environment={"locale": "pt_BR"}, root=str(tmp_path))
    assert again["shots"][0]["kept"] == "assets/ui/worlds/waist.png"
    [(_, opened)] = [one for one in sent if one[0] == "open"]
    assert opened["locale"] == "pt_BR" and opened["display"] is True
    assert sent[-1] == ("close", "g9")


def test_keep_naming_a_shot_the_clip_has_not_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        camera.shots(clip_file(tmp_path), session="g1", camera="Camera", out="o",
                     keep={"3": "a.png"}, root=str(tmp_path))
    assert refused.value.code == "clip.bad-camera"


def test_a_stood_up_clip_whose_anchors_are_absent_names_them(tmp_path, monkeypatch):
    from polyweave.layers.engine import driving

    closed = []
    monkeypatch.setattr(driving, "opened", lambda root, **said: {"session": "g9"})
    monkeypatch.setattr(driving, "send", lambda session, cmd, **said: {
        "result": {"missing": ["ship"]}})
    monkeypatch.setattr(driving, "closed",
                        lambda session, **said: closed.append(session))
    with pytest.raises(PolyweaveError) as refused:
        camera.shots(clip_file(tmp_path), clip="cinema/opening.tscn", out="o",
                     root=str(tmp_path))
    assert refused.value.code == "clip.anchor-absent"
    assert "ship" in refused.value.message
    assert closed == ["g9"]


@pytest.mark.parametrize("given", [{}, {"camera": "Camera", "clip": "c.tscn"}])
def test_neither_or_both_of_camera_and_clip_is_refused(tmp_path, given):
    with pytest.raises(PolyweaveError) as refused:
        camera.shots(clip_file(tmp_path), session="g1", out="o", root=str(tmp_path),
                     **given)
    assert refused.value.code == "clip.camera-absent"


WORLD = """extends Node3D

func _ready() -> void:
\tvar ship := Node3D.new()
\tship.name = "ship"
\tship.position = Vector3(100, 0, 0)
\tadd_child(ship)
"""


def test_the_driver_stands_a_clip_up_where_its_anchor_is(tmp_path):
    """§PW591, in the engine: the camera made, its anchor found by name, and seeking
    it frames the shot in that anchor's frame."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    from polyweave.layers.engine import driving, godot

    camera.build(clip_file(tmp_path), root=str(tmp_path))
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="camera"\n'
        'run/main_scene="res://main.tscn"\n', encoding="utf-8")
    (tmp_path / "main.gd").write_text(WORLD, encoding="utf-8")
    (tmp_path / "main.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://main.gd" id="1"]\n\n'
        '[node name="Main" type="Node3D"]\nscript = ExtResource("1")\n',
        encoding="utf-8")
    godot.install(tmp_path, addon="polyweave_driver")
    root = str(tmp_path)
    session = driving.opened(root)["session"]
    try:
        driving.stepped(session, frames=2, root=root)
        absent = driving.send(session, "clip_camera", root=root,
                              scene="res://cinema/opening.tscn", names=["ghost"],
                              anchors={}, place="")
        assert absent["result"] == {"missing": ["ghost"]}
        made = driving.send(session, "clip_camera", root=root,
                            scene="res://cinema/opening.tscn", names=["ship"],
                            anchors={}, place="")["result"]["path"]
        driving.called(session, path=made, method="seek", args=[0.0], root=root)
        (found,) = driving.queried(session, path=made,
                                   properties=["global_position", "current"],
                                   root=root)["result"]
        # The first shot starts at [0, 2, 10] in the ship's frame, 100 along x.
        assert found["properties"]["current"] is True
        assert "100" in str(found["properties"]["global_position"])
    finally:
        driving.closed(session, root=root)


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
\tcam.pinned = 1.2
\tcam.seek(0.25)
\tprint("camera: pinned time=%.2f shown=%d y=%.4f" % [cam.time, cam.shown,
\t\tcam.global_position.y])
\tcam.pinned = -1.0
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
    # A pinned moment is framed whatever the game seeks (§PW372, clip.shots).
    assert "pinned time=1.20 shown=1 y=24.0000" in said
    # Seeking back into the first shot and on again is two more cuts.
    assert "cuts=0:,1:citadel,0:,1:citadel length=1.50" in said
