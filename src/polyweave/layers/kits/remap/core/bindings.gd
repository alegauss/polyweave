class_name PolyweaveBindings
extends RefCounted
## What each action is bound to, rebindable and kept (polyweave kit "remap", §PW345).
##
## Extracted from Starship's bindings: an action's binding is stored as codes a settings
## file can hold, `key:<physical keycode>`, `button:<joypad button>` and
## `axis:<joypad axis>:<-1 or 1>`. Keys and pad are two halves of a binding, replaced
## apart: rebinding with a key leaves the pad alone. A code another action holds on the
## same half is swapped, never shared. A reset goes back to the project's own InputMap,
## as project.godot declares it, and the stick's deadzone and inverted vertical sit
## beside the bindings in one file under user://.

## every rebind, reset and load, once the InputMap holds it (§PW540): the players kit
## narrows the first player's pad bindings to their pad again on it, so a rebind on the
## remap screen mid-co-op leaves each player's pad on their own actions
signal changed

const FILE := "user://polyweave_bindings.cfg"
## The project's own declaration (§PW397): `const FROM := ["user://settings.cfg",
## "controls"]` names the file and section a game kept its players' bindings in before
## the kit, so the first launch with the kit takes them instead of resetting them.
const PROJECT := "res://polyweave_remap.gd"
## the prompts kit this one requires, told on every change so its labels refill (§PW434)
const _PwPrompts := preload("res://addons/polyweave/prompts/prompts.gd")
## how far a stick or trigger must move to be read as a binding, and back to be let go
const AXIS_PRESS := 0.6
const AXIS_RELEASE := 0.25

## the actions a player may rebind; every project action but the ui_ ones where unset
var actions: Array = []
var deadzone := 0.5
## the least and most the deadzone may be, the declaration's DEADZONE where it says
var deadzone_least := 0.05
var deadzone_most := 0.95
var invert_vertical := false
## a game's own pad options and their values now, as OPTIONS declares them (§PW433)
var options := {}
## each option's declaration: [default] for a switch, [default, least, most] for a number
var declared_options := {}
var _defaults := {}
var _path := FILE
## the section of the game's own settings file the bindings and pad options are kept
## in, its other sections left as they are; "" keeps the kit's own file, sectioned
var section := ""
## where the game kept its bindings before the kit, [file, section], or empty
var from: Array = []
## what the last load had to say: bindings taken from an older file
var said: Array[String] = []
## each action's row in the game's string table, in the order the screen shows them,
## as the declaration's `const LABELS := {"jump": "ACTION_JUMP", ...}` says (§PW432)
var labels: Dictionary = {}
## the actions the kit's screens confirm and go back on, as the declaration's `const
## CONFIRM := ["fire"]` and `const BACK := ["bomb"]` say (§PW542); ui_accept and
## ui_cancel where it names none
var confirm: Array = []
var back: Array = []

static var _shared: RefCounted


## The game's one store, made and loaded the first time it is asked, so a script reads
## `invert_vertical` or an option every frame without holding a store of its own.
static func shared() -> RefCounted:
	if _shared == null:
		_shared = load("res://addons/polyweave/remap/bindings.gd").new()
		_shared.load_kept()
	return _shared


