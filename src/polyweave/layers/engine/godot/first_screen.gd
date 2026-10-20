extends SceneTree
## An exported pack's main scene drawn in a window and its first screen kept, as
## game.export_smoke runs it with `shot` (§PW578). Run from outside the pack, so a
## release never carries it. Takes `frames=N` and `shot=<file>` after `--`, saves the
## frame drawn after N frames and prints `FIRST shot=<file>`.

var frames := 120
var shot := ""
var seen := 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("frames="):
			frames = int(arg.get_slice("=", 1))
		elif arg.begins_with("shot="):
			shot = arg.substr(5)
	var scene := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	var packed := load(scene) as PackedScene if scene != "" else null
	if packed == null:
		push_error("first_screen: the pack names no main scene to draw")
		quit(1)
		return
	var made := packed.instantiate()
	root.add_child(made)
	current_scene = made


func _process(_delta: float) -> bool:
	seen += 1
	if seen < frames:
		return false
	root.get_texture().get_image().save_png(shot)
	print("FIRST shot=%s" % shot)
	return true
