"""A game born adopted, from one call (§PW369).

Making one installs kits and proves each where $GODOT is set; the refusal and the files
it writes are checked everywhere.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from polyweave import newgame
from polyweave.errors import PolyweaveError


def test_a_folder_that_holds_files_is_refused_for_project_init(tmp_path):
    (tmp_path / "already.txt").write_text("here", encoding="utf-8")
    with pytest.raises(PolyweaveError) as caught:
        newgame.new(str(tmp_path), name="Late")
    assert caught.value.code == "adopt.not-empty"
    assert "project.init" in caught.value.remedy


def test_a_game_with_no_kits_is_made_and_adopted(tmp_path):
    made = newgame.new(str(tmp_path / "bare"), name="Bare", kits=[], git=False)
    here = tmp_path / "bare"
    assert made["check"]["clean"] is True, made["check"]
    assert 'config/name="Bare"' in (here / "project.godot").read_text(encoding="utf-8")
    assert "fallback_to_opengl3=true" in (here / "project.godot").read_text(
        encoding="utf-8")
    assert ".godot/" in (here / ".gitignore").read_text(encoding="utf-8")
    attributes = (here / ".gitattributes").read_text(encoding="utf-8")
    assert "*.png filter=lfs diff=lfs merge=lfs -text" in attributes
    assert (here / "polyweave.toml").is_file()
    assert (here / "tools" / "gate.py").is_file()
    assert made["carries"] == []
    assert made["repository"] is False


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_new_game_carries_its_base_kits_and_its_gate_passes_at_once(tmp_path):
    here = tmp_path / "born"
    made = newgame.new(str(here), name="Born")
    assert made["ok"] is True, made
    carried = {one["kit"] for one in made["carries"]}
    assert carried == {"prompts", "remap", "menus", "options", "saves", "tests"}
    assert made["repository"] is True
    assert (here / "tests" / "main_test.gd").is_file()
    gate = subprocess.run([sys.executable, "tools/gate.py"], cwd=here,
                          capture_output=True, text=True, check=False, timeout=900)
    assert gate.returncode == 0, gate.stdout + gate.stderr
