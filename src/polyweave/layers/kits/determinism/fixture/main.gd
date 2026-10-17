extends Node2D
## Spawns by chance, drawn from the kit's streams, and a player held right by the input.

const _PwRandom := preload("res://addons/polyweave/determinism/random.gd")

var player_x := 0.0
var enemies := 0
var last_spawn := 0.0


func _physics_process(_delta: float) -> void:
	if Input.is_action_pressed("right"):
		player_x += 2.0
	if _PwRandom.randf("spawns") < 0.2:
		enemies += 1
		last_spawn = _PwRandom.randf_range(0.0, 640.0, "spawns")
