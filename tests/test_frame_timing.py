"""Play timed by frames, named where it is written (§PW657).

Spinhold's replays drifted from patterns a read of its scripts names at their line: a
hit stop counted down in `_process` and read per tick, `time_scale` set in a physics
step, and play waiting on an idle-clock tween. This reads text; it runs anywhere.
"""

from __future__ import annotations

from pathlib import Path

from polyweave.layers.engine import frame_timing, integrity

HIT_STOP = """extends Node

var stop_left := 0.0
var speed := 4.0

func _process(delta: float) -> void:
\tif stop_left > 0.0:
\t\tstop_left -= delta

func _physics_process(delta: float) -> void:
\tif stop_left <= 0.0:
\t\tposition.x += speed * delta
"""

SCALE = """extends Node

func _physics_process(_delta: float) -> void:
\tif Input.is_action_pressed("slow"):
\t\tEngine.time_scale = 0.5
"""

WAITS = """extends Node

func fly() -> void:
\tvar tween := create_tween()
\ttween.tween_property(self, "position:x", 100.0, 1.0)
\tawait tween.finished
"""

CLEAN = """extends Node

var hp := 3

func _physics_process(_delta: float) -> void:
\tif hp <= 0:
\t\tqueue_free()

func _process(_delta: float) -> void:
\tqueue_redraw()
"""


def game(tmp_path) -> Path:
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    for name, text in {"hit_stop.gd": HIT_STOP, "scale.gd": SCALE, "waits.gd": WAITS,
                       "clean.gd": CLEAN}.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    kit = tmp_path / "addons" / "kit" / "kit.gd"
    kit.parent.mkdir(parents=True)
    kit.write_text(SCALE, encoding="utf-8")
    return tmp_path


def by_file(found: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for one in found:
        out.setdefault(one["file"], []).append(one)
    return out


def test_each_frame_timed_pattern_is_named_at_its_line(tmp_path):
    read = frame_timing.hazards(game(tmp_path))
    found = by_file(read["findings"])
    [stop] = found["res://hit_stop.gd"]
    assert stop["line"] == 8 and "stop_left" in stop["said"]
    [scale] = found["res://scale.gd"]
    assert scale["line"] == 5 and "time_scale" in scale["said"]
    [wait] = found["res://waits.gd"]
    assert wait["line"] == 6 and "tween.finished" in wait["said"]
    assert all(one["code"] == "engine.frame-timed" for one in read["findings"])
    assert all(one["severity"] == "warning" for one in read["findings"])


def test_a_clean_script_and_the_plugins_own_are_left_alone(tmp_path):
    read = frame_timing.hazards(game(tmp_path))
    files = {one["file"] for one in read["findings"]}
    assert "res://clean.gd" not in files
    assert not any(f.startswith("res://addons/") for f in files)
    assert read["scripts"] == 4


def test_a_tween_on_the_physics_clock_is_not_a_hazard(tmp_path):
    root = game(tmp_path)
    (root / "waits.gd").write_text(WAITS.replace(
        "create_tween()",
        "create_tween().set_process_mode(Tween.TWEEN_PROCESS_PHYSICS)"),
        encoding="utf-8")
    files = {one["file"] for one in frame_timing.hazards(root)["findings"]}
    assert "res://waits.gd" not in files


def test_engine_check_carries_them(tmp_path):
    found = integrity.check(str(game(tmp_path)), parse=False)
    timed = [one for one in found["findings"] if one["code"] == "engine.frame-timed"]
    assert len(timed) == 3
    assert found["frame_timing"] == {"scripts": 4}
    assert found["clean"] is True
