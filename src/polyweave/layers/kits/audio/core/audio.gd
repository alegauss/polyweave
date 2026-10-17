class_name PolyweaveAudio
extends Node
## A game's audio through one service (polyweave kit "audio", §PW351), from Cottony's
## scripts/music.gd and scripts/sound.gd. The buses are declared once, in the project's
## res://polyweave_audio.gd, and laid out the first time the service is asked for: each
## missing bus is added and every bus is routed to the bus it sends to.
##
## - Music crossfades between tracks at equal power, so the level holds through the
##   change, and ducks by DUCK_DB while anything plays on the Voice bus.
## - A sound plays from a pool of POOL players with its pitch varied by up to PITCH,
##   so a sound repeated quickly neither cuts itself off nor machine-guns.
## - UI_SOUNDS {"focus": path, "confirm": path} play on the UI bus whenever a control
##   takes focus and whenever a focused button is pressed, which is what the menus
##   kit's pad navigation does.
##
## The sounds are the project's: the kit carries none. A bus declares `name`, `send`
## (Master where unset, and a bus declared before it, since Godot mixes a bus into one
## ahead of it only), `volume_db`, and `loudness`, the RMS level in dBFS a track
## mastered for that bus plays at through it, which the proof holds every bus to.

signal played(bus: String, stream: AudioStream)

const HERE := "res://addons/polyweave/audio/audio.gd"
const PROJECT := "res://polyweave_audio.gd"
## what the project's script may declare, and what holds where it does not
const DEFAULTS := {
	"BUSES": [
		{"name": "Master"},
		{"name": "Music", "send": "Master", "loudness": -18.0},
		{"name": "SFX", "send": "Master", "loudness": -18.0},
		{"name": "UI", "send": "Master", "loudness": -18.0},
		{"name": "Voice", "send": "Master", "loudness": -18.0},
	],
	"CROSSFADE": 1.5,
	"DUCK_DB": -10.0,
	"DUCK_SECONDS": 0.15,
	"POOL": 8,
	"PITCH": 0.06,
	"UI_SOUNDS": {},
	"LOUDNESS_TOLERANCE": 1.0,
}
const SILENT_DB := -80.0
## a Voice bus louder than this, in dBFS, ducks the music
const VOICE_HEARD_DB := -50.0

var declared := {}
## what laying out the buses or loading a UI sound could not do
var said: Array[String] = []
var ui_sounds := {}
var _music: Array[AudioStreamPlayer] = []
var _current := 0
var _fade_seconds := 0.0
var _fade_at := -1.0
var _duck := 0.0
var _pool: Array[AudioStreamPlayer] = []
var _started := {}
var _hooked := {}

static var _shared: Node


## the one service every sound goes through, made the first time and ready a frame on
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweaveAudio"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


## what the project declares, each name it leaves out at the kit's default
static func declaration(project := PROJECT) -> Dictionary:
	var out := DEFAULTS.duplicate(true)
	if ResourceLoader.exists(project):
		var map := (load(project) as GDScript).get_script_constant_map()
		for key in map:
			out[key] = map[key]
	return out


## add each declared bus that is missing and route each to its send; what could not be
## laid out is answered, never dropped
static func lay_out(buses: Array) -> Array[String]:
	var out: Array[String] = []
	for bus in buses:
		if AudioServer.get_bus_index(bus["name"]) == -1:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, bus["name"])
	for bus in buses:
		var at := AudioServer.get_bus_index(bus["name"])
		if at == 0:
			continue
		var send: String = bus.get("send", "Master")
		var to := AudioServer.get_bus_index(send)
		if to == -1 or to >= at:
			out.append("%s sends to %s, which is %s" % [bus["name"], send,
				"no bus" if to == -1 else "not a bus ahead of it, so nothing would be heard"])
			continue
		AudioServer.set_bus_send(at, send)
		if bus.has("volume_db"):
			AudioServer.set_bus_volume_db(at, float(bus["volume_db"]))
	return out


## each declared bus missing, or not sending where it is declared to
static func misrouted(buses: Array) -> Array[String]:
	var out: Array[String] = []
	for bus in buses:
		var at := AudioServer.get_bus_index(bus["name"])
		if at == -1:
			out.append("there is no bus %s" % bus["name"])
		elif at > 0 and str(AudioServer.get_bus_send(at)) != bus.get("send", "Master"):
			out.append("%s sends to %s, not to %s" % [bus["name"],
				AudioServer.get_bus_send(at), bus.get("send", "Master")])
	return out


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	declared = declaration()
	said.append_array(lay_out(declared["BUSES"]))
	for i in 2:
		var player := AudioStreamPlayer.new()
		player.bus = "Music"
		player.volume_db = SILENT_DB
		add_child(player)
		_music.append(player)
	for i in int(declared["POOL"]):
		var player := AudioStreamPlayer.new()
		add_child(player)
		_pool.append(player)
	for kind in declared["UI_SOUNDS"]:
		var path: String = declared["UI_SOUNDS"][kind]
		var stream := sound(path)
		if stream != null:
			ui_sounds[kind] = stream
		else:
			said.append("the UI sound %s is %s, which is not a sound there" % [kind, path])


