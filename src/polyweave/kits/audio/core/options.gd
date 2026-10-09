extends RefCounted
## The audio tab the audio kit contributes to the options kit's screen (§PW351): a
## volume row for every bus the project declares, in the order it declares them, so the
## layout is declared once, in res://polyweave_audio.gd, and read here.

const TAB := "audio"
const Audio := preload("res://addons/polyweave/audio/audio.gd")


static func options() -> Array[Dictionary]:
	var buses: Array = Audio.declaration()["BUSES"]
	Audio.lay_out(buses)
	var out: Array[Dictionary] = []
	for bus in buses:
		var name: String = bus["name"]
		var at := func() -> int: return AudioServer.get_bus_index(name)
		out.append({
			"tab": TAB, "key": name.to_lower(), "label": name.to_lower() + " volume",
			"default": float(bus.get("volume_db", 0.0)), "range": [-40.0, 0.0, 1.0],
			"apply": func(v: float) -> void: AudioServer.set_bus_volume_db(at.call(), v),
			"read": func() -> float: return AudioServer.get_bus_volume_db(at.call()),
		})
	return out
