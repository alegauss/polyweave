extends Node
## Draws each frame while the window is minimised (§PW296).
##
## Godot draws nothing while every window is minimised, so `frame_post_draw` never
## fires and a movie repeats its last frame. polyweave loads this as an autoload through
## the run's override.cfg, and it draws where the engine would have, after every other
## node has processed.


func _ready() -> void:
	process_priority = 2147483647


func _process(_delta: float) -> void:
	if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_MINIMIZED:
		RenderingServer.force_draw(false)
