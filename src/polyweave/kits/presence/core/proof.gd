extends SceneTree
## The presence kit's proof, run in the game it lands in (§PW356), by simulated events.
## A PlayStation pad leaving pauses the game, stops its ticking, names its player and
## draws the PlayStation confirm; it coming back resumes. Leaving again, another pad's
## wrong button keeps the game held and its confirm resumes it, by an Xbox pad's
## convention, then by a Switch pad's. A game already paused by its own menu stays paused
## when the pad returns. Losing focus pauses, regaining it does not resume, and a confirm
## does; with PAUSE_ON_FOCUS off, losing focus pauses nothing. Prints KIT PROVED, or KIT
## FAILED with why.

const Presence := preload("res://addons/polyweave/presence/presence.gd")

var failed := []
var presence: Presence
var ticker: Node


func _initialize() -> void:
	presence = Presence.shared()
	var counting := GDScript.new()
	counting.source_code = "extends Node\nvar ticks := 0\nfunc _process(_d):\n\tticks += 1\n"
	counting.reload()
	ticker = Node.new()
	ticker.set_script(counting)
	root.add_child(ticker)


func _pad(device: int, index: int) -> void:
	var event := InputEventJoypadButton.new()
	event.device = device
	event.button_index = index as JoyButton
	event.pressed = true
	root.push_input(event)
	var released := event.duplicate() as InputEventJoypadButton
	released.pressed = false
	root.push_input(released)


var stage := 0
var frames := 0
var ticks := 0


func _process(_delta: float) -> bool:
	if not presence.is_inside_tree():
		return false
	match stage:
		0:
			presence.named(0, "DualSense Wireless Controller")
			presence.named(1, "Xbox Wireless Controller")
			presence.named(2, "Nintendo Switch Pro Controller")
			Input.joy_connection_changed.emit(0, false)
			if not paused or not presence.visible:
				failed.append("a pad leaving did not pause the game")
			if presence.family != "playstation":
				failed.append("a PlayStation pad leaving drew the %s family" % presence.family)
			if not str(presence.confirm_icon.get_meta("path", "")).ends_with("playstation/south_64.png") \
					or presence.confirm_icon.texture == null:
				failed.append("a PlayStation pad leaving drew no PlayStation confirm")
			if not presence.message.text.contains("1"):
				failed.append("a pad leaving said %s, not whose it was" % presence.message.text)
			ticks = ticker.ticks
			stage = 1
		1:
			frames += 1
			if frames < 3:
				return false
			if ticker.ticks != ticks:
				failed.append("the game ticked %d times while the pad was gone" % (ticker.ticks - ticks))
			Input.joy_connection_changed.emit(0, true)
			if paused or presence.visible:
				failed.append("the pad coming back did not resume the game")
			_others()
			_own_pause()
			_focus()
			print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
			return true
	return false


## another pad's wrong button holds, its own confirm resumes, in two conventions
func _others() -> void:
	for pair in [[1, JOY_BUTTON_B, JOY_BUTTON_A, "an Xbox"], [2, JOY_BUTTON_A, JOY_BUTTON_B, "a Switch"]]:
		Input.joy_connection_changed.emit(0, false)
		_pad(pair[0], pair[1])
		if not paused:
			failed.append("%s pad's back button resumed the game" % pair[3])
		_pad(pair[0], pair[2])
		if paused:
			failed.append("%s pad's confirm did not resume the game" % pair[3])
		presence.resume()


func _own_pause() -> void:
	paused = true
	Input.joy_connection_changed.emit(0, false)
	Input.joy_connection_changed.emit(0, true)
	if not paused:
		failed.append("a pad coming back unpaused a game its own menu had paused")
	paused = false


func _focus() -> void:
	presence.notification(NOTIFICATION_APPLICATION_FOCUS_OUT)
	if not paused or presence.why != "focus":
		failed.append("losing focus did not pause the game")
	presence.notification(NOTIFICATION_APPLICATION_FOCUS_IN)
	if not paused:
		failed.append("regaining focus resumed the game before the player said so")
	_pad(1, JOY_BUTTON_A)
	if paused:
		failed.append("a confirm after focus came back did not resume the game")
	presence.pause_on_focus = false
	presence.notification(NOTIFICATION_APPLICATION_FOCUS_OUT)
	if paused:
		failed.append("with PAUSE_ON_FOCUS off, losing focus paused the game")
	presence.pause_on_focus = bool(presence.declared["PAUSE_ON_FOCUS"])
	paused = false
