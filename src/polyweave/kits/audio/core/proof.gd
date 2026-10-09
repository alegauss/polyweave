extends SceneTree
## The audio kit's proof, run in the game it lands in (§PW351), on what the engine mixes:
## every declared bus exists and routes as declared; each bus's output, a tone mastered
## to its declared loudness played through it, is written beside the game and printed
## as a KIT SOUND line, which polyweave holds to that loudness with sound.measure, the
## measure a track is held to; a crossfade keeps its level, with no gap, no bump and no
## clipping; music ducks under voice and comes back; the pool plays at once and varies
## its pitch; a pad's focus and confirm in a menu play the UI sounds; and every bus's
## volume row reads back what it sets. Prints KIT PROVED, or KIT FAILED with why.

const Audio := preload("res://addons/polyweave/audio/audio.gd")
const Options := preload("res://addons/polyweave/audio/options.gd")
const Menu := preload("res://addons/polyweave/menus/menu.gd")
const HEARD := "res://.polyweave/kits/audio"
## seconds of a bus heard before its level is taken, and how long it is taken for
const SETTLE := 0.15
const TAKE := 0.6
## how far, in dB, a crossfade's or a duck's level may stray from what it should be
const HOLD_DB := 1.5
const WINDOW := 0.05

var failed := []
var audio: Audio
var declared := {}
var stage := "start"
var step := 0
var since := 0
var queue := []
var heard := PackedVector2Array()
var before := 0.0
var master_capture := AudioEffectCapture.new()
var music_capture := AudioEffectCapture.new()
var player: AudioStreamPlayer
var menu: Menu
var played := []


func _initialize() -> void:
	audio = Audio.shared()
	declared = audio.declared
	AudioServer.add_bus_effect(0, master_capture)
	var music := AudioServer.get_bus_index("Music")
	if music != -1:
		AudioServer.add_bus_effect(music, music_capture)
	audio.played.connect(func(bus: String, stream: AudioStream) -> void: played.append([bus, stream]))


func _seconds() -> float:
	return (Time.get_ticks_msec() - since) / 1000.0


func _next(named: String) -> void:
	stage = named
	step = 0
	since = Time.get_ticks_msec()


func _step() -> void:
	step += 1
	since = Time.get_ticks_msec()


## a tone looped on whole cycles whose RMS is `db` dBFS
func _tone(hertz: float, db: float) -> AudioStreamWAV:
	var rate := 44100
	var cycle := int(round(rate / hertz))
	var amplitude := db_to_linear(db) * sqrt(2.0)
	var data := PackedByteArray()
	data.resize(cycle * 20 * 2)
	for i in cycle * 20:
		data.encode_s16(i * 2, int(round(sin(TAU * i / cycle) * amplitude * 32767.0)))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = rate
	wav.stereo = false
	wav.data = data
	wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
	wav.loop_end = cycle * 20
	return wav


func _drain(capture: AudioEffectCapture) -> PackedVector2Array:
	return capture.get_buffer(capture.get_frames_available())


func _rms_db(frames: PackedVector2Array) -> float:
	if frames.is_empty():
		return -INF
	var sum := 0.0
	for f in frames:
		sum += (f.x * f.x + f.y * f.y) / 2.0
	return linear_to_db(sqrt(sum / frames.size()))


