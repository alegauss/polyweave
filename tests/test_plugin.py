"""Installed as a plugin, and announced in one line (§PW132)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from polyweave import commands, describe

REPO = Path(__file__).parents[1]
SKILL = REPO / "skills" / "polyweave"

#: The driving skill is read whole when it triggers, so it is held to a size; the
#: reference pages are opened on demand and held separately.
SKILL_BUDGET = 3_400
#: 3,100 once the world's four operations joined operations.md (§PW196, §PW197): a
#: table row per task, and Block Q is a task no row covered.
#: 3,200 at 3,162 with sound.declared (§PW185), Block P's first read, which joins the
#: judging row beside sound.measure rather than opening a row of its own.
REFERENCE_BUDGET = 3_200


def test_the_manifest_and_the_marketplace_name_the_plugin():
    plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    market = json.loads(
        (REPO / ".claude-plugin" / "marketplace.json").read_text("utf-8")
    )
    assert plugin["name"] == "polyweave"
    assert plugin["mcpServers"]["polyweave"]["args"] == ["-m", "polyweave", "serve"]
    assert market["plugins"] == [
        {**market["plugins"][0], "name": "polyweave", "source": "./"}
    ]


def test_a_session_starts_with_the_notice():
    hooks = json.loads((REPO / "hooks" / "hooks.json").read_text("utf-8"))
    (start,) = hooks["hooks"]["SessionStart"]
    assert "polyweave notice" in start["hooks"][0]["command"]


def test_the_notice_is_one_line_within_its_budget(tmp_path):
    (tmp_path / "crate.accept.toml").write_text("asset = 'crate'\n", encoding="utf-8")
    said = commands.notice(str(tmp_path))
    assert "\n" not in said
    assert len(said) <= commands.NOTICE_BUDGET
    assert "0 declarations, 1 specs here" in said
    assert "asset.brief" in said


def test_the_skill_and_its_references_stay_within_their_budgets():
    assert len((SKILL / "SKILL.md").read_text("utf-8")) <= SKILL_BUDGET
    for page in (SKILL / "references").glob("*.md"):
        assert len(page.read_text("utf-8")) <= REFERENCE_BUDGET, page.name


def test_every_operation_the_skill_names_exists():
    named = set()
    for page in [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md")]:
        named |= set(re.findall(r"`([a-z]+\.[a-z_]+)", page.read_text("utf-8")))
    named = {n for n in named if not n.endswith((".toml", ".md", ".png"))}
    assert named - set(describe.operations()) == set()


def test_no_skill_name_serves_both_sides():
    """A plugin skill drives the tool, a project skill changes it: never one name."""
    plugin = {p.name for p in (REPO / "skills").iterdir() if p.is_dir()}
    project = {p.name for p in (REPO / ".claude" / "skills").iterdir() if p.is_dir()}
    assert plugin & project == set()
