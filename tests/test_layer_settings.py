"""A layer declares the tables it reads from polyweave.toml (§PW508)."""

from __future__ import annotations

import sys

import pytest

import polyweave.layers
from polyweave.kernel import config as C
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError

LAYER = '''
from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="scent",
    summary="A fixture medium with a table of its own.",
    modules=(),
    config="polyweave.layers.scent.settings",
)
'''

SETTINGS = '''
TABLES = {{"{table}": {{"strength": 5, "note": "lavender"}}}}
CHOICES = {{"note": ("lavender", "cedar")}}
'''


def _shelve(tmp_path, monkeypatch, table="scent"):
    shelf = tmp_path / "shelf" / "scent"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER, encoding="utf-8")
    (shelf / "settings.py").write_text(SETTINGS.format(table=table), encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()
    C._schema.cache_clear()


def _forget(monkeypatch):
    monkeypatch.undo()
    L.layers.cache_clear()
    C._schema.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.scent")]:
        del sys.modules[name]


@pytest.fixture
def scent(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch)
    game = tmp_path / "game"
    game.mkdir()
    yield game
    _forget(monkeypatch)


def _project(game, body):
    (game / C.FILENAME).write_text(body, encoding="utf-8")
    return C.load(game)


def test_a_layers_table_is_read_and_defaulted_with_no_kernel_file_touched(scent):
    config = _project(scent, "[scent]\nstrength = 7\n")
    assert config.get("scent.strength") == 7
    assert config.get("scent.note") == "lavender"
    assert C._schema().owner["scent"] == "scent"


@pytest.mark.parametrize(
    ("body", "code"),
    [("[scent]\nsweetness = 2\n", "config.unknown-key"),
     ('[scent]\nnote = "rose"\n', "config.bad-type")],
    ids=["an unknown key", "a word outside its choices"],
)
def test_a_layers_table_refuses_what_it_does_not_declare(scent, body, code):
    with pytest.raises(PolyweaveError) as refused:
        _project(scent, body)
    assert refused.value.code == code


def test_a_table_two_layers_declare_is_refused(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch, table="render")
    try:
        with pytest.raises(PolyweaveError) as refused:
            C._schema()
    finally:
        _forget(monkeypatch)
    assert refused.value.code == "layer.declared-twice"
    assert "geometry" in refused.value.message


def test_the_kernel_keeps_only_the_tables_every_project_has():
    assert set(C.KERNEL_DEFAULTS) == {
        "project", "paths", "tolerance", "cache", "provenance", "adoption", "review",
        "service", "budget", "layers", "extend",
    }
    assert C._schema().owner["voxels"] == "geometry"
