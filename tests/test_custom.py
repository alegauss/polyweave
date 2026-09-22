"""The escape hatch, which is a node and never a mode.

§PW34's case: any format will eventually meet a shape it cannot state, and the framework
that forces the shape into the format anyway produces worse geometry than the script it
replaced.
"""

from __future__ import annotations

import pytest

from polyweave import geometry as G
from polyweave.errors import PolyweaveError
from polyweave.geometry import custom

ROPE = '''
"""A shape the format cannot state, which is the whole point of this node."""


def build(along=None, thickness=1.0, twist=0):
    count = int(max(3, twist))
    points = [[float(i), thickness, 0.0] for i in range(count)]
    return {"vertices": points, "faces": [tuple(range(count))]}


def nothing(**how):
    return None


def angry(**how):
    raise ValueError("the rope came apart")
'''

SHAPE = """
name   = "prop"
output = "rope"

[params]
bevel = 2.0

[[nodes]]
id    = "face"
op    = "plate"
rect  = ["0", "0", "10", "10"]
depth = 2

[[nodes]]
id     = "rope"
op     = "custom"
fn     = "tools/rope.py:build"
inputs = { along = "face" }
args   = { thickness = "bevel * 1.5", twist = 12 }
"""


def project(tmp_path, body=SHAPE, code=ROPE):
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "rope.py").write_text(code, encoding="utf-8")
    (tmp_path / "prop.toml").write_text(body, encoding="utf-8")
    return G.read("prop.toml", root=tmp_path)


def node_of(document, one="rope"):
    return next(n for n in document["nodes"] if n["id"] == one)


def instance_of(document, one="rope", **given):
    resolved = G.expand(document, **given)
    return next(n for n in resolved["nodes"] if n["id"] == one)["instances"][0]


# -- the parameters stay declared ----------------------------------------------------


def test_the_custom_node_s_arguments_are_expressions_over_the_document(tmp_path):
    """So a search can still reach `thickness` by turning `bevel`."""
    document = project(tmp_path)
    assert instance_of(document)["args"]["thickness"] == pytest.approx(3.0)
    assert instance_of(document, bevel=4.0)["args"]["thickness"] == pytest.approx(6.0)


def test_a_custom_node_rebuilds_when_a_parameter_it_reads_changes(tmp_path):
    assert "rope" in G.rebuilds(project(tmp_path), "bevel")


def test_the_rest_of_the_shape_is_still_data(tmp_path):
    """A declaration does not become a script because one node in it is custom."""
    document = project(tmp_path)
    assert [n["op"] for n in document["nodes"]] == ["plate", "custom"]
    assert instance_of(document, one="face")["rect"] == [0.0, 0.0, 10.0, 10.0]


# -- the source is hashed --------------------------------------------------------------


def test_the_function_s_file_is_hashed_into_the_record(tmp_path):
    found = custom.records(project(tmp_path), root=tmp_path)
    assert len(found) == 1
    assert len(found[0]["sha256"]) == 64
    assert found[0]["fn"] == "tools/rope.py:build"


def test_changing_the_code_changes_the_digest(tmp_path):
    """Or a custom node whose file changed comes back as the shape it used to be."""
    before = custom.records(project(tmp_path), root=tmp_path)[0]["sha256"]
    after = custom.records(
        project(tmp_path, code=ROPE.replace("thickness, 0.0", "thickness, 0.5")),
        root=tmp_path,
    )[0]["sha256"]
    assert before != after


def test_a_document_with_no_custom_node_hashes_nothing(tmp_path):
    without_the_rope = SHAPE.replace('output = "rope"', 'output = "face"').split(
        '[[nodes]]\nid     = "rope"'
    )[0]
    (tmp_path / "plain.toml").write_text(without_the_rope, encoding="utf-8")
    assert custom.records(G.read("plain.toml", root=tmp_path), root=tmp_path) == []


def test_a_function_that_is_not_a_file_in_the_tree_says_so_rather_than_guessing(
    tmp_path,
):
    found = custom.source("math:floor", root=tmp_path)
    assert found["sha256"] == ""
    assert found["why"] == "not a file in the tree"


# -- calling it ------------------------------------------------------------------------


def built_face():
    return {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "faces": [(0, 1, 2)]}


def test_the_function_is_handed_its_inputs_as_meshes_and_not_as_ids(tmp_path):
    document = project(tmp_path)
    made = custom.build(
        node_of(document), instance_of(document), {"face": built_face()}, root=tmp_path
    )
    assert len(made["vertices"]) == 12, "twist = 12, which the function read"
    assert made["faces"]


def test_the_resolved_arguments_reach_the_function(tmp_path):
    document = project(tmp_path)
    made = custom.build(
        node_of(document),
        instance_of(document, bevel=4.0),
        {"face": built_face()},
        root=tmp_path,
    )
    assert made["vertices"][0][1] == pytest.approx(6.0), "bevel * 1.5"


def test_an_input_nothing_built_is_refused(tmp_path):
    document = project(tmp_path)
    with pytest.raises(PolyweaveError) as caught:
        custom.build(node_of(document), instance_of(document), {}, root=tmp_path)
    assert caught.value.code == "geom.unknown-node"


def test_a_function_that_does_not_load_is_refused(tmp_path):
    body = SHAPE.replace(
        'fn     = "tools/rope.py:build"', 'fn     = "tools/rope.py:nope"'
    )
    document = project(tmp_path, body)
    with pytest.raises(PolyweaveError) as caught:
        custom.build(
            node_of(document),
            instance_of(document),
            {"face": built_face()},
            root=tmp_path,
        )
    assert caught.value.code == "geom.no-function"


def test_a_custom_node_naming_no_function_is_refused(tmp_path):
    body = SHAPE.replace('fn     = "tools/rope.py:build"\n', "")
    document = project(tmp_path, body)
    with pytest.raises(PolyweaveError) as caught:
        custom.build(
            node_of(document),
            instance_of(document),
            {"face": built_face()},
            root=tmp_path,
        )
    assert caught.value.code == "geom.no-function"
    assert "path/to/file.py:name" in caught.value.remedy


def test_a_function_that_raises_says_what_it_takes(tmp_path):
    body = SHAPE.replace(
        'fn     = "tools/rope.py:build"', 'fn     = "tools/rope.py:angry"'
    )
    document = project(tmp_path, body)
    with pytest.raises(PolyweaveError) as caught:
        custom.build(
            node_of(document),
            instance_of(document),
            {"face": built_face()},
            root=tmp_path,
        )
    assert caught.value.code == "geom.no-function"
    assert "along" in caught.value.remedy, "the inputs it was handed"
    assert "thickness" in caught.value.remedy, "and the arguments"


def test_a_function_returning_something_that_is_not_geometry_is_refused(tmp_path):
    body = SHAPE.replace(
        'fn     = "tools/rope.py:build"', 'fn     = "tools/rope.py:nothing"'
    )
    document = project(tmp_path, body)
    with pytest.raises(PolyweaveError) as caught:
        custom.build(
            node_of(document),
            instance_of(document),
            {"face": built_face()},
            root=tmp_path,
        )
    assert caught.value.code == "geom.not-geometry"
    assert "nothing to compose with" in caught.value.remedy


# -- and it reads like everything else -------------------------------------------------


def test_a_custom_node_reads_back_in_words(tmp_path):
    from polyweave.geometry import review

    found = review.describe(project(tmp_path))
    says = next(one["says"] for one in found["nodes"] if one["id"] == "rope")
    assert "tools/rope.py:build" in says


def test_and_builds_after_what_it_takes(tmp_path):
    assert G.order(project(tmp_path)) == ["face", "rope"]
