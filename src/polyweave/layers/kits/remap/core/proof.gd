extends SceneTree
## The remap kit's proof, run in the game it lands in (§PW345): a rebind takes, a clash is
## swapped and never shared, a key leaves the pad's half alone, what was kept comes back
## after a restart, and a reset goes back to project.godot. It works on three actions
## of its own, declared as project.godot would declare them, so it holds in any game
## whatever actions the game has (§PW392), and the pad screen binds on the picture
## (§PW428). Prints KIT PROVED, or KIT FAILED with why.

const _PwBindings := preload("res://addons/polyweave/remap/bindings.gd")
const _PwPrompts := preload("res://addons/polyweave/prompts/prompts.gd")
const J := "proof_jump"
const F := "proof_fire"
const P := "proof_pause"
## The proof reads the screen's words in a language of its own (§PW537), as the prompts
## proof does (§PW485): a game whose table says the swap in Portuguese, on a machine set
## to Portuguese, is a game with words, not a broken screen.
const PROOF_LOCALE := "zz"

var _failed := []
var _game_locale := ""
## A folder of this run's own (§PW523): Godot names user:// after the project, so two
## proofs at once in fixtures of one name wrote the same fixed files.
var _run := ""
var _kept := ""
var _menu: Node
var _fire_key := ""


func _keys(code: String) -> bool:
	return _PwBindings.on_keys(code)


## the engine errors logged while it listens, each as its rationale says it
class _Errors extends Logger:
	var said: Array[String] = []

	func _log_error(_function: String, _file: String, _line: int, code: String,
			rationale: String, _editor_notify: bool, _error_type: int,
			_script_backtrace: Array[ScriptBacktrace]) -> void:
		said.append(rationale if rationale != "" else code)


