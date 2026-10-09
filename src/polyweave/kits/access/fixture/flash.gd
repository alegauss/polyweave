extends ColorRect
## A strobe over the whole screen, eight times a second, asked through the kit as a
## game's own effect would ask it: with flashes off it stays dark.

const Access := preload("res://addons/polyweave/access/access.gd")


func _process(_delta: float) -> void:
	var on := (Engine.get_process_frames() / 4) % 2 == 1
	color = Color.WHITE * Access.shared().flash(1.0 if on else 0.0)
	color.a = 1.0
