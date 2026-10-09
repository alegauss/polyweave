extends Camera2D
## A camera that shakes every frame, through the kit, as a game's own effect would.

const Access := preload("res://addons/polyweave/access/access.gd")


func _process(_delta: float) -> void:
	offset = Access.shared().shake(Vector2(randf_range(-6.0, 6.0), randf_range(-6.0, 6.0)))
