class_name PolyweaveConfirm
extends "res://addons/polyweave/menus/menu.gd"
## A yes-or-no confirm (polyweave kit "menus", §PW346): "no" is focused first and back
## answers it, so a press too many never says yes. `answered` carries the answer.

signal answered(yes: bool)


func _init() -> void:
	items.assign(["yes", "no"])
	back_to = "no"
	first = "no"
	chosen.connect(func(item: String) -> void: answered.emit(item == "yes"))
