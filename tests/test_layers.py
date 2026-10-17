"""A layer declares itself in layer.py, and nothing lists the layers (§PW500)."""

from __future__ import annotations

import sys
from typing import Annotated

import pytest

import polyweave.layers
from polyweave.kernel import describe as D
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError
from polyweave.surface import capabilities as C


def test_the_hand_kept_module_list_is_gone():
    assert not hasattr(D, "MODULES")


def test_every_layer_folder_is_a_declared_layer():
    import pkgutil

    found = pkgutil.iter_modules(polyweave.layers.__path__)
    folders = {m.name for m in found if m.ispkg}
    assert set(L.layers()) == folders
    for name, declared in L.layers().items():
        assert declared.name == name and declared.summary and declared.modules


def test_every_operation_belongs_to_exactly_one_layer_or_to_the_core():
    D.load()
    naming = {}
    for declared in L.layers().values():
        for module in declared.modules:
            assert module not in naming, f"{module} is named by two layers"
            naming[module] = declared.name
    for op in D._REGISTRY.values():
        module = op.fn.__module__
        if module.startswith("polyweave.layers."):
            assert naming.get(module) == op.layer == L.layer_of(module), op.name
        else:
            assert op.layer is None
            assert module.split(".")[1] in L.CORE, op.name


def test_a_layer_module_says_its_layer_when_described():
    assert D.describe("render.bake")["layer"] == "geometry"
    assert D.describe("game.open")["layer"] == "engine"
    # Said only where there is one: the core's operations belong to every project.
    assert "layer" not in D.describe("verdict.answer")


def test_an_operation_from_a_module_its_layer_does_not_name_is_refused_by_name():
    def stray(
        what: Annotated[str, D.Param("anything")],
    ) -> str:
        """A stray operation."""
        return what

    stray.__module__ = "polyweave.layers.sound.stray"
    with pytest.raises(PolyweaveError) as refused:
        D.operation("sound.stray")(stray)
    assert refused.value.code == "layer.unnamed-module"
    assert "polyweave.layers.sound.stray" in refused.value.message
    assert "layers/sound/layer.py" in refused.value.remedy
    assert "sound.stray" not in D._REGISTRY


def test_a_layer_folder_without_a_declaration_is_refused(tmp_path, monkeypatch):
    (tmp_path / "undeclared").mkdir()
    (tmp_path / "undeclared" / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(polyweave.layers, "__path__", [str(tmp_path)])
    L.layers.cache_clear()
    try:
        with pytest.raises(PolyweaveError) as refused:
            L.layers()
    finally:
        monkeypatch.undo()
        L.layers.cache_clear()
        sys.modules.pop("polyweave.layers.undeclared", None)
    assert refused.value.code == "layer.undeclared"
    assert "polyweave.layers.undeclared" in refused.value.message


def test_capabilities_lists_each_layer_and_what_it_is_missing():
    present = {"blender": True, "godot": False, "audio": True, "text": None}
    said = C._layers(present)
    assert set(said) == set(L.layers())
    assert said["engine"] == {
        "summary": L.layers()["engine"].summary,
        "requires": ["godot"],
        "state": "missing",
        "missing": ["godot"],
    }
    assert said["geometry"]["state"] == "available"
    assert said["words"]["state"] == "available"


def test_a_requirement_not_probed_is_said_as_such():
    said = C._layers({"blender": None, "godot": None})
    assert said["geometry"]["state"] == "not probed"
    assert "missing" not in said["geometry"]
    assert "layers" in C.capabilities(probe=False)


def test_every_requirement_a_layer_names_is_one_polyweave_finds():
    for declared in L.layers().values():
        assert set(declared.requires) <= set(L.REQUIREMENTS)
