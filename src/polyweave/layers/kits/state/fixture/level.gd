extends Node

var wave := 1


func snapshot() -> Dictionary:
	return {"wave": wave, "enemies": 4}
