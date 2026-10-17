"""A project turns on the layers it uses (§PW509)."""

from __future__ import annotations

import json

import pytest

from polyweave.kernel import config as C
from polyweave.kernel import describe as D
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.layer import on
from polyweave.surface import server


def _project(path, body=""):
    (path / C.FILENAME).write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def two_layers(tmp_path, monkeypatch):
    monkeypatch.chdir(_project(tmp_path, '[layers]\non = ["picture", "sound"]\n'))
    return tmp_path


def _named(listed):
    return {tool["name"] for tool in listed}


def test_a_two_layer_project_is_served_only_its_layers_and_the_core(two_layers):
    served = _named(server.tools(blender=True, root=two_layers))
    assert "picture_buy" in served and "sound_measure" in served
    assert "verdict_answer" in served and "describe" in served
    assert "geometry_build" not in served and "game_open" not in served


def test_a_project_that_says_nothing_is_served_every_layer(tmp_path):
    served = _named(server.tools(blender=True, root=_project(tmp_path)))
    assert {"geometry_build", "game_open", "picture_buy"} <= served
    assert len(served) == len(D.operations()) + 1


def test_calling_an_off_layers_tool_says_which_line_turns_it_on(two_layers):
    said = server.call("geometry_build", {"source": "box.toml"})
    assert said["isError"]
    refused = json.loads(said["content"][0]["text"])["refused"]
    assert refused["code"] == "layer.off"
    assert "geometry" in refused["message"]
    assert '"geometry"' in refused["remedy"]


def test_an_off_layers_operation_is_still_described_and_marked_off(two_layers):
    said = server.call("describe", {"operation": "geometry.build"})
    described = json.loads(said["content"][0]["text"])
    assert described["operation"] == "geometry.build" and described["off"] is True
    kept = json.loads(server.call("describe", {"operation": "picture.buy"})[
        "content"][0]["text"])
    assert "off" not in kept


def test_a_table_of_an_off_layer_is_refused_by_the_layers_name(tmp_path):
    _project(tmp_path, '[layers]\non = ["picture"]\n\n[voxels]\nbudget = 4\n')
    with pytest.raises(PolyweaveError) as refused:
        C.load(tmp_path)
    assert refused.value.code == "layer.off"
    assert "geometry" in refused.value.message


def test_a_layer_no_one_has_is_refused_with_the_ones_there_are(tmp_path):
    _project(tmp_path, '[layers]\non = ["picture", "smell"]\n')
    with pytest.raises(PolyweaveError) as refused:
        on(tmp_path)
    assert refused.value.code == "layer.unknown"
    assert "picture" in refused.value.allowed
