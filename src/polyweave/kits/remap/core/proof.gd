extends SceneTree
## The remap kit's proof, run in the game it lands in (§PW345): a rebind takes, a clash is
## swapped and never shared, a key leaves the pad's half alone, what was kept comes back
## after a restart, and a reset goes back to project.godot. It works on three actions
## of its own, declared as project.godot would declare them, so it holds in any game
## whatever actions the game has (§PW392). Prints KIT PROVED, or KIT FAILED with why.

const Bindings := preload("res://addons/polyweave/remap/bindings.gd")
const KEPT := "user://polyweave_bindings_proof.cfg"
const J := "proof_jump"
const F := "proof_fire"
const P := "proof_pause"

var _failed := []
var _menu: Node
var _fire_key := ""


func _keys(code: String) -> bool:
	return Bindings.on_keys(code)


## the proof's three actions, each bound on both halves as project.godot declares them,
## so a rebind can clash on the keys' half while the pad's stays put
func _declare() -> void:
	var space := InputEventKey.new()
	space.physical_keycode = KEY_SPACE
	var south := InputEventJoypadButton.new()
	south.button_index = JOY_BUTTON_A
	south.device = -1
	var click := InputEventMouseButton.new()
	click.button_index = MOUSE_BUTTON_LEFT
	var trigger := InputEventJoypadMotion.new()
	trigger.axis = JOY_AXIS_TRIGGER_RIGHT
	trigger.axis_value = 1.0
	trigger.device = -1
	var escape := InputEventKey.new()
	escape.physical_keycode = KEY_ESCAPE
	var back := InputEventJoypadButton.new()
	back.button_index = JOY_BUTTON_BACK
	back.device = -1
	for pair in [[J, [space, south]], [F, [click, trigger]], [P, [escape, back]]]:
		ProjectSettings.set_setting("input/" + pair[0], {"deadzone": 0.5, "events": pair[1]})
		if not InputMap.has_action(pair[0]):
			InputMap.add_action(pair[0])
		for event in pair[1]:
			InputMap.action_add_event(pair[0], event)


func _initialize() -> void:
	var failed := _failed
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	_declare()
	var actions := [J, F, P]
	var bindings := Bindings.new(actions, KEPT)
	var start := bindings.current()
	for action in actions:
		if (start[action] as Array).is_empty():
			failed.append("%s starts with no binding" % action)

	var fire_key: String = start[F].filter(_keys)[0]
	var jump_pad: Array = start[J].filter(func(c: String) -> bool: return not Bindings.on_keys(c))
	bindings.rebind(J, Bindings.decode(fire_key))
	var now := bindings.current()
	if not (now[J] as Array).has(fire_key):
		failed.append("jump was not rebound to fire's key")
	if (now[F] as Array).has(fire_key):
		failed.append("fire still shares its key with jump")
	if not (now[F] as Array).has(start[J].filter(_keys)[0]):
		failed.append("fire did not take jump's old key in the swap")
	if now[J].filter(func(c: String) -> bool: return not Bindings.on_keys(c)) != jump_pad:
		failed.append("rebinding jump's key changed its pad binding")

	var east := InputEventJoypadButton.new()
	east.button_index = JOY_BUTTON_B
	bindings.rebind(J, east)
	var from_pad_one := InputEventJoypadButton.new()
	from_pad_one.device = 1
	from_pad_one.button_index = JOY_BUTTON_B
	if not InputMap.event_is_action(from_pad_one, J):
		failed.append("a pad binding rebound answers pad 0 alone, not a player on pad 1")
	bindings.apply(J, now[J])

	if bindings.rebind(P, InputEventAction.new()):
		failed.append("an event no binding can hold was taken")

	bindings.set_deadzone(0.3)
	bindings.set_invert_vertical(true)
	var kept := now.duplicate(true)
	bindings.reset()
	bindings.apply(J, kept[J])
	bindings.apply(F, kept[F])
	bindings.save()
	for action in actions:
		InputMap.action_erase_events(action)
	var restarted := Bindings.new(actions, KEPT)
	restarted.load_kept()
	if restarted.current() != kept:
		failed.append("the bindings did not come back after a restart: %s" % restarted.current())
	if not is_equal_approx(restarted.deadzone, 0.3) or not restarted.invert_vertical:
		failed.append("the deadzone or the inverted vertical did not come back")
	if not is_equal_approx(InputMap.action_get_deadzone(J), 0.3):
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
	var said: String = menu.take(P, Bindings.decode(fire_key))
	if not said.contains("took it from"):
		failed.append("the screen did not say the swap: %s" % said)
	menu._listen(J, true)
	var stray := InputEventKey.new()
	stray.physical_keycode = KEY_Q
	stray.pressed = true
	menu._input(stray)
	var north := InputEventJoypadButton.new()
	north.button_index = JOY_BUTTON_Y
	north.pressed = true
	menu._input(north)
	var on_pad := menu.bindings.current()[J] as Array
	if not on_pad.has("button:3") or on_pad.has("button:0") or on_pad.has("key:%d" % KEY_Q):
		failed.append("the screen listening on the pad bound jump to %s" % [on_pad])
	menu.bindings.reset()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	return true
