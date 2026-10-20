"""A plastic finish asked for in a few numbers, the shader inputs derived (§PW494)."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers import geometry as G
from polyweave.layers.geometry import finish, review

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


HOOKS = {"hue": "instance", "include": "res://world/hold.gdshaderinc",
         "hold": "held", "amount": "backdrop"}


def test_a_closed_finish_is_left_as_the_bake_used_it():
    """§PW569: a project that opens nothing keeps the material it always had."""
    assert finish.opened({"hue": "", "include": "", "hold": "", "amount": "backdrop"}) \
        is None
    assert finish.godot({k: v for k, v in PLASTIC.items() if k != "sheen"},
                        None)["shader"] is None


def test_an_opened_finish_turns_each_instance_and_holds_it_by_the_projects_hand():
    """§PW569: always the shader, its hue an instance's and its colour held."""
    made = finish.godot({"colour": "#F27BA8", "coat": 1.0}, finish.opened(HOOKS))
    shader = made["shader"]
    assert '#include "res://world/hold.gdshaderinc"' in shader
    assert "instance uniform float backdrop = 1.0;" in shader
    assert "hue = INSTANCE_CUSTOM.x;" in shader
    assert "ALBEDO = held(colour, backdrop);" in shader
    assert "shader_parameter/clearcoat = 1" in made["material"]
    alone = finish.godot({"coat": 1.0}, finish.opened({**HOOKS, "include": "",
                                                        "hold": ""}))["shader"]
    assert "#include" not in alone and "ALBEDO = colour;" in alone


@pytest.mark.parametrize("table, said", [
    ({"hue": "random"}, "nothing or by each instance"),
    ({"include": "res://a.gdshaderinc"}, "an include and no hold"),
    ({"hold": "held"}, "a hold and no include"),
    ({"include": "world/a.gdshaderinc", "hold": "held"}, "res:// path"),
    ({"include": "res://a.gdshaderinc", "hold": "held(x)"}, "not a shader name"),
])
def test_an_opened_finish_that_cannot_be_written_is_refused(table, said):
    with pytest.raises(PolyweaveError) as refused:
        finish.opened(table)
    assert refused.value.code == "geom.bad-surface"
    assert said in refused.value.message


GODOT_PARSES = """extends SceneTree

func _initialize() -> void:
\tvar paint: ShaderMaterial = load("res://built/post.pink_plastic.tres")
\tvar names := paint.shader.get_shader_uniform_list().map(func(u): return u.name)
\tprint("parsed: %s" % ",".join(names))
\tquit()
"""


