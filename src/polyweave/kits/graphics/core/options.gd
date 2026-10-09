extends RefCounted
## The graphics tab the graphics kit contributes to the options kit's screen (§PW366): a
## preset row whose default is the one the video adapter suggests, applied through
## PolyweaveGraphics and read back as the preset in force.

const TAB := "graphics"
const Graphics := preload("res://addons/polyweave/graphics/graphics.gd")


static func options() -> Array[Dictionary]:
	var graphics: Graphics = Graphics.shared()
	var names: Array = graphics.presets.keys()
	return [{
		"tab": TAB, "key": "preset", "label": "quality", "default": graphics.first(),
		"choices": names,
		"apply": func(v: String) -> void: graphics.apply(v),
		"read": func() -> String: return graphics.preset,
	}]
