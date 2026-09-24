## A voxel model polyweave built, as Godot data (§PW102).
##
## What the build wrote in `<name>.voxels.json`, read once into packed arrays: where each
## cell is, what it wears, which fragment it breaks off with and how deep it sits. How the
## game draws, lights and shatters it stays the game's own code; this ends where the data
## becomes Godot's. `voxels.gd` makes one of these from a file.
extends Resource

## The edge of one cell, in the model's own units.
@export var cell: float = 1.0
## Cells along x, y and z.
@export var size: Vector3i = Vector3i.ZERO
## Where the grid's low corner sits; Y up and -Z forward, as Godot has them.
@export var origin: Vector3 = Vector3.ZERO
## Every filled cell's middle, in the model's units.
@export var centres: PackedVector3Array = PackedVector3Array()
## Each cell's slot in `palette`.
@export var wears: PackedInt32Array = PackedInt32Array()
## Each palette slot's colour; grey where the material names none.
@export var palette: Array[Color] = []
## Each palette slot's material, whole: its name and every key the declaration gave it,
## `glow` and the rest, which mean something to a game and nothing to the plugin.
@export var materials: Array[Dictionary] = []
## Each cell's fragment, when the declaration planned how it breaks; empty otherwise.
@export var fragment_of: PackedInt32Array = PackedInt32Array()
## The fragments: their cells, centre and mass.
@export var fragments: Array[Dictionary] = []
## Each cell's depth from the surface, 1 outermost, which is the order a hit chips them.
@export var depth: PackedInt32Array = PackedInt32Array()


## The cells as one MultiMesh, a cube each in its palette colour, ready to assign to a
## MultiMeshInstance3D. `mesh` is the shape drawn per cell; a cube one cell wide unless
## the game gives its own.
func multimesh(mesh: Mesh = null) -> MultiMesh:
	var drawn := MultiMesh.new()
	drawn.transform_format = MultiMesh.TRANSFORM_3D
	drawn.use_colors = true
	if mesh == null:
		var cube := BoxMesh.new()
		cube.size = Vector3.ONE * cell
		var paint := StandardMaterial3D.new()
		paint.vertex_color_use_as_albedo = true
		cube.material = paint
		mesh = cube
	drawn.mesh = mesh
	drawn.instance_count = centres.size()
	for index in centres.size():
		drawn.set_instance_transform(index, Transform3D(Basis(), centres[index]))
		drawn.set_instance_color(index, palette[wears[index]])
	return drawn
