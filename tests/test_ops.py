"""One file per geometry op (§PW513)."""

from __future__ import annotations

import sys

import pytest

from polyweave.layers.geometry import build, ops, review
from polyweave.layers.geometry.representations.voxels import model as voxels

OP = '''
from .. import solid as S

NAME = "pebble"
FIELDS = ("size",)
TRACED = True


def build(node, instance, built, root):
    return S.shape({"kind": "sphere", "size": instance.get("size", [1, 1, 1])})


def words(node, instance, takes, rest, skip):
    return "a pebble", rest
'''


def test_every_op_answers_every_part():
    for name, op in ops.every().items():
        assert callable(op.build) and op.words is not None, name
        assert op.fields is not None or name == "custom", name
        # A voxel build reads an op's own box and cells, or traces its mesh.
        assert op.traced or (op.bounds is not None and op.inside is not None), name


def test_the_tables_are_read_off_the_op_modules():
    assert list(build.BUILDS) == list(ops.ORDER)
    assert set(build.FIELDS) == set(build.BUILDS)
    assert set(voxels.TRACED) == {
        "crowned", "annulus", "inflate", "blend", "custom", "mesh"}


@pytest.fixture
def pebble(tmp_path, monkeypatch):
    (tmp_path / "pebble.py").write_text(OP, encoding="utf-8")
    monkeypatch.setattr(ops, "__path__", [*ops.__path__, str(tmp_path)])
    ops.every.cache_clear()
    yield
    monkeypatch.undo()
    ops.every.cache_clear()
    sys.modules.pop("polyweave.layers.geometry.ops.pebble", None)


def test_a_new_op_is_one_new_file(pebble):
    assert "pebble" in build.BUILDS and build.FIELDS["pebble"] == ("size",)
    assert "pebble" in voxels.TRACED
    node = {"id": "p", "op": "pebble"}
    assert review._says(node, {"size": [1, 1, 1]}).startswith("a pebble")
