"""A layer measures its own subject for accept (§PW503)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import accept, measure

LAYER = '''
from polyweave.kernel.layer import Layer, Subject

LAYER = Layer(
    name="scent",
    summary="A fixture medium whose files say how strong they smell.",
    modules=(),
    subjects=(
        Subject(
            about="a bottle's label",
            measures="polyweave.layers.scent.notes:MEASURES",
            target="polyweave.layers.scent.notes:predicate",
        ),
    ),
)
'''

NOTES = '''
from pathlib import Path

MEASURES = {{"{name}": "how strong the bottle says it is, 0 to 10"}}


def predicate(p, subject, root, seen):
    where = Path(root) / (p.of or subject)
    seen[str(where)] = seen.get(str(where), 0) + 1
    return {{"value": float(where.read_text(encoding="utf-8")), "of": str(where),
             "read": seen[str(where)]}}
'''

SPEC = '''
asset = "bottle"

[[predicate]]
id = "strong"
measure = "strength"
max = 6

[[predicate]]
id = "there"
measure = "strength"
min = 1
'''


def _shelve(tmp_path, monkeypatch, name="strength"):
    shelf = tmp_path / "shelf" / "scent"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER, encoding="utf-8")
    (shelf / "notes.py").write_text(NOTES.format(name=name), encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()


def _forget(monkeypatch):
    monkeypatch.undo()
    L.layers.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.scent")]:
        del sys.modules[name]


@pytest.fixture
def scent(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch)
    yield tmp_path
    _forget(monkeypatch)


@pytest.mark.parametrize("module", [accept, measure])
def test_the_loop_imports_nothing_from_a_layer(module):
    source = Path(module.__file__).read_text(encoding="utf-8")
    imported = [
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    ]
    assert [m for m in imported if m.startswith("polyweave.layers")] == []


def test_a_layers_subject_is_bounded_and_checked_end_to_end(scent):
    (scent / "bottle.txt").write_text("7.5", encoding="utf-8")
    (scent / "bottle.accept.toml").write_text(SPEC, encoding="utf-8")
    said = accept.checked("bottle.accept.toml", "bottle.txt", root=str(scent))
    assert said["failed"] == ["strong"]
    strong, there = said["predicates"]
    assert strong["value"] == 7.5 and strong["passed"] is False
    assert strong["of"].endswith("bottle.txt") and strong["rung"] is None
    assert there["passed"] is True
    # One check reads a file once, whichever predicates bound it.
    assert (strong["read"], there["read"]) == (1, 2)
    # Read off a file, so it asks nothing of the render ladder.
    assert said["needs_rung"] == "sphere"


def test_a_measure_two_layers_declare_is_refused(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch, name="triangles")
    try:
        with pytest.raises(PolyweaveError) as refused:
            L.subjects()
    finally:
        _forget(monkeypatch)
    assert refused.value.code == "layer.declared-twice"
    assert "triangles" in refused.value.message


def test_a_file_measure_asked_of_a_picture_names_its_layer():
    with pytest.raises(PolyweaveError) as refused:
        measure.resolve("triangles")
    assert refused.value.code == "spec.unknown-measure"
    assert "geometry layer" in refused.value.message


def test_a_predicate_with_no_measure_is_told_every_layers_names():
    with pytest.raises(PolyweaveError) as refused:
        accept.parse({"predicate": [{"id": "x", "max": 1}]})
    for name in ("triangles", "loudness", "flashes", "video_seconds"):
        assert name in refused.value.remedy
