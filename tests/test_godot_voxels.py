"""The Godot addon that reads a voxel model polyweave wrote (§PW102).

The install is checked everywhere. The loader is checked in the engine itself, and those
tests skip without `$GODOT`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from polyweave import engine, godot
from polyweave.errors import PolyweaveError
from polyweave.geometry import voxels as V

SHIP = {
    "name": "ship",
    "version": 1,
    "params": {},
    "materials": {
        "hull": {"colour": "#808080"},
        "glass": {"colour": "#40C0FF", "glow": 2},
    },
    "nodes": [
        {
            "id": "hull",
            "op": "plate",
            "rect": [0, 0, 4, 2],
            "depth": 1,
            "material": "hull",
        },
        {
            "id": "canopy",
            "op": "plate",
            "rect": [1, 0, 2, 1],
            "depth": 1,
            "material": "glass",
        },
        {"id": "ship", "op": "union", "inputs": ["hull", "canopy"]},
    ],
    "output": "ship",
    "voxels": {"cell": 1.0, "fracture": {"size": [2, 4], "seed": 1}},
}

READ = """extends SceneTree

func _initialize() -> void:
\tvar Voxels = load("res://addons/polyweave_voxels/voxels.gd")
\tvar model = Voxels.load_model("res://%s")
\tif model == null:
\t\tprint("voxels: refused")
\telse:
\t\tvar drawn: MultiMesh = model.multimesh()
\t\tvar glass := 0
\t\tfor slot in model.wears:
\t\t\tif model.materials[slot]["name"] == "glass":
\t\t\t\tglass += 1
\t\tvar said := "voxels: %%d cells %%d instances %%d glass glow %%s first %%s"
\t\tsaid += " fragments %%d"
\t\tprint(said %% [
\t\t\tmodel.centres.size(), drawn.instance_count, glass,
\t\t\tstr(model.materials[1].get("glow", "none")), str(model.centres[0]),
\t\t\tmodel.fragments.size()])
\tquit()
"""

SAID = (
    r"voxels: (?P<cells>\d+) cells (?P<instances>\d+) instances (?P<glass>\d+) glass "
    r"glow (?P<glow>\S+) first (?P<first>\(.*?\)) fragments (?P<fragments>\d+)"
    r"|voxels: (?P<refused>refused)"
)


def game(tmp_path):
    (tmp_path / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="voxels"\n', encoding="utf-8"
    )
    return godot.install(tmp_path)


def test_the_addon_installs_into_a_project(tmp_path):
    found = game(tmp_path)
    assert found["files"] == [
        "addons/polyweave_voxels/voxel.gdshader",
        "addons/polyweave_voxels/voxel_draw.gd",
        "addons/polyweave_voxels/voxel_model.gd",
        "addons/polyweave_voxels/voxels.gd",
    ]


def test_an_install_replaces_an_older_copy(tmp_path):
    game(tmp_path)
    stale = tmp_path / "addons" / "polyweave_voxels" / "stale.gd"
    stale.write_text("extends Node\n", encoding="utf-8")
    game(tmp_path)
    assert not stale.exists()


def test_a_folder_that_is_not_a_project_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        godot.install(tmp_path)
    assert refused.value.code == "engine.not-a-project"


def test_the_cells_say_which_format_they_are():
    assert V.voxelize(SHIP)["format"] == V.FORMAT


def read_in_engine(tmp_path, name):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    (tmp_path / "read.gd").write_text(READ % name, encoding="utf-8")
    return engine.run(tmp_path / "read.gd", expect=SAID, root=tmp_path, headless=True)


def test_the_engine_reads_every_cell_and_what_it_wears(tmp_path):
    game(tmp_path)
    written = V.write(SHIP, "ship.glb", root=tmp_path, mesh=False, sheet=False)
    made = written["model"]
    found = read_in_engine(tmp_path, Path(written["voxels"]).name)
    said = found["found"]
    assert found["ok"], found.get("why")
    assert int(said["cells"]) == made["count"] == int(said["instances"])
    assert int(said["glass"]) == 2
    # Passed through untouched; JSON numbers are floats to Godot, its own reading.
    assert float(said["glow"]) == 2
    assert int(said["fragments"]) == made["fracture"]["count"]
    # The first cell's middle, in the model's own units, as Godot reads it.
    x, y, z = (made["cells"][axis][0] for axis in "xyz")
    middle = [
        made["origin"][i] + (v + 0.5) * made["cell"] for i, v in enumerate((x, y, z))
    ]
    assert said["first"] == "(" + ", ".join(f"{v:g}" for v in middle) + ")"


SOLID = {
    "name": "block",
    "version": 1,
    "params": {},
    "materials": {"stone": {"colour": "#808080"}},
    "nodes": [
        {
            "id": "block",
            "op": "plate",
            "rect": [0, 0, 4, 4],
            "depth": 4,
            "material": "stone",
        },
    ],
    "output": "block",
    "voxels": {"cell": 1.0},
}

SKIN = """extends SceneTree

