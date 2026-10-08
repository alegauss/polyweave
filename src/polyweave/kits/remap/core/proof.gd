extends SceneTree
## The remap kit's proof, run in the game it lands in (§PW345): a rebind takes, a clash is
## swapped and never shared, a key leaves the pad's half alone, what was kept comes back
## after a restart, and a reset goes back to project.godot. Prints KIT PROVED, or
## KIT FAILED with why.

const Bindings := preload("res://addons/polyweave/remap/bindings.gd")
const KEPT := "user://polyweave_bindings_proof.cfg"

var _failed := []
var _menu: Node
var _fire_key := ""


func _keys(code: String) -> bool:
	return Bindings.on_keys(code)


func _initialize() -> void:
	var failed := _failed
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	var actions := ["jump", "fire", "pause"]
	var bindings := Bindings.new(actions, KEPT)
	var start := bindings.current()
	for action in actions:
		if (start[action] as Array).is_empty():
			failed.append("%s starts with no binding" % action)

	var fire_key: String = start["fire"].filter(_keys)[0]
	var jump_pad: Array = start["jump"].filter(func(c: String) -> bool: return not Bindings.on_keys(c))
	bindings.rebind("jump", Bindings.decode(fire_key))
	var now := bindings.current()
	if not (now["jump"] as Array).has(fire_key):
		failed.append("jump was not rebound to fire's key")
	if (now["fire"] as Array).has(fire_key):
		failed.append("fire still shares its key with jump")
	if not (now["fire"] as Array).has(start["jump"].filter(_keys)[0]):
		failed.append("fire did not take jump's old key in the swap")
	if now["jump"].filter(func(c: String) -> bool: return not Bindings.on_keys(c)) != jump_pad:
		failed.append("rebinding jump's key changed its pad binding")

	if bindings.rebind("pause", InputEventAction.new()):
		failed.append("an event no binding can hold was taken")

	bindings.set_deadzone(0.3)
	bindings.set_invert_vertical(true)
	var kept := now.duplicate(true)
	bindings.reset()
	bindings.apply("jump", kept["jump"])
	bindings.apply("fire", kept["fire"])
	bindings.save()
	for action in actions:
		InputMap.action_erase_events(action)
	var restarted := Bindings.new(actions, KEPT)
	restarted.load_kept()
	if restarted.current() != kept:
		failed.append("the bindings did not come back after a restart: %s" % restarted.current())
	if not is_equal_approx(restarted.deadzone, 0.3) or not restarted.invert_vertical:
		failed.append("the deadzone or the inverted vertical did not come back")
	if not is_equal_approx(InputMap.action_get_deadzone("jump"), 0.3):
		failed.append("the kept deadzone is not in the InputMap")

	restarted.reset()
	if restarted.current() != start:
		failed.append("a reset did not go back to the game's own bindings")
	var again := Bindings.new(actions, KEPT)
	again.load_kept()
	if again.current() != start:
		failed.append("a reset was not kept")

	_fire_key = fire_key
	_menu = load("res://addons/polyweave/remap/remap_menu.gd").new()
	_menu.actions.assign(actions)
	root.add_child(_menu)


## the screen is ready only once the tree runs, so its half of the proof waits a frame
func _process(_delta: float) -> bool:
	if _menu == null or not _menu.is_node_ready():
		return false
	var menu := _menu
	var fire_key := _fire_key
	var failed := _failed
	menu.bindings = Bindings.new(menu.bindings.actions, KEPT)
	var said: String = menu.take("pause", Bindings.decode(fire_key))
	if not said.contains("took it from"):
		failed.append("the screen did not say the swap: %s" % said)
	menu._listen("jump", true)
	var stray := InputEventKey.new()
	stray.physical_keycode = KEY_Q
	stray.pressed = true
	menu._input(stray)
	var north := InputEventJoypadButton.new()
	north.button_index = JOY_BUTTON_Y
	north.pressed = true
	menu._input(north)
	var on_pad := menu.bindings.current()["jump"] as Array
	if not on_pad.has("button:3") or on_pad.has("button:0") or on_pad.has("key:%d" % KEY_Q):
		failed.append("the screen listening on the pad bound jump to %s" % [on_pad])
	menu.bindings.reset()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	return true