## a key pressed, as the screens read one
func _key(keycode: Key) -> InputEventKey:
	var key := InputEventKey.new()
	key.physical_keycode = keycode
	key.pressed = true
	return key


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
	_game_locale = TranslationServer.get_locale()
	TranslationServer.set_locale(PROOF_LOCALE)
	_run = "user://polyweave_proof/remap_%d_%d" % [OS.get_process_id(), Time.get_ticks_usec()]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(_run))
	_kept = _run + "/bindings.cfg"
	_declare()
	var actions := [J, F, P]
	var bindings := _PwBindings.new(actions, _kept)
	var start := bindings.current()
	for action in actions:
		if (start[action] as Array).is_empty():
			failed.append("%s starts with no binding" % action)

	var fire_key: String = start[F].filter(_keys)[0]
	var jump_pad: Array = start[J].filter(func(c: String) -> bool: return not _PwBindings.on_keys(c))
	bindings.rebind(J, _PwBindings.decode(fire_key))
	var now := bindings.current()
	if not (now[J] as Array).has(fire_key):
		failed.append("jump was not rebound to fire's key")
	if (now[F] as Array).has(fire_key):
		failed.append("fire still shares its key with jump")
	if not (now[F] as Array).has(start[J].filter(_keys)[0]):
		failed.append("fire did not take jump's old key in the swap")
	if now[J].filter(func(c: String) -> bool: return not _PwBindings.on_keys(c)) != jump_pad:
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
	var restarted := _PwBindings.new(actions, _kept)
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
	var again := _PwBindings.new(actions, _kept)
	again.load_kept()
	if again.current() != start:
		failed.append("a reset was not kept")

	# A game's older file (§PW397): with no kit file yet, its bindings are taken once,
	# written to the kit's own file and said, and the older file is left as it was.
	var older_path := _run + "/older.cfg"
	var older := ConfigFile.new()
	older.set_value("controls", J, ["key:%d" % KEY_Q, "button:3"])
	older.set_value("controls", "deadzone", 0.4)
	older.save(older_path)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(_kept))
	var adopting := _PwBindings.new(actions, _kept)
	adopting.from = [older_path, "controls"]
	# The older file names one action of three: the two it never names keep their
	# defaults in silence, with no engine error each (§PW543).
	var errors := _Errors.new()
	OS.add_logger(errors)
	adopting.load_kept()
	OS.remove_logger(errors)
	if not errors.said.is_empty():
		failed.append("taking an older file logged %d engine errors: %s"
			% [errors.said.size(), errors.said[0]])
	if adopting.current()[J] != ["key:%d" % KEY_Q, "button:3"]:
		failed.append("an older file's binding was not taken: %s" % [adopting.current()[J]])
	if not is_equal_approx(adopting.deadzone, 0.4):
		failed.append("an older file's deadzone was not taken")
	if adopting.said.is_empty() or not FileAccess.file_exists(_kept):
		failed.append("taking an older file was not said, or not written to the kit's own")
	var later := _PwBindings.new(actions, _kept)
	later.from = [older_path, "controls"]
	later.load_kept()
	if not later.said.is_empty():
		failed.append("the older file was taken again once the kit had its own")
	# Back to the game's own bindings for the screen's half of the proof.
	later.reset()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(older_path))

	# The game's own store (§PW433): the bindings and the pad's settings kept in its one
	# file and section beside its other sections, a deadzone held to the game's range,
	# and options of its own, kept, held to their range and read back.
	var settings_path := _run + "/store.cfg"
	var settings := ConfigFile.new()
	settings.set_value("video", "fullscreen", true)
	settings.set_value("controls", "sensitivity", 9.0)
	settings.save(settings_path)
	var store := _PwBindings.new(actions, settings_path)
	store.section = "controls"
	store.deadzone_least = 0.05
	store.deadzone_most = 0.6
	store.declare_options({"twin_stick": [true], "sensitivity": [1.0, 0.5, 2.0]})
	store.load_kept()
	if not is_equal_approx(float(store.option("sensitivity")), 2.0):
		failed.append("a kept option outside its range read %s" % store.option("sensitivity"))
	store.set_deadzone(0.9)
	store.set_option("twin_stick", false)
	if not is_equal_approx(store.deadzone, 0.6):
		failed.append("the deadzone left the game's range: %s" % store.deadzone)
	if store.set_option("never_declared", 1):
		failed.append("an option nobody declared was kept")
	var reread := ConfigFile.new()
	reread.load(settings_path)
	if reread.get_value("video", "fullscreen", false) != true \
			or reread.get_value("controls", "twin_stick", true) != false \
			or not reread.has_section_key("controls", J):
		failed.append("the game's file did not keep its own and the kit's together")
	var again_store := _PwBindings.new(actions, settings_path)
	again_store.section = "controls"
	again_store.declare_options({"twin_stick": [true], "sensitivity": [1.0, 0.5, 2.0]})
	again_store.load_kept()
	if again_store.option("twin_stick") != false:
		failed.append("an option did not come back from the game's file")
	again_store.reset()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(settings_path))
	if _PwBindings.shared() != _PwBindings.shared():
		failed.append("the shared store is not one store")

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
	# Again here: a game's own autoloads set the player's language in their _ready,
	# which runs after _initialize (§PW537).
	TranslationServer.set_locale(PROOF_LOCALE)
	# the screen binds on the game's one store (§PW540); the proof then gives it a store
	# of its own run, so it never rebinds the player's controls
	if menu.bindings != _PwBindings.shared():
		failed.append("the screen keeps a store of its own, not the game's shared one")
	menu.bindings = _PwBindings.new(menu.actions, _kept)
	var said: String = menu.take(P, _PwBindings.decode(fire_key))
	# Said in whatever words the game's table gives it, it names both actions.
	if not (said.contains(menu.bindings.label(P)) and said.contains(menu.bindings.label(F))):
		failed.append("the screen did not say the swap: %s" % said)
	# A host game hears when the screen listens and when it stops, and the button a pad
	# focused is still the one focused once it binds (§PW541).
	var heard: Array[String] = []
	var hear_start := func(action: String) -> void: heard.append("listening " + action)
	var hear_stop := func(action: String) -> void: heard.append("listened " + action)
	menu.listening.connect(hear_start)
	menu.listened.connect(hear_stop)
	var focused: Button = menu.button_of(J, true)
	focused.grab_focus()
	menu._listen(J, true)
	if not menu.is_listening():
		failed.append("the screen listening for jump says it is not")
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
	menu.listening.disconnect(hear_start)
	menu.listened.disconnect(hear_stop)
	if heard != ["listening " + J, "listened " + J] or menu.is_listening():
		failed.append("the screen did not say it listened for jump and stopped: %s" % [heard])
	if not is_instance_valid(focused) or focused.is_queued_for_deletion() \
			or root.gui_get_focus_owner() != focused:
		failed.append("binding jump lost the focus on its button")
	# A game's declared CONFIRM presses the focused button, where ui_accept has no pad
	# button of its own (§PW542).
	menu.bindings.confirm = [J]
	menu.button_of(F, false).grab_focus()
	menu._input(_key(KEY_SPACE))
	if menu._listening != F:
		failed.append("the declared confirm did not press the focused button")
	menu._stop("")
	menu.bindings.confirm = []
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
	# "pad" has no row of the proof's: the game's own, where its table has one in the
	# fallback language, else the kit's English (§PW537).
	var pad_row := String(TranslationServer.translate("REMAP_PAD"))
	var pad := "Pad" if pad_row == "REMAP_PAD" else pad_row
	if menu.said("reset") != "Restaurar" or menu.said("pad") != pad:
		failed.append("the screen's words ignore the table: %s, %s"
			% [menu.said("reset"), menu.said("pad")])
	if menu.bindings.label(J) != "Pular" or menu.bindings.label(F) != F:
		failed.append("an action's label reads %s" % menu.bindings.label(J))
	TranslationServer.remove_translation(table)
	menu.bindings.reset()
	_pad_screen(menu.open_pad())
	menu.bindings.reset()
	var at := ProjectSettings.globalize_path(_run)
	for name in DirAccess.get_files_at(at):
		DirAccess.remove_absolute(at.path_join(name))
	DirAccess.remove_absolute(at)
	TranslationServer.set_locale(_game_locale)
	if failed.is_empty():
		print("KIT PROVED")
	else:
		# Read in the proof's own language; the game's is said, for a finding on a word.
		print("KIT FAILED (words read in %s, the game's language %s): %s"
			% [PROOF_LOCALE, _game_locale, "; ".join(failed)])
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
			if _PwBindings.decode(slot["code"]) == null or screen.glyph(slot["code"], layout) == "":
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
	# Each place reads its action's declared label, the help names the buttons that work
	# the screen, and a declared CONFIRM and BACK work it (§PW542).
	var table := Translation.new()
	table.locale = TranslationServer.get_locale()
	table.add_message("PROOF_FIRE", "Atirar")
	TranslationServer.add_translation(table)
	screen.bindings.labels = {F: "PROOF_FIRE"}
	if screen.held_text(south) != "Atirar":
		failed.append("the pad screen labels fire's place %s, not its declared label"
			% screen.held_text(south))
	TranslationServer.remove_translation(table)
	screen.bindings.labels = {}
	screen.bindings.confirm = [J]
	screen.bindings.back = [P]
	var help: String = screen.help_text()
	# a game's own help row may name no button; the kit's own always names them
	if String(TranslationServer.translate("PAD_HELP")) == "PAD_HELP" and (
			"{" in help or not help.contains(_PwPrompts.shared().fill("{%s}" % J))):
		failed.append("the pad screen's help names no confirm button: %s" % help)
	screen._input(_key(KEY_SPACE))
	if screen.choosing == "":
		failed.append("the declared confirm did not choose on the pad screen")
	screen._input(_key(KEY_ESCAPE))
	if screen.choosing != "":
		failed.append("the declared back did not back out of the choice")
	screen.bindings.confirm = []
	screen.bindings.back = []
	screen.press("ui_cancel")
	if not screen.is_queued_for_deletion():
		failed.append("cancel did not close the pad screen")
