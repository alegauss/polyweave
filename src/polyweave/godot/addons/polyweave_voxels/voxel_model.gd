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


## Where each cell sits in the grid, built on first use for `exposed_by`.
var _at: Dictionary = {}


## The cells a camera can see: depth 1, a face on the outside (§PW142). A solid model
## eight cells across has 512 cells and 296 of them here, so drawing these alone draws
## the skin and not the volume. Read off `depth` where the file carries it, which it does
## when the declaration planned a fracture, and off the cells' neighbours where not.
func skin() -> PackedInt32Array:
	var found := PackedInt32Array()
	for index in centres.size():
		if _outside(index):
			found.append(index)
	return found


## The cells nothing can see until a hit removes what covers them.
func buried() -> PackedInt32Array:
	var found := PackedInt32Array()
	for index in centres.size():
		if not _outside(index):
			found.append(index)
	return found


func _outside(index: int) -> bool:
	if not depth.is_empty():
		return depth[index] <= 1
	_index()
	var here := _grid(centres[index])
	for step in _FACES:
		if not _at.has(here + step):
			return true
	return false


const _FACES := [Vector3i.RIGHT, Vector3i.LEFT, Vector3i.UP, Vector3i.DOWN,
		Vector3i.BACK, Vector3i.FORWARD]


func _index() -> void:
	if _at.is_empty():
		for index in centres.size():
			_at[_grid(centres[index])] = index


## The cells a hit reveals: every cell sharing a face with one in `removed` that was
## not removed itself. Drawing the skin and adding these as it is chipped keeps what is
## drawn to what can be seen, in the order the depths already state.
func exposed_by(removed: PackedInt32Array) -> PackedInt32Array:
	_index()
	var gone := {}
	for index in removed:
		gone[index] = true
	var found := PackedInt32Array()
	var seen := {}
	for index in removed:
		var here := _grid(centres[index])
		for step in _FACES:
			var next = _at.get(here + step, -1)
			if next >= 0 and not gone.has(next) and not seen.has(next):
				seen[next] = true
				found.append(next)
	return found


func _grid(centre: Vector3) -> Vector3i:
	var at := (centre - origin) / cell - Vector3.ONE * 0.5
	return Vector3i(roundi(at.x), roundi(at.y), roundi(at.z))


## The cells as one MultiMesh, a cube each in its palette colour, ready to assign to a
## MultiMeshInstance3D. `mesh` is the shape drawn per cell; a cube one cell wide unless
## the game gives its own. `cells` draws those indices only, `skin()` being the usual
## choice; every cell when it is empty, and then instance i is cell i.
func multimesh(mesh: Mesh = null, cells: PackedInt32Array = PackedInt32Array()) -> MultiMesh:
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
	if cells.is_empty():
		for index in centres.size():
			cells.append(index)
	drawn.instance_count = cells.size()
	for slot in cells.size():
		var index := cells[slot]
		drawn.set_instance_transform(slot, Transform3D(Basis(), centres[index]))
		drawn.set_instance_color(slot, palette[wears[index]])
	return drawn
