class_name PolyweavePrompts
extends Node
## Button prompts for the pad in the player's hands (polyweave kit "prompts", §PW344).
##
## Knows the family in use (xbox, playstation, switch, keyboard) from the pad's name and
## the last event, switches live when the player picks up another device, and answers an
## action's binding as an icon. Reach it as `preload(<this file>).shared()`; a script
## naming the class works too once the editor has scanned the project.

signal family_changed(family: String)

const HERE := "res://addons/polyweave/prompts/prompts.gd"
const FAMILIES: Array[String] = ["xbox", "playstation", "switch", "keyboard"]

## Where each family's icons are, as `<root>/<family>/<button>_64.png`. A game may point
## it at another set, such as a platform holder's own glyphs, which polyweave never
## carries.
var icons_root := "res://addons/polyweave/prompts/icons"
var family := "keyboard"

## A pad's buttons by where they sit, so a Switch pad's south button reads B.
const BUTTONS := {
	JOY_BUTTON_A: "south", JOY_BUTTON_B: "east", JOY_BUTTON_X: "west",
	JOY_BUTTON_Y: "north", JOY_BUTTON_BACK: "select", JOY_BUTTON_START: "start",
	JOY_BUTTON_LEFT_STICK: "ls", JOY_BUTTON_RIGHT_STICK: "rs",
	JOY_BUTTON_LEFT_SHOULDER: "lb", JOY_BUTTON_RIGHT_SHOULDER: "rb",
	JOY_BUTTON_DPAD_UP: "dpad_up", JOY_BUTTON_DPAD_DOWN: "dpad_down",
	JOY_BUTTON_DPAD_LEFT: "dpad_left", JOY_BUTTON_DPAD_RIGHT: "dpad_right",
}
const AXES := {
	JOY_AXIS_LEFT_X: "l_stick", JOY_AXIS_LEFT_Y: "l_stick",
	JOY_AXIS_RIGHT_X: "r_stick", JOY_AXIS_RIGHT_Y: "r_stick",
	JOY_AXIS_TRIGGER_LEFT: "lt", JOY_AXIS_TRIGGER_RIGHT: "rt",
}
const MOUSE := {
	MOUSE_BUTTON_LEFT: "mouse_left", MOUSE_BUTTON_RIGHT: "mouse_right",
	MOUSE_BUTTON_MIDDLE: "mouse_middle",
}

static var _shared: Node


## The one service the game's prompts share, made and put in the tree the first time.
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweavePrompts"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


func _input(event: InputEvent) -> void:
	note(event)


## The family the player is holding now: the pad an event came from, or the keyboard.
func note(event: InputEvent) -> void:
	var now := family
	if event is InputEventJoypadButton or (
		event is InputEventJoypadMotion and absf(event.axis_value) > 0.5
	):
		now = family_of(Input.get_joy_name(event.device))
	elif event is InputEventKey or event is InputEventMouseButton:
		now = "keyboard"
	if now != family:
		family = now
		family_changed.emit(family)


## A pad's family from the name the system gives it; a pad no one names is an Xbox one.
static func family_of(joy_name: String) -> String:
	var said := joy_name.to_lower()
	for word in ["playstation", "dualshock", "dualsense", "ps3", "ps4", "ps5", "sony"]:
		if word in said:
			return "playstation"
	for word in ["nintendo", "switch", "pro controller", "joy-con", "joycon"]:
		if word in said:
			return "switch"
	return "xbox"


## The icon name an event is drawn as, or "" where no icon draws it.
static func button_of(event: InputEvent) -> String:
	if event is InputEventJoypadButton:
		return BUTTONS.get(event.button_index, "")
	if event is InputEventJoypadMotion:
		return AXES.get(event.axis, "")
	if event is InputEventMouseButton:
		return MOUSE.get(event.button_index, "")
	if event is InputEventKey:
		var code: int = event.physical_keycode if event.physical_keycode else event.keycode
		var said := OS.get_keycode_string(code).to_lower().replace(" ", "_")
		return "key_" + said if said != "" else ""
	return ""


## The binding of an action that a family draws: a pad's for a pad, a key's otherwise.
func event_for(action: StringName, in_family := "") -> InputEvent:
	var wanted := in_family if in_family != "" else family
	if not InputMap.has_action(action):
		return null
	for event in InputMap.action_get_events(action):
		var on_keys := event is InputEventKey or event is InputEventMouseButton
		if on_keys == (wanted == "keyboard") and button_of(event) != "":
			return event
	return null


## Where an action's icon is in a family, or "" where it has none.
func icon_path(action: StringName, in_family := "") -> String:
	var wanted := in_family if in_family != "" else family
	var event := event_for(action, wanted)
	if event == null:
		return ""
	var path := "%s/%s/%s_64.png" % [icons_root, wanted, button_of(event)]
	return path if ResourceLoader.exists(path) or FileAccess.file_exists(path) else ""


## An action's icon in a family, imported or straight from the file, or null.
func icon(action: StringName, in_family := "") -> Texture2D:
	var path := icon_path(action, in_family)
	if path == "":
		return null
	if ResourceLoader.exists(path):
		return load(path)
	var image := Image.load_from_file(ProjectSettings.globalize_path(path))
	return ImageTexture.create_from_image(image) if image != null else null


## Text for a RichTextLabel with each `[action=jump]` drawn as that action's icon.
func bbcode(text: String, size := 32) -> String:
	var tag := RegEx.create_from_string("\\[action=([A-Za-z0-9_]+)\\]")
	var out := text
	for found in tag.search_all(text):
		var path := icon_path(StringName(found.get_string(1)))
		var drawn := "[img=%d]%s[/img]" % [size, path] if path != "" else found.get_string(1)
		out = out.replace(found.get_string(0), drawn)
	return out
