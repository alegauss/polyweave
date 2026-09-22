"""The environment a picture of the running game is taken in.

§PW25's case: the same script on two machines gives two different pictures, because the
game picks its language from the machine's locale and nothing says which language the
picture is being taken in.

The real-engine tests are at the end and skip without `$GODOT`. Everything before them
holds the comparison itself, which is where the failure lives.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from polyweave import capture
from polyweave.errors import PolyweaveError

SHOT = r"captured: (?P<artefact>\S+) (?P<width>\d+) x (?P<height>\d+)"

HONEST = """extends SceneTree

var frames := 0
var view: SubViewport
var applied := {}

func _initialize() -> void:
\tfor arg in OS.get_cmdline_user_args():
\t\tif arg == "offscreen":
\t\t\tDisplayServer.window_set_position(Vector2i(-32000, -32000))
\t\telif arg.find("=") > 0:
\t\t\tvar bits := arg.split("=", true, 1)
\t\t\tapplied[bits[0]] = bits[1]
\tif applied.has("locale"):
\t\tTranslationServer.set_locale(applied["locale"])
\tview = SubViewport.new()
\tview.size = Vector2i(24, 24)
\tview.render_target_update_mode = SubViewport.UPDATE_ALWAYS
\tvar patch := ColorRect.new()
\tpatch.color = Color(0.9, 0.4, 0.1)
\tpatch.size = Vector2(24, 24)
\tview.add_child(patch)
\troot.add_child(view)