## The declaration (§PW397, §PW432, §PW433) may say, beside FROM and LABELS:
## `const STORE := ["user://settings.cfg", "controls"]`, the game's own file and section
## to keep everything in; `const DEADZONE := [0.25, 0.05, 0.6]`, its default and range;
## `const OPTIONS := {"twin_stick": [true], "sensitivity": [1.0, 0.5, 2.0]}`, pad
## options of its own. A path handed in, as a proof hands one, keeps the kit's file.
func _init(rebindable: Array = [], path := FILE, project := PROJECT) -> void:
	_path = path
	if ResourceLoader.exists(project):
		var declared: Dictionary = (load(project) as GDScript).get_script_constant_map()
		from = Array(declared.get("FROM", []))
		labels = Dictionary(declared.get("LABELS", {}))
		confirm = _named(declared.get("CONFIRM", []))
		back = _named(declared.get("BACK", []))
		var store := Array(declared.get("STORE", []))
		if store.size() == 2 and path == FILE:
			_path = str(store[0])
			section = str(store[1])
		var zone := Array(declared.get("DEADZONE", []))
		if zone.size() == 3:
			deadzone_least = float(zone[1])
			deadzone_most = float(zone[2])
			deadzone = clampf(float(zone[0]), deadzone_least, deadzone_most)
		declare_options(Dictionary(declared.get("OPTIONS", {})))
	actions = rebindable if not rebindable.is_empty() else (
		labels.keys() if not labels.is_empty() else _project_actions())
	for action in actions:
		_defaults[action] = defaults(action)


## take a game's own pad options, each at its default
func declare_options(declared: Dictionary) -> void:
	declared_options = declared
	options.clear()
	for name in declared:
		options[name] = (declared[name] as Array)[0]


## an option's value, its declared default where it was never set
func option(name: String) -> Variant:
	return options.get(name, null)


## set a declared option, a number held to its range, and keep it; false for a name
## the game never declared
func set_option(name: String, value: Variant) -> bool:
	if not declared_options.has(name):
		return false
	options[name] = _held(name, value)
	save()
	return true


func _held(name: String, value: Variant) -> Variant:
	var declared: Array = declared_options[name]
	if declared[0] is bool:
		return bool(value)
	var number := float(value)
	if declared.size() >= 3:
		number = clampf(number, float(declared[1]), float(declared[2]))
	return int(number) if declared[0] is int else number


## what the player reads for an action: its declared row in the game's string table, or
## its own name where it has none
func label(action: String) -> String:
	var key: String = labels.get(action, "")
	if key == "":
		return action
	var text := String(TranslationServer.translate(key))
	return action if text == key else text


## an action or a list of them, as a declaration may spell either
static func _named(declared: Variant) -> Array:
	return [str(declared)] if declared is String or declared is StringName \
		else Array(declared).map(func(one: Variant) -> String: return str(one))


## the action a screen confirms on (`back` false) or goes back on: the first declared,
## else ui_accept or ui_cancel; what its help line names as `{confirm}` and `{back}`
func screen_action(going_back := false) -> String:
	var declared := back if going_back else confirm
	return str(declared[0]) if not declared.is_empty() else (
		"ui_cancel" if going_back else "ui_accept")


## whether `event` presses what a screen confirms on, or goes back on: a declared action,
## or ui_accept and ui_cancel where none is declared
func pressed_on_screen(event: InputEvent, going_back := false) -> bool:
	var declared := back if going_back else confirm
	for action in declared if not declared.is_empty() else [screen_action(going_back)]:
		if InputMap.has_action(action) and event.is_action_pressed(action):
			return true
	return false


static func _project_actions() -> Array:
	var out := []
	for setting in ProjectSettings.get_property_list():
		var named: String = setting["name"]
		if named.begins_with("input/") and not named.begins_with("input/ui_"):
			out.append(named.trim_prefix("input/"))
	return out


## the codes project.godot binds `action` to: what a reset goes back to
static func defaults(action: String) -> Array:
	var declared: Variant = ProjectSettings.get_setting("input/" + action, {})
	var out := []
	for event in (declared as Dictionary).get("events", []):
		var code := encode(event)
		if code != "":
			out.append(code)
	return out


## the code of a pressed key, button or axis moved far enough, or "" for anything else
static func encode(event: InputEvent) -> String:
	if event is InputEventKey:
		var key := event as InputEventKey
		var physical := key.physical_keycode if key.physical_keycode != KEY_NONE else key.keycode
		return "key:%d" % physical if physical != KEY_NONE else ""
	if event is InputEventMouseButton:
		return "mouse:%d" % (event as InputEventMouseButton).button_index
	if event is InputEventJoypadButton:
		return "button:%d" % (event as InputEventJoypadButton).button_index
	if event is InputEventJoypadMotion:
		var motion := event as InputEventJoypadMotion
		if absf(motion.axis_value) < AXIS_PRESS:
			return ""
		return "axis:%d:%d" % [motion.axis, 1 if motion.axis_value > 0.0 else -1]
	return ""


