extends RefCounted
## The accessibility tab the access kit contributes to the options kit's screen
## (§PW355): the text scale, the colour filter, subtitles, shake, flashes, and hold or
## toggle, each put in force through PolyweaveAccess and read back from it.

const TAB := "accessibility"
const Access := preload("res://addons/polyweave/access/access.gd")


static func options() -> Array[Dictionary]:
	var access: Access = Access.shared()
	var scales: Array = access.declared["SCALES"]
	return [
		{
			"tab": TAB, "key": "text_scale", "label": "text size", "default": 1.0,
			"choices": scales,
			"names": scales.map(func(s: float) -> String: return "%d%%" % int(round(s * 100))),
			"apply": func(v: float) -> void: access.set_text_scale(v),
			"read": func() -> float: return access.text_scale,
		},
		{
			"tab": TAB, "key": "colour_filter", "label": "colour filter", "default": "off",
			"choices": ["off", "protanopia", "deuteranopia", "tritanopia"],
			"apply": func(v: String) -> void: access.set_filter(v),
			"read": func() -> String: return access.filter,
		},
		{
			"tab": TAB, "key": "subtitles", "label": "subtitles", "default": true,
			"apply": func(v: bool) -> void: access.subtitles = v,
			"read": func() -> bool: return access.subtitles,
		},
		{
			"tab": TAB, "key": "shake", "label": "screen shake", "default": true,
			"apply": func(v: bool) -> void: access.shaking = v,
			"read": func() -> bool: return access.shaking,
		},
		{
			"tab": TAB, "key": "flashes", "label": "flashes", "default": true,
			"apply": func(v: bool) -> void: access.flashing = v,
			"read": func() -> bool: return access.flashing,
		},
		{
			"tab": TAB, "key": "hold_toggle", "label": "toggle held actions", "default": false,
			"apply": func(v: bool) -> void: access.set_toggling(v),
			"read": func() -> bool: return access.toggling,
		},
	]
