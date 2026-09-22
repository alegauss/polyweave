"""§4: what this installation can actually do on this machine.

The point of the call is that a caller plans against it instead of discovering a missing
binary three calls later, so the tests are about what it says when a binary is missing
as much as when one is there.
"""

from __future__ import annotations

import sys

import pytest

from polyweave.capabilities import capabilities


def test_it_reports_this_interpreter_and_this_machine():
    found = capabilities(probe=False)
    assert found["python"]["executable"] == sys.executable
    assert found["platform"]["system"]
    assert found["polyweave"]


def test_a_binary_that_is_not_there_says_where_it_looked(tmp_path):
    found = capabilities(blender=tmp_path / "nowhere" / "blender.exe")
    blender = found["renderer"]["blender"]
    assert blender["found"] is False
    assert blender["version"] is None
    assert "nowhere" in blender["why"]


def test_a_binary_is_asked_its_version_rather_than_assumed(tmp_path):
    """A path that exists is not a renderer; being able to answer is."""
    found = capabilities(blender=sys.executable, probe=True)
    blender = found["renderer"]["blender"]
    assert blender["found"] is True
    assert blender["path"] == sys.executable
    assert "Python" in (blender["version"] or "")


def test_a_service_key_is_reported_by_presence_and_never_by_value(monkeypatch):
    monkeypatch.setenv("POLYWEAVE_TEST_KEY", "sk-should-never-appear")
    found = capabilities(service_key_env="POLYWEAVE_TEST_KEY", probe=False)
    assert found["service"] == {
        "key_env": "POLYWEAVE_TEST_KEY",
        "key_present": True,
    }
    assert "sk-should-never-appear" not in repr(found)


def test_an_absent_key_is_absent_rather_than_unknown(monkeypatch):
    monkeypatch.delenv("POLYWEAVE_TEST_KEY", raising=False)
    found = capabilities(service_key_env="POLYWEAVE_TEST_KEY", probe=False)
    assert found["service"]["key_present"] is False


def test_no_key_env_named_is_not_the_same_as_no_key():
    found = capabilities(probe=False)
    assert found["service"]["key_present"] is None


def test_it_reports_the_surface_that_already_exists():
    found = capabilities(probe=False)
    assert "bake" in found["jobs"]["kinds"]
    assert found["jobs"]["terminal"] == ["done", "failed", "cancelled"]
    assert "render" in found["assertions"]["always"]
    assert "manifold" in found["assertions"]["optional"]
    assert isinstance(found["operations"], list)


def test_it_lists_the_failures_a_caller_can_plan_for():
    found = capabilities(probe=False)
    assert "job.worker-gone" in found["errors"]["codes"]
    assert found["errors"]["areas"]["post"]


def test_what_is_not_established_yet_names_the_line_that_will():
    found = capabilities(probe=False)
    assert "PW23" in found["pending"]["offscreen"]
    assert "PW14" in found["pending"]["cache"]


def test_a_budget_nobody_declared_is_not_an_unlimited_one():
    assert capabilities(probe=False)["budget"]["spendable"] is False


# -- whether a colour can be measured here at all (§PW43) ------------------------


def test_an_unprobed_read_does_not_render_anything():
    """A colour check costs a render, so it belongs to the probing read only."""
    found = capabilities(probe=False)["renderer"]["colour"]
    assert found["checked"] is False
    assert found["why"] == "not probed"


def test_usable_and_trustworthy_are_different_questions(tmp_path):
    """A renderer that runs can hand back a colour that is not the authored one."""
    found = capabilities(tmp_path)["renderer"]
    assert set(found) >= {"usable", "colour"}


def test_this_installation_says_whether_a_measured_colour_is_the_authored_one(tmp_path):
    """§PW43's whole point: an installation that cannot measure colour says so."""
    bpy = pytest.importorskip("bpy", reason="the probe needs a renderer")
    assert bpy
    found = capabilities(tmp_path)["renderer"]["colour"]
    assert found["checked"] is True
    assert found["authored"] == 128
    assert found["view_transform"], "and which transform produced that"
    if found["trustworthy"]:
        assert found["off_by"] <= 2
        assert found["why"] is None
    else:
        assert "came back as" in found["why"], "a failure names the number it saw"


def test_the_probe_is_deterministic_so_a_second_read_agrees_with_the_first(tmp_path):
    bpy = pytest.importorskip("bpy", reason="the probe needs a renderer")
    assert bpy
    first = capabilities(tmp_path)["renderer"]["colour"]["measured"]
    assert capabilities(tmp_path)["renderer"]["colour"]["measured"] == first


def test_a_machine_with_no_renderer_says_that_rather_than_failing(monkeypatch):
    """The read is a report. A probe that cannot run is an answer, not a stop."""
    from polyweave.render import blender

    monkeypatch.setattr(blender, "available", lambda: {"found": False, "why": "none"})
    found = capabilities(probe=True)["renderer"]["colour"]
    assert found["checked"] is False
    assert "bpy is not importable" in found["why"]
