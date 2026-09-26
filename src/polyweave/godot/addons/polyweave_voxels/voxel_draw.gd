class_name VoxelDraw
extends MultiMeshInstance3D
## Draws a voxel model polyweave built, with no script of the game's own (§PW235).
##
## One cube a cell, the skin only (`skin()`), each in its palette colour with its
## material's `glow` beside it in the instance's custom data. Every node drawing one file
## shares one MultiMesh, so twenty actors are twenty draw calls over one buffer, and a
## node's own look is set through instance uniforms rather than on the shared mesh:
## `wash(color, amount)` lays one colour over every cell, `fade(amount)` dissolves it.
##
##     var ship := VoxelDraw.new()
##     ship.source = "res://art/ship.voxels.json"
##     add_child(ship)
##     ship.wash(Color.GOLD, 0.4)
##
## `voxel.gdshader` is the look it wears unless `shader` names another; a game's own
## reads the same inputs: INSTANCE_CUSTOM (colour, glow in alpha) and the `wash` and
## `fade` instance uniforms.

const Voxels := preload("voxels.gd")
const SHADER := preload("voxel.gdshader")

## The model's file.
@export_file("*.json") var source := ""
## Centred on the model's box, as an actor's mesh is, whatever corner its grid was
## anchored on; false draws it where the grid sits.
@export var centred := true
## The shader each cube wears; the addon's own when empty.
@export var shader: Shader = null
## The glow a cell gets where its material states none.
@export var glow := 0.0

## What one file draws as: the key names the file and every choice above, so two nodes
## differing in any of them do not share a mesh they would both be wrong in.
static var _made := {}

## The model this node draws, once `show_model` has read it.
var model: Resource


func _ready() -> void:
	if source != "":
		show_model(source)


## Draw the model at `path`, sharing its MultiMesh with every other node drawing it.
func show_model(path: String) -> void:
	source = path
	var look: Shader = shader if shader != null else SHADER
	var key := "%s|%s|%s|%d" % [path, centred, glow, look.get_instance_id()]
	var made: Array = _made.get(key, [])
	if made.is_empty():
		var loaded: Resource = Voxels.load_model(path)
		if loaded == null:
			return
		made = [loaded, drawn(loaded, centred, look, glow)]
		_made[key] = made
	model = made[0]
	multimesh = made[1]


## Forget every file read, so a model rebuilt while the game runs is read again.
static func forget() -> void:
	_made.clear()


## A model's skin as one MultiMesh: a cube a cell wearing `look`, its palette colour and
## glow in each instance's custom data.
static func drawn(
	voxels: Resource, centre := true, look: Shader = SHADER, unlit := 0.0
) -> MultiMesh:
	var cube := BoxMesh.new()
	cube.size = Vector3.ONE * voxels.cell
	var paint := ShaderMaterial.new()
	paint.shader = look
	cube.material = paint
	var made := MultiMesh.new()
	made.transform_format = MultiMesh.TRANSFORM_3D
	made.use_custom_data = true
	made.mesh = cube
	var cells: PackedInt32Array = voxels.skin()
	var middle := centre_of(voxels) if centre else Vector3.ZERO
	made.instance_count = cells.size()
	for slot in cells.size():
		var index := cells[slot]
		made.set_instance_transform(slot, Transform3D(Basis(), voxels.centres[index] - middle))
		made.set_instance_custom_data(slot, tint_of(voxels, voxels.wears[index], unlit))
	return made


## The middle of a model's box, in its own units.
static func centre_of(voxels: Resource) -> Vector3:
	return voxels.origin + Vector3(voxels.size) * voxels.cell * 0.5


## Palette slot `slot`'s colour, with its material's `glow` in alpha (`unlit` where it
## states none).
static func tint_of(voxels: Resource, slot: int, unlit := 0.0) -> Color:
	var colour: Color = voxels.palette[slot]
	var material: Dictionary = voxels.materials[slot]
	return Color(colour.r, colour.g, colour.b, float(material.get("glow", unlit)))


## Lay `color` over every cell of this node, `amount` of the way (0 to 1): an elite's
## gold, an armed mine's red. This node's alone, though the mesh is shared.
func wash(color: Color, amount: float) -> void:
	set_instance_shader_parameter("wash", Color(color.r, color.g, color.b, clampf(amount, 0.0, 1.0)))


## Dissolve this node, 0 whole and 1 gone.
func fade(amount: float) -> void:
	set_instance_shader_parameter("fade", clampf(amount, 0.0, 1.0))


## The model's box, in its own units: what a hitbox is held to.
func bounds() -> Vector3:
	return Vector3(model.size) * model.cell if model else Vector3.ZERO
