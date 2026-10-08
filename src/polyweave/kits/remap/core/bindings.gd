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

const FILE := "user://polyweave_bindings.cfg"
## how far a stick or trigger must move to be read as a binding
const AXIS_PRESS := 0.6

## the actions a player may rebind; every project action but the ui_ ones where unset
var actions: Array = []
var deadzone := 0.5
var invert_vertical := false
var _defaults := {}
var _path := FILE


func _init(rebindable: Array = [], path := FILE) -> void:
	_path = path
	actions = rebindable if not rebindable.is_empty() else _project_actions()
	for action in actions:
		_defaults[action] = defaults(action)


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
			return button
		"axis":
			var motion := InputEventJoypadMotion.new()
			motion.axis = int(parts[1]) as JoyAxis
			motion.axis_value = float(parts[2])
			return motion
	return null


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
	return true


## every action back to project.godot's bindings, and kept
func reset() -> void:
	for action in actions:
		apply(action, _defaults[action])
	save()


func set_deadzone(value: float) -> void:
	deadzone = clampf(value, 0.05, 0.95)
	for action in actions:
		if InputMap.has_action(action):
			InputMap.action_set_deadzone(action, deadzone)
	save()


func set_invert_vertical(value: bool) -> void:
	invert_vertical = value
	save()


func save() -> void:
	var file := ConfigFile.new()
	var now := current()
	for action in now:
		file.set_value("bindings", action, now[action])
	file.set_value("pad", "deadzone", deadzone)
	file.set_value("pad", "invert_vertical", invert_vertical)
	file.save(_path)


## what was kept, put back in force; a code that no longer reads is left out
func load_kept() -> void:
	var file := ConfigFile.new()
	if file.load(_path) != OK:
		return
	deadzone = float(file.get_value("pad", "deadzone", deadzone))
	invert_vertical = bool(file.get_value("pad", "invert_vertical", invert_vertical))
	for action in actions:
		var codes: Variant = file.get_value("bindings", action, null)
		if codes is Array:
			apply(action, (codes as Array).filter(func(c: Variant) -> bool:
				return c is String and decode(c) != null))
