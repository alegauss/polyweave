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


## What a family's face buttons, shoulders, triggers and menu buttons are called, by
## where each sits, as the pad prints them (§PW394). A Switch pad's south button is B.
const GLYPHS := {
	"xbox": {"south": "A", "east": "B", "west": "X", "north": "Y", "lb": "LB",
		"rb": "RB", "lt": "LT", "rt": "RT", "select": "VIEW", "start": "MENU"},
	"playstation": {"south": "CROSS", "east": "CIRCLE", "west": "SQUARE",
		"north": "TRIANGLE", "lb": "L1", "rb": "R1", "lt": "L2", "rt": "R2",
		"select": "CREATE", "start": "OPTIONS"},
	"switch": {"south": "B", "east": "A", "west": "Y", "north": "X", "lb": "L",
		"rb": "R", "lt": "ZL", "rt": "ZR", "select": "MINUS", "start": "PLUS"},
}
## What every pad calls its sticks, their clicks and its d-pad, read through the
## game's string table under PAD_ (a stick's direction is PAD_LS_LEFT, say).
const SPOKEN := {
	"ls": "LS", "rs": "RS", "dpad_up": "D-UP", "dpad_down": "D-DOWN",
	"dpad_left": "D-LEFT", "dpad_right": "D-RIGHT",
}
## The four moves, in the order a help line reads them, which `{move}` names as one.
var moves: Array[String] = ["move_up", "move_left", "move_down", "move_right"]


## A player's own action: the first player's is the action itself, every other's the
## copy the players kit gives them, p2_jump and so on.
static func action_of(action: StringName, player := 0) -> StringName:
	return action if player == 0 else StringName("p%d_%s" % [player + 1, action])


## The family the player holds: the first player's is the one in use; another's is
## the pad the players kit seated them on, read by its name.
func family_for(player := 0) -> String:
	if player == 0 or not ResourceLoader.exists(
			"res://addons/polyweave/players/players.gd"):
		return family
	var seats: Node = load("res://addons/polyweave/players/players.gd").shared()
	var pad: int = seats.pads.get(player, -1)
	return family_of(Input.get_joy_name(pad)) if pad >= 0 else family


## A name as the game's string table says it under `prefix`, or the name itself where
## the table has no row for it.
static func said(prefix: String, name: String) -> String:
	var key := prefix + name.to_upper().replace("-", "_").replace(" ", "_")
	var text := TranslationServer.translate(key)
	return name if String(text) == key else String(text)


## An action's binding in words, as the player holding it reads it (§PW394): a pad's
## buttons in its family's glyphs, a key and a stick through the string table.
func named(action: StringName, player := 0, in_family := "") -> String:
	var wanted := in_family if in_family != "" else family_for(player)
	var event := event_for(action_of(action, player), wanted)
	if event == null:
		return String(action).to_upper()
	if event is InputEventKey:
		var code: int = event.physical_keycode if event.physical_keycode else event.keycode
		return said("KEYNAME_", OS.get_keycode_string(code).to_upper())
	if event is InputEventMouseButton:
		return said("KEYNAME_", button_of(event).to_upper().replace("_", " "))
	var button := button_of(event)
	var glyphs: Dictionary = GLYPHS.get(wanted, GLYPHS["xbox"])
	if glyphs.has(button):
		return glyphs[button]
	if event is InputEventJoypadMotion and button in ["l_stick", "r_stick"]:
		var stick := "LS" if button == "l_stick" else "RS"
		var axis: int = event.axis
		var vertical := axis == JOY_AXIS_LEFT_Y or axis == JOY_AXIS_RIGHT_Y
		var way := ("DOWN" if event.axis_value > 0 else "UP") if vertical \
			else ("RIGHT" if event.axis_value > 0 else "LEFT")
		return said("PAD_", "%s %s" % [stick, way])
	return said("PAD_", SPOKEN.get(button, button.to_upper()))


## The four moves as one prompt: WASD on keys, the stick alone where all four are one
## stick's directions, or each in turn.
func move_named(player := 0, in_family := "") -> String:
	var four := []
	for one in moves:
		four.append(named(one, player, in_family))
	var stick: String = four[0].get_slice(" ", 0)
	if four.all(func(n: String) -> bool: return " " in n and n.get_slice(" ", 0) == stick):
		return stick
	if four.all(func(n: String) -> bool: return n.length() == 1):
		return "".join(four)
	return " ".join(four)


## `text` with each `{action}` replaced by what player `player` presses for it and
## `{move}` by the four moves, so a help line holds marks and never a fixed button.
func fill(text: String, player := 0, in_family := "") -> String:
	if not "{" in text:
		return text
	if "{move}" in text:
		text = text.replace("{move}", move_named(player, in_family))
	var mark := RegEx.create_from_string("\\{([A-Za-z0-9_]+)\\}")
	for found in mark.search_all(text):
		text = text.replace(found.get_string(0),
			named(StringName(found.get_string(1)), player, in_family))
	return text


## Text for a RichTextLabel with each `[action=jump]` drawn as that action's icon.
func bbcode(text: String, size := 32) -> String:
	var tag := RegEx.create_from_string("\\[action=([A-Za-z0-9_]+)\\]")
	var out := text
	for found in tag.search_all(text):
		var path := icon_path(StringName(found.get_string(1)))
		var drawn := "[img=%d]%s[/img]" % [size, path] if path != "" else found.get_string(1)
		out = out.replace(found.get_string(0), drawn)
	return out
