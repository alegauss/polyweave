"""Record kinds, staleness and what ships, contributed by layers (§PW502)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import layer as L
from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError

LAYER = '''
from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="scent",
    summary="A fixture medium whose records say what they smell of.",
    modules=(),
    kinds=({kinds}),
    staleness={{"notes": "polyweave.layers.scent.notes:still"}},
    outdated={{"scent": "polyweave.layers.scent.notes:behind"}},
)
'''

NOTES = '''
def still(source, record, one):
    """A changed notes file still holds the note the record was made from."""
    return record["details"]["note"] in source.read_text(encoding="utf-8")


def behind(root):
    return ["lavender"]
'''


def _shelve(tmp_path, monkeypatch, kinds='"scent",'):
    shelf = tmp_path / "shelf" / "scent"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER.format(kinds=kinds), encoding="utf-8")
    (shelf / "notes.py").write_text(NOTES, encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()


@pytest.fixture
def scent(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch)
    yield tmp_path / "game"
    _forget(monkeypatch)


def _forget(monkeypatch):
    monkeypatch.undo()
    L.layers.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.scent")]:
        del sys.modules[name]


def test_provenance_imports_nothing_from_a_layer():
    source = Path(provenance.__file__).read_text(encoding="utf-8")
    imported = [
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    ]
    assert [m for m in imported if m.startswith("polyweave.layers")] == []


def test_the_kinds_are_the_nine_they_were():
    assert set(provenance.kinds()) == {
        "render", "mesh", "capture", "fetch", "picture", "sound", "vfx", "camera",
        "borrow",
    }


def test_a_layers_kind_is_recorded_and_its_staleness_answered(scent):
    scent.mkdir()
    (scent / "notes.txt").write_text("lavender and cedar\n", encoding="utf-8")
    (scent / "bottle.png").write_bytes(b"bottle")
    record = provenance.build(
        "scent",
        scent / "bottle.png",
        root=scent,
        inputs=[provenance.source("notes", scent / "notes.txt", scent)],
    )
    record["details"] = {"note": "lavender"}
    provenance.write(record, scent)
    # The file changed and the note the record was made from is still in it.
    (scent / "notes.txt").write_text("lavender and pine\n", encoding="utf-8")
    said = provenance.outdated(root=str(scent))
    assert said["outdated"] == []
    assert said["scent"] == ["lavender"]
    (scent / "notes.txt").write_text("pine alone\n", encoding="utf-8")
    assert provenance.outdated(root=str(scent))["outdated"][0]["moved"] == [
        "notes.txt"]


def test_a_kind_two_layers_declare_is_refused(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch, kinds='"capture",')
    try:
        with pytest.raises(PolyweaveError) as refused:
            provenance.kinds()
    finally:
        _forget(monkeypatch)
    assert refused.value.code == "layer.declared-twice"
    assert "capture" in refused.value.message


def test_a_layer_cannot_take_a_kind_the_kernel_writes(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch, kinds='"fetch",')
    try:
        with pytest.raises(PolyweaveError) as refused:
            provenance.kinds()
    finally:
        _forget(monkeypatch)
    assert refused.value.code == "layer.declared-twice"
    assert "'fetch'" in refused.value.message
