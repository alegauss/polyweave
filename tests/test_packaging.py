"""Published under a name of its own, at one version (§PW602)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from polyweave import __version__

REPO = Path(__file__).parents[1]
DISTRIBUTION = "polyweave-gamekit"


def test_the_distribution_is_named_apart_from_the_other_polyweave():
    project = tomllib.loads((REPO / "pyproject.toml").read_text("utf-8"))["project"]
    assert project["name"] == DISTRIBUTION
    assert project["dynamic"] == ["version"]


def test_the_plugin_manifest_carries_the_package_version():
    manifest = REPO / "plugin" / ".claude-plugin" / "plugin.json"
    assert json.loads(manifest.read_text("utf-8"))["version"] == __version__


def test_no_remedy_installs_the_other_project():
    """`polyweave` on PyPI is Sigma-Pi hypernetworks: an agent that follows a remedy
    naming it installs that, and the extra it was told about is still missing."""
    wrong = re.compile(r"\bpolyweave\[")
    found = [
        f"{path.relative_to(REPO)}:{number}"
        for path in (REPO / "src" / "polyweave").rglob("*.py")
        for number, line in enumerate(path.read_text("utf-8").splitlines(), 1)
        if wrong.search(line)
    ]
    assert found == []
