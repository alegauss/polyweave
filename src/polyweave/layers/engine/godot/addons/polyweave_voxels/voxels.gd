## Reads a `<name>.voxels.json` polyweave wrote into a voxel model resource (§PW102).
##
## A loader rather than an import plugin, on purpose: Godot picks an importer by the last
## extension alone, so one claiming `json` would take every JSON file in the project.
##
##     var Voxels = preload("res://addons/polyweave_voxels/voxels.gd")
##     var model = Voxels.load_model("res://art/ship.voxels.json")
##     $Ship.multimesh = model.multimesh()
extends RefCounted

## The one format this reads. Another is refused rather than half-read.
const FORMAT := 1

const VoxelModel := preload("voxel_model.gd")


## The model in the file, or null with the reason pushed as an error.
static func load_model(path: String) -> Resource:
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("polyweave_voxels: nothing to read at %s" % path)
		return null
	var stated = JSON.parse_string(text)
	if typeof(stated) != TYPE_DICTIONARY:
		push_error("polyweave_voxels: %s is not a voxel model" % path)
		return null
	if int(stated.get("format", 0)) != FORMAT:
		push_error(
			"polyweave_voxels: %s is format %s, and this reads format %d; rebuild it or update the addon"
			% [path, stated.get("format", "none"), FORMAT]
		)
		return null
	return _from(stated)


static func _from(stated: Dictionary) -> Resource:
	var model = VoxelModel.new()
	model.cell = float(stated["cell"])
	var size: Array = stated["size"]
	model.size = Vector3i(int(size[0]), int(size[1]), int(size[2]))
	var origin: Array = stated["origin"]
	model.origin = Vector3(float(origin[0]), float(origin[1]), float(origin[2]))

	for entry in stated["palette"]:
		model.materials.append(entry)
		model.palette.append(_colour(entry))

	var cells: Dictionary = stated["cells"]
	var xs: Array = cells["x"]
	var ys: Array = cells["y"]
	var zs: Array = cells["z"]
	var half := Vector3.ONE * 0.5
	for index in xs.size():
		var at := Vector3(float(xs[index]), float(ys[index]), float(zs[index]))
		model.centres.append(model.origin + (at + half) * model.cell)
		model.wears.append(int(cells["palette"][index]))
	if cells.has("fragment"):
		for one in cells["fragment"]:
			model.fragment_of.append(int(one))
	if cells.has("depth"):
		for one in cells["depth"]:
			model.depth.append(int(one))
	if stated.has("fracture"):
		for one in stated["fracture"]["fragments"]:
			model.fragments.append(one)
	return model


static func _colour(entry: Dictionary) -> Color:
	for key in ["colour", "color", "base_color"]:
		if entry.has(key) and typeof(entry[key]) == TYPE_STRING:
			return Color.html(entry[key])
	return Color(0.6, 0.6, 0.6)