func _process(_delta: float) -> bool:
\tframes += 1
\tif frames < 4:
\t\treturn false
\tvar said := PackedStringArray()
\tfor name in applied:
\t\tsaid.append("%s=%s" % [name, applied[name]])
\tsaid.sort()
\tprint("environment: %s" % " ".join(said))
\tvar image := view.get_texture().get_image()
\timage.save_png("res://shot.png")
\tprint("captured: res://shot.png %d x %d" % [image.get_width(), image.get_height()])
\treturn true
"""


def project(tmp_path, body="", *, script=HONEST):
    (tmp_path / "polyweave.toml").write_text(body, encoding="utf-8")
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="probe"\n', encoding="utf-8"
    )
    (tmp_path / "shot.gd").write_text(script, encoding="utf-8")
    return tmp_path / "shot.gd"


def taking(output, *, ok=True, artefacts=(), verdict="ok"):
    """A capture that produced this log, standing in for one that ran."""

    def take(script, *, expect, root, args, **how):
        log = Path(root) / "run.log"
        log.write_text(output, encoding="utf-8")
        return {
            "ok": ok,
            "verdict": verdict,
            "why": "" if ok else "it did not work",
            "script": str(script),
            "artefacts": [str(a) for a in artefacts],
            "log": str(log),
            "seconds": 0.5,
            "frames": None,
            "route": "window-offscreen",
            "about": "a real display driver",
            "args": args,
        }

    return take


# -- what a project says matters ----------------------------------------------------


def test_the_settings_that_matter_are_the_project_s_own(tmp_path):
    project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    assert capture.declared(tmp_path) == ["locale"]


def test_a_project_may_name_a_setting_this_plugin_never_heard_of(tmp_path):
    """The list is per project and short; one that cannot be added to is no use."""
    project(tmp_path, '[capture]\ndeclared = ["theme"]\ntheme = "dark"\n')
    assert capture.wanted(tmp_path) == {"theme": "dark"}


def test_a_declared_setting_with_no_value_stops_before_anything_runs(tmp_path):
    project(tmp_path, '[capture]\ndeclared = ["theme"]\n')
    with pytest.raises(PolyweaveError) as caught:
        capture.wanted(tmp_path)
    assert caught.value.code == "capture.undeclared"
    assert "left to the machine" in caught.value.remedy


def test_an_argument_beats_the_project_s_own_value(tmp_path):
    project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    assert capture.wanted(tmp_path, locale="en_GB") == {"locale": "en_GB"}


def test_a_setting_passed_but_not_declared_comes_along_anyway(tmp_path):
    project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    found = capture.wanted(tmp_path, seed=7)
    assert found == {"locale": "pt_BR", "seed": "7"}


# -- how a value is written, both ways along -------------------------------------------


def test_a_resolution_is_written_the_way_a_person_reads_it():
    assert capture.as_text([1920, 1080]) == "1920x1080"


def test_a_whole_number_does_not_arrive_with_a_decimal_point():
    assert capture.as_text(60.0) == "60"


def test_the_arguments_are_in_a_fixed_order_so_a_command_is_reproducible():
    assert capture.as_args({"seed": "7", "locale": "pt_BR"}) == (
        "locale=pt_BR",
        "seed=7",
    )


# -- what the script says it applied ---------------------------------------------------


def test_the_environment_line_is_read_back():
    found = capture.applied("loading\nenvironment: locale=pt_BR seed=7\ndone\n")
    assert found == {"locale": "pt_BR", "seed": "7"}


def test_a_run_with_no_such_line_reports_nothing():
    assert capture.applied("loading\ndone\n") == {}


def test_an_empty_line_is_a_line_with_nothing_on_it():
    assert capture.applied("environment:\n") == {}


# -- asked against applied, which is the whole check -----------------------------------


def test_the_two_agreeing_is_what_holds():
    found = capture.compare({"locale": "pt_BR"}, {"locale": "pt_BR"})
    assert found["holds"] is True
    assert found["why"] == ""


def test_naming_a_setting_and_not_applying_it_is_caught():
    """Which is the case a naive check passes and the wrong picture comes out of."""
    found = capture.compare({"locale": "pt_BR", "seed": "7"}, {"seed": "7"})
    assert found["holds"] is False
    assert found["missing"] == ["locale"]
    assert "locale was never applied" in found["why"]


def test_applying_a_different_value_is_caught_too():
    found = capture.compare({"locale": "pt_BR"}, {"locale": "en_GB"})
    assert found["holds"] is False
    assert found["differing"] == [
        {"setting": "locale", "asked": "pt_BR", "applied": "en_GB"}
    ]
    assert "asked at pt_BR and applied at en_GB" in found["why"]


def test_a_setting_the_script_applied_and_nobody_asked_for_is_not_a_failure():
    assert capture.compare({"locale": "pt_BR"}, {"locale": "pt_BR", "theme": "dark"})[
        "holds"
    ]


# -- the run ---------------------------------------------------------------------------


def test_the_environment_rides_on_the_command_as_arguments(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    found = capture.run(
        script,
        expect=SHOT,
        root=tmp_path,
        take=taking("environment: locale=pt_BR\ncaptured: res://x.png 24 x 24\n"),
    )
    assert found["args"][-2:] == ("--", "locale=pt_BR")
    assert found["environment"]["holds"] is True


def test_a_capture_that_did_not_apply_it_comes_back_not_ok(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    found = capture.run(
        script,
        expect=SHOT,
        root=tmp_path,
        take=taking("captured: res://x.png 24 x 24\n"),
    )
    assert found["ok"] is False
    assert found["environment"]["missing"] == ["locale"]


def test_the_environment_is_written_down_beside_the_picture(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n")
    found = capture.run(
        script,
        expect=SHOT,
        root=tmp_path,
        artefacts=(shot,),
        take=taking(
            "environment: locale=pt_BR\ncaptured: res://shot.png 24 x 24\n",
            artefacts=(shot,),
        ),
    )
    record = json.loads(Path(found["records"][0]).read_text(encoding="utf-8"))
    assert record["params"] == {"locale": "pt_BR"}
    assert record["kind"] == "capture"
    assert record["engine"]["route"] == "window-offscreen"


# -- as a gate -------------------------------------------------------------------------


def test_a_script_that_reported_no_environment_at_all_is_said_so(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    with pytest.raises(PolyweaveError) as caught:
        capture.require(
            script,
            expect=SHOT,
            root=tmp_path,
            take=taking("captured: res://x.png 24 x 24\n"),
        )
    assert caught.value.code == "capture.not-reported"


def test_a_script_that_reported_some_of_it_names_which(tmp_path):
    script = project(
        tmp_path,
        '[capture]\ndeclared = ["locale", "seed"]\nlocale = "pt_BR"\nseed = 7\n',
    )
    with pytest.raises(PolyweaveError) as caught:
        capture.require(
            script,
            expect=SHOT,
            root=tmp_path,
            take=taking("environment: seed=7\ncaptured: res://x.png 24 x 24\n"),
        )
    assert caught.value.code == "capture.not-applied"
    assert "locale was never applied" in caught.value.message


def test_a_constant_inside_the_script_winning_is_caught(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    with pytest.raises(PolyweaveError) as caught:
        capture.require(
            script,
            expect=SHOT,
            root=tmp_path,
            take=taking("environment: locale=en_GB\ncaptured: res://x.png 24 x 24\n"),
        )
    assert caught.value.code == "capture.differs"
    assert "from a constant" in caught.value.remedy


def test_a_capture_that_agreed_passes_through(tmp_path):
    script = project(tmp_path, '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n')
    found = capture.require(
        script,
        expect=SHOT,
        root=tmp_path,
        record=False,
        take=taking("environment: locale=pt_BR\ncaptured: res://x.png 24 x 24\n"),
    )
    assert found["ok"] is True


# -- against the engine itself ---------------------------------------------------------


def test_a_real_capture_reports_the_language_it_was_taken_in(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    script = project(
        tmp_path,
        f'[paths]\ngodot = "{Path(os.environ["GODOT"]).as_posix()}"\n\n'
        '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n',
    )
    found = capture.require(script, expect=SHOT, produces=("artefact",), root=tmp_path)
    assert found["environment"]["applied"]["locale"] == "pt_BR"
    assert (tmp_path / "shot.png").is_file()
    record = json.loads(Path(found["records"][0]).read_text(encoding="utf-8"))
    assert record["params"]["locale"] == "pt_BR"


def test_and_taking_it_in_another_one_is_a_different_record(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    script = project(
        tmp_path,
        f'[paths]\ngodot = "{Path(os.environ["GODOT"]).as_posix()}"\n\n'
        '[capture]\ndeclared = ["locale"]\nlocale = "pt_BR"\n',
    )
    found = capture.require(
        script,
        expect=SHOT,
        produces=("artefact",),
        root=tmp_path,
        environment={"locale": "en_GB"},
    )
    assert found["environment"]["applied"]["locale"] == "en_GB"
