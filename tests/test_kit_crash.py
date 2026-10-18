"""The crash kit the plugin carries, and game.crash_read reading what it left (§PW361).

The kit's proof forces an error and a run left unclosed, which only the running game can
do; it runs where $GODOT is set and is said skipped where not. Reading a capture back
runs anywhere.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers import kits
from polyweave.layers.engine import driving, engine

CAPTURE = {"format": 1, "reason": "error", "seed": 7, "state": {"health": 0},
           "error": {"said": "Invalid call", "script": "res://boss.gd", "line": 41},
           "lines": [{"said": "the boss enters"}]}


def test_the_crash_kit_is_declared_and_proved_by_script():
    found = kits.every()["crash"]
    assert found["requires"] == []
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def test_the_crash_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("crash")["kits"]
    assert said["status"] == "skipped"


def test_a_capture_a_person_sent_is_read_back_as_facts(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "sent.json").write_text(json.dumps(CAPTURE), encoding="utf-8")
    read = driving.crash_read("sent.json", root=str(tmp_path))
    assert read["at"] == "res://boss.gd:41"
    assert read["state"] == {"health": 0}
    assert read["seed"] == 7
    assert read["says"] == "error: Invalid call at res://boss.gd:41"


def test_the_newest_capture_on_this_machine_is_read_where_none_is_named(tmp_path,
                                                                        monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    folder = tmp_path / "user" / "polyweave_log" / "captures"
    folder.mkdir(parents=True)
    monkeypatch.setattr(driving, "_user_dir", lambda root: tmp_path / "user")
    with pytest.raises(PolyweaveError) as caught:
        driving.crash_read(root=str(tmp_path))
    assert caught.value.code == "game.no-capture"
    (folder / "1-error.json").write_text(json.dumps(CAPTURE), encoding="utf-8")
    time.sleep(0.05)
    later = {**CAPTURE, "reason": "unclean-exit", "error": {"said": "never closed"}}
    (folder / "2-unclean-exit.json").write_text(json.dumps(later), encoding="utf-8")
    read = driving.crash_read(root=str(tmp_path))
    assert read["reason"] == "unclean-exit"
    assert read["captures"] == 2


def test_user_dir_follows_the_project_name_or_its_custom_folder(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "project.godot").write_text(
        '[application]\n\nconfig/name="Star Garden"\n', encoding="utf-8")
    assert driving._user_dir(tmp_path).parts[-2:] == ("app_userdata", "Star Garden")
    (tmp_path / "project.godot").write_text(
        '[application]\n\nconfig/name="Star Garden"\nconfig/use_custom_user_dir=true\n'
        'config/custom_user_dir_name="stargarden"\n', encoding="utf-8")
    assert driving._user_dir(tmp_path).name == "stargarden"


def _installed(tmp_path):
    """The fixture, under a name of its own so its user:// is its own (§PW525).

    Godot names user:// after the project, and the kit logs to a fixed folder there, so
    copies sharing the fixture's name read each other's log and marker under xdist.
    """
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "crash" / "fixture", game)
    project = game / "project.godot"
    named = 'config/name="polyweave crash fixture"'
    text = project.read_text(encoding="utf-8")
    assert named in text
    own = f'config/name="polyweave crash fixture {os.getpid()} {time.monotonic_ns()}"'
    project.write_text(text.replace(named, own), encoding="utf-8")
    return game, kits.install("crash", root=str(game))


@pytest.fixture
def installed(tmp_path):
    """The fixture installed, and its user:// removed after."""
    game, said = _installed(tmp_path)
    yield game, said
    shutil.rmtree(driving._user_dir(game), ignore_errors=True)


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_crash_kit_holds_in_its_fixture(installed):
    _, said = installed
    assert said["proved"]["passed"] is True, said["proved"]


LOG = "addons/polyweave/crash/log.gd"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    ("addons/polyweave/crash/catcher.gd", 'if not file.begins_with("res://"):',
     "if false:", "the capture names core/"),
    (LOG, 'DirAccess.remove_absolute(ProjectSettings.globalize_path(DIR + "/running"))',
     "pass", "left its marker behind"),
    (LOG, 'capture("unclean-exit", {"said": "the last run ended without closing',
     'pass #("unclean-exit", {"said": "the last run ended without closing',
     "was not packed as an unclean exit"),
])
def test_a_broken_log_fails_the_proof_by_name(installed, where, before, after, said):
    game, _ = installed
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["crash"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_game_killed_mid_run_is_read_back_as_an_unclean_exit(installed):
    game, _ = installed
    godot = engine.find(game)
    log = driving._user_dir(game) / "polyweave_log" / "log.jsonl"

    def started() -> int:
        if not log.is_file():
            return 0
        text = log.read_text(encoding="utf-8", errors="replace")
        return text.count("the fixture starts")

    before = started()
    running = subprocess.Popen([godot, "--headless", "--path", str(game)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # "Mid run" is a place in the run, not a moment (§PW525): a fixed sleep under
        # the full gate's load killed the game before it had logged its first line.
        deadline = time.monotonic() + 120
        while started() == before and time.monotonic() < deadline:
            assert running.poll() is None, "the fixture quit before it logged"
            time.sleep(0.1)
        assert started() > before, "the fixture never logged that it started"
    finally:
        running.kill()
        running.wait()
    subprocess.run([godot, "--headless", "--path", str(game), "--quit-after", "30"],
                   capture_output=True, timeout=120, check=False)
    read = driving.crash_read(root=str(game))
    assert read["reason"] == "unclean-exit"
    assert read["lines"][-1]["said"] == "the fixture starts"
