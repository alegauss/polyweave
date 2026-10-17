"""Triangles and cells as representations of one graph (§PW514)."""

from __future__ import annotations

import json
import sys

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import build as B
from polyweave.layers.geometry import representations as R

TILES = '''
import json
from pathlib import Path

from .. import build as B
from . import Representation


def write(document, out, *, root=".", manifold=False, **given):
    made = B.build(document, root=root, **given)
    where = Path(root) / out
    where.write_text(json.dumps({"faces": len(made["output"]["faces"]),
                                 "tile": document["tiles"]["size"]}), encoding="utf-8")
    return {**made, "artefact": str(where)}


def member(document, folder, here, given, preview, wanted, answer, mesh):
    return answer


REPRESENTATION = Representation(name="tiles", table="tiles", write=write, member=member)
'''

DECLARATION = {
    "name": "slab",
    "version": 1,
    "params": {},
    "materials": {},
    "nodes": [
        {"id": "box", "op": "primitive", "kind": "cube", "size": 2.0},
        {"id": "it", "op": "transform", "of": "box", "scale": 2.0},
    ],
    "output": "it",
}


def test_build_write_has_no_branch_of_its_own():
    import inspect

    assert "voxels" not in inspect.getsource(B.write).split('"""')[-1]


def test_a_declaration_is_claimed_by_its_table_or_by_the_default():
    assert R.claim(DECLARATION).name == "mesh"
    assert R.claim({**DECLARATION, "voxels": {"cell": 1}}).name == "voxels"


@pytest.fixture
def tiles(tmp_path, monkeypatch):
    (tmp_path / "shelf").mkdir()
    (tmp_path / "shelf" / "tiles.py").write_text(TILES, encoding="utf-8")
    monkeypatch.setattr(R, "__path__", [*R.__path__, str(tmp_path / "shelf")])
    R.every.cache_clear()
    yield tmp_path
    monkeypatch.undo()
    R.every.cache_clear()
    sys.modules.pop("polyweave.layers.geometry.representations.tiles", None)


def test_a_third_representation_builds_a_two_op_declaration_end_to_end(tiles):
    said = B.write({**DECLARATION, "tiles": {"size": 8}}, "slab.tiles.json",
                   root=tiles)
    written = json.loads((tiles / "slab.tiles.json").read_text(encoding="utf-8"))
    assert written == {"faces": 6, "tile": 8}
    assert said["artefact"].endswith("slab.tiles.json")


def test_two_representations_asked_for_at_once_are_refused(tiles):
    with pytest.raises(PolyweaveError) as refused:
        R.claim({**DECLARATION, "tiles": {"size": 8}, "voxels": {"cell": 1}})
    assert "tiles" in refused.value.message and "voxels" in refused.value.message
