extends SceneTree
## A model drawn by the game's own engine at the rig a bake drew it at, as
## render.in_game runs it (§PW495): the imported scene, wearing whatever materials its
## import gives it, in a transparent SubViewport the bake's size, under the bake's
## camera, three lights and world. Prints `MODEL_AT_RIG shot=<file>` once the picture is
## saved. Takes `model=res://…`, `size=WxH`, `shot=<file>` and `rig=<JSON>` after `--`:
## camera {location, look_at, fov_deg, keep}, lights [{location, energy, range}],
## ambient {colour, energy}, exposure and transparent.

## Frames drawn before the picture is taken, so shadows and the environment settle.
const SETTLE := 6

var shot := ""
var view: SubViewport
var drawn := 0


func _initialize() -> void:
	var model := ""
	var size := Vector2i(256, 256)
	var rig := {}
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("model="):
			model = arg.substr(6)
		elif arg.begins_with("size="):
			var sides := arg.substr(5).split("x")
			size = Vector2i(int(sides[0]), int(sides[1]))
		elif arg.begins_with("shot="):
			shot = arg.substr(5)
		elif arg.begins_with("rig="):
			rig = JSON.parse_string(arg.substr(4))
	var packed := load(model) as PackedScene
	if packed == null:
		printerr("MODEL_AT_RIG failed: %s did not load as a scene" % model)
		quit(1)
		return
	view = SubViewport.new()
	view.size = size
	view.own_world_3d = true
	view.transparent_bg = bool(rig.get("transparent", true))
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(view)
	view.add_child(packed.instantiate())

	var seen: Dictionary = rig["camera"]
	var camera := Camera3D.new()
	camera.keep_aspect = Camera3D.KEEP_WIDTH if seen["keep"] == "width" \
		else Camera3D.KEEP_HEIGHT
	camera.fov = float(seen["fov_deg"])
	view.add_child(camera)
	var place := _at(seen["location"])
	var target := _at(seen["look_at"])
	var up := Vector3.UP
	if absf((target - place).normalized().dot(up)) > 0.999:
		up = Vector3.FORWARD
	# From its position: the tree is not entered yet while _initialize runs.
	camera.look_at_from_position(place, target, up)
	camera.current = true

	for one in rig["lights"]:
		var lamp := OmniLight3D.new()
		lamp.light_energy = float(one["energy"])
		lamp.omni_range = float(one["range"])
		# Inverse square, as the bake's lights fall off, and not Godot's gentler default.
		lamp.omni_attenuation = 2.0
		lamp.shadow_enabled = true
		view.add_child(lamp)
		lamp.position = _at(one["location"])

	var world := Environment.new()
	world.background_mode = Environment.BG_CLEAR_COLOR
	world.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world.ambient_light_color = Color.html(str(rig["ambient"]["colour"]))
	world.ambient_light_energy = float(rig["ambient"]["energy"])
	world.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.tonemap_exposure = pow(2.0, float(rig.get("exposure", 0.0)))
	var holder := WorldEnvironment.new()
	holder.environment = world
	view.add_child(holder)


func _at(xyz: Array) -> Vector3:
	return Vector3(float(xyz[0]), float(xyz[1]), float(xyz[2]))


func _process(_delta: float) -> bool:
	drawn += 1
	if drawn < SETTLE:
		return false
	var image := view.get_texture().get_image()
	DirAccess.make_dir_recursive_absolute(shot.get_base_dir())
	image.save_png(shot)
	print("MODEL_AT_RIG shot=%s" % shot)
	return true
