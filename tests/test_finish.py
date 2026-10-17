"""A plastic finish asked for in a few numbers, the shader inputs derived (§PW494)."""

from __future__ import annotations

import pytest

from polyweave import geometry as G
from polyweave.errors import PolyweaveError
from polyweave.geometry import finish, review

PLASTIC = {
    "colour": "#F27BA8",
    "roughness": 0.35,
    "coat": {"weight": 1.0, "roughness": 0.04},
    "sheen": 0.2,
    "rim": 0.6,
    "subsurface": {"weight": 0.3, "depth": 0.05, "tint": "#FF8080"},
}


def test_a_finish_becomes_the_sockets_it_stands_for():
    made = finish.inputs(PLASTIC)
    assert made["colour"] == "#F27BA8" and made["roughness"] == 0.35
    assert made["coat_weight"] == 1.0 and made["coat_roughness"] == 0.04
    assert made["sheen_weight"] == 0.2
    assert made["subsurface_weight"] == 0.3 and made["subsurface_scale"] == 0.05
    # Red carries furthest, so the pastel glows warm rather than greying.
    assert made["subsurface_radius"] == pytest.approx([1.0, 128 / 255, 128 / 255])
    assert made["rim"] == 0.6, "not a socket: the bake builds it"
    assert not set(finish.ASKS) & (set(made) - {"rim"})


def test_a_coat_or_a_subsurface_may_be_only_its_weight():
    made = finish.inputs({"coat": 0.8, "subsurface": 0.5})
    assert made["coat_weight"] == 0.8
    assert made["coat_roughness"] == finish.COAT["roughness"]
    assert made["subsurface_scale"] == finish.SUBSURFACE["depth"]
    assert "subsurface_radius" not in made


@pytest.mark.parametrize("material, said", [
    ({"coat": {"weight": 1.0, "gloss": 0.1}}, "takes no gloss"),
    ({"sheen": 1.5}, "outside nought to one"),
    ({"rim": "bright"}, "not a number"),
    ({"subsurface": {"depth": 0.0}}, "not into it"),
    ({"subsurface": {"tint": "red"}}, "not a colour"),
])
def test_a_finish_that_is_not_one_is_refused(material, said):
    with pytest.raises(PolyweaveError) as refused:
        finish.inputs(material)
    assert refused.value.code == "geom.bad-surface"
    assert said in refused.value.message


def test_a_material_reads_back_in_words():
    assert finish.says(PLASTIC) == (
        "clear-coated, with a sheen, rim-lit, lit from within, glossy")
    assert finish.says({"coat": 1.0}) == "clear-coated, glossy"
    assert finish.says({"sheen": 0.4, "roughness": 0.9}) == "with a sheen, matte"
    assert finish.says({"colour": "#FFFFFF", "roughness": 0.2}) == "", "no finish asked"


def test_the_review_says_the_finish_a_node_wears(tmp_path):
    """`in pink plastic, clear-coated, glossy`, as the line asked for."""
    document = {
        "name": "post", "version": 1, "params": {"shine": 0.9},
        "materials": {"pink plastic": {"colour": "#F27BA8", "coat": "shine"}},
        "nodes": [{"id": "post", "op": "primitive", "kind": "capsule",
                   "size": [1, 1, 3], "material": "pink plastic"}],
        "output": "post",
    }
    said = review.describe(document)["nodes"][0]["says"]
    assert said.endswith("in pink plastic, clear-coated, glossy")
    # And the weight is an expression over the parameters, as a search needs.
    resolved = G.expand(document)
    assert resolved["materials"]["pink plastic"]["coat"] == pytest.approx(0.9)


def test_the_bake_puts_the_finish_on_the_shader():
    pytest.importorskip("bpy")
    from polyweave.render import blender

    blender.reset()
    made = blender._material(blender.as_inputs(PLASTIC), "pink plastic")
    bsdf = made.node_tree.nodes.get("Principled BSDF")
    assert bsdf.inputs["Coat Weight"].default_value == pytest.approx(1.0)
    assert bsdf.inputs["Coat Roughness"].default_value == pytest.approx(0.04)
    assert bsdf.inputs["Sheen Weight"].default_value == pytest.approx(0.2)
    assert bsdf.inputs["Subsurface Weight"].default_value == pytest.approx(0.3)
    # The rim is the view's angle driving the emission, lighting the edge alone.
    strength = bsdf.inputs["Emission Strength"]
    assert strength.is_linked
    assert {node.type for node in made.node_tree.nodes} >= {"LAYER_WEIGHT", "MATH"}
