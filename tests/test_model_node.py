"""Another declaration's model, placed with its materials (§PW588).

Spinhold's worlds are voxel dioramas of kit pieces that are each their own declaration.
Every count here is arithmetic on cubes of whole cells.
"""

from __future__ import annotations

import collections

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers import geometry as G
from polyweave.layers.geometry.representations.voxels import model as V

#: A 2 by 2 by 2 cottage: a wall cube below a roof slab, each in its own material.
COTTAGE = """name = "cottage"
output = "cottage"

[voxels]
cell = 1.0

[materials.wall]
colour = "#EEDDCC"

[materials.roof]
colour = "#AA3322"
glow = 0.5

[[nodes]]
id = "wall"
op = "primitive"
kind = "cube"
size = [2, 2, 1]
at = [0, 0, -0.5]
material = "wall"

[[nodes]]
id = "roof"
op = "primitive"
kind = "cube"
size = [2, 2, 1]
at = [0, 0, 0.5]
material = "roof"

[[nodes]]
id = "cottage"
op = "union"
of = ["wall", "roof"]
"""

DIORAMA = """name = "diorama"
output = "street"

[voxels]
cell = 1.0

[materials.ground]
colour = "#335533"
{extra}
[[nodes]]
id = "ground"
op = "primitive"
kind = "cube"
size = [8, 2, 1]
at = [0, 0, -1.5]
material = "ground"

[[nodes]]
id = "houses"
op = "model"
path = "kit/cottage.toml"
at = ["x", 0, 0]
repeat = [{{ var = "x", from = -3, to = 3, step = 6 }}]

[[nodes]]
id = "street"
op = "union"
of = ["ground", "houses"]
"""


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "kit").mkdir()
    (tmp_path / "kit" / "cottage.toml").write_text(COTTAGE, encoding="utf-8")
    return tmp_path


def built(tree, extra=""):
    (tree / "street.toml").write_text(DIORAMA.format(extra=extra), encoding="utf-8")
    return V.voxelize(G.read(tree / "street.toml", root=tree), root=tree)


def worn(made):
    names = [one["name"] for one in made["palette"]]
    return collections.Counter(names[i] for i in made["cells"]["palette"])


def test_each_piece_keeps_its_materials_named_under_it(tree):
    made = built(tree)
    assert worn(made) == {"ground": 16, "cottage.wall": 8, "cottage.roof": 8}
    roof = next(one for one in made["palette"] if one["name"] == "cottage.roof")
    assert roof["colour"] == "#AA3322" and roof["glow"] == 0.5
    assert [f for f in made["checks"]["findings"] if f["check"] == "material"] == []


def test_a_name_the_diorama_declares_is_its_own(tree):
    made = built(tree, '\n[materials.roof]\ncolour = "#000000"\n')
    assert worn(made) == {"ground": 16, "cottage.wall": 8, "roof": 8}
    roof = next(one for one in made["palette"] if one["name"] == "roof")
    assert roof["colour"] == "#000000"


def test_a_piece_is_moved_as_a_transform_moves_it(tree):
    (tree / "one.toml").write_text(
        'name = "one"\noutput = "big"\n\n[voxels]\ncell = 1.0\n\n'
        '[[nodes]]\nid = "big"\nop = "model"\npath = "kit/cottage.toml"\n'
        "scale = [2, 1, 1]\nat = [10, 0, 0]\n",
        encoding="utf-8",
    )
    made = V.voxelize(G.read(tree / "one.toml", root=tree), root=tree)
    assert made["count"] == 16
    assert made["size"] == [4, 2, 2]
    assert made["origin"][0] == pytest.approx(8.0)


def test_a_piece_that_places_itself_is_refused(tree):
    (tree / "kit" / "loop.toml").write_text(
        'name = "loop"\noutput = "again"\n\n[voxels]\ncell = 1.0\n\n'
        '[[nodes]]\nid = "again"\nop = "model"\npath = "kit/loop.toml"\n',
        encoding="utf-8",
    )
    with pytest.raises(PolyweaveError) as refused:
        V.voxelize(G.read(tree / "kit" / "loop.toml", root=tree), root=tree)
    assert "contain itself" in refused.value.message


def test_a_path_with_no_declaration_is_refused(tree):
    (tree / "kit" / "cottage.toml").unlink()
    with pytest.raises(PolyweaveError) as refused:
        built(tree)
    assert refused.value.code == "geom.bad-solid"
    assert "kit/cottage.toml" in refused.value.message


def test_a_mesh_declaration_is_told_to_build_as_voxels(tree):
    document = G.read(tree / "kit" / "cottage.toml", root=tree)
    mesh = {**document, "nodes": [
        {"id": "piece", "op": "model", "path": "kit/cottage.toml"}], "output": "piece"}
    mesh.pop("voxels", None)
    with pytest.raises(PolyweaveError) as refused:
        G.build.build(mesh, root=tree)
    assert "[voxels]" in refused.value.remedy
