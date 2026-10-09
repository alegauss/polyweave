class_name PolyweaveRecorder
extends Node
## A run's input, each action's press and release stamped with its physics frame
## (polyweave kit "determinism", §PW360). With the run's seed it is all it takes to play
## the run again: `replay(record)` feeds the events back at their frames, and
## game.record_flow turns a saved record into a game.keep flow, so a bug seen once is a
## flow game.replay runs in the gate from then on.

const Random := preload("res://addons/polyweave/determinism/random.gd")
const FILE := "user://polyweave_record.json"

var recording := false
var events: Array = []
var _start := 0
var _playing: Array = []
var _held := {}


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


## the physics frame of the run, counted from the start of the recording or replay
func frame() -> int:
	return Engine.get_physics_frames() - _start


func start() -> void:
	events.clear()
	recording = true
	_start = Engine.get_physics_frames()


## the record: the seed and every event, as a file holds it
func stop() -> Dictionary:
	recording = false
	return {"format": 1, "seed": Random.seed_of(), "events": events.duplicate(true)}


## keep the record, and say where it went
func save(path := FILE) -> String:
	var record := stop()
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(record, "\t"))
	file.close()
	var where := ProjectSettings.globalize_path(path)
	print("polyweave_record: saved %s" % where)
	return where


func _input(event: InputEvent) -> void:
	if not recording or event.is_echo():
		return
	for action in InputMap.get_actions():
		if str(action).begins_with("ui_") or not event.is_action(action):
			continue
		var pressed := event.is_action_pressed(action)
		if pressed == _held.get(action, false):
			continue
		_held[action] = pressed
		events.append({"frame": frame(), "action": str(action), "pressed": pressed})


## play a record's events back at their frames, from the next physics frame
func replay(record: Dictionary) -> void:
	_playing = (record.get("events", []) as Array).duplicate(true)
	_start = Engine.get_physics_frames()


func _physics_process(_delta: float) -> void:
	while not _playing.is_empty() and int(_playing[0]["frame"]) <= frame():
		var event: Dictionary = _playing.pop_front()
		if event["pressed"]:
			Input.action_press(event["action"])
		else:
			Input.action_release(event["action"])
