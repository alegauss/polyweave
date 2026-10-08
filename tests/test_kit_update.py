"""An installed kit that has fallen behind, heard of and brought up, proved (§PW343)."""

from __future__ import annotations

import pytest

from polyweave import kits, provenance
from test_kit_install import kit

KITS_TOML = "kit.toml"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    from test_kit_install import GAME

    shelf, game = tmp_path / "kits", tmp_path / "game"
    shelf.mkdir()
    game.mkdir()
    (game / "project.godot").write_text(GAME, encoding="utf-8")
    monkeypatch.setattr(kits, "KITS", shelf)
    kit(shelf, "input")
    kits.install("input", root=str(game))
    return shelf, game


def newer(shelf, *, version="0.2.0", low=None):
    """The kit as the plugin now carries it: a newer version, with what it changed."""
    toml = shelf / "input" / KITS_TOML
    toml.write_text(
        toml.read_text("utf-8").replace('version = "0.1.0"', f'version = "{version}"')
        + '\n[changes]\n"0.2.0" = "the Switch layout swaps A and B"\n'
        + (f'"{version}" = "focus no longer lost on a closed menu"\n'
           if version != "0.2.0" else ""),
        encoding="utf-8",
    )
    (shelf / "input" / "core" / "switch.gd").write_text("# new\n", encoding="utf-8")
    (shelf / "input" / "scene" / "input.tscn").write_text(
        "[gd_scene format=3]\n[node name=\"Controls\"]\n", encoding="utf-8")
    if low is not None:
        proof = shelf / "input" / "proof.accept.toml"
        proof.write_text(proof.read_text("utf-8").replace("0.1", str(low)), "utf-8")


def test_a_kit_behind_the_plugin_is_named_with_what_changed_since(setup):
    shelf, game = setup
    assert provenance.outdated(root=str(game))["kits"] == []
    newer(shelf, version="0.3.0")
    [behind] = provenance.outdated(root=str(game))["kits"]
    assert (behind["kit"], behind["installed"], behind["carried"]) == (
        "input", "0.1.0", "0.3.0")
    assert [c["version"] for c in behind["changes"]] == ["0.2.0", "0.3.0"]


def test_an_update_replaces_the_core_keeps_the_scene_and_is_proved(setup):
    shelf, game = setup
    (game / "kits" / "input" / "input.tscn").write_text("mine\n", encoding="utf-8")
    newer(shelf)
    said = kits.update("input", root=str(game))
    assert said["ok"] is True and said["proved"]["passed"] is True
    assert (game / "addons" / "polyweave" / "input" / "switch.gd").is_file()
    assert (game / "kits" / "input" / "input.tscn").read_text("utf-8") == "mine\n"
    assert any("Controls" in line for line in said["scene"]["differs"])
    assert provenance.outdated(root=str(game))["kits"] == []


def test_a_core_edited_in_the_project_is_a_finding_never_an_overwrite(setup):
    shelf, game = setup
    (game / "addons" / "polyweave" / "input" / "icon.png").write_bytes(b"edited")
    newer(shelf)
    said = kits.update("input", root=str(game))
    assert said["ok"] is False and said["edited"] == ["icon.png"]
    assert (game / "addons" / "polyweave" / "input" / "icon.png").read_bytes() == (
        b"edited")


def test_an_update_whose_proof_fails_is_put_back(setup):
    shelf, game = setup
    newer(shelf, low=0.99)
    said = kits.update("input", root=str(game))
    assert said["ok"] is False and said["wrote"] is False
    assert not (game / "addons" / "polyweave" / "input" / "switch.gd").exists()


def test_a_dry_run_writes_nothing(setup):
    shelf, game = setup
    newer(shelf)
    said = kits.update("input", write=False, root=str(game))
    assert said["wrote"] is False and said["carried"] == "0.2.0"
    assert not (game / "addons" / "polyweave" / "input" / "switch.gd").exists()
