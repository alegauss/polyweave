extends SceneTree
## The access kit's proof, run in the game it lands in (§PW355). Every row of the
## accessibility tab reads back what it sets. At the largest text scale the project's
## screens (SCREENS, or the main scene) are laid out, and every visible Label and Button
## grows with the scale and still fits its control. The declared shake run (SHAKE_RUN)
## keeps every camera's offset at zero with shake off, and moves one with shake on, so
## the run is shown to shake at all. With hold or toggle on, an action turns on at one
## press and off at the next, and with it off it is held only while pressed. Each pair
## of COLOUR_PAIRS is drawn as a player with each deficiency sees it with its correction
## on, a box of one colour in a ring of the other, and printed as a KIT CONTRAST line,
## which polyweave holds to PAIR_DELTA_E with measure.contrast. Prints KIT PROVED, or
## KIT FAILED with why.

const Access := preload("res://addons/polyweave/access/access.gd")
const Options := preload("res://addons/polyweave/access/options.gd")
const Filters := preload("res://addons/polyweave/access/filters.gd")
const PROBE := "polyweave_access_probe"
const SEEN := "res://.polyweave/kits/access"
## each pair's swatch, and the box of the first colour inside it
const SWATCH := 120
const BOX := 40

var failed := []
var access: Access
var stage := "rows"
var screens := []
var frames := 0
var since := 0
var run: Node
var moved := false
var still := true


func _initialize() -> void:
	access = Access.shared()


func _process(_delta: float) -> bool:
	match stage:
		"rows":
			if access.is_inside_tree():
				_rows()
				_toggle()
				_pairs()
				_scaled()
		"scale":
			frames += 1
			if frames >= 3:
				_fits()
				_shake_run(false)
		"shake_off", "shake_on":
			_watch()
		"done":
			print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
			return true
	return false


func _rows() -> void:
	for row in Options.options():
		var other: Variant = (not row["default"]) if row["default"] is bool \
			else row["choices"][-1]
		row["apply"].call(other)
		if row["read"].call() != other:
			failed.append("the %s row set %s and read back %s" % [row["key"], other, row["read"].call()])
		row["apply"].call(row["default"])


## each declared pair as each deficiency sees it, corrected, for measure.contrast
func _pairs() -> void:
	var pairs: Array = access.declared["COLOUR_PAIRS"]
	if pairs.is_empty():
		return
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SEEN))
	for deficiency in Filters.DEFICIENCIES:
		var image := Image.create(SWATCH * pairs.size(), SWATCH, false, Image.FORMAT_RGB8)
		var targets := []
		for i in pairs.size():
			var left := i * SWATCH
			var inset := (SWATCH - BOX) / 2
			image.fill_rect(Rect2i(left, 0, SWATCH, SWATCH), Filters.seen(Color(pairs[i][1]), deficiency))
			image.fill_rect(Rect2i(left + inset, inset, BOX, BOX), Filters.seen(Color(pairs[i][0]), deficiency))
			targets.append({"box": [left + inset, inset, left + inset + BOX, inset + BOX]})
		var picture := "%s/%s.png" % [SEEN, deficiency]
		var listed := "%s/%s.json" % [SEEN, deficiency]
		image.save_png(ProjectSettings.globalize_path(picture))
		var file := FileAccess.open(ProjectSettings.globalize_path(listed), FileAccess.WRITE)
		file.store_string(JSON.stringify(targets))
		file.close()
		print("KIT CONTRAST %s %s delta_e_min %.2f 1000" % [picture.trim_prefix("res://"),
			listed.trim_prefix("res://"), float(access.declared["PAIR_DELTA_E"])])


func _press(action: String, pressed: bool) -> void:
	# the state at once, and the event to the service, since a parsed event waits for
	# the frame to flush and would reach it a second time then
	if pressed:
		Input.action_press(action)
	else:
		Input.action_release(action)
	var event := InputEventAction.new()
	event.action = action
	event.pressed = pressed
	access._input(event)


func _toggle() -> void:
	InputMap.add_action(PROBE)
	access.set_toggling(false)
	_press(PROBE, true)
	var while_pressed := access.held(PROBE)
	_press(PROBE, false)
	if not while_pressed or access.held(PROBE):
		failed.append("with toggle off, an action is not held exactly while pressed")
	access.set_toggling(true)
	_press(PROBE, true)
	_press(PROBE, false)
	var after_one := access.held(PROBE)
	_press(PROBE, true)
	_press(PROBE, false)
	if not after_one or access.held(PROBE):
		failed.append("with toggle on, an action does not turn on at one press and off at the next")
	access.set_toggling(false)
	InputMap.erase_action(PROBE)