func _write(frames: PackedVector2Array, named: String) -> String:
	var data := PackedByteArray()
	data.resize(frames.size() * 4)
	for i in frames.size():
		data.encode_s16(i * 4, int(clampf(frames[i].x, -1.0, 1.0) * 32767.0))
		data.encode_s16(i * 4 + 2, int(clampf(frames[i].y, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = int(AudioServer.get_mix_rate())
	wav.stereo = true
	wav.data = data
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(HEARD))
	var at := "%s/%s.wav" % [HEARD, named]
	wav.save_to_wav(ProjectSettings.globalize_path(at))
	return at.trim_prefix("res://")


func _pad(index: int) -> void:
	var event := InputEventJoypadButton.new()
	event.button_index = index as JoyButton
	event.pressed = true
	root.push_input(event)
	var released := event.duplicate() as InputEventJoypadButton
	released.pressed = false
	root.push_input(released)


func _process(_delta: float) -> bool:
	match stage:
		"start":
			if audio.is_inside_tree():
				_routes()
		"loud":
			_loud()
		"fade":
			_fade()
		"duck":
			_ducking()
		"ui":
			_ui()
		"done":
			_finish()
			return true
	if Time.get_ticks_msec() > 60000:
		failed.append("the proof did not finish in a minute, at %s" % stage)
		_finish()
		return true
	return false


func _routes() -> void:
	for line in Audio.misrouted(declared["BUSES"]) + audio.said:
		failed.append(line)
	for bus in declared["BUSES"]:
		if bus.has("loudness"):
			queue.append(bus)
	player = null
	_next("loud")


## each bus heard on the Master bus alone, a tone at its declared loudness played through it
func _loud() -> void:
	if queue.is_empty():
		_next("fade")
		return
	var bus: Dictionary = queue[0]
	if player == null:
		_drain(master_capture)
		player = audio.play(_tone(441.0, float(bus["loudness"])), bus["name"], 0.0)
		heard = PackedVector2Array()
		since = Time.get_ticks_msec()
		return
	var taken := _drain(master_capture)
	if _seconds() < SETTLE:
		return
	heard.append_array(taken)
	if _seconds() < SETTLE + TAKE:
		return
	player.stop()
	player = null
	queue.pop_front()
	var tolerance := float(declared["LOUDNESS_TOLERANCE"])
	var target := float(bus["loudness"])
	print("KIT SOUND %s loudness %.2f %.2f" % [_write(heard, bus["name"]), target - tolerance,
		target + tolerance])


## one track to another at the declared crossfade, its level held throughout
func _fade() -> void:
	var level := float(declared["BUSES"].filter(
		func(b: Dictionary) -> bool: return b["name"] == "Music")[0].get("loudness", -18.0))
	var taken := _drain(music_capture)
	match step:
		0:
			audio.play_music(_tone(441.0, level), 0.0)
			_step()
		1:
			heard.append_array(taken)
			if _seconds() < 0.5:
				return
			# what a capture hands over runs behind what was played, so the level is
			# the last of what was heard, the first track alone and settled
			before = _rms_db(heard.slice(heard.size() - int(0.1 * AudioServer.get_mix_rate())))
			heard = PackedVector2Array()
			audio.play_music(_tone(294.0, level))
			_step()
		2:
			heard.append_array(taken)
			if _seconds() < float(declared["CROSSFADE"]) + 0.3:
				return
			_held_through(heard)
			heard = PackedVector2Array()
			_next("duck")


func _held_through(frames: PackedVector2Array) -> void:
	var rate := AudioServer.get_mix_rate()
	var window := int(WINDOW * rate)
	# a clip flattens a run of samples at full scale; a lone sample there is one the
	# capture handed over torn, racing the mixer, and not what was played
	var full := 0.999
	for i in range(1, frames.size()):
		var now := maxf(absf(frames[i].x), absf(frames[i].y))
		var was := maxf(absf(frames[i - 1].x), absf(frames[i - 1].y))
		if now >= full and was >= full:
			failed.append("the crossfade clipped %.2fs in" % (i / rate))
			break
	for at in range(0, frames.size() - window, window):
		var db := _rms_db(frames.slice(at, at + window))
		if db < before - HOLD_DB:
			failed.append("the crossfade fell %.1f dB below its level %.2fs in: a gap" % [
				before - db, at / rate])
			return
		if db > before + HOLD_DB:
			failed.append("the crossfade rose %.1f dB over its level %.2fs in" % [
				db - before, at / rate])
			return


## the music before a line of speech, under it and after it
func _ducking() -> void:
	var taken := _drain(music_capture)
	var settle := float(declared["DUCK_SECONDS"]) + 0.2
	match step:
		0:
			heard.append_array(taken)
			if _seconds() < 0.2:
				return
			before = _rms_db(heard)
			heard = PackedVector2Array()
			player = audio.say(_tone(441.0, -18.0))
			_step()
		1:
			if _seconds() < settle:
				return
			heard.append_array(taken)
			if _seconds() < settle + 0.2:
				return
			var under := _rms_db(heard) - before
			var duck := float(declared["DUCK_DB"])
			if absf(under - duck) > HOLD_DB:
				failed.append("the music under voice moved %.1f dB, not the %.1f declared" % [
					under, duck])
			player.stop()
			player = null
			heard = PackedVector2Array()
			_step()
		2:
			if _seconds() < settle + 0.4:
				return
			heard.append_array(taken)
			if _seconds() < settle + 0.6:
				return
			var after := _rms_db(heard) - before
			if absf(after) > HOLD_DB:
				failed.append("the music after the voice stayed %.1f dB from its level" % after)
			audio.stop_music()
			_pool()
			_rows()
			_next("ui")


## more sounds at once than the pool holds: every player plays, at pitches that differ
func _pool() -> void:
	var tone := _tone(441.0, -30.0)
	var size := int(declared["POOL"])
	for i in size + 2:
		audio.play(tone, "SFX")
	var pitches := []
	for each in audio.pool():
		if not each.playing:
			failed.append("%d sounds at once left a player of %d idle" % [size + 2, size])
			break
		pitches.append(each.pitch_scale)
	var vary := float(declared["PITCH"])
	if vary > 0.0 and pitches.max() == pitches.min():
		failed.append("%d sounds at once all played at one pitch, %.3f" % [size, pitches[0]])
	for pitch in pitches:
		if absf(pitch - 1.0) > vary + 0.0001:
			failed.append("a sound played at pitch %.3f, past the %.3f declared" % [pitch, vary])
			break
	for each in audio.pool():
		each.stop()


## every bus's row sets its volume and reads it back
func _rows() -> void:
	for row in Options.options():
		row["apply"].call(-7.0)
		if absf(float(row["read"].call()) + 7.0) > 0.01:
			failed.append("the %s row set -7 dB and read back %s" % [row["key"], row["read"].call()])
		row["apply"].call(row["default"])


## a pad walking a menu and confirming plays the declared UI sounds
func _ui() -> void:
	if not audio.ui_sounds.has("focus") and not audio.ui_sounds.has("confirm"):
		_next("done")
		return
	if menu == null:
		menu = Menu.new()
		menu.items.assign(["play", "options", "quit"])
		root.add_child(menu)
		since = Time.get_ticks_msec()
		return
	if _seconds() < 0.1:
		return
	played.clear()
	_pad(JOY_BUTTON_DPAD_DOWN)
	_pad(JOY_BUTTON_A)
	var ui := played.filter(func(p: Array) -> bool: return p[0] == "UI").map(
		func(p: Array) -> AudioStream: return p[1])
	for kind in ["focus", "confirm"]:
		if audio.ui_sounds.has(kind) and not ui.has(audio.ui_sounds[kind]):
			failed.append("a pad's %s in a menu played no %s sound on the UI bus" % [kind, kind])
	_next("done")


func _finish() -> void:
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