## the event a code stands for; a pad's answers every pad, as project.godot's own do,
## since a new event's device is 0 and would bind pad 0 alone (§PW391)
static func decode(code: String) -> InputEvent:
	var parts := code.split(":")
	match parts[0]:
		"key":
			var key := InputEventKey.new()
			key.physical_keycode = int(parts[1]) as Key
			return key
		"mouse":
			var mouse := InputEventMouseButton.new()
			mouse.button_index = int(parts[1]) as MouseButton
			return mouse
		"button":
			var button := InputEventJoypadButton.new()
			button.button_index = int(parts[1]) as JoyButton
			button.device = -1
			return button
		"axis":
			var motion := InputEventJoypadMotion.new()
			motion.axis = int(parts[1]) as JoyAxis
			motion.axis_value = float(parts[2])
			motion.device = -1
			return motion
	return null


## whether `event` presses something a binding could hold: a key, a mouse or pad button
## down, or a stick or trigger past `AXIS_PRESS`
static func is_press(event: InputEvent) -> bool:
	if event is InputEventJoypadMotion:
		return absf((event as InputEventJoypadMotion).axis_value) >= AXIS_PRESS
	return (event is InputEventKey or event is InputEventMouseButton
		or event is InputEventJoypadButton) and event.is_pressed() and not event.is_echo()


## whether `event` lets go of what `code` pressed: the same key or button up, or its
## stick or trigger back under `AXIS_RELEASE`
static func is_release(event: InputEvent, code: String) -> bool:
	if event is InputEventJoypadMotion:
		var motion := event as InputEventJoypadMotion
		return code.begins_with("axis:%d:" % motion.axis) \
			and absf(motion.axis_value) <= AXIS_RELEASE
	if not (event is InputEventKey or event is InputEventMouseButton
			or event is InputEventJoypadButton) or event.is_pressed():
		return false
	return encode(event) == code


## a key and a mouse button are the keyboard's half; a pad's button and axis, the pad's
static func on_keys(code: String) -> bool:
	return code.begins_with("key:") or code.begins_with("mouse:")


## every action's codes as the InputMap holds them now
func current() -> Dictionary:
	var out := {}
	for action in actions:
		var codes := []
		if InputMap.has_action(action):
			for event in InputMap.action_get_events(action):
				var code := encode(event)
				if code != "":
					codes.append(code)
		out[action] = codes
	return out


## every action's codes after binding `code` to `action`: it replaces the half of the
## action's codes `code` belongs to, and an action that held `code` takes the codes the
## rebound action had on that half instead
static func bind(now: Dictionary, action: String, code: String) -> Dictionary:
	var out := {}
	for each in now:
		out[each] = (now[each] as Array).duplicate()
	var half := on_keys(code)
	var before: Array = out[action].filter(func(c: String) -> bool: return on_keys(c) == half)
	var kept: Array = out[action].filter(func(c: String) -> bool: return on_keys(c) != half)
	out[action] = [code] + kept if half else kept + [code]
	for each in out:
		if each == action or not (out[each] as Array).has(code):
			continue
		var theirs: Array = out[each].filter(func(c: String) -> bool: return c != code)
		for old in before:
			if old != code and not theirs.has(old):
				theirs.append(old)
		out[each] = theirs
	return out


## put `codes` in the InputMap as all `action` is bound to
func apply(action: String, codes: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, deadzone)
	InputMap.action_erase_events(action)
	InputMap.action_set_deadzone(action, deadzone)
	for code in codes:
		var event := decode(code)
		if event != null:
			InputMap.action_add_event(action, event)


