"""§4: what this installation can actually do on this machine.

The point of the call is that a caller plans against it instead of discovering a missing
binary three calls later, so the tests are about what it says when a binary is missing
as much as when one is there.
"""

from __future__ import annotations

import sys

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


def test_what_is_not_established_yet_names_the_line_that_will():
    found = capabilities(probe=False)
    assert "PW5" in found["pending"]["budget"]
    assert "PW23" in found["pending"]["offscreen"]
