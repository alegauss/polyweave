"""`python -m polyweave build`, a declaration built with no script (§PW101)."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from polyweave import cli

VOXEL = """name = "box"
output = "box"

[params]
size = 4

[voxels]
cell = 1

[[nodes]]
id = "box"
op = "primitive"
kind = "cube"
size = "size"
"""


def declared(tmp_path, body=VOXEL, name="box.toml"):
    (tmp_path / name).write_text(body, encoding="utf-8")
    return name


def run(tmp_path, *argv, capsys):
    status = cli.main(["build", *argv, "--root", str(tmp_path)])
    return status, capsys.readouterr()


def test_a_voxel_declaration_builds_and_says_what_came_out(tmp_path, capsys):
    status, printed = run(tmp_path, declared(tmp_path), "--out", "out", capsys=capsys)
    assert status == 0
    assert "= a voxel model 4 by 4 by 4, 64 cells in 1 material" in printed.out
    assert (tmp_path / "out" / "box.voxels.json").is_file()


def test_a_setting_reaches_the_shape(tmp_path, capsys):
    status, printed = run(
        tmp_path, declared(tmp_path), "--set", "size=2", "--json", capsys=capsys
    )
    assert status == 0
    assert json.loads(printed.out)["says"].startswith("a voxel model 2 by 2 by 2")


def test_a_preview_writes_the_contact_sheet(tmp_path, capsys):
    status, printed = run(
        tmp_path, declared(tmp_path), "--preview", "--json", capsys=capsys
    )
    outputs = json.loads(printed.out)["outputs"]
    assert status == 0
    assert any(one.endswith("box.voxels.png") for one in outputs)


def test_a_refusal_prints_its_code_and_exits_non_zero(tmp_path, capsys):
    broken = VOXEL.replace('kind = "cube"', 'kind = "cone"')
    status, printed = run(tmp_path, declared(tmp_path, broken), capsys=capsys)
    assert status == 1
    assert "geom.unknown-shape" in printed.out
    assert "do: name one of" in printed.out


def test_a_setting_that_sets_nothing_is_refused(tmp_path, capsys):
    status, printed = run(tmp_path, declared(tmp_path), "--set", "size", capsys=capsys)
    assert status == 2
    assert "op.bad-setting" in printed.err


def test_all_skips_what_has_not_changed_and_rebuilds_what_has(tmp_path, capsys):
    (tmp_path / "art").mkdir()
    declared(tmp_path / "art")
    (tmp_path / "art" / "not_a_shape.toml").write_text("[x]\ny = 1\n", encoding="utf-8")

    status, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    first = json.loads(printed.out)
    assert status == 0
    assert [one["status"] for one in first] == ["built"]

    _, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    assert [one["status"] for one in json.loads(printed.out)] == ["cached"]

    declared(tmp_path / "art", VOXEL.replace("size = 4", "size = 3"))
    _, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    again = json.loads(printed.out)
    assert [one["status"] for one in again] == ["built"]
    assert again[0]["says"].startswith("a voxel model 3 by 3 by 3")


def test_a_mesh_declaration_writes_its_mesh_and_a_silhouette(tmp_path, capsys):
    pytest.importorskip("bpy")
    body = VOXEL.replace("[voxels]\ncell = 1\n", "")
    status, printed = run(
        tmp_path, declared(tmp_path, body), "--preview", "--json", capsys=capsys
    )
    outputs = json.loads(printed.out)["outputs"]
    assert status == 0
    assert (tmp_path / "box.glb").is_file()
    assert any(one.endswith("box.preview.png") for one in outputs)


def test_a_declaration_saved_with_a_byte_order_mark_still_builds(tmp_path, capsys):
    (tmp_path / "box.toml").write_text(VOXEL, encoding="utf-8-sig")
    status, printed = run(tmp_path, "box.toml", capsys=capsys)
    assert status == 0, printed.out


def test_it_runs_as_a_module(tmp_path):
    declared(tmp_path)
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "polyweave",
            "build",
            "box.toml",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    assert "built" in done.stdout
