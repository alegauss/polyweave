class_name PolyweaveScenes
extends Node
## Every change of scene through one service (polyweave kit "launch", §PW349): the
## scene is loaded on a thread (ResourceLoader.load_threaded_request) while a loading
## screen is up and the game keeps drawing, then put in place. Each change measures
## its frame times, so a hitch is a number: `last` holds the path, whether it loaded,
## its seconds, its frames, the 95th percentile and the longest frame in milliseconds.
## `launch_ms` is the time from the engine's start to the first scene put in place.

signal changed(path: String, ok: bool)

const HERE := "res://addons/polyweave/launch/scenes.gd"
## frames still measured after the scene is put in place, where it is instanced
const SETTLE := 2

## the project's loading screen; a method `progress(share)` on it is told how far the
## load has come. A plain dark screen where unset: the look is the project's.
@export var loading_scene := ""

var launch_ms := -1
var last := {}
var _path := ""
var _requested := {}
var _frames := PackedFloat64Array()
var _tick := 0
var _started := 0
var _settle := -1
var _ok := false
var _layer: CanvasLayer
var _screen: Node

static var _shared: Node


## the one service every change of scene goes through, made the first time
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweaveScenes"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


## start loading `path` now, so a later `go` finds it ready
func prefetch(path: String) -> bool:
	if _requested.has(path):
		return true
	if ResourceLoader.load_threaded_request(path) != OK:
		return false
	_requested[path] = true
	return true


## change to the scene at `path` behind the loading screen; false while one is under way
## or where the path cannot be loaded
func go(path: String) -> bool:
	if _path != "" or not prefetch(path):
		return false
	_path = path
	_ok = false
	_settle = -1
	_frames.clear()
	_tick = Time.get_ticks_usec()
	_started = _tick
	_show()
	return true


func busy() -> bool:
	return _path != ""


func _show() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = 100
	if loading_scene != "" and ResourceLoader.exists(loading_scene):
		_screen = (load(loading_scene) as PackedScene).instantiate()
	else:
		var plain := ColorRect.new()
		plain.color = Color.BLACK
		plain.set_anchors_preset(Control.PRESET_FULL_RECT)
		_screen = plain
	_layer.add_child(_screen)
	add_child(_layer)


func _process(_delta: float) -> void:
	if _path == "":
		return
	var now := Time.get_ticks_usec()
	_frames.append((now - _tick) / 1000.0)
	_tick = now
	if _settle >= 0:
		_settle -= 1
		if _settle < 0:
			_finish()
		return
	var share := []
	var status := ResourceLoader.load_threaded_get_status(_path, share)
	if _screen != null and _screen.has_method("progress") and not share.is_empty():
		_screen.progress(share[0])
	if status == ResourceLoader.THREAD_LOAD_LOADED:
		var packed := ResourceLoader.load_threaded_get(_path) as PackedScene
		_requested.erase(_path)
		_ok = packed != null and get_tree().change_scene_to_packed(packed) == OK
		_settle = SETTLE
	elif status in [ResourceLoader.THREAD_LOAD_FAILED, ResourceLoader.THREAD_LOAD_INVALID_RESOURCE]:
		_requested.erase(_path)
		push_error("scenes: %s could not be loaded" % _path)
		_finish()


func _finish() -> void:
	if _layer != null:
		_layer.queue_free()
		_layer = null
	last = {
		"path": _path, "ok": _ok, "seconds": (Time.get_ticks_usec() - _started) / 1e6,
		"frames": _frames.size(), "p95_ms": percentile(_frames, 0.95),
		"max_ms": percentile(_frames, 1.0),
	}
	if _ok and launch_ms < 0:
		launch_ms = Time.get_ticks_msec()
	var path := _path
	_path = ""
	changed.emit(path, _ok)


## the value `share` of the way up the sorted values: a percentile, never a mean, so one
## long hitch is not averaged away by a hundred short frames
static func percentile(values: PackedFloat64Array, share: float) -> float:
	if values.is_empty():
		return 0.0
	var sorted := values.duplicate()
	sorted.sort()
	return sorted[clampi(ceili(share * sorted.size()) - 1, 0, sorted.size() - 1)]
