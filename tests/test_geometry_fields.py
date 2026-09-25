"""A declaration refuses a key it does not read (§PW146).

A misspelt field used to build the shape without it and say nothing. Found shipping
PW123, and the first thing the refusal caught was a test fixture: a bevel node saying
`amount` where the builder reads `bevel`, which had been dropped since it was written.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polyweave import geometry
from polyweave.errors import PolyweaveError
from polyweave.geometry.build import BUILDS, FIELDS

BOX = {
    "name": "box",
    "nodes": [{"id": "box", "op": "primitive", "kind": "cube", "size": 2}],
}


def refused(stated: dict) -> PolyweaveError:
    with pytest.raises(PolyweaveError) as caught:
        geometry.parse(stated, named="box.toml")
    assert caught.value.code == "geom.unknown-field"
    return caught.value


def test_a_misspelt_key_at_the_top_level_is_refused():
    found = refused({**BOX, "materails": {}})
    assert "'materails'" in found.message
    assert found.at == "materails"
    assert "materials" in found.as_dict()["did_you_mean"]


def test_a_misspelt_field_on_a_node_is_refused_with_the_real_one():
    node = {"id": "box", "op": "primitive", "kind": "cube", "sizee": 9}
    found = refused({**BOX, "nodes": [node]})
    assert found.at == "nodes.box.sizee"
    assert "size" in found.as_dict()["did_you_mean"]


def test_a_misspelt_key_in_a_repeat_is_refused():
    node = {
        **BOX["nodes"][0],
        "repeat": [{"var": "i", "from": 0, "too": 3}],
    }
    assert refused({**BOX, "nodes": [node]}).at == "nodes.box.repeat.too"


def test_a_field_of_another_op_is_refused_on_this_one():
    """`corner` is a plate's; on a prism nothing reads it."""
    node = {"id": "p", "op": "prism", "outline": "star", "depth": 1, "corner": 2}
    assert refused({"name": "p", "nodes": [node]}).at == "nodes.p.corner"


def test_a_custom_node_takes_the_arguments_its_function_does():
    node = {"id": "c", "op": "custom", "fn": "x.py:f", "anything": 1}
    assert geometry.parse({"name": "c", "nodes": [node]})["nodes"][0]["anything"] == 1


def test_every_op_that_builds_declares_its_fields():
    assert set(FIELDS) == set(BUILDS)


def test_every_committed_declaration_still_reads():
    """The lists are complete: every declaration in the repository parses unchanged."""
    root = Path(__file__).resolve().parent.parent
    read = 0
    for where in sorted((root / "tests").rglob("*.toml")):
        from polyweave.cli import is_declaration

        if is_declaration(where):
            geometry.read(where)
            read += 1
    assert read > 0
