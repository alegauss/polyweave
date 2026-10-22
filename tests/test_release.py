"""The next version, worked out and written by tools/release.py (§PW602)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "tools" / "release.py"


@pytest.fixture
def release(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    package = tmp_path / "__init__.py"
    package.write_text('"""polyweave."""\n\n__version__ = "0.1.0"\n', encoding="utf-8")
    manifest = tmp_path / "plugin.json"
    manifest.write_text('{\n  "name": "polyweave",\n  "version": "0.1.0",\n'
                        '  "license": "MIT"\n}\n', encoding="utf-8")
    monkeypatch.setattr(module, "PACKAGE", package)
    monkeypatch.setattr(module, "MANIFEST", manifest)
    return module


@pytest.mark.parametrize(("asked", "then"), [
    ("patch", "0.1.1"), ("minor", "0.2.0"), ("major", "1.0.0"), ("0.3.0", "0.3.0"),
])
def test_the_next_version_is_worked_out_from_the_current(release, asked, then):
    assert release.bumped(release.current(), asked) == then


@pytest.mark.parametrize("asked", ["0.1.0", "0.0.9", "next", "1.2"])
def test_a_version_pypi_would_refuse_is_refused_first(release, asked):
    with pytest.raises(release.Refused):
        release.bumped("0.1.0", asked)


def test_both_files_carry_the_new_version_and_nothing_else_moves(release):
    release.written("0.1.1")
    assert release.current() == "0.1.1"
    manifest = json.loads(release.MANIFEST.read_text("utf-8"))
    assert manifest == {"name": "polyweave", "version": "0.1.1", "license": "MIT"}
    assert release.PACKAGE.read_text("utf-8").startswith('"""polyweave."""\n')
