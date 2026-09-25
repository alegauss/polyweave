"""A picture or a mesh bought from the world's description of an entity (§PW198)."""

from __future__ import annotations

import json

import pytest

from polyweave import mesh_buy, picture, provenance
from polyweave.errors import PolyweaveError
from test_mesh_buy import GLB, Meshy
from test_mesh_buy import PROJECT as MESHY
from test_picture import PNG, Service
from test_picture import PROJECT as IDEOGRAM

WORLD = """\
[entity.mason]
name = "The Mason"
kind = "character"
style = "portrait"

[entity.mason.look]
description = "a stooped builder in a dust-grey apron"
shows = ["a trowel", "chalk on the hands"]
never = ["a weapon"]

[entity.ada]
name = "Captain Ada"
kind = "character"
"""

STYLE = '\n[style.portrait]\npalette = ["#3a2e39"]\n\n[style.scenery]\n'


@pytest.fixture
def world(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(IDEOGRAM + STYLE, encoding="utf-8")
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_I", "sk-picture")
    fake = Service()
    monkeypatch.setattr(picture, "_send", fake.send)
    monkeypatch.setattr(picture, "_download", lambda link: PNG)
    return fake


def _bought(tmp_path, **over):
    fields = {"out": "refs/mason.png", "service": "ideogram", "root": tmp_path}
    return picture.buy(**{**fields, **over})


def test_a_picture_of_an_entity_is_composed_from_the_world(tmp_path, world):
    _bought(tmp_path, entity="mason", prompt="leaning on a wall")
    sent = json.loads(world.sent[0][2]["json_prompt"])
    assert sent["high_level_description"] == (
        "a stooped builder in a dust-grey apron. leaning on a wall. "
        "It shows a trowel, chalk on the hands. It never shows a weapon."
    )
    assert sent["style_description"]["color_palette"] == ["#3a2e39"]
    record = provenance.read("refs/mason.png", root=tmp_path)
    assert record["details"]["family"] == "portrait"
    assert record["details"]["entity"]["id"] == "mason"
    assert [i["role"] for i in record["inputs"]] == ["world"]


def test_a_family_other_than_the_entity_s_own_is_refused(tmp_path, world):
    with pytest.raises(PolyweaveError) as refused:
        _bought(tmp_path, entity="mason", family="scenery")
    assert refused.value.code == "world.family-mismatch"
    assert world.sent == []


def test_an_entity_the_world_lacks_is_refused_before_anything_is_spent(tmp_path, world):
    with pytest.raises(PolyweaveError) as refused:
        _bought(tmp_path, entity="masn")
    assert refused.value.code == "world.unknown-entity"
    assert refused.value.did_you_mean == "mason"
    assert world.sent == []


def test_only_what_was_drawn_from_the_changed_entity_is_outdated(tmp_path, world):
    _bought(tmp_path, entity="mason")
    world_file = tmp_path / "game.world.toml"
    world_file.write_text(WORLD.replace("Captain Ada", "Admiral Ada"), "utf-8")
    assert provenance.outdated(root=tmp_path)["sound"] is True
    world_file.write_text(WORLD.replace("a trowel", "a hammer"), "utf-8")
    stale = provenance.outdated(root=tmp_path)["outdated"]
    assert [s["artefact"] for s in stale] == ["refs/mason.png"]
    found = provenance.dependents("game.world.toml", root=tmp_path)["artefacts"]
    assert [a["entity"] for a in found] == ["mason"]


def test_a_mesh_of_an_entity_is_bought_from_the_world_s_words(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text(MESHY + STYLE, encoding="utf-8")
    (tmp_path / "game.world.toml").write_text(WORLD, encoding="utf-8")
    monkeypatch.setenv("POLYWEAVE_TEST_M", "msy")
    fake = Meshy()
    monkeypatch.setattr(mesh_buy, "_json", fake)
    monkeypatch.setattr(mesh_buy, "POLL_EVERY", 0)
    monkeypatch.setattr(picture, "_download", lambda link: GLB)
    mesh_buy.buy(out="m/mason.glb", entity="mason", root=tmp_path)
    _, payload = fake.sent[0]
    assert payload["prompt"].startswith("a stooped builder in a dust-grey apron.")
    record = provenance.read("m/mason.glb", root=tmp_path)
    assert record["details"]["entity"]["id"] == "mason"