def test_godot_parses_an_opened_finish_with_the_projects_include(tmp_path):
    """§PW569: the shader with the project's hold in it is one Godot reads whole."""
    import os

    from polyweave.layers.engine import engine

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "world").mkdir()
    (tmp_path / "world" / "hold.gdshaderinc").write_text(
        "vec3 held(vec3 c, float amount) {\n\treturn c * (1.0 - 0.5 * amount);\n}\n",
        encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text(
        '[finish]\nhue = "instance"\ninclude = "res://world/hold.gdshaderinc"\n'
        'hold = "held"\n', encoding="utf-8")
    folder = tmp_path / "built"
    folder.mkdir()
    finish.write_godot({"colour": "#F27BA8", "coat": 1.0}, "pink plastic", folder,
                       "post", tmp_path)
    (tmp_path / "parses.gd").write_text(GODOT_PARSES, encoding="utf-8")
    found = engine.run("parses.gd", root=tmp_path, headless=True,
                       expect=r"parsed: (?P<names>\S+)")
    assert found["ok"] is True, found["why"]
    assert {"albedo", "clearcoat", "sheen"} <= set(found["found"]["names"].split(","))


STRUCK = {"give": 0.3, "wobble": 3, "lifetime": 0.9, "falloff": 1.5, "height": 6,
          "radius": 8, "amount": 8}


def test_a_struck_finish_gives_where_a_strike_lands_and_keeps_its_look():
    """§PW574: the finish's own numbers, and vfx's give in the same shader."""
    from polyweave.layers.vfx.vfx import settle_rate

    hooks = finish.opened({"hue": "instance", "struck": STRUCK})
    made = finish.godot({"colour": "#F27BA8", "coat": 1.0}, hooks)
    assert "uniform vec4 hits[8];" in made["shader"]
    assert "VERTEX += sway;" in made["shader"]
    assert "CLEARCOAT = clearcoat;" in made["shader"]
    assert made["fields"]["settle"] == pytest.approx(settle_rate(0.9))
    assert made["fields"]["felt"] == 8 and made["fields"]["clearcoat"] == 1.0
    assert "uniform vec4 hits" not in finish.godot(
        {"coat": 1.0}, finish.opened({"hue": "instance"}))["shader"]


@pytest.mark.parametrize("lifetime", [0.25, 0.6, 2.0])
def test_a_struck_finish_settles_on_vfx_s_own_curve(lifetime):
    # Written out in geometry, which may not import vfx without needing Godot; held
    # here to one curve with the struck pieces vfx makes (§PW574).
    from polyweave.layers.vfx.vfx import settle_rate

    assert finish.settle_rate(lifetime) == settle_rate(lifetime)


@pytest.mark.parametrize("struck, said", [
    ({**STRUCK, "bounce": 2}, "takes no bounce"),
    ({**STRUCK, "give": 0}, "struck give is 0"),
    ({**STRUCK, "amount": 20}, "struck amount is 20"),
    ({k: v for k, v in STRUCK.items() if k != "radius"}, "states no radius"),
    ("hard", "not a table"),
])
def test_a_struck_finish_that_cannot_give_is_refused(struck, said):
    with pytest.raises(PolyweaveError) as refused:
        finish.opened({"struck": struck})
    assert refused.value.code == "geom.bad-surface"
    assert said in refused.value.message


GODOT_STRIKES = """extends SceneTree

func _initialize() -> void:
\tvar paint: ShaderMaterial = load("res://built/post.pink_plastic.tres")
\tvar names := paint.shader.get_shader_uniform_list().map(func(u): return u.name)
\tvar strikes = load("res://built/finish_strikes.gd").new()
\tstrikes.watch(paint)
\tstrikes.strike(Vector3(1, 2, 3), 0.5)
\tvar hit: Vector4 = paint.get_shader_parameter("hits")[0]
\tprint("struck: %s %s %s" % [",".join(names), hit, strikes.swinging()])
\tstrikes.free()
\tquit()
"""


def test_godot_strikes_a_struck_finish_through_the_written_script(tmp_path):
    """§PW574: Godot reads the composed shader, and the script hands it a strike."""
    import os

    from polyweave.layers.engine import engine

    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text(
        '[finish]\nhue = "instance"\n'
        'struck = { give = 0.3, wobble = 3, lifetime = 0.9, '
        'falloff = 1.5, height = 6, radius = 8, amount = 8 }\n', encoding="utf-8")
    folder = tmp_path / "built"
    folder.mkdir()
    written = finish.write_godot({"colour": "#F27BA8", "coat": 1.0}, "pink plastic",
                                 folder, "post", tmp_path)
    assert folder / "finish_strikes.gd" in written
    (tmp_path / "strikes.gd").write_text(GODOT_STRIKES, encoding="utf-8")
    found = engine.run("strikes.gd", root=tmp_path, headless=True,
                       expect=r"struck: (?P<names>\S+) (?P<hit>\(.*\)) (?P<on>\S+)")
    assert found["ok"] is True, found["why"]
    assert {"give", "hits", "ages", "albedo"} <= set(found["found"]["names"].split(","))
    assert found["found"]["hit"] == "(1.0, 2.0, 3.0, 0.5)"
    assert found["found"]["on"] == "true"


def _godot_project(tmp_path) -> Path:
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "built").mkdir(exist_ok=True)
    (tmp_path / "built" / "post.glb").write_bytes(b"")
    (tmp_path / "built" / "post.pink_plastic.tres").write_text("", encoding="utf-8")
    return tmp_path / "built" / "post.glb"


def test_a_mesh_is_imported_wearing_its_written_materials(tmp_path):
    """§PW570: the import names each material's .tres, written fresh or merged."""
    import json

    mesh = _godot_project(tmp_path)
    worn = {"pink plastic": tmp_path / "built" / "post.pink_plastic.tres"}
    wired = finish.wire_import(mesh, worn, tmp_path)
    text = wired.read_text(encoding="utf-8")
    assert 'importer="scene"' in text
    held = json.loads(text.partition("_subresources=")[2])
    assert held["materials"]["pink plastic"] == {
        "use_external/enabled": True,
        "use_external/path": "res://built/post.pink_plastic.tres"}
    # Godot's own import, with its settings and an empty mapping, keeps the settings
    wired.write_text('[params]\n\nmeshes/generate_lods=true\n_subresources={}\n'
                     'gltf/naming_version=2', encoding="utf-8")
    text = finish.wire_import(mesh, worn, tmp_path).read_text(encoding="utf-8")
    assert "meshes/generate_lods=true" in text and "gltf/naming_version=2" in text
    assert "res://built/post.pink_plastic.tres" in text


def test_an_import_the_project_filled_or_no_godot_project_is_left_alone(tmp_path):
    mesh = _godot_project(tmp_path)
    worn = {"pink plastic": tmp_path / "built" / "post.pink_plastic.tres"}
    Path(f"{mesh}.import").write_text(
        '[params]\n_subresources={\n"nodes": {}\n}\n', encoding="utf-8")
    assert finish.wire_import(mesh, worn, tmp_path) is None
    (tmp_path / "project.godot").unlink()
    Path(f"{mesh}.import").unlink()
    assert finish.wire_import(mesh, worn, tmp_path) is None


GODOT_WEARS = """extends SceneTree

func _find(node: Node) -> MeshInstance3D:
\tif node is MeshInstance3D:
\t\treturn node
\tfor child in node.get_children():
\t\tvar found := _find(child)
\t\tif found:
\t\t\treturn found
\treturn null

func _initialize() -> void:
\tvar shape := _find((load("res://built/post.glb") as PackedScene).instantiate())
\tprint("wears: %s" % shape.mesh.surface_get_material(0).resource_path)
\tquit()
"""


