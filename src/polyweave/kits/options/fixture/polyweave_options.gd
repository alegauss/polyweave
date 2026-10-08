extends RefCounted
## The options fixture's own rows: a bus's volume, the language and a subtitles switch,
## each put in force and read back, and a key an older build of it called otherwise.

const VERSION := 2


static func renamed() -> Dictionary:
	return {"audio/master_db": "audio/master"}


static func options() -> Array[Dictionary]:
	return [
		{
			"tab": "audio", "key": "master", "label": "master volume", "default": 0.0,
			"range": [-40.0, 0.0, 1.0],
			"apply": func(v: float) -> void: AudioServer.set_bus_volume_db(0, v),
			"read": func() -> float: return AudioServer.get_bus_volume_db(0),
		},
		{
			"tab": "general", "key": "language", "label": "language", "default": "en",
			"choices": ["en", "pt_BR"], "names": ["English", "Português"],
			"apply": func(v: String) -> void: TranslationServer.set_locale(v),
			"read": func() -> String: return TranslationServer.get_locale(),
		},
		{
			"tab": "general", "key": "subtitles", "label": "subtitles", "default": true,
			"apply": func(v: bool) -> void: Engine.set_meta("subtitles", v),
			"read": func() -> bool: return Engine.get_meta("subtitles", true),
		},
	]
