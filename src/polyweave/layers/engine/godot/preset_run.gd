extends SceneTree
## One graphics settings combination on one scene, as engine.preset_search runs it
## (§PW367): the settings put on the root viewport and the scene's environments, every
## frame's wall-clock time with vsync off after a short settling, and the last frame
## saved. Prints `PRESET p95_ms=… p99_ms=…`. Takes `scene=res://…`, `frames=N`,
## `shot=<file>` and `settings=<JSON>` after `--`, the settings in the graphics kit's
## terms: scale, scaler, msaa, taa, fxaa, shadows and effects.

const SETTLE := 10
const SCALERS := {"bilinear": Viewport.SCALING_3D_MODE_BILINEAR,
	"fsr": Viewport.SCALING_3D_MODE_FSR, "fsr2": Viewport.SCALING_3D_MODE_FSR2}
const MSAA := {0: Viewport.MSAA_DISABLED, 2: Viewport.MSAA_2X, 4: Viewport.MSAA_4X,
	8: Viewport.MSAA_8X}
const EFFECTS := ["sdfgi_enabled", "ssao_enabled", "volumetric_fog_enabled"]

var frames := 120
var shot := ""
var times := PackedFloat64Array()
var last := 0
var seen := 0


func _initialize() -> void:
	var scene := ""
	var settings := {}
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("scene="):
			scene = arg.get_slice("=", 1)
		elif arg.begins_with("frames="):
			frames = int(arg.get_slice("=", 1))
		elif arg.begins_with("shot="):
			shot = arg.substr(5)
		elif arg.begins_with("settings="):
			settings = JSON.parse_string(arg.substr(9))
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var made := (load(scene) as PackedScene).instantiate()
	root.add_child(made)
	current_scene = made
	root.scaling_3d_mode = SCALERS.get(settings.get("scaler", "bilinear"), 0)
	root.scaling_3d_scale = float(settings.get("scale", 1.0))
	root.msaa_3d = MSAA.get(int(settings.get("msaa", 0)), Viewport.MSAA_DISABLED)
	root.use_taa = bool(settings.get("taa", false))
	root.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if settings.get("fxaa", false) \
		else Viewport.SCREEN_SPACE_AA_DISABLED
	root.positional_shadow_atlas_size = int(settings.get("shadows", 4096))
	for found in made.find_children("*", "WorldEnvironment", true, false):
		var env := (found as WorldEnvironment).environment
		for effect in EFFECTS:
			if env != null and env.get(effect):
				env.set(effect, bool(settings.get("effects", true)))


func _process(_delta: float) -> bool:
	var now := Time.get_ticks_usec()
	seen += 1
	if seen > SETTLE and last > 0:
		times.append((now - last) / 1000.0)
	last = now
	if times.size() < frames:
		return false
	var sorted := times.duplicate()
	sorted.sort()
	if shot != "":
		root.get_texture().get_image().save_png(shot)
	print("PRESET p95_ms=%.3f p99_ms=%.3f" % [_at(sorted, 0.95), _at(sorted, 0.99)])
	return true


func _at(sorted: PackedFloat64Array, share: float) -> float:
	return sorted[mini(sorted.size() - 1, int(ceil(share * sorted.size())) - 1)]
