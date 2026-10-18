"""`python -m polyweave migrate`, a project carried across the layout break (§PW520).

The fixtures under `fixtures/migrate/` are the two consumers as the break found them:
every Python file of Cottony (at 89dc304) and Spinhold (at c38268e) that imports
polyweave, and each one's polyweave.toml, copied unchanged.
"""

from __future__ import annotations

import ast
import json
import shutil
import tomllib
from pathlib import Path

import pytest

from polyweave.surface import cli
from polyweave.surface.commands import as_data
from polyweave.surface.migrate import holds, is_module, migrate, table

FIXTURES = Path(__file__).parent / "fixtures" / "migrate"


def consumer(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    shutil.copytree(FIXTURES / name, root)
    return root


def test_every_line_of_the_table_names_what_the_package_holds():
    moved = table()
    for old, new in moved["modules"].items():
        assert is_module(new), f"{old} -> {new}, which is no module"
        assert not is_module(f"polyweave.{old}") or old == "loop", old
    for old, new in moved["names"].items():
        name = old.split(":")[1]
        assert holds(new, name), f"{old} -> {new}, which does not hold {name}"


@pytest.mark.parametrize("name", ["cottony", "spinhold"])
def test_each_consumer_migrates_and_every_import_then_resolves(tmp_path, name):
    root = consumer(tmp_path, name)
    answer = migrate(root, write=True)
    assert answer["clean"], answer["unmapped"]
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module.startswith("polyweave"):
                for alias in node.names:
                    assert holds(node.module, alias.name), (path.name, alias.name)
    again = migrate(root)
    assert again["diff"] == "" and again["clean"]


@pytest.mark.parametrize("name", ["cottony", "spinhold"])
def test_a_migrated_consumer_passes_an_import_order_lint(tmp_path, name):
    """Five of Cottony's ten files failed ruff's I001 until sorted by hand (§PW530)."""
    import subprocess
    import sys

    root = consumer(tmp_path, name)

    def flagged() -> set[str]:
        # From the consumer's own root, as its gate runs it: from here, polyweave's
        # src/ would make polyweave first-party, which it never is in a game.
        said = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "I",
             "--output-format", "json", "."],
            cwd=root, capture_output=True, text=True, check=False,
        )
        return {Path(one["filename"]).name for one in json.loads(said.stdout)}

    (root / "pyproject.toml").write_text(
        '[tool.ruff]\ntarget-version = "py311"\nline-length = 110\n', encoding="utf-8")
    # Spinhold's site_assets.py was never import-sorted, and migrate leaves it alone.
    before = flagged()
    migrate(root, write=True)
    assert flagged() <= before


def test_a_run_of_imports_is_sorted_and_a_module_s_names_merged(tmp_path):
    (tmp_path / "x.py").write_text(
        "import polyweave\n"
        "from polyweave import geometry, measure, render\n"
        "from polyweave.geometry import build\n"
        "from polyweave.pack import pack as exported\n"
        "from polyweave.pack import source_of\n",
        encoding="utf-8",
    )
    migrate(tmp_path, write=True)
    assert (tmp_path / "x.py").read_text(encoding="utf-8") == (
        "import polyweave\n"
        "from polyweave.layers import geometry\n"
        "from polyweave.layers.engine.pack import pack as exported\n"
        "from polyweave.layers.engine.pack import source_of\n"
        "from polyweave.layers.geometry import build, render\n"
        "from polyweave.loop import measure\n"
    )


def test_a_cottony_import_reads_as_its_new_path(tmp_path):
    root = consumer(tmp_path, "cottony")
    migrate(root, write=True)
    trays = (root / "tools/art/frame_trays.py").read_text(encoding="utf-8")
    assert "from polyweave.layers.geometry import build" in trays
    assert "from polyweave.loop import measure" in trays
    assert "from polyweave.kernel.image import load" in trays
    assert "from polyweave import geometry" not in trays
    boot = (root / "tools/check_boot.py").read_text(encoding="utf-8")
    assert "from polyweave.layers.engine.testing import boot" in boot
    assert "import polyweave\n" in boot  # readable() stayed where it was


def test_one_import_of_several_modules_splits_by_where_each_went(tmp_path):
    root = consumer(tmp_path, "spinhold")
    migrate(root, write=True)
    meshy = (root / "tools/art/meshy.py").read_text(encoding="utf-8")
    assert "from polyweave.layers.geometry import mesh_buy, normalise" in meshy
    assert "from polyweave.kernel import provenance" in meshy
    assert "from polyweave.services import purchase" in meshy
    assert "from polyweave import readable" in meshy
    fit = (root / "tools/art/voxel_fit.py").read_text(encoding="utf-8")
    assert "from polyweave.layers.geometry.representations.voxels.fit import fit" in fit