## the project's screens at the largest scale, two frames on so they are laid out
func _scaled() -> void:
	var scales: Array = access.declared["SCALES"]
	access.set_text_scale(float(scales.max()))
	var paths: Array = access.declared["SCREENS"]
	if paths.is_empty():
		var main := str(ProjectSettings.get_setting("application/run/main_scene", ""))
		if main != "":
			paths = [main]
	for path in paths:
		var packed := load(path) as PackedScene
		if packed == null:
			failed.append("the screen %s does not load" % path)
			continue
		var screen := packed.instantiate()
		root.add_child(screen)
		screens.append(screen)
	stage = "scale"


func _fits() -> void:
	var largest := float(access.declared["SCALES"].max())
	var texts := []
	for screen in screens:
		_texts(screen, texts)
	for node: Control in texts:
		var size := node.get_theme_font_size("font_size")
		if largest > 1.0 and size <= access.base_size():
			failed.append("%s draws at %d px at %d%%: it sets a size of its own, so the text scale never reaches it" % [
				node.get_path(), size, int(largest * 100)])
		for unfit in _unfit(node, node.tr(node.text)):
			failed.append("at %d%% %s %s" % [int(largest * 100), node.get_path(), unfit])
	for screen in screens:
		screen.queue_free()
	access.set_text_scale(1.0)


func _texts(node: Node, out: Array) -> void:
	if (node is Label or node is Button) and (node as CanvasItem).is_visible_in_tree() \
			and str(node.text) != "":
		out.append(node)
	for child in node.get_children():
		_texts(child, out)


## what keeps a line from fitting its control as laid out: game.text_fit's measure
func _unfit(node: Control, shown: String) -> Array:
	var out := []
	var font: Font = node.get_theme_font("font")
	var size: int = node.get_theme_font_size("font_size")
	var widest := 0.0
	for line in shown.split("\n"):
		widest = maxf(widest, font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x)
	var wraps := node is Label and (node as Label).autowrap_mode != TextServer.AUTOWRAP_OFF
	if not wraps and widest > node.size.x + 0.5:
		out.append("is %d px wide in a %d px box" % [widest, node.size.x])
	if node is Label and (node as Label).get_line_count() > (node as Label).get_visible_line_count():
		out.append("shows %d of its %d lines" % [(node as Label).get_visible_line_count(),
			(node as Label).get_line_count()])
	var parent := node.get_parent()
	if parent is Control and not parent is ScrollContainer:
		var outer := (parent as Control).get_global_rect()
		if outer.size.x > 0 and not outer.grow(0.5).encloses(node.get_global_rect()):
			out.append("leaves its container %s" % parent.get_path())
	return out


func _shake_run(on: bool) -> void:
	var path := str(access.declared["SHAKE_RUN"])
	if path == "":
		stage = "done"
		return
	var packed := load(path) as PackedScene
	if packed == null:
		failed.append("the shake run %s does not load" % path)
		stage = "done"
		return
	access.shaking = on
	moved = false
	run = packed.instantiate()
	root.add_child(run)
	since = Time.get_ticks_msec()
	stage = "shake_on" if on else "shake_off"


func _watch() -> void:
	for camera in _cameras(run, []):
		var offset: Vector2 = camera.offset if camera is Camera2D \
			else Vector2(camera.h_offset, camera.v_offset)
		if offset != Vector2.ZERO:
			moved = true
			if stage == "shake_off":
				failed.append("with shake off, %s moved to %s" % [camera.get_path(), offset])
				still = false
				_end_run()
				return
	if (Time.get_ticks_msec() - since) / 1000.0 < float(access.declared["RUN_SECONDS"]):
		return
	if stage == "shake_on" and not moved:
		failed.append("the shake run never moved a camera, so switching shake off proves nothing")
	_end_run()


func _end_run() -> void:
	run.queue_free()
	access.shaking = true
	if stage == "shake_off" and still:
		_shake_run(true)
	else:
		stage = "done"


func _cameras(node: Node, out: Array) -> Array:
	if node is Camera2D or node is Camera3D:
		out.append(node)
	for child in node.get_children():
		_cameras(child, out)
	return out