func _initialize() -> void:
\tvar model = load("res://addons/polyweave_voxels/voxels.gd").load_model("res://%s")
\tvar skin: PackedInt32Array = model.skin()
\tvar drawn: MultiMesh = model.multimesh(null, skin)
\tvar hit := PackedInt32Array([%d])
\tprint("skin: %%d cells %%d skin %%d buried %%d drawn %%s exposed" %% [
\t\tmodel.centres.size(), skin.size(), model.buried().size(), drawn.instance_count,
\t\t",".join(Array(model.exposed_by(hit)).map(func(i): return str(i)))])
\tquit()
"""


@pytest.mark.parametrize("fractured", [False, True], ids=["neighbours", "depth"])
def test_the_skin_is_drawn_and_a_hit_says_what_it_reveals(tmp_path, fractured):
    """§PW142: a solid model drawn whole pays for its volume; its skin is what shows.
    Read off the depths where a fracture plan wrote them, off the neighbours where not.
    """
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    game(tmp_path)
    solid = json.loads(json.dumps(SOLID))
    if fractured:
        solid["voxels"]["fracture"] = {"size": [2, 4], "seed": 1}
    written = V.write(solid, "block.glb", root=tmp_path, mesh=False, sheet=False)
    made = written["model"]
    assert ("depth" in made["cells"]) is fractured
    at = list(zip(*(made["cells"][axis] for axis in "xyz"), strict=True))
    # A cell in the middle of a face, and the buried one straight behind it.
    face = next(i for i, c in enumerate(at) if c[0] == 0 and c[1:] == (1, 1))
    behind = at.index((1, 1, 1))
    (tmp_path / "skin.gd").write_text(
        SKIN % (Path(written["voxels"]).name, face), encoding="utf-8"
    )
    found = engine.run(
        tmp_path / "skin.gd",
        expect=r"skin: (?P<cells>\d+) cells (?P<skin>\d+) skin (?P<buried>\d+) buried "
        r"(?P<drawn>\d+) drawn (?P<exposed>\S*) exposed",
        root=tmp_path,
        headless=True,
    )
    said = found["found"]
    assert found["ok"], found.get("why")
    assert int(said["cells"]) == 64
    assert int(said["skin"]) == int(said["drawn"]) == 56
    assert int(said["buried"]) == 8
    assert behind in [int(i) for i in said["exposed"].split(",")]


DRAW = """extends SceneTree

func _initialize() -> void:
\tvar Draw = load("res://addons/polyweave_voxels/voxel_draw.gd")
\tvar one = Draw.new()
\tvar two = Draw.new()
\tvar placed = Draw.new()
\tplaced.centred = false
\tfor node in [one, two, placed]:
\t\tnode.source = "res://%s"
\t\troot.add_child(node)
\tawait process_frame
\t# A headless run's renderer keeps no instance buffer to read back, so what each
\t# instance is given is read off the functions that give it.
\tvar drawn: MultiMesh = one.multimesh
\tvar middle: Vector3 = Draw.centre_of(one.model)
\tvar glass := int(Draw.tint_of(one.model, 0).a)
\tone.wash(Color.GOLD, 0.5)
\tone.fade(2.0)
\tvar paint: ShaderMaterial = drawn.mesh.material
\tprint("draw: %%d drawn %%d skin shared %%s apart %%s middle %%s glow %%d washed %%s \
fade %%s other %%s shader %%s" %% [
\t\tdrawn.instance_count, one.model.skin().size(), str(two.multimesh == drawn),
\t\tstr(placed.multimesh != drawn), str(middle).replace(" ", ""), glass,
\t\tstr(one.get_instance_shader_parameter("wash").a),
\t\tstr(one.get_instance_shader_parameter("fade")),
\t\tstr(two.get_instance_shader_parameter("wash")),
\t\tstr(paint.shader.resource_path.get_file())])
\tquit()
"""


def test_a_model_is_drawn_with_no_script_of_the_games_own(tmp_path):
    """§PW235: the addon's node draws the skin, shared, centred and washed per node."""
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    game(tmp_path)
    solid = json.loads(json.dumps(SOLID))
    solid["materials"]["stone"]["glow"] = 2
    written = V.write(solid, "block.glb", root=tmp_path, mesh=False, sheet=False)
    (tmp_path / "draw.gd").write_text(
        DRAW % Path(written["voxels"]).name, encoding="utf-8"
    )
    found = engine.run(
        tmp_path / "draw.gd",
        expect=r"draw: (?P<drawn>\d+) drawn (?P<skin>\d+) skin shared (?P<shared>\S+) "
        r"apart (?P<apart>\S+) middle (?P<middle>\S+) glow (?P<glow>\d+) washed "
        r"(?P<washed>\S+) fade (?P<fade>\S+) other (?P<other>.*?) "
        r"shader (?P<shader>\S+)",
        errors=engine.ERRORS.pattern + "|SHADER ERROR",
        root=tmp_path,
        headless=True,
    )
    said = found["found"]
    assert found["ok"], found.get("why")
    assert int(said["drawn"]) == int(said["skin"]) == 56
    assert said["shared"] == "true"
    assert said["apart"] == "true"
    # The block runs 0 to 4 on each side, so its box is centred on (2, 2, 2).
    assert said["middle"] == "(2.0,2.0,2.0)"
    assert int(said["glow"]) == 2
    assert float(said["washed"]) == 0.5
    assert float(said["fade"]) == 1.0
    assert said["other"] in ("<null>", "null", "")
    assert said["shader"] == "voxel.gdshader"


def test_the_engine_refuses_a_format_it_does_not_read(tmp_path):
    game(tmp_path)
    written = V.write(SHIP, "ship.glb", root=tmp_path, mesh=False, sheet=False)
    where = Path(written["voxels"])
    data = json.loads(where.read_text(encoding="utf-8"))
    data["format"] = 99
    where.write_text(json.dumps(data), encoding="utf-8")
    found = read_in_engine(tmp_path, where.name)
    assert found["found"]["refused"] == "refused"