## rebind `action` to the input `event`, swap any clash, and keep the result
func rebind(action: String, event: InputEvent) -> bool:
	var code := encode(event)
	if code == "" or not actions.has(action):
		return false
	var after := bind(current(), action, code)
	for each in after:
		apply(each, after[each])
	save()
	_PwPrompts.rebound()
	changed.emit()
	return true


## every action back to project.godot's bindings, and kept
func reset() -> void:
	for action in actions:
		apply(action, _defaults[action])
	save()
	_PwPrompts.rebound()
	changed.emit()


func set_deadzone(value: float) -> void:
	deadzone = clampf(value, deadzone_least, deadzone_most)
	for action in actions:
		if InputMap.has_action(action):
			InputMap.action_set_deadzone(action, deadzone)
	save()


func set_invert_vertical(value: bool) -> void:
	invert_vertical = value
	save()


## the sections the bindings and the pad's settings are kept under: the game's one
## section where it named one, else the kit's file's two
func _sections() -> Array:
	return [section, section] if section != "" else ["bindings", "pad"]


## keep every binding, the deadzone, the inverted vertical and the game's options; in
## the game's own file, every other section and key in it is kept as it was
func save() -> void:
	var file := ConfigFile.new()
	if section != "":
		file.load(_path)
	var into := _sections()
	var now := current()
	for action in now:
		file.set_value(into[0], action, now[action])
	file.set_value(into[1], "deadzone", deadzone)
	file.set_value(into[1], "invert_vertical", invert_vertical)
	for name in options:
		file.set_value(into[1], name, options[name])
	file.save(_path)


## what was kept, put back in force; a code that no longer reads is left out, and a
## deadzone or option outside its range is brought into it. With no file of the kit's
## own yet, the bindings the game kept before are taken (§PW397).
func load_kept() -> void:
	said.clear()
	var file := ConfigFile.new()
	if file.load(_path) != OK:
		if section == "":
			_adopt()
		_PwPrompts.rebound()
		changed.emit()
		return
	_read(file, _sections())
	_PwPrompts.rebound()
	changed.emit()


func _read(file: ConfigFile, into: Array) -> int:
	if file.has_section_key(into[1], "deadzone"):
		set_deadzone_quietly(float(file.get_value(into[1], "deadzone")))
	invert_vertical = bool(file.get_value(into[1], "invert_vertical", invert_vertical))
	for name in declared_options:
		if file.has_section_key(into[1], name):
			options[name] = _held(name, file.get_value(into[1], name))
	var took := 0
	for action in actions:
		var codes: Variant = file.get_value(into[0], action, null)
		if codes is Array:
			var kept := (codes as Array).filter(func(c: Variant) -> bool:
				return c is String and decode(c) != null)
			if not kept.is_empty() or section == "":
				apply(action, kept)
				took += 1
	return took


## the deadzone held to its range and put in the InputMap, without keeping it yet
func set_deadzone_quietly(value: float) -> void:
	deadzone = clampf(value, deadzone_least, deadzone_most)
	for action in actions:
		if InputMap.has_action(action):
			InputMap.action_set_deadzone(action, deadzone)


## the bindings the game kept before the kit, under each action's name in the declared
## section, with a deadzone, inverted vertical and declared options where it kept them,
## each held to its range; written to the kit's own file at once, the older file left
## as it was, and said
func _adopt() -> void:
	if from.size() != 2:
		return
	var older := ConfigFile.new()
	if older.load(str(from[0])) != OK:
		return
	var kept_in := str(from[1])
	var took := 0
	for action in actions:
		var codes: Variant = older.get_value(kept_in, action, null)
		if codes is Array and not (codes as Array).filter(func(c: Variant) -> bool:
				return c is String and decode(c) != null).is_empty():
			took += 1
	_read(older, [kept_in, kept_in])
	save()
	said.append("took %d bindings from %s [%s], which stays as it was"
		% [took, from[0], kept_in])
