"""The declaration is the source, and the guard says so (§PW133)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from polyweave import cli, provenance

GUARD = Path(__file__).parents[1] / "hooks" / "guard.py"

VOXEL = """name = "crate"
output = "crate"

[params]
size = 4

[voxels]
cell = 1

[[nodes]]
id = "crate"
op = "primitive"
kind = "cube"
size = "size"
"""


def hook(mode: str, event: dict) -> dict | None:
    done = subprocess.run(
        [sys.executable, str(GUARD), mode],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(done.stdout) if done.stdout.strip() else None


def built(tmp_path) -> Path:
    (tmp_path / "crate.toml").write_text(VOXEL, encoding="utf-8")
    answer = cli.build_one("crate.toml", root=tmp_path)
    return Path(next(one for one in answer["outputs"] if one.endswith(".json")))


def test_an_edit_to_a_built_file_is_denied_naming_the_declaration(tmp_path):
    output = built(tmp_path)
    said = hook(
        "pre",
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(output)},
            "cwd": str(tmp_path),
        },
    )
    decision = said["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "crate.toml" in decision["permissionDecisionReason"]
    assert "geometry.build --source crate.toml" in decision["permissionDecisionReason"]


def test_the_declaration_itself_may_be_edited(tmp_path):
    built(tmp_path)
    event = {"tool_name": "Write", "tool_input": {"file_path": "crate.toml"}}
    assert hook("pre", {**event, "cwd": str(tmp_path)}) is None


def test_a_recorded_artefact_is_denied_too(tmp_path):
    (tmp_path / "shot.png").write_bytes(b"png")
    provenance.write(
        provenance.build("capture", tmp_path / "shot.png", root=tmp_path), root=tmp_path
    )
    said = hook(
        "pre",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": "shot.png"},
            "cwd": str(tmp_path),
        },
    )
    assert said["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_shell_command_naming_a_derived_file_is_asked_about(tmp_path):
    output = built(tmp_path)
    command = f"sed -i s/a/b/ {output.name}"
    said = hook(
        "pre",
        {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(tmp_path)},
    )
    assert said["hookSpecificOutput"]["permissionDecision"] == "ask"
    other = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(tmp_path)}
    assert hook("pre", other) is None


def test_a_hand_edit_since_the_session_began_blocks_the_stop(tmp_path):
    (tmp_path / "shot.png").write_bytes(b"png")
    provenance.write(
        provenance.build("capture", tmp_path / "shot.png", root=tmp_path), root=tmp_path
    )
    hook("start", {"cwd": str(tmp_path)})
    assert hook("stop", {"cwd": str(tmp_path)}) is None
    (tmp_path / "shot.png").write_bytes(b"edited by hand")
    said = hook("stop", {"cwd": str(tmp_path)})
    assert said["decision"] == "block"
    assert "shot.png" in said["reason"]
    assert hook("stop", {"cwd": str(tmp_path), "stop_hook_active": True}) is None


def test_a_broken_event_allows_rather_than_breaks():
    done = subprocess.run(
        [sys.executable, str(GUARD), "pre"],
        input="not json",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0
    assert done.stdout == ""


def test_the_guard_imports_nothing_outside_the_standard_library():
    import ast

    imported = set()
    for node in ast.walk(ast.parse(GUARD.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}
