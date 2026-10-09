extends SceneTree
## The graphics kit's proof, run in the game it lands in (§PW366): the main scene runs,
## and every preset, applied, is read back from the viewport and the environments as it
## declares; an effect the game's environments never switched on is never switched on;
## a first launch picks the lightest preset for an integrated or software adapter; the
## options row reads back each preset it sets; and the project keeps Godot's fallback to
## the Compatibility renderer on. Prints KIT PROVED, or KIT FAILED with why.

const Graphics := preload("res://addons/polyweave/graphics/graphics.gd")
const Options := preload("res://addons/polyweave/graphics/options.gd")

var failed := []
var graphics: Graphics
var frames := 0


func _initialize() -> void:
	graphics = Graphics.shared()
	var main := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if main != "":
		change_scene_to_file(main)


func _process(_delta: float) -> bool:
	frames += 1
	if frames < 3 or not graphics.is_inside_tree():
		return false
	if current_scene != null:
		graphics.watch(current_scene)
	var untouched := _off_effects()
	for named in graphics.presets:
		graphics.apply(named)
		var declared: Dictionary = graphics.presets[named]
		var now := graphics.in_force()
		for key in declared:
			if now.has(key) and not _same(now[key], declared[key]):
				failed.append("the %s preset declares %s %s, and %s is in force" % [
					named, key, declared[key], now[key]])
	if _off_effects() != untouched:
		failed.append("a preset switched on an effect no environment of the game uses")
	var row: Dictionary = Options.options()[0]
	for named in graphics.presets:
		row["apply"].call(named)
		if row["read"].call() != named:
			failed.append("the graphics row set %s and read back %s" % [named, row["read"].call()])
	if not bool(ProjectSettings.get_setting(Graphics.FALLBACK, false)):
		failed.append("%s is off, so a driver that refuses Vulkan leaves the game dark" % Graphics.FALLBACK)
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	return true


func _same(now: Variant, declared: Variant) -> bool:
	if declared is float or now is float:
		return absf(float(now) - float(declared)) < 0.002
	return now == declared


## every effect the game's environments have off, which no preset may switch on
func _off_effects() -> Array:
	var off := []
	if current_scene == null:
		return off
	for found in current_scene.find_children("*", "WorldEnvironment", true, false):
		var env := (found as WorldEnvironment).environment
		for effect in Graphics.EFFECTS:
			if env != null and not env.get(effect):
				off.append("%s.%s" % [found.name, effect])
	return off
