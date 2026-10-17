"""A plastic finish asked for in a few numbers, the shader inputs derived (§PW494)."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyweave import geometry as G
from polyweave import provenance
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


def test_the_game_is_given_the_numbers_the_bake_used():
    """§PW495: a StandardMaterial3D for the finish it has fields for."""
    made = finish.godot({k: v for k, v in PLASTIC.items() if k != "sheen"})
    assert made["shader"] is None
    fields = made["fields"]
    assert fields["albedo_color"] == "Color(0.94902, 0.482353, 0.658824, 1)"
    assert fields["roughness"] == 0.35
    assert fields["clearcoat_enabled"] is True and fields["clearcoat"] == 1.0
    assert fields["clearcoat_roughness"] == 0.04
    assert fields["rim"] == 0.6 and fields["rim_tint"] == 0.0
    assert fields["subsurf_scatter_strength"] == 0.3
    assert fields["subsurf_scatter_transmittance_depth"] == 0.05
    # Where the declaration says nothing, the bake's Principled defaults, not Godot's.
    assert finish.godot({"coat": 1.0})["fields"]["roughness"] == 0.5


def test_a_sheen_the_standard_material_lacks_is_a_shader_of_its_own():
    made = finish.godot(PLASTIC)
    assert "shader_type spatial;" in made["shader"]
    assert made["fields"]["sheen"] == 0.2
    assert "shader_parameter/clearcoat = 1" in made["material"]


def _plastic_post(tmp_path, material) -> dict:
    (tmp_path / "post.toml").write_text(
        'name = "post"\nversion = 1\noutput = "post"\n\n[params]\nshine = 0.9\n\n'
        f'[materials."pink plastic"]\n{material}\n\n'
        '[[nodes]]\nid = "post"\nop = "primitive"\nkind = "capsule"\n'
        'size = [1, 1, 3]\nmaterial = "pink plastic"\n',
        encoding="utf-8")
    from polyweave.cli import build_one

    return build_one("post.toml", out="built", root=str(tmp_path))


def test_a_build_writes_the_finish_beside_its_mesh(tmp_path):
    pytest.importorskip("bpy")
    found = _plastic_post(
        tmp_path, 'colour = "#F27BA8"\nroughness = 0.35\ncoat = "shine"\nrim = 0.6')
    assert found["status"] == "built", found
    names = sorted(Path(one).name for one in found["outputs"])
    assert names == ["post.glb", "post.pink_plastic.tres"]
    text = (tmp_path / "built" / "post.pink_plastic.tres").read_text(encoding="utf-8")
    assert "clearcoat = 0.9" in text, "the coat's weight resolved from the params"
    assert provenance.read(str(tmp_path / "built" / "post.pink_plastic.tres"),
                           root=tmp_path)["kind"] == "mesh"


def test_a_material_with_no_finish_is_left_to_the_gltf(tmp_path):
    pytest.importorskip("bpy")
    found = _plastic_post(tmp_path, 'colour = "#F27BA8"\nroughness = 0.35')
    assert [Path(one).name for one in found["outputs"]] == ["post.glb"]


GODOT_READS = """extends SceneTree

func _initialize() -> void:
\tvar standard: StandardMaterial3D = load("res://built/post.pink_plastic.tres")
\tvar shaded: ShaderMaterial = load("res://built/sheen.pink_plastic.tres")
\tprint("read: coat=%.2f rim=%.2f sss=%.2f rough=%.2f sheen=%.2f" % [
\t\tstandard.clearcoat, standard.rim, standard.subsurf_scatter_strength,
\t\tstandard.roughness, shaded.get_shader_parameter("sheen")])
\tquit()
"""


def test_godot_loads_the_material_with_the_numbers_it_was_written_with(tmp_path):
    """§PW495: the game loads what was judged, read back by the engine itself."""
    import os

    from polyweave import engine

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    folder = tmp_path / "built"
    folder.mkdir()
    finish.write_godot({k: v for k, v in PLASTIC.items() if k != "sheen"},
                       "pink plastic", folder, "post", tmp_path)
    finish.write_godot(PLASTIC, "pink plastic", folder, "sheen", tmp_path)
    (tmp_path / "reads.gd").write_text(GODOT_READS, encoding="utf-8")
    found = engine.run(
        "reads.gd", root=tmp_path, headless=True,
        expect=r"read: coat=(?P<coat>\S+) rim=(?P<rim>\S+) sss=(?P<sss>\S+) "
               r"rough=(?P<rough>\S+) sheen=(?P<sheen>\S+)",
    )
    assert found["ok"] is True, found["why"]
    assert found["found"] == {"coat": "1.00", "rim": "0.60", "sss": "0.30",
                              "rough": "0.35", "sheen": "0.20"}


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
