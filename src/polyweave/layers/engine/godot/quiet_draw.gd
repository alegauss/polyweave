extends Node
## Draws each frame while the window is minimised (§PW296).
##
## Godot draws nothing while every window is minimised, so `frame_post_draw` never
## fires and a movie repeats its last frame. polyweave loads this as an autoload through
## the run's override.cfg, and it draws where the engine would have, after every other
## node has processed.
##
## A forced draw still skips the viewport of a minimised window, so a movie wrote its
## first frame again and again: every effect filmed stood still (§PW598). A run writing
## a movie has its window put back and moved off the desktop instead, where it draws.


func _ready() -> void:
	process_priority = 2147483647
	if Engine.get_write_movie_path() != "":
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
		DisplayServer.window_set_position(Vector2i(-32000, -32000))


func _process(_delta: float) -> void:
	if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_MINIMIZED:
		RenderingServer.force_draw(false)
