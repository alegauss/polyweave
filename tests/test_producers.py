"""A layer produces a sample, and one search aims every layer (§PW504)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import calibrate, search

LAYER = '''
from polyweave.kernel.layer import Layer, Producer, Subject

LAYER = Layer(
    name="scent",
    summary="A fixture medium whose bottles are mixed to a strength.",
    modules=(),
    producers=(
        Producer(
            name="mix",
            about="a bottle mixed at a strength",
            target="polyweave.layers.scent.notes:mix",
        ),
    ),
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

MEASURES = {"strength": "how strong the bottle is, 0 to 10"}
MIXED = []


def mix(report, *, out, rung=None, root=".", inline=True, strength=0.0):
    where = Path(root) / out
    where.write_text(str(strength), encoding="utf-8")
    MIXED.append(strength)
    return {"artefact": str(where)}


def predicate(p, subject, root, seen):
    where = Path(root) / (p.of or subject)
    return {"value": float(where.read_text(encoding="utf-8")), "of": str(where)}
'''

SPEC = '''
asset = "bottle"

[[predicate]]
id = "balanced"
measure = "strength"
min = 3.5
max = 4.5

[search.strength]
min = 0
max = 10
'''


@pytest.fixture
def scent(tmp_path, monkeypatch):
    shelf = tmp_path / "shelf" / "scent"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER, encoding="utf-8")
    (shelf / "notes.py").write_text(NOTES, encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()
    game = tmp_path / "game"
    game.mkdir()
    (game / "bottle.accept.toml").write_text(SPEC, encoding="utf-8")
    yield game
    monkeypatch.undo()
    L.layers.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.scent")]:
        del sys.modules[name]


@pytest.mark.parametrize("module", [search, calibrate])
def test_the_search_imports_nothing_from_a_layer(module):
    source = Path(module.__file__).read_text(encoding="utf-8")
    imported = [
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    ]
    assert [m for m in imported if m.startswith("polyweave.layers")] == []


def test_a_layers_producer_is_swept_traced_and_reported(scent):
    found = search.sweep(
        "bottle.accept.toml", out="bottle.txt", root=str(scent), producer="mix",
        budget=12, trace="bottle.trace",
    )
    assert found["passed"] is True
    assert 3.5 <= found["best"]["strength"] <= 4.5
    from polyweave.layers.scent import notes

    # Every sample the budget paid for was made by the layer's producer.
    assert 0 < found["spent"] <= min(len(notes.MIXED), 12)
    written = json.loads((scent / "bottle.trace.json").read_text(encoding="utf-8"))
    assert len(written["samples"]) == found["trace_written"]["samples"] > 0
    # Nothing it made is in the render cache, so there is no sheet, and it says so.
    assert found["trace_written"]["sheet"] is None


def test_the_render_is_one_producer_among_them():
    made = L.producers()["render"]
    assert made.target == "polyweave.layers.geometry.render:bake"
    assert made.plan and made.described


def test_an_unknown_producer_is_refused_with_the_ones_there_are(scent):
    with pytest.raises(PolyweaveError) as refused:
        search.sweep("bottle.accept.toml", out="s.txt", root=str(scent),
                     producer="blender")
    assert refused.value.code == "search.unknown-producer"
    assert "render" in refused.value.allowed
