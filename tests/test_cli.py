"""`python -m polyweave build`, a declaration built with no script (§PW101)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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


def test_all_rebuilds_after_the_plugin_changed(tmp_path, capsys, monkeypatch):
    """§PW140: the stamp hashed the inputs alone, so a fixed builder kept the output
    the defect had produced and called it cached."""
    (tmp_path / "art").mkdir()
    declared(tmp_path / "art")
    run(tmp_path, "--all", "art", "--json", capsys=capsys)

    monkeypatch.setattr("polyweave.provenance.__version__", "9.9.9-fixed")
    _, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    assert [one["status"] for one in json.loads(printed.out)] == ["built"]


def test_a_preview_is_not_answered_from_a_build_without_one(tmp_path, capsys):
    (tmp_path / "art").mkdir()
    declared(tmp_path / "art")
    run(tmp_path, "--all", "art", "--json", capsys=capsys)
    _, printed = run(tmp_path, "--all", "art", "--preview", "--json", capsys=capsys)
    (again,) = json.loads(printed.out)
    assert again["status"] == "built"
    assert any(one.endswith(".png") for one in again["outputs"])


def test_every_output_carries_the_record_the_stamp_is_the_key_of(tmp_path, capsys):
    from polyweave import provenance

    (tmp_path / "polyweave.toml").write_text(
        '[paths]\nmeshes = "art"\n', encoding="utf-8"
    )
    (tmp_path / "art").mkdir()
    declared(tmp_path / "art")
    _, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    (built,) = json.loads(printed.out)
    stamped = json.loads((tmp_path / "art" / "box.build.json").read_text("utf-8"))
    for output in built["outputs"]:
        record = provenance.read(output, root=str(tmp_path))
        assert provenance.cache_key(record) == stamped["stamp"]
        assert record["params"]["made_by"] == "geometry.build"
    assert provenance.unrecorded(str(tmp_path)) == []


def test_all_reports_a_declaration_with_a_typo_and_fails(tmp_path, capsys):
    """§PW123: a declaration `read` refused used to drop out silently, exiting 0."""
    (tmp_path / "art").mkdir()
    declared(tmp_path / "art")
    (tmp_path / "art" / "typo.toml").write_text(
        VOXEL.replace('name = "box"\noutput = "box"', 'name = "typo"\noutput = "bxo"'),
        encoding="utf-8",
    )
    (tmp_path / "art" / "spec.toml").write_text(
        "asset = 'box'\n[[predicate]]\nid = 'a'\n", encoding="utf-8"
    )
    status, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    found = {Path(one["document"]).name: one for one in json.loads(printed.out)}
    assert status == 1
    assert set(found) == {"box.toml", "typo.toml"}
    assert found["box.toml"]["status"] == "built"
    assert found["typo.toml"]["status"] == "refused"
    assert found["typo.toml"]["refusal"]["code"] == "geom.unknown-node"


def test_all_reports_a_declaration_that_is_not_even_toml(tmp_path, capsys):
    (tmp_path / "art").mkdir()
    broken = tmp_path / "art" / "broken.toml"
    broken.write_text("[[nodes]\nid = 1\n", encoding="utf-8")
    status, printed = run(tmp_path, "--all", "art", "--json", capsys=capsys)
    (one,) = json.loads(printed.out)
    assert status == 1
    assert one["refusal"]["code"] == "geom.unreadable"


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
