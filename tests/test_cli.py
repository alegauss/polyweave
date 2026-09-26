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


def test_a_voxel_declaration_can_ask_for_its_cells_alone(tmp_path, capsys):
    """§PW226: a Godot project drawing the cells imports any .glb and never uses it."""
    alone = VOXEL.replace("cell = 1\n", "cell = 1\nmesh = false\n")
    status, printed = run(tmp_path, declared(tmp_path, alone), "--json", capsys=capsys)
    built = json.loads(printed.out)
    assert status == 0
    assert [Path(one).name for one in built["outputs"]] == ["box.voxels.json"]
    assert not (tmp_path / "box.glb").exists()


def test_no_mesh_on_the_call_writes_the_cells_alone_and_takes_back_an_old_mesh(
    tmp_path, capsys
):
    source = declared(tmp_path)
    first = cli.build_one(source, root=str(tmp_path))
    if not any(one.endswith(".glb") for one in first["outputs"]):
        pytest.skip("renderer absent: the mesh needs Blender to write")
    again = cli.build_one(source, root=str(tmp_path), mesh=False)
    assert [Path(one).name for one in again["outputs"]] == ["box.voxels.json"]
    assert not (tmp_path / "box.glb").exists()
    assert not (tmp_path / "box.glb.prov.json").exists()
    stamped = json.loads((tmp_path / "box.build.json").read_text("utf-8"))
    assert [Path(one).name for one in stamped["outputs"]] == ["box.voxels.json"]


def test_the_cells_alone_and_both_are_two_stamps(tmp_path, capsys):
    (tmp_path / "art").mkdir()
    declared(tmp_path / "art")
    run(tmp_path, "--all", "art", "--json", capsys=capsys)
    _, printed = run(tmp_path, "--all", "art", "--no-mesh", "--json", capsys=capsys)
    assert [one["status"] for one in json.loads(printed.out)] == ["built"]


def test_a_mesh_setting_that_is_not_a_yes_or_no_is_refused(tmp_path, capsys):
    odd = VOXEL.replace("cell = 1\n", 'cell = 1\nmesh = "no"\n')
    status, printed = run(tmp_path, declared(tmp_path, odd), capsys=capsys)
    assert status == 1
    assert "geom.bad-voxels" in printed.out


def test_a_mesh_declaration_ignores_no_mesh_since_the_mesh_is_all_it_makes(
    tmp_path, capsys
):
    body = VOXEL.replace("[voxels]\ncell = 1\n", "")
    found = cli.build_one(declared(tmp_path, body), root=str(tmp_path), mesh=False)
    if found["status"] == "refused":
        pytest.skip("renderer absent: a mesh declaration needs Blender to write")
    assert [Path(one).name for one in found["outputs"]] == ["box.glb"]


def test_two_checkouts_write_the_same_stamp_bytes(tmp_path):
    """§PW227: the stamp named every output by its absolute path on the building
    machine, so it churned per checkout or had to be ignored by hand."""
    stamps = []
    for checkout in ("one", "two"):
        root = tmp_path / checkout
        (root / "art").mkdir(parents=True)
        declared(root / "art", VOXEL.replace("cell = 1\n", "cell = 1\nmesh = false\n"))
        cli.build_one("art/box.toml", root=str(root))
        stamps.append((root / "art" / "box.build.json").read_bytes())
    assert stamps[0] == stamps[1]
    said = json.loads(stamps[0])
    assert said["source"] == "art/box.toml"
    assert said["outputs"] == ["art/box.voxels.json"]
    assert b"\r\n" not in stamps[0]


def test_a_stamp_written_with_absolute_paths_still_reads_as_cached(tmp_path):
    source = declared(tmp_path)
    cli.build_one(source, root=str(tmp_path))
    mark = tmp_path / "box.build.json"
    said = json.loads(mark.read_text("utf-8"))
    said["outputs"] = [str((tmp_path / one).resolve()) for one in said["outputs"]]
    mark.write_text(json.dumps(said), encoding="utf-8")
    again = cli.build_one(source, root=str(tmp_path), force=False)
    assert again["status"] == "cached"
    assert all(Path(one).is_file() for one in again["outputs"])


def test_declarations_with_no_cell_build_on_the_projects(tmp_path):
    """§PW229: a game's actors break into their own cubes, so they share one cell."""
    (tmp_path / "polyweave.toml").write_text("[voxels]\ncell = 0.5\n", encoding="utf-8")
    bare = VOXEL.replace("cell = 1\n", "mesh = false\n")
    for name in ("drone.toml", "boss.toml"):
        declared(tmp_path, bare.replace('"box"', f'"{name[:-5]}"'), name)
        found = cli.build_one(name, root=str(tmp_path))
        assert found["status"] == "built"
        assert "cell 0.5, the project's" in found["reads"]
        cells = json.loads((tmp_path / f"{name[:-5]}.voxels.json").read_text("utf-8"))
        assert cells["cell"] == 0.5
        assert "cell_from" not in cells


def test_a_declarations_own_cell_wins_and_its_drift_is_reported(tmp_path):
    (tmp_path / "polyweave.toml").write_text("[voxels]\ncell = 0.5\n", encoding="utf-8")
    own = VOXEL.replace("cell = 1\n", "cell = 1\nmesh = false\n")
    found = cli.build_one(declared(tmp_path, own), root=str(tmp_path))
    assert found["says"].startswith("a voxel model 4 by 4 by 4")
    assert any("the project's is 0.5" in one for one in found["warnings"])


def test_a_declaration_with_neither_and_no_project_cell_is_still_refused(tmp_path):
    bare = VOXEL.replace("cell = 1\n", "mesh = false\n")
    found = cli.build_one(declared(tmp_path, bare), root=str(tmp_path))
    assert found["status"] == "refused"
    assert found["refusal"]["code"] == "geom.bad-voxels"


@pytest.mark.parametrize(
    ("typo", "meant"), [("acros = 16", "across"), ("mehs = false", "mesh")]
)
def test_a_misspelt_voxel_setting_is_refused_naming_the_real_one(tmp_path, typo, meant):
    """§PW231: the unread-key check stopped at the top level and the nodes."""
    body = VOXEL.replace("cell = 1\n", f"cell = 1\n{typo}\n")
    found = cli.build_one(declared(tmp_path, body), root=str(tmp_path))
    assert found["status"] == "refused"
    refusal = found["refusal"]
    assert refusal["code"] == "geom.unknown-field"
    assert refusal["at"] == f"voxels.{typo.split(' ')[0]}"
    assert meant in refusal["allowed"]


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
