"""A kit landed in a game, recorded and proved there, in one call (§PW341).

The kits are built here: a core holding one picture, a scene the project will own, and
a proof whose spec holds the picture the core installs. The game is a project.godot
with an InputMap, which is all a kit reads before it installs.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import kits, provenance
from polyweave.config import load
from polyweave.errors import PolyweaveError

KIT = """name = "{name}"
version = "{version}"
summary = "a part every game repeats"
requires = {requires}

[installs]
core = "core"
scene = "scene/{name}.tscn"

[declares]
layouts = ["xbox", "playstation"]

[proves]
spec = "proof.accept.toml"
fixture = "fixture"
"""

PROOF = """asset = "{name}"
artefact = "addons/polyweave/{name}/icon.png"

[[predicate]]
id = "lit"
measure = "luma_p99"
region = "frame"
min = {{ value = {low}, origin = "margin" }}
"""

GAME = """config_version=5

[application]
config/name="game"
run/main_scene="res://main.tscn"

[input]
jump={{}}
move_left={{}}
"""


def kit(under, name, *, version="0.1.0", requires=(), low=0.1):
    folder = under / name
    (folder / "core").mkdir(parents=True)
    Image.new("RGBA", (8, 8), (230, 230, 230, 255)).save(folder / "core" / "icon.png")
    (folder / "scene").mkdir()
    (folder / "scene" / f"{name}.tscn").write_text("[gd_scene format=3]\n", "utf-8")
    (folder / "proof.accept.toml").write_text(PROOF.format(name=name, low=low), "utf-8")
    (folder / "fixture").mkdir()
    (folder / "fixture" / "project.godot").write_text(GAME, encoding="utf-8")
    (folder / "kit.toml").write_text(
        KIT.format(name=name, version=version, requires=json.dumps(list(requires))),
        encoding="utf-8",
    )


@pytest.fixture
def setup(tmp_path, monkeypatch):
    shelf, game = tmp_path / "kits", tmp_path / "game"
    shelf.mkdir()
    game.mkdir()
    (game / "project.godot").write_text(GAME, encoding="utf-8")
    monkeypatch.setattr(kits, "KITS", shelf)
    return shelf, game


def test_a_kit_lands_records_its_version_and_is_proved_in_one_call(setup):
    shelf, game = setup
    kit(shelf, "input")
    said = kits.install("input", root=str(game))
    assert said["ok"] is True and said["proved"]["passed"] is True
    assert (game / "addons" / "polyweave" / "input" / "icon.png").is_file()
    assert (game / "kits" / "input" / "input.tscn").is_file()
    assert said["game"]["actions"] == ["jump", "move_left"]
    assert said["game"]["main_scene"] == "res://main.tscn"
    record = provenance.read("addons/polyweave/input/kit.json", root=game)
    assert record["kit"] == {"name": "input", "version": "0.1.0"}
    assert load(game).table("kit")["input"]["layouts"] == ["xbox", "playstation"]


def test_a_dry_run_answers_the_same_and_writes_nothing(setup):
    shelf, game = setup
    kit(shelf, "input")
    said = kits.install("input", write=False, root=str(game))
    assert said["wrote"] is False and said["declared"] == {
        "input": {"layouts": ["xbox", "playstation"]}
    }
    assert sorted(p.name for p in game.iterdir()) == ["project.godot"]


def test_what_a_kit_requires_lands_first(setup):
    shelf, game = setup
    kit(shelf, "input")
    kit(shelf, "settings", requires=["input"])
    said = kits.install("settings", root=str(game))
    assert said["order"] == ["input", "settings"]
    assert {one["name"] for one in said["installed"]} == {"input", "settings"}


def test_the_projects_declaration_and_scene_are_left_as_they_are(setup):
    shelf, game = setup
    kit(shelf, "input")
    (game / "polyweave.toml").write_text('[kit.input]\nlayouts = ["switch"]\n', "utf-8")
    (game / "kits" / "input").mkdir(parents=True)
    (game / "kits" / "input" / "input.tscn").write_text("mine", encoding="utf-8")
    said = kits.install("input", root=str(game))
    assert said["declared"] == {}
    assert load(game).table("kit")["input"]["layouts"] == ["switch"]
    assert (game / "kits" / "input" / "input.tscn").read_text("utf-8") == "mine"


def test_an_upgrade_replaces_the_core_and_says_what_was_there(setup):
    shelf, game = setup
    kit(shelf, "input")
    kits.install("input", root=str(game))
    (game / "addons" / "polyweave" / "input" / "stale.gd").write_text("x", "utf-8")
    (shelf / "input" / "kit.toml").write_text(
        (shelf / "input" / "kit.toml").read_text("utf-8").replace("0.1.0", "0.2.0"),
        encoding="utf-8",
    )
    said = kits.install("input", root=str(game))
    assert said["installed"][0]["was"] == "0.1.0"
    assert not (game / "addons" / "polyweave" / "input" / "stale.gd").exists()


def test_a_proof_that_fails_is_the_first_finding(setup):
    shelf, game = setup
    kit(shelf, "input", low=0.99)
    said = kits.install("input", root=str(game))
    assert said["ok"] is False
    assert said["proved"]["first"]["status"] == "failed"


def test_an_unknown_kit_or_no_game_is_refused(setup, tmp_path):
    shelf, game = setup
    kit(shelf, "input")
    with pytest.raises(PolyweaveError) as unknown:
        kits.install("save", root=str(game))
    assert unknown.value.code == "kits.unknown"
    (tmp_path / "empty").mkdir()
    with pytest.raises(PolyweaveError) as nowhere:
        kits.install("input", root=str(tmp_path / "empty"))
    assert nowhere.value.code == "kits.no-game"
