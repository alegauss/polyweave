"""A layer contributes its part of the brief, the page and the report (§PW505)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import brief, loop, review

LAYER = '''
from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="scent",
    summary="A fixture medium with a part in every shared read.",
    modules=(),
    parts={
        "brief:scent": "polyweave.layers.scent.notes:briefed",
        "report:scent": "polyweave.layers.scent.notes:reported",
        "review:scent": "polyweave.layers.scent.notes:shown",
    },
)
'''

NOTES = '''
def briefed(path, here):
    return {"bottles": 3, "of": path}


def reported(root):
    return {"bottles": 3, "from": "bottles.json"}


def shown(here):
    return [{"bottle": "lavender"}]
'''

SPEC = '''
asset = "bottle"

[[predicate]]
id = "dim"
measure = "saturation_p99"
max = 0.5
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


@pytest.mark.parametrize("module", [brief, review, loop])
def test_the_shared_reads_import_nothing_from_a_layer(module):
    source = Path(module.__file__).read_text(encoding="utf-8")
    imported = [
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    ]
    assert [m for m in imported if m.startswith("polyweave.layers")] == []


def test_a_layers_part_shows_up_in_the_brief_the_report_and_the_page(scent):
    said = brief.brief("bottle", root=str(scent))
    assert said["scent"] == {"bottles": 3, "of": None}
    # The picture layer's own part is there beside it, under its key as before.
    assert "gate" in said
    assert loop.report(root=str(scent))["scent"] == {
        "bottles": 3, "from": "bottles.json"}
    page = review.state(root=str(scent))
    assert page["scent"] == [{"bottle": "lavender"}]
    assert {"gates", "turntables"} <= set(page)


def test_a_part_no_layer_answers_is_refused_by_name():
    with pytest.raises(PolyweaveError) as refused:
        L.needed("page.smell")
    assert refused.value.code == "layer.missing-part"
    assert "page.admit" in refused.value.allowed
