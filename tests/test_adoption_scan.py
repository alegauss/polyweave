"""What a project still does its own way, beside the call that does it (§PW59)."""

from __future__ import annotations

from polyweave.kernel import config as C
from polyweave.surface import adoption, project
from polyweave.surface.cli import command_line
from polyweave.surface.commands import run

RUNNER = '''import subprocess
GODOT = "godot"
subprocess.run([GODOT, "--path", ".", "--quit-after", "400", "--script", "t.gd"])
'''
RIG = "import bpy\nbpy.ops.render.render(write_still=True)\n"
CLIENT = 'BASE = "https://api.meshy.ai/openapi/v2"\n'
GATE = """import sys
import numpy as np
from PIL import Image
tail = np.percentile(np.asarray(Image.open("board.png")), 99)
sys.exit(0 if tail > 0.8 else 1)
"""
PASS = """import numpy as np
from PIL import Image
cheek = np.median(np.asarray(Image.open("face.png")), axis=0)
"""


def tree(tmp_path, files: dict[str, str], config: str = "") -> str:
    (tmp_path / C.FILENAME).write_text(config, encoding="utf-8")
    for name, text in files.items():
        where = tmp_path / name
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text, encoding="utf-8")
    return str(tmp_path)


def own(found) -> dict:
    return {name: one["own"] for name, one in found["surfaces"].items() if one["own"]}


def test_each_surface_is_read_off_what_the_code_does(tmp_path):
    root = tree(
        tmp_path,
        {
            "tools/run_tests.py": RUNNER,
            "tools/art/bake.py": RIG,
            "tools/art/fetch.py": CLIENT,
            "tools/check_vivid.py": GATE,
        },
    )
    found = adoption.adoption(root)
    assert own(found) == {
        "engine": ["tools/run_tests.py"],
        "render": ["tools/art/bake.py"],
        "fetch": ["tools/art/fetch.py"],
        "measure": ["tools/check_vivid.py"],
    }
    assert found["clean"] is False
    assert found["adopted"] == {"surfaces": 0, "of": 4, "clear": []}
    assert "sheet" in found["unread"]


def test_what_only_resembles_a_surface_is_not_one(tmp_path):
    root = tree(
        tmp_path,
        {
            # git through subprocess is not the engine, and a median a pass paints with
            # is not a gate: neither exits on a picture's statistic.
            "tools/publish.py": 'import subprocess\nsubprocess.run(["git", "push"])\n',
            "tools/art/passes.py": PASS,
            "docs/about.md": RIG,
        },
    )
    found = adoption.adoption(root)
    assert own(found) == {}
    assert found["clean"] is True
    assert found["adopted"]["surfaces"] == 4


def test_a_file_kept_with_its_reason_fails_nothing_and_still_counts(tmp_path):
    root = tree(
        tmp_path,
        {"tools/run_tests.py": RUNNER, "tools/art/bake.py": RIG},
        '[adoption.own]\n"tools/run_tests.py" = "moves onto game.test next"\n'
        '"tools/gone.py" = "deleted since"\n',
    )
    found = adoption.adoption(root)
    assert found["surfaces"]["engine"]["kept"] == [
        {"file": "tools/run_tests.py", "why": "moves onto game.test next"}
    ]
    assert own(found) == {"render": ["tools/art/bake.py"]}
    assert "engine" not in found["adopted"]["clear"]
    assert found["stale"] == ["tools/gone.py"]


def test_the_work_area_and_hidden_folders_are_not_the_project_s_code(tmp_path):
    root = tree(
        tmp_path,
        {
            ".polyweave/jobs/runner.py": RUNNER,
            ".venv/lib/bake.py": RIG,
            "node_modules/x/fetch.py": CLIENT,
        },
    )
    assert own(adoption.adoption(root)) == {}


def test_project_check_fails_on_a_surface_done_here_and_names_the_call(tmp_path):
    root = tree(tmp_path, {"tools/run_tests.py": RUNNER})
    findings = project.check(root)["findings"]
    found = [f for f in findings if f["code"] == "adopt.own-surface"]
    assert len(found) == 1
    assert found[0]["severity"] == "error"
    assert "tools/run_tests.py starts Godot itself (engine)" in found[0]["message"]
    assert "engine.run" in found[0]["remedy"]
    assert "[adoption] own" in found[0]["remedy"]


def test_the_command_exits_non_zero_while_a_file_is_unkept(tmp_path, capsys):
    root = tree(tmp_path, {"tools/run_tests.py": RUNNER})
    stated = command_line().parse_args(["project.adoption", "--root", root])
    assert run(stated) == 1
    (tmp_path / C.FILENAME).write_text(
        '[adoption.own]\n"tools/run_tests.py" = "moves onto game.test next"\n', "utf-8"
    )
    assert run(stated) == 0
