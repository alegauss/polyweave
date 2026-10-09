extends SceneTree
## The credits kit's proof, run in the game it lands in (§PW350): every record in the
## project whose licence requires a credit has that credit on the screen; the screen
## lists nothing the file provenance.credits wrote does not hold; it scrolls at its
## rate; and a press from every family ends it. Prints KIT PROVED, or KIT FAILED with why.

const Credits := preload("res://addons/polyweave/credits/credits.gd")
const FILE := "res://credits.json"

var failed := []
var screen: Credits
var presses: Array[InputEvent] = []
var stage := "rate"
var since := 0


## every credit a record in the project carries, walked from res://
func _owed(dir := "res://") -> Array[String]:
	var out: Array[String] = []
	var here := DirAccess.open(dir)
	if here == null:
		return out
	for name in here.get_directories():
		if not name.begins_with(".") and name != "addons":
			out.append_array(_owed(dir.path_join(name)))
	for name in here.get_files():
		if name.ends_with(".prov.json"):
			var record: Variant = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join(name)))
			if record is Dictionary and str(record.get("credit", "")) != "":
				out.append(str(record["credit"]))
			if record is Dictionary:
				for one in record.get("instruments", []):
					if str(one.get("credit", "")) != "":
						out.append(str(one["credit"]))
	return out


func _initialize() -> void:
	if not FileAccess.file_exists(FILE):
		failed.append("%s is not there: write it with provenance.credits out=credits.json" % FILE)
		return
	var held: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(FILE))
	screen = _screen()
	for credit in _owed():
		if not screen.lines.has(credit):
			failed.append("%s is owed a credit the screen does not show" % credit)
	var expected := (held.get("people", []) as Array).size() + (held.get("owed", []) as Array).size()
	if screen.lines.size() != expected:
		failed.append("the screen shows %d lines, the file holds %d" % [screen.lines.size(), expected])
	var key := InputEventKey.new()
	key.physical_keycode = KEY_ENTER
	var mouse := InputEventMouseButton.new()
	mouse.button_index = MOUSE_BUTTON_LEFT
	presses.append_array([key, mouse])
	for index in [JOY_BUTTON_A, JOY_BUTTON_B, JOY_BUTTON_START]:
		var button := InputEventJoypadButton.new()
		button.button_index = index
		presses.append(button)
	for press in presses:
		press.set("pressed", true)
	since = Time.get_ticks_msec()


func _screen() -> Credits:
	var made := Credits.new()
	made.file = FILE
	made.rate = 200.0
	root.add_child(made)
	made.fill()
	return made


func _process(_delta: float) -> bool:
	if screen == null:
		return _end()
	match stage:
		"rate":
			var seconds := (Time.get_ticks_msec() - since) / 1000.0
			if seconds < 0.5:
				return false
			var expected := screen.rate * seconds
			if absf(screen._offset - expected) > expected * 0.3:
				failed.append("the screen scrolled %.0f px in %.2f s, not %.0f" % [screen._offset, seconds, expected])
			stage = "skip"
		"skip":
			if presses.is_empty():
				return _end()
			var press: InputEvent = presses.pop_front()
			screen.queue_free()
			screen = _screen()
			var ended := [false]
			screen.finished.connect(func() -> void: ended[0] = true)
			root.push_input(press)
			if not ended[0]:
				failed.append("a %s press did not end the credits" % press.get_class())
	return false


func _end() -> bool:
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	return true