## a sound by its path: imported where the editor imported it, read from the file where
## nothing has (a game run before the editor ever opened it)
static func sound(path: String) -> AudioStream:
	if ResourceLoader.exists(path):
		return load(path) as AudioStream
	if not FileAccess.file_exists(path):
		return null
	match path.get_extension().to_lower():
		"wav":
			return AudioStreamWAV.load_from_file(path)
		"ogg":
			return AudioStreamOggVorbis.load_from_file(path)
		"mp3":
			return AudioStreamMP3.load_from_file(path)
	return null


func _ready() -> void:
	get_viewport().gui_focus_changed.connect(_focused)


## crossfade to `stream` over `seconds` (the declared CROSSFADE where unset); the same
## track already playing goes on
func play_music(stream: AudioStream, seconds := -1.0) -> void:
	var now := _music[_current]
	if now.playing and now.stream == stream:
		return
	var next := _music[1 - _current]
	next.stream = stream
	next.volume_db = SILENT_DB
	next.play()
	_current = 1 - _current
	_fade_seconds = float(declared["CROSSFADE"]) if seconds < 0.0 else seconds
	_fade_at = 0.0
	_mix_music()


func stop_music() -> void:
	for player in _music:
		player.stop()
	_fade_at = -1.0


## the track playing, or null
func music() -> AudioStream:
	return _music[_current].stream if _music[_current].playing else null


## play a sound from the pool on `bus`, its pitch varied by up to `spread` (the declared
## PITCH where unset); the player that started longest ago is taken when none is free
func play(stream: AudioStream, bus := "SFX", spread := -1.0) -> AudioStreamPlayer:
	var player: AudioStreamPlayer = null
	for each in _pool:
		if not each.playing:
			player = each
			break
	if player == null:
		player = _pool[0]
		for each in _pool:
			if _started.get(each, 0) < _started.get(player, 0):
				player = each
	var vary := float(declared["PITCH"]) if spread < 0.0 else spread
	player.stream = stream
	player.bus = bus
	player.pitch_scale = 1.0 + randf_range(-vary, vary)
	player.play()
	_started[player] = Time.get_ticks_usec()
	played.emit(bus, stream)
	return player


## a line of speech on the Voice bus, at its own pitch; the music ducks under it
func say(stream: AudioStream) -> AudioStreamPlayer:
	return play(stream, "Voice", 0.0)


## the players of the pool, for a game's own tests
func pool() -> Array[AudioStreamPlayer]:
	return _pool


## the decibels the music is ducked by now, 0 where it is not
func ducked_db() -> float:
	return _duck


func _voice_heard() -> bool:
	for each in _pool:
		if each.playing and each.bus == "Voice":
			return true
	var at := AudioServer.get_bus_index("Voice")
	return at != -1 and maxf(AudioServer.get_bus_peak_volume_left_db(at, 0),
		AudioServer.get_bus_peak_volume_right_db(at, 0)) > VOICE_HEARD_DB


func _process(delta: float) -> void:
	var target := float(declared["DUCK_DB"]) if _voice_heard() else 0.0
	var rate := absf(float(declared["DUCK_DB"])) / maxf(float(declared["DUCK_SECONDS"]), 0.001)
	_duck = move_toward(_duck, target, rate * delta)
	if _fade_at >= 0.0:
		_fade_at += delta
	_mix_music()


## equal power: the incoming track at sin, the outgoing at cos, so two tracks at one
## level sum to that level throughout and never to more
func _mix_music() -> void:
	var share := 1.0
	if _fade_at >= 0.0:
		share = 1.0 if _fade_seconds <= 0.0 else clampf(_fade_at / _fade_seconds, 0.0, 1.0)
	var incoming := _music[_current]
	var outgoing := _music[1 - _current]
	incoming.volume_db = _db(sin(share * PI / 2.0)) + _duck
	outgoing.volume_db = _db(cos(share * PI / 2.0)) + _duck
	if share >= 1.0 and _fade_at >= 0.0:
		outgoing.stop()
		_fade_at = -1.0


func _db(gain: float) -> float:
	return SILENT_DB if gain <= 0.0001 else linear_to_db(gain)


func _focused(control: Control) -> void:
	if ui_sounds.has("focus"):
		play(ui_sounds["focus"], "UI", 0.0)
	if control is BaseButton and not _hooked.has(control.get_instance_id()):
		_hooked[control.get_instance_id()] = true
		(control as BaseButton).pressed.connect(_confirmed)


func _confirmed() -> void:
	if ui_sounds.has("confirm"):
		play(ui_sounds["confirm"], "UI", 0.0)
