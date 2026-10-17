"""A layer declares its own error codes (§PW507)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import codes as C
from polyweave.kernel import layer as L
from polyweave.kernel.errors import PolyweaveError, explain

LAYER = '''
from polyweave.kernel.layer import Layer

LAYER = Layer(
    name="scent",
    summary="A fixture medium with errors of its own.",
    modules=(),
    codes="polyweave.layers.scent.codes",
)
'''

CODES = '''
from polyweave.kernel.codes import Code

AREAS = {{"{area}": "a bottle and what it smells of"}}

CODES = {{
    "{code}": Code(
        means="the bottle is empty",
        when="a scent is asked of a bottle with nothing in it",
        doors=("fill the bottle",),
    ),
}}
'''


def _shelve(tmp_path, monkeypatch, area="scent", code="scent.empty"):
    shelf = tmp_path / "shelf" / "scent"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER, encoding="utf-8")
    (shelf / "codes.py").write_text(CODES.format(area=area, code=code),
                                    encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()
    C._every.cache_clear()


def _forget(monkeypatch):
    monkeypatch.undo()
    L.layers.cache_clear()
    C._every.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.scent")]:
        del sys.modules[name]


@pytest.fixture
def scent(tmp_path, monkeypatch):
    _shelve(tmp_path, monkeypatch)
    yield
    _forget(monkeypatch)


def test_a_layers_code_is_raised_and_explained_with_no_kernel_file_touched(scent):
    refused = PolyweaveError("scent.empty", "the bottle is empty", "fill it")
    assert refused.code == "scent.empty"
    said = explain("scent.empty")
    assert said["layer"] == "scent" and said["means"] == "the bottle is empty"
    assert "scent" in C.AREAS


def test_the_kernels_table_holds_only_the_kernel_and_the_loop():
    kernel = {C.area_of(code) for code in C.KERNEL_CODES}
    layered = {area for one in L.layers().values() if one.codes
               for area in __import__(one.codes, fromlist=["AREAS"]).AREAS}
    assert kernel.isdisjoint(layered)
    assert {"op", "config", "spec", "loop", "job"} <= kernel
    assert "geom" in layered and "music" in layered


def test_every_code_is_explained_by_the_layer_that_owns_it():
    assert explain("geom.unknown-op")["layer"] == "geometry"
    assert "layer" not in explain("op.unknown")


@pytest.mark.parametrize(
    ("area", "code"),
    [("geom", "geom.empty"), ("scent", "smell.empty")],
    ids=["an area another layer owns", "a code outside its own areas"],
)
def test_a_code_declared_where_it_does_not_belong_is_refused(
    tmp_path, monkeypatch, area, code
):
    _shelve(tmp_path, monkeypatch, area=area, code=code)
    try:
        with pytest.raises(PolyweaveError) as refused:
            C._every()
    finally:
        _forget(monkeypatch)
    assert refused.value.code == "layer.declared-twice"


def test_the_kernels_codes_file_is_no_longer_the_whole_table():
    kernel = Path(C.__file__).read_text(encoding="utf-8")
    assert len(kernel.splitlines()) < 1400
