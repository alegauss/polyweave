extends SceneTree
## The remap kit's proof, run in the game it lands in (§PW345): a rebind takes, a clash is
## swapped and never shared, a key leaves the pad's half alone, what was kept comes back
## after a restart, and a reset goes back to project.godot. It works on three actions
## of its own, declared as project.godot would declare them, so it holds in any game
## whatever actions the game has (§PW392), and the pad screen binds on the picture
## (§PW428). Prints KIT PROVED, or KIT FAILED with why.

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

	# A game's older file (§PW397): with no kit file yet, its bindings are taken once,
	# written to the kit's own file and said, and the older file is left as it was.
	var older_path := "user://polyweave_bindings_proof_older.cfg"
	var older := ConfigFile.new()
	older.set_value("controls", J, ["key:%d" % KEY_Q, "button:3"])
	older.set_value("controls", "deadzone", 0.4)
	older.save(older_path)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	var adopting := Bindings.new(actions, KEPT)
	adopting.from = [older_path, "controls"]
	adopting.load_kept()
	if adopting.current()[J] != ["key:%d" % KEY_Q, "button:3"]:
		failed.append("an older file's binding was not taken: %s" % [adopting.current()[J]])
	if not is_equal_approx(adopting.deadzone, 0.4):
		failed.append("an older file's deadzone was not taken")
	if adopting.said.is_empty() or not FileAccess.file_exists(KEPT):
		failed.append("taking an older file was not said, or not written to the kit's own")
	var later := Bindings.new(actions, KEPT)
	later.from = [older_path, "controls"]
	later.load_kept()
	if not later.said.is_empty():
		failed.append("the older file was taken again once the kit had its own")
	# Back to the game's own bindings for the screen's half of the proof.
	later.reset()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(older_path))

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
	if (menu.bindings.current()[J] as Array).has("button:3"):
		failed.append("the screen bound on the press, before it was let go")
	var let_go := north.duplicate()
	let_go.pressed = false
	menu._input(let_go)
	var on_pad := menu.bindings.current()[J] as Array
	if not on_pad.has("button:3") or on_pad.has("button:0") or on_pad.has("key:%d" % KEY_Q):
		failed.append("the screen listening on the pad bound jump to %s" % [on_pad])
	# A stick binds the way it was pushed, once it comes back (§PW432).
	menu._listen(F, true)
	for value in [-0.9, -0.4, 0.1]:
		var stick := InputEventJoypadMotion.new()
		stick.axis = JOY_AXIS_LEFT_X
		stick.axis_value = value
		menu._input(stick)
	if not (menu.bindings.current()[F] as Array).has("axis:0:-1"):
		failed.append("a stick pushed left bound fire to %s" % [menu.bindings.current()[F]])
	# A press held past hold_to_cancel cancels, and binds nothing when let go.
	var before: Array = menu.bindings.current()[P]
	menu._listen(P, true)
	var held := InputEventJoypadButton.new()
	held.button_index = JOY_BUTTON_X
	held.pressed = true
	menu._input(held)
	menu._process(menu.hold_to_cancel + 0.1)
	var held_go := held.duplicate()
	held_go.pressed = false
	menu._input(held_go)
	if menu.bindings.current()[P] != before or menu._listening != "":
		failed.append("a held press bound pause to %s" % [menu.bindings.current()[P]])
	# Its words and each action's label come from the game's table, English where it
	# has no row.
	var table := Translation.new()
	table.locale = TranslationServer.get_locale()
	table.add_message("REMAP_RESET", "Restaurar")
	table.add_message("PROOF_JUMP", "Pular")
	TranslationServer.add_translation(table)
	menu.bindings.labels = {J: "PROOF_JUMP"}
	if menu.said("reset") != "Restaurar" or menu.said("pad") != "Pad":
		failed.append("the screen's words ignore the table: %s, %s"
			% [menu.said("reset"), menu.said("pad")])
	if menu.bindings.label(J) != "Pular" or menu.bindings.label(F) != F:
		failed.append("an action's label reads %s" % menu.bindings.label(J))
	TranslationServer.remove_translation(table)
	menu.bindings.reset()
	_pad_screen(menu.open_pad())
	menu.bindings.reset()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	return true


## The pad screen (§PW428): every layout names each of its places, a real press lights
## its place, a rebind on the picture takes and swaps, and cancel closes it.
func _pad_screen(screen: CanvasLayer) -> void:
	var failed := _failed
	if not screen.is_node_ready():
		failed.append("the pad screen did not open")
		return
	for layout in screen.LAYOUTS:
		var slots: Array = screen.spots(layout)
		var codes := {}
		for slot: Dictionary in slots:
			codes[slot["code"]] = true
			if Bindings.decode(slot["code"]) == null or screen.glyph(slot["code"], layout) == "":
				failed.append("the %s pad has a place no glyph names: %s" % [layout, slot["code"]])
		if slots.is_empty() or codes.size() != slots.size():
			failed.append("the %s pad's places are missing or repeated" % layout)
		if screen.picture(layout) == null:
			failed.append("the %s pad has no picture" % layout)
	var north := InputEventJoypadButton.new()
	north.button_index = JOY_BUTTON_Y
	north.pressed = true
	screen._input(north)
	if not screen.lit("button:3"):
		failed.append("pressing Y did not light its place on the pad")
	var south := -1
	for i in screen.slots.size():
		if screen.slots[i]["code"] == "button:0":
			south = i
	screen.picked = south
	screen.press("ui_accept")
	if screen.choosing != J:
		failed.append("choosing on jump's button offered %s, not jump" % screen.choosing)
	screen.press("ui_right")
	screen.press("ui_accept")
	var now: Dictionary = screen.bindings.current()
	if not (now[F] as Array).has("button:0") or (now[J] as Array).has("button:0") \
			or not (now[J] as Array).has("axis:5:1"):
		failed.append("binding fire on the picture did not swap with jump: %s" % [now])
	screen.press("ui_cancel")
	if not screen.is_queued_for_deletion():
		failed.append("cancel did not close the pad screen")