def test_godot_imports_the_mesh_in_the_material_that_was_judged(tmp_path):
    """§PW570: read back by the engine, the surface is the written .tres."""
    import os
    import subprocess

    from polyweave.layers.engine import engine

    pytest.importorskip("bpy")
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    found = _plastic_post(tmp_path, 'colour = "#F27BA8"\ncoat = 1.0')
    assert found["status"] == "built", found
    subprocess.run([os.environ["GODOT"], "--headless", "--path", str(tmp_path),
                    "--import"], capture_output=True, timeout=300, check=False)
    (tmp_path / "wears.gd").write_text(GODOT_WEARS, encoding="utf-8")
    ran = engine.run("wears.gd", root=tmp_path, headless=True,
                     expect=r"wears: (?P<path>\S+)")
    assert ran["ok"] is True, ran["why"]
    assert ran["found"]["path"] == "res://built/post.pink_plastic.tres"


def test_a_finish_opened_after_a_build_builds_it_again(tmp_path):
    """§PW569: the project's [finish] is in the stamp, so opening it is not cached."""
    pytest.importorskip("bpy")
    from polyweave.layers.geometry.make import build_one

    first = _plastic_post(tmp_path, 'colour = "#F27BA8"\ncoat = 1.0')
    again = build_one("post.toml", out="built", root=str(tmp_path), force=False)
    assert (first["status"], again["status"]) == ("built", "cached")
    (tmp_path / "polyweave.toml").write_text('[finish]\nhue = "instance"\n',
                                             encoding="utf-8")
    opened = build_one("post.toml", out="built", root=str(tmp_path), force=False)
    assert opened["status"] == "built"
    assert "INSTANCE_CUSTOM.x" in (tmp_path / "built" / "post.pink_plastic.gdshader")\
        .read_text(encoding="utf-8")


def test_a_finish_opened_leaves_a_build_without_one_cached(tmp_path):
    """§PW569: only a document whose materials ask for a finish is built again."""
    pytest.importorskip("bpy")
    from polyweave.layers.geometry.make import build_one

    first = _plastic_post(tmp_path, 'colour = "#F27BA8"\nroughness = 0.35')
    (tmp_path / "polyweave.toml").write_text('[finish]\nhue = "instance"\n',
                                             encoding="utf-8")
    again = build_one("post.toml", out="built", root=str(tmp_path), force=False)
    assert (first["status"], again["status"]) == ("built", "cached")


def _plastic_post(tmp_path, material) -> dict:
    (tmp_path / "post.toml").write_text(
        'name = "post"\nversion = 1\noutput = "post"\n\n[params]\nshine = 0.9\n\n'
        f'[materials."pink plastic"]\n{material}\n\n'
        '[[nodes]]\nid = "post"\nop = "primitive"\nkind = "capsule"\n'
        'size = [1, 1, 3]\nmaterial = "pink plastic"\n',
        encoding="utf-8")
    from polyweave.surface.cli import build_one

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


def test_a_rebuild_removes_what_it_wrote_for_a_material_now_gone(tmp_path):
    """§PW567: a redrawn kit left its old materials' files beside the new ones."""
    pytest.importorskip("bpy")
    from polyweave.surface.cli import build_one

    _plastic_post(tmp_path, 'colour = "#F27BA8"\ncoat = 1.0')
    built = tmp_path / "built"
    old = built / "post.pink_plastic.tres"
    assert old.is_file()
    # a file the project made by hand beside it is not the build's to remove
    (built / "post.by_hand.tres").write_text("[gd_resource]\n", encoding="utf-8")
    source = (tmp_path / "post.toml").read_text(encoding="utf-8")
    (tmp_path / "post.toml").write_text(source.replace("pink plastic", "cream"),
                                        encoding="utf-8")
    again = build_one("post.toml", out="built", root=str(tmp_path))
    assert again["status"] == "built", again
    assert (built / "post.cream.tres").is_file()
    assert not old.exists()
    assert not provenance.sidecar(old, tmp_path).exists()
    assert again["removed"] == ["built/post.pink_plastic.tres"]
    assert (built / "post.by_hand.tres").is_file()


def test_a_rebuild_finds_an_orphan_its_stamp_forgot_by_its_record(tmp_path):
    """A stamp written over before §PW567 no longer lists the old material's file."""
    pytest.importorskip("bpy")
    from polyweave.surface.cli import build_one

    _plastic_post(tmp_path, 'colour = "#F27BA8"\ncoat = 1.0')
    (tmp_path / "built" / "post.build.json").unlink()
    source = (tmp_path / "post.toml").read_text(encoding="utf-8")
    (tmp_path / "post.toml").write_text(source.replace("pink plastic", "cream"),
                                        encoding="utf-8")
    again = build_one("post.toml", out="built", root=str(tmp_path))
    assert again["removed"] == ["built/post.pink_plastic.tres"]


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

    from polyweave.layers.engine import engine

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
    from polyweave.layers.geometry.render import blender

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
