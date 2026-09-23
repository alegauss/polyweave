extends SceneTree

# The scene script the offscreen tests actually run, which is why it lives in a file
# rather than in a Python string literal full of escaped tabs (§PW48): as a literal
# nothing highlighted it, nothing linted it, and GDScript's tabs were two characters.
#
# It draws one blue patch into a SubViewport, waits four frames for the render target to
# have something in it, and saves. The route being tested is what the window does while
# that happens — moved off the desktop, minimised, or never opened at all — and the
# point of the patch is that a route which silently renders nothing comes back black.

var frames := 0
var view: SubViewport

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "offscreen":
			DisplayServer.window_set_position(Vector2i(-32000, -32000))
		elif arg == "minimized":
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	view = SubViewport.new()
	view.size = Vector2i(32, 32)
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	var patch := ColorRect.new()
	patch.color = Color(0.0, 0.0, 1.0)
	patch.size = Vector2(32, 32)
	view.add_child(patch)
	root.add_child(view)

func _process(_delta: float) -> bool:
	frames += 1
	if frames < 4:
		return false
	var image := view.get_texture().get_image()
	image.save_png("res://shot.png")
	print("captured: res://shot.png %d x %d" % [image.get_width(), image.get_height()])
	return true
