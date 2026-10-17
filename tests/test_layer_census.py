"""A layer says which of its modules are internal (§PW511)."""

from __future__ import annotations

import sys

import pytest

import polyweave.layers
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError
from polyweave.surface import census

#: Each layer's pending surface, which only shrinks; none is pending today.
PENDING: dict[str, int] = {}

LAYER = '''
from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="scent",
    summary="A fixture medium with a helper of each kind.",
    modules=(),
    census={{
        "polyweave.layers.scent.notes": ("internal", "the notes a bottle reads"),
        "polyweave.layers.scent.mixing": ("pending", "the mixer, not yet an operation"),
        {extra}
    }},
)
'''

HELPER = "def {name}():\n    return 1\n"


def _shelve(tmp_path, monkeypatch, extra=""):
    shelf = tmp_path / "shelf" / "scent"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER.format(extra=extra), encoding="utf-8")
    for module, name in (("notes", "smell"), ("mixing", "mix"), ("_bottle", "pour")):
        (shelf / f"{module}.py").write_text(HELPER.format(name=name), encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()


def _forget(monkeypatch):
    monkeypatch.undo()
    L.layers.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.scent")]:
        del sys.modules[name]


def test_a_layers_helpers_are_classified_with_no_census_edit(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch)
    try:
        found = census.census()
    finally:
        _forget(monkeypatch)
    assert "polyweave.layers.scent.notes:smell" in found["internal"]
    assert "polyweave.layers.scent._bottle:pour" in found["internal"]
    assert "polyweave.layers.scent.mixing:mix" in found["pending"]
    assert not [one for one in found["unclassified"] if ".scent." in one]


def test_a_layer_classifying_another_layers_module_is_refused(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch,
            extra='"polyweave.layers.sound.sound": ("internal", "not mine"),')
    try:
        with pytest.raises(PolyweaveError) as refused:
            census.classified()
    finally:
        _forget(monkeypatch)
    assert "polyweave.layers.sound.sound" in refused.value.message


def test_each_layers_pending_surface_only_shrinks():
    by_layer: dict[str, int] = {}
    for target in census.census()["pending"]:
        name = L.layer_of(target.split(":")[0]) or "core"
        by_layer[name] = by_layer.get(name, 0) + 1
    assert by_layer == PENDING, "lower or raise a layer's pin only as its pending moves"


def test_the_census_keeps_only_the_cores_helpers():
    assert not [key for key in census.CORE if L.layer_of(key.split(":")[0])]
