extends SceneTree
## The launch kit's proof, run in the game it lands in (§PW349): a press from each
## family skips the splash; the time from launch to the first scene is held to the
## project's budget; and a change to a large scene, loaded on a thread, keeps its frames
## under the frame budget at the 95th percentile. Budgets are the project's, in
## res://polyweave_launch.gd as LAUNCH_MS and FRAME_MS. Prints KIT PROVED, or
## KIT FAILED with why.

const Splash := preload("res://addons/polyweave/launch/splash.gd")
const Scenes := preload("res://addons/polyweave/launch/scenes.gd")
const BIG := "user://polyweave_launch_big.tscn"
const NODES := 4000

var failed := []
var launch_budget := 5000
var frame_budget := 100.0
var presses: Array[InputEvent] = []
var splash: Splash
var frame := 0
var stage := "skip"
var since := 0


func _initialize() -> void:
	if ResourceLoader.exists("res://polyweave_launch.gd"):
		var declared := (load("res://polyweave_launch.gd") as GDScript).get_script_constant_map()
		launch_budget = int(declared.get("LAUNCH_MS", launch_budget))
		frame_budget = float(declared.get("FRAME_MS", frame_budget))
	var key := InputEventKey.new()
	key.physical_keycode = KEY_SPACE
	var mouse := InputEventMouseButton.new()
	mouse.button_index = MOUSE_BUTTON_LEFT
	presses.append_array([key, mouse])
	for index in [JOY_BUTTON_A, JOY_BUTTON_B, JOY_BUTTON_START, JOY_BUTTON_RIGHT_SHOULDER]:
		var button := InputEventJoypadButton.new()
		button.button_index = index
		presses.append(button)
	for press in presses:
		press.set("pressed", true)
	_big_scene()


## a scene of many nodes, so its load and its instancing are worth measuring
func _big_scene() -> void:
	var top := Node2D.new()
	top.name = "Big"
	for i in NODES:
		var child := Sprite2D.new()
		child.name = "s%d" % i
		child.position = Vector2(i % 64, i / 64)
		top.add_child(child)
		child.owner = top
	var packed := PackedScene.new()
	packed.pack(top)
	ResourceSaver.save(packed, BIG)
	top.free()


func _splash(at: Array[String], held: Array[float], next := "") -> Splash:
	var made := Splash.new()
	made.logos = at
	made.seconds = held
	made.next_scene = next
	root.add_child(made)
	return made


## whether `seconds` have gone by since the stage began: frames run unbounded headless
func _late(seconds: int) -> bool:
	return Time.get_ticks_msec() - since > seconds * 1000


func _end(why := "") -> bool:
	if why != "":
		failed.append(why)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(BIG))
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	return true


func _process(_delta: float) -> bool:
	frame += 1
	match stage:
		"skip":
			if splash != null:
				var press: InputEvent = presses[0]
				root.push_input(press)
				if not splash.skipped:
					failed.append("a %s press did not skip the splash" % press.get_class())
				splash.queue_free()
				splash = null
				presses.remove_at(0)
				return false
			if presses.is_empty():
				stage = "launch"
				since = Time.get_ticks_msec()
				splash = _splash(["res://logo.png"], [0.3], "res://main.tscn")
				return false
			splash = _splash(["res://logo.png"], [30.0])
		"launch":
			var scenes := Scenes.shared() as Scenes
			if scenes.launch_ms < 0:
				return _end("the first scene never came in place") if _late(20) else false
			if scenes.launch_ms > launch_budget:
				failed.append("the first scene came after %d ms, over the budget of %d ms"
					% [scenes.launch_ms, launch_budget])
			if current_scene == null or current_scene.scene_file_path != "res://main.tscn":
				failed.append("the splash did not lead to main.tscn")
			stage = "big"
			since = Time.get_ticks_msec()
			scenes.go(BIG)
		"big":
			var scenes := Scenes.shared() as Scenes
			if scenes.busy():
				return _end("the large scene never came in place") if _late(60) else false
			var last: Dictionary = scenes.last
			if not last.get("ok", false) or current_scene == null or current_scene.name != "Big":
				return _end("the large scene was not put in place: %s" % [last])
			if current_scene.get_child_count() != NODES:
				failed.append("the large scene came with %d nodes of %d"
					% [current_scene.get_child_count(), NODES])
			if last["p95_ms"] > frame_budget:
				failed.append("the change to the large scene ran %.1f ms frames at the 95th percentile, over %.1f"
					% [last["p95_ms"], frame_budget])
			if last["frames"] < Scenes.SETTLE + 1:
				failed.append("the change was measured over %d frames" % last["frames"])
			return _end()
	return false
