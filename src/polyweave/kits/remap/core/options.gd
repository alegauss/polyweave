extends RefCounted
## The controls tab the remap kit contributes to the options kit's screen (§PW347): a
## row that opens the remap screen, which keeps the bindings, the deadzone and the
## inverted vertical in its own file.

const TAB := "controls"


static func options() -> Array[Dictionary]:
	return [{"tab": TAB, "key": "remap", "label": "controls",
		"opens": "res://kits/remap/remap_menu.tscn"}]