def test_the_project_file_gets_its_layers_and_still_loads(tmp_path):
    from polyweave.kernel.config import load

    root = consumer(tmp_path, "spinhold")
    answer = migrate(root, write=True)
    declared = tomllib.loads((root / "polyweave.toml").read_text(encoding="utf-8"))
    assert declared["layers"]["on"] == answer["config"]["layers"]["on"]
    assert {"engine", "picture", "sound", "words"} <= set(declared["layers"]["on"])
    assert load(root).get("layers.on") == declared["layers"]["on"]
    # a second run leaves a file that already says which layers it uses
    assert migrate(root)["config"]["layers"] is None


def test_a_report_writes_nothing(tmp_path):
    root = consumer(tmp_path, "cottony")
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    answer = migrate(root)
    assert answer["diff"] and not answer["wrote"]
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_the_work_area_is_cleared_and_records_are_never_touched(tmp_path):
    root = consumer(tmp_path, "cottony")
    for one in ("jobs", "cache"):
        (root / ".polyweave" / one).mkdir(parents=True)
        (root / ".polyweave" / one / "old.json").write_text("{}", encoding="utf-8")
    record = root / "docs" / "a.png.prov.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"kind": "fetch", "artefact": {}}), encoding="utf-8")
    stray = root / "docs" / "b.png.prov.json"
    stray.write_text(json.dumps({"kind": "no-such-kind"}), encoding="utf-8")
    held = record.read_bytes(), stray.read_bytes()
    assert migrate(root)["clears"] == [".polyweave/jobs", ".polyweave/cache"]
    answer = migrate(root, write=True)
    assert answer["cleared"] == [".polyweave/jobs", ".polyweave/cache"]
    assert not (root / ".polyweave" / "jobs").exists()
    assert (record.read_bytes(), stray.read_bytes()) == held
    assert answer["unreadable"] == [{"record": "docs/b.png.prov.json",
                                     "kind": "no-such-kind"}]


def test_an_import_the_table_cannot_map_is_named_and_left(tmp_path):
    (tmp_path / "x.py").write_text(
        "from polyweave.nowhere import thing\nfrom polyweave import errors\n",
        encoding="utf-8",
    )
    answer = migrate(tmp_path, write=True)
    assert not answer["clean"]
    assert answer["unmapped"] == [{"file": "x.py", "line": 1,
                                   "import": "from polyweave.nowhere import thing",
                                   "name": "thing"}]
    text = (tmp_path / "x.py").read_text(encoding="utf-8")
    assert "from polyweave.nowhere import thing\n" in text
    assert "from polyweave.kernel import errors" in text


def test_a_name_used_through_a_module_that_no_longer_holds_it_is_named(tmp_path):
    (tmp_path / "x.py").write_text(
        "from polyweave import purchase\n\npurchase.quote()\npurchase.read()\n",
        encoding="utf-8",
    )
    answer = migrate(tmp_path)
    assert [one["name"] for one in answer["unmapped"]] == ["purchase.quote"]


def test_a_dotted_import_takes_its_uses_along(tmp_path):
    (tmp_path / "x.py").write_text(
        "import polyweave.capture\n\npolyweave.capture.run()\n", encoding="utf-8"
    )
    migrate(tmp_path, write=True)
    assert (tmp_path / "x.py").read_text(encoding="utf-8") == (
        "import polyweave.layers.engine.capture\n\n"
        "polyweave.layers.engine.capture.run()\n"
    )


def test_a_document_naming_a_moved_module_is_reported_not_rewritten(tmp_path):
    skill = tmp_path / ".claude" / "skills" / "art" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    said = "Call `polyweave.geometry.voxel_fit` and read polyweave.toml.\n"
    skill.write_text(said, encoding="utf-8")
    answer = migrate(tmp_path, write=True)
    assert answer["mentions"] == [{
        "file": ".claude/skills/art/SKILL.md", "line": 1,
        "was": "polyweave.geometry.voxel_fit",
        "now": "polyweave.layers.geometry.representations.voxels.fit",
    }]
    assert skill.read_text(encoding="utf-8") == said


def test_the_reads_a_project_is_judged_by_answer_the_same_after(tmp_path):
    from polyweave.kernel.provenance import outdated
    from polyweave.surface.adoption import adoption
    from polyweave.surface.project import check

    root = consumer(tmp_path, "cottony")

    def reads():
        return [as_data(one(str(root))) for one in (check, adoption, outdated)]

    before = reads()
    migrate(root, write=True)
    assert reads() == before


def test_the_command_line_exits_non_zero_on_what_it_cannot_map(tmp_path, capsys):
    (tmp_path / "x.py").write_text("from polyweave import errors\n", encoding="utf-8")
    assert cli.main(["migrate", "--root", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["imports"]
    (tmp_path / "y.py").write_text("from polyweave.nowhere import x\n",
                                   encoding="utf-8")
    assert cli.main(["migrate", "--root", str(tmp_path), "--write"]) == 1
