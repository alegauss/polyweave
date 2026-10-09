class_name PolyweaveLog
extends Node
## What a crash leaves behind (polyweave kit "crash", §PW361). Every line the game logs,
## and every error the engine raises, goes to user://polyweave_log/log.jsonl as one JSON
## object a line: its time, level, physics frame, current scene and words, rotated past
## MAX_KB into KEEP older files. An error also packs a capture beside it, in
## user://polyweave_log/captures/: the error with the script and line that raised it,
## the last LINES of the log, the state kit's snapshot and the determinism kit's seed
## where the game carries them. A run that ends without saying so (killed, frozen, a
## crash of the engine itself) leaves its marker behind, and the next launch packs what
## the log holds as an unclean exit.
##
## game.crash_read reads a capture back, from this machine's user:// or a file a person
## sends, and answers the first error, its script and line, and the state at the time.

const HERE := "res://addons/polyweave/crash/log.gd"
const PROJECT := "res://polyweave_crash.gd"
const DIR := "user://polyweave_log"
const STATE := "res://addons/polyweave/state/state.gd"
const RANDOM := "res://addons/polyweave/determinism/random.gd"
const DEFAULTS := {"MAX_KB": 256, "KEEP": 3, "LINES": 40, "CAPTURES": 5}

var declared := {}
## where the last capture went, as a file on this machine
var last_capture := ""
var _captured := 0
var _catcher: Logger

static var _shared: Node


## the one log, opened the first time: a project calls it first thing, so an unclean exit
## before it is packed and every error after it is caught
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweaveLog"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


static func declaration(project := PROJECT) -> Dictionary:
	var out := DEFAULTS.duplicate(true)
	if ResourceLoader.exists(project):
		var map := (load(project) as GDScript).get_script_constant_map()
		for key in map:
			out[key] = map[key]
	return out


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	declared = declaration()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR + "/captures"))
	if FileAccess.file_exists(DIR + "/running"):
		capture("unclean-exit", {"said": "the last run ended without closing its log"})
	_mark()
	_catcher = load("res://addons/polyweave/crash/catcher.gd").new(self)
	OS.add_logger(_catcher)


func _mark() -> void:
	var file := FileAccess.open(DIR + "/running", FileAccess.WRITE)
	file.store_string(str(OS.get_process_id()))
	file.close()


## the run ends as it should: the marker goes, so the next launch finds nothing to pack
func close() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(DIR + "/running"))
	if _catcher != null:
		OS.remove_logger(_catcher)
		_catcher = null


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		close()


func info(words: String) -> void:
	write("info", words)


func warn(words: String) -> void:
	write("warning", words)


func error(words: String) -> void:
	write("error", words)


## one line of the log, rotated when the file passes MAX_KB
func write(level: String, words: String, extra := {}) -> void:
	var path := DIR + "/log.jsonl"
	if FileAccess.file_exists(path) and FileAccess.open(path, FileAccess.READ).get_length() \
			> int(declared["MAX_KB"]) * 1024:
		_rotate()
	var file := FileAccess.open(path, FileAccess.READ_WRITE if FileAccess.file_exists(path)
		else FileAccess.WRITE)
	file.seek_end()
	var tree := get_tree() if is_inside_tree() else Engine.get_main_loop() as SceneTree
	var scene := tree.current_scene.scene_file_path if tree != null and tree.current_scene != null else ""
	var entry := {"t": Time.get_unix_time_from_system(), "level": level,
		"frame": Engine.get_physics_frames(), "scene": scene, "said": words}
	entry.merge(extra)
	file.store_line(JSON.stringify(entry))
	file.close()


func _rotate() -> void:
	var keep := int(declared["KEEP"])
	for i in range(keep - 1, 0, -1):
		var older := "%s/log.%d.jsonl" % [DIR, i]
		if FileAccess.file_exists(older):
			DirAccess.rename_absolute(ProjectSettings.globalize_path(older),
				ProjectSettings.globalize_path("%s/log.%d.jsonl" % [DIR, i + 1]))
	DirAccess.rename_absolute(ProjectSettings.globalize_path(DIR + "/log.jsonl"),
		ProjectSettings.globalize_path(DIR + "/log.1.jsonl"))


## the last lines the log holds, oldest first
func tail(count: int) -> Array:
	var path := DIR + "/log.jsonl"
	if not FileAccess.file_exists(path):
		return []
	var lines := FileAccess.get_file_as_string(path).strip_edges().split("\n")
	var out := []
	for line in lines.slice(maxi(0, lines.size() - count)):
		var parsed = JSON.parse_string(line)
		if parsed != null:
			out.append(parsed)
	return out


## an error the engine raised, logged and packed; called by the catcher
func caught(error: Dictionary) -> void:
	write("error", str(error.get("said", "")), {"script": error.get("script", ""),
		"line": error.get("line", 0)})
	if _captured < int(declared["CAPTURES"]):
		_captured += 1
		capture("error", error)


## the error, the log's last lines and the state at the time, as one file
func capture(reason: String, error: Dictionary) -> String:
	var packed := {"format": 1, "reason": reason, "t": Time.get_unix_time_from_system(),
		"error": error, "lines": tail(int(declared["LINES"]))}
	if reason != "unclean-exit" and ResourceLoader.exists(STATE):
		packed["state"] = load(STATE).snapshot()
	if ResourceLoader.exists(RANDOM):
		packed["seed"] = load(RANDOM).seed_of()
	var name := "%s/captures/%d-%s.json" % [DIR, Time.get_ticks_usec(), reason]
	var file := FileAccess.open(name, FileAccess.WRITE)
	file.store_string(JSON.stringify(packed, "\t"))
	file.close()
	last_capture = ProjectSettings.globalize_path(name)
	print("polyweave_crash: captured %s" % last_capture)
	return last_capture
