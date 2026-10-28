extends SceneTree
## The determinism kit's proof, run in the game it lands in (§PW360): the project's RUN
## scene is played twice for RUN_TICKS physics frames, both times from SEED and with the
## input of RECORD (a record PolyweaveRecorder saved) fed at its frames, and the state
## kit's snapshot is taken after every physics frame of each. The two runs must agree name
## by name, frame by frame; the first frame and name that differ are named, which is
## usually the one draw something made outside PolyweaveRandom. Physics frames are what is
## counted, since only they step by a fixed time. Prints KIT PROVED, or KIT FAILED with
## why.
##
## With `-- --trace=<path>` the scene is played once instead and each physics frame's
## snapshot is written to <path>, a trace line a name and a tick, which game.replay_rates
## lays beside the same run flown at another frame rate (§PW640): frames and ticks part
## only off one tick a frame, which is where play timed by frames drifts. Prints
## KIT TRACED with the ticks and frames it ran.

const _PwRandom := preload("res://addons/polyweave/determinism/random.gd")
const _PwRecorder := preload("res://addons/polyweave/determinism/recorder.gd")
const _PwState := preload("res://addons/polyweave/state/state.gd")
const PROJECT := "res://polyweave_random.gd"

var failed := []
var declared := {}
var record := {}
var recorder: _PwRecorder
var watcher: Node
var runs: Array = [[], []]
var run := -1
var scene: Node
var trace := ""
var drawn := 0


func _initialize() -> void:
	for given in OS.get_cmdline_user_args():
		if given.begins_with("--trace="):
			trace = given.trim_prefix("--trace=")
	if ResourceLoader.exists(PROJECT):
		declared = (load(PROJECT) as GDScript).get_script_constant_map()
	if str(declared.get("RUN", "")) == "":
		print("KIT FAILED: res://polyweave_random.gd declares no RUN scene to play twice")
		quit(1)
		return
	var kept := str(declared.get("RECORD", ""))
	if kept != "":
		record = JSON.parse_string(FileAccess.get_file_as_string(kept))
		if record == null:
			print("KIT FAILED: the record %s does not read as JSON" % kept)
			quit(1)
			return
		# a record flies back at the tick rate it was made at, whatever the frame rate
		if record.has("ticks_per_second"):
			Engine.physics_ticks_per_second = int(record["ticks_per_second"])
	recorder = _PwRecorder.new()
	recorder.process_physics_priority = -1000
	root.add_child(recorder)
	var counting := GDScript.new()
	counting.source_code = "extends Node\nsignal ticked\nfunc _physics_process(_d):\n\tticked.emit()\n"
	counting.reload()
	watcher = Node.new()
	watcher.set_script(counting)
	watcher.process_physics_priority = 1000
	root.add_child(watcher)
	watcher.ticked.connect(_ticked)
	_begin()


## a run from the top: the same seed, the same record, a fresh scene
func _begin() -> void:
	run += 1
	if scene != null:
		scene.free()
	for action in InputMap.get_actions():
		Input.action_release(action)
	_PwRandom.reseed(int(declared.get("SEED", 1234)))
	recorder.replay(record)
	scene = (load(str(declared["RUN"])) as PackedScene).instantiate()
	root.add_child(scene)
	current_scene = scene


func _ticked() -> void:
	if run > 1 or scene == null:
		return
	runs[run].append(_PwState.snapshot())
	if runs[run].size() == 1:
		drawn = Engine.get_process_frames()
	if runs[run].size() < int(declared.get("RUN_TICKS", 120)):
		return
	if trace != "":
		_traced()
		return
	if run == 0:
		_begin()
		return
	run = 2
	_compare()
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	quit()


## the one run as a trace: each name's value at each tick, spelled as Godot spells it,
## so two runs agree only where they hold the same bits
func _traced() -> void:
	run = 2
	var file := FileAccess.open(trace, FileAccess.WRITE)
	if file == null:
		print("KIT FAILED: the trace %s could not be written" % trace)
		quit(1)
		return
	for tick in runs[0].size():
		var one: Dictionary = runs[0][tick]
		for name in one:
			file.store_line(JSON.stringify({"frame": tick + 1, "id": str(name),
				"value": var_to_str(one[name])}))
	file.close()
	print("KIT TRACED ticks=%d frames=%d" % [runs[0].size(),
		Engine.get_process_frames() - drawn + 1])
	quit()


func _compare() -> void:
	if runs[0].is_empty() or (runs[0][0] as Dictionary).is_empty():
		failed.append("the state kit declares nothing to compare the two runs by")
		return
	for tick in runs[0].size():
		var one: Dictionary = runs[0][tick]
		var two: Dictionary = runs[1][tick]
		for name in one:
			if one[name] != two.get(name):
				failed.append("the two runs part at physics frame %d: %s was %s, then %s" % [
					tick + 1, name, one[name], two.get(name)])
				return
	var moved := false
	for name in runs[0][0]:
		if runs[0][0][name] != runs[0][-1][name]:
			moved = true
	if not moved:
		failed.append("nothing the state kit names changed over the run, so its agreeing proves nothing")
