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
## `generic` is a pad nobody can name (§PW431): its face buttons are called by where they
## sit, since what they print is anyone's guess.
const FAMILIES: Array[String] = ["xbox", "playstation", "switch", "generic", "keyboard"]

## Where each family's icons are, as `<root>/<family>/<button>_64.png`. A game may point
## it at another set, such as a platform holder's own glyphs, which polyweave never
## carries.
var icons_root := "res://addons/polyweave/prompts/icons"
var family := "keyboard"

## A pad's buttons by where they sit, so a Switch pad's south button reads B.
const BUTTONS := {
	JOY_BUTTON_A: "south", JOY_BUTTON_B: "east", JOY_BUTTON_X: "west",
	JOY_BUTTON_Y: "north", JOY_BUTTON_BACK: "select", JOY_BUTTON_START: "start",
	JOY_BUTTON_GUIDE: "guide",
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


## A player's family moved; `family_changed` is the first player's alone (§PW395).
signal player_changed(player: int, family: String)

## Who holds which device, as the players kit seats them; found when installed, and a
## stand-in may be set in its place. It answers player_of_event(event) and count().
var seats: Object = null
## Each player's family and the device it came from, a pad's id or -1 for the keyboard.
var families := {}
var devices := {}


## Labels kept filled, each [weakref to it, its table key, its player] (§PW434), and the
## callables run on every change, so a screen states once what it shows.
var _watched: Array = []
var _followers: Array[Callable] = []


## Whether any input has been noted yet; before it, the first player's family is the
## first connected pad's (§PW545).
var _touched := false


func _ready() -> void:
	Input.joy_connection_changed.connect(unplugged)
	start(Array(Input.get_connected_joypads()))


func _input(event: InputEvent) -> void:
	note(event)


## Before any input, the first player holds the first of the `connected` pads, as a game
## launched from a couch is played with the pad in hand (§PW545), and the keyboard where
## none is. `names` stands in for the names the system gives the pads, pad -> name.
## Once an input is noted the device in use decides, and this changes nothing.
func start(connected: Array, names := {}) -> String:
	if _touched or connected.is_empty():
		return family
	var pad := int(connected[0])
	devices[0] = pad
	_moved(0, family_of(str(names.get(pad, Input.get_joy_name(pad)))))
	return family


## Fill `label`'s text from the table row `key` through `fill`, for `player`, and keep
## it filled: again when that player's device moves, a binding changes or the language
## does. Anything with a `text` serves, a Label, a RichTextLabel or a Button; one freed
## is let go.
func watch(label: Object, key: String, player := 0) -> void:
	_watched = _watched.filter(func(one: Array) -> bool: return one[0].get_ref() != label)
	_watched.append([weakref(label), key, player, 0])
	label.set("text", _filled(_watched[-1]))


## `watch` for a RichTextLabel drawn in icons (§PW551): the row filled by `fill_bbcode`
## at `size`, and kept filled on the same changes.
func watch_bbcode(label: Object, key: String, player := 0, size := 32) -> void:
	_watched = _watched.filter(func(one: Array) -> bool: return one[0].get_ref() != label)
	_watched.append([weakref(label), key, player, size])
	label.set("text", _filled(_watched[-1]))


## A watched label's text now: [label, key, player, size], in words where size is 0.
func _filled(one: Array) -> String:
	var row := String(TranslationServer.translate(one[1]))
	return fill_bbcode(row, one[2], "", one[3]) if int(one[3]) > 0 else fill(row, one[2])


## Run `redraw` on every change `watch` refills on; one whose object is freed is let go.
func follow(redraw: Callable) -> void:
	if not _followers.has(redraw):
		_followers.append(redraw)


## Refill every watched label and run every follower: what a device, binding or
## language change does, and what a game calls after changing bindings by hand.
func refresh() -> void:
	_watched = _watched.filter(func(one: Array) -> bool: return one[0].get_ref() != null)
	for one in _watched:
		var label: Object = one[0].get_ref()
		label.set("text", _filled(one))
	_followers = _followers.filter(func(redraw: Callable) -> bool: return redraw.is_valid())
	for redraw in _followers:
		redraw.call()


## A binding changed somewhere: the shared service refills, where there is one. The
## remap kit calls this on every rebind, reset and load.
static func rebound() -> void:
	if _shared != null and is_instance_valid(_shared):
		_shared.refresh()


func _notification(what: int) -> void:
	if what == NOTIFICATION_TRANSLATION_CHANGED:
		refresh()


func _seats() -> Object:
	if seats == null and ResourceLoader.exists("res://addons/polyweave/players/players.gd"):
		seats = load("res://addons/polyweave/players/players.gd").shared()
	return seats


## The player an event is theirs, or -1 for a pad nobody holds while two play: the
## keyboard and every pad are the only player's while one plays.
func player_of(event: InputEvent) -> int:
	var held := _seats()
	if held == null or event is InputEventKey or event is InputEventMouse:
		return 0
	var player: int = held.player_of_event(event)
	if player < 0 and held.count() <= 1:
		return 0
	return player


## The family a player is holding now, moved only by their own input (§PW395): a key
## pressed, a pad button pressed, a stick or trigger past half way.
func note(event: InputEvent) -> void:
	var device := -2
	if event is InputEventJoypadButton and event.pressed or (
		event is InputEventJoypadMotion and absf(event.axis_value) > 0.5
	):
		device = event.device
	elif (event is InputEventKey and event.pressed and not event.echo) \
			or event is InputEventMouseButton:
		device = -1
	if device == -2:
		return
	_touched = true
	var player := player_of(event)
	if player < 0:
		return
	var now := "keyboard" if device < 0 else family_of(Input.get_joy_name(device))
	devices[player] = device
	_moved(player, now)


func _moved(player: int, now: String) -> void:
	if families.get(player, family if player == 0 else "") == now:
		families[player] = now
		return
	families[player] = now
	if player == 0:
		family = now
		family_changed.emit(family)
	player_changed.emit(player, now)
	refresh()


## A pad came or went (§PW395): each player whose prompts followed it moves to another
## pad still connected and held by nobody else, or to the keyboard.
func unplugged(pad: int, connected: bool, connected_now: Array = []) -> void:
	if connected:
		# a pad plugged in before any input is the one in hand (§PW545)
		if not devices.has(0) or devices[0] < 0:
			start([pad])
		return
	var left := connected_now if not connected_now.is_empty() \
		else Array(Input.get_connected_joypads())
	left = left.filter(func(p: int) -> bool:
		return p != pad and not devices.values().has(p))
	for player in devices.keys():
		if devices[player] != pad:
			continue
		var next: int = left.pop_front() if not left.is_empty() else -1
		devices[player] = next
		_moved(player, "keyboard" if next < 0 else family_of(Input.get_joy_name(next)))


## A pad's family from the name the system gives it: a pad it gives no name is an Xbox
## one, as most are, and one named but not known is generic (§PW431).
static func family_of(joy_name: String) -> String:
	var said := joy_name.to_lower()
	for word in ["playstation", "dualshock", "dualsense", "ps3", "ps4", "ps5", "sony"]:
		if word in said:
			return "playstation"
	for word in ["nintendo", "switch", "pro controller", "joy-con", "joycon"]:
		if word in said:
			return "switch"
	for word in ["xbox", "xinput", "microsoft", "x-box"]:
		if word in said:
			return "xbox"
	return "generic" if said.strip_edges() != "" else "xbox"


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
## The clicks are the family's own too (§PW431): L3 and R3 on a PlayStation pad and a
## generic one, LS and RS elsewhere. A generic pad's face buttons are its compass names,
## read through the string table as PAD_SOUTH and the rest.
const GLYPHS := {
	"xbox": {"south": "A", "east": "B", "west": "X", "north": "Y", "lb": "LB",
		"rb": "RB", "lt": "LT", "rt": "RT", "select": "VIEW", "start": "MENU",
		"ls": "LS", "rs": "RS"},
	"playstation": {"south": "CROSS", "east": "CIRCLE", "west": "SQUARE",
		"north": "TRIANGLE", "lb": "L1", "rb": "R1", "lt": "L2", "rt": "R2",
		"select": "CREATE", "start": "OPTIONS", "ls": "L3", "rs": "R3"},
	"switch": {"south": "B", "east": "A", "west": "Y", "north": "X", "lb": "L",
		"rb": "R", "lt": "ZL", "rt": "ZR", "select": "MINUS", "start": "PLUS",
		"ls": "LS", "rs": "RS"},
	"generic": {"south": "SOUTH", "east": "EAST", "west": "WEST", "north": "NORTH",
		"lb": "L1", "rb": "R1", "lt": "L2", "rt": "R2", "select": "SELECT",
		"start": "START", "ls": "L3", "rs": "R3"},
}
## What every pad calls its d-pad and its guide button, read through the game's string
## table under PAD_ (a stick's direction is PAD_LS_LEFT, say).
const SPOKEN := {
	"dpad_up": "D-UP", "dpad_down": "D-DOWN", "dpad_left": "D-LEFT",
	"dpad_right": "D-RIGHT", "guide": "GUIDE",
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
	if families.has(player):
		return families[player]
	if player == 0 or not ResourceLoader.exists(
			"res://addons/polyweave/players/players.gd"):
		return family
	var seats: Node = load("res://addons/polyweave/players/players.gd").shared()
	var pad: int = seats.pads.get(player, -1)
	return family_of(Input.get_joy_name(pad)) if pad >= 0 else family


## A name as the game's string table says it under `prefix`, or the name itself where
## the table has no row for it, or where it holds no word to translate: a letter, a
## digit, F1 or L3 reads as it is (§PW431).
static func said(prefix: String, name: String) -> String:
	if RegEx.create_from_string("[A-Za-z]{2,}").search(name) == null:
		return name
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
	return event_named(event, wanted)


## One input in words in a family, bound or not: a key and a stick's direction through
## the string table, a pad's button in the family's glyphs, a generic pad's by where it
## sits, through the table too.
static func event_named(event: InputEvent, in_family: String) -> String:
	if event is InputEventKey:
		var code: int = event.physical_keycode if event.physical_keycode else event.keycode
		return said("KEYNAME_", OS.get_keycode_string(code).to_upper())
	if event is InputEventMouseButton:
		return said("KEYNAME_", button_of(event).to_upper().replace("_", " "))
	var button := button_of(event)
	var glyphs: Dictionary = GLYPHS.get(in_family, GLYPHS["xbox"])
	if glyphs.has(button):
		return said("PAD_", glyphs[button]) if in_family == "generic" else glyphs[button]
	if event is InputEventJoypadMotion and button in ["l_stick", "r_stick"]:
		var stick := "LS" if button == "l_stick" else "RS"
		var axis: int = event.axis
		var vertical := axis == JOY_AXIS_LEFT_Y or axis == JOY_AXIS_RIGHT_Y
		var way := ("DOWN" if event.axis_value > 0 else "UP") if vertical \
			else ("RIGHT" if event.axis_value > 0 else "LEFT")
		return said("PAD_", "%s %s" % [stick, way])
	if button == "" and event is InputEventJoypadButton:
		return said("PAD_", "BUTTON %d" % event.button_index)
	if button == "" and event is InputEventJoypadMotion:
		return said("PAD_", "AXIS %d%s" % [event.axis, "+" if event.axis_value > 0 else "-"])
	return said("PAD_", SPOKEN.get(button, button.to_upper()))


## The input a stored code stands for, as the remap kit writes it: `key:<keycode>`,
## `mouse:<n>`, `button:<n>` or `axis:<n>:<-1 or 1>`; null for anything else.
static func event_of(code: String) -> InputEvent:
	var parts := code.split(":")
	if parts.size() < 2 or not parts[1].is_valid_int():
		return null
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
			if parts.size() < 3:
				return null
			var motion := InputEventJoypadMotion.new()
			motion.axis = int(parts[1]) as JoyAxis
			motion.axis_value = float(parts[2])
			return motion
	return null


## A stored code in words in a family, bound or not (§PW431): what a screen showing a
## pad's every button labels each with. The code itself where it is no code.
static func named_code(code: String, in_family := "xbox") -> String:
	var event := event_of(code)
	return event_named(event, in_family) if event != null else code


## A binding's codes in words, the keys' then the pad's in `in_family`, as a controls
## row reads it: `SPACE / ENTER   |   A`, `-` for a half with nothing bound.
static func describe(codes: Array, in_family := "xbox") -> String:
	var keys := PackedStringArray()
	var pad := PackedStringArray()
	for code: String in codes:
		if code.begins_with("key:") or code.begins_with("mouse:"):
			keys.append(named_code(code, "keyboard"))
		else:
			pad.append(named_code(code, in_family))
	return "%s   |   %s" % [" / ".join(keys) if keys else "-", " / ".join(pad) if pad else "-"]


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


## `fill` drawn in icons, for a RichTextLabel (§PW551): the same `{action}` and `{move}`
## marks a help row holds, each the icon of what player `player` presses for it in the
## family they hold (or `in_family`), the word `fill` would give where that family has
## no icon for it, and `{move}` one stick's icon where all four moves are that stick's,
## else each move's in turn. So a row is written once and drawn as words or as icons.
func fill_bbcode(text: String, player := 0, in_family := "", size := 32) -> String:
	if not "{" in text:
		return text
	var wanted := in_family if in_family != "" else family_for(player)
	if "{move}" in text:
		text = text.replace("{move}", _moves_drawn(player, wanted, size))
	var mark := RegEx.create_from_string("\\{([A-Za-z0-9_]+)\\}")
	for found in mark.search_all(text):
		text = text.replace(found.get_string(0),
			_drawn(StringName(found.get_string(1)), player, wanted, size))
	return text


## One action as player `player` presses it in `wanted`: its icon, else its word.
func _drawn(action: StringName, player: int, wanted: String, size: int) -> String:
	var path := icon_path(action_of(action, player), wanted)
	return "[img=%d]%s[/img]" % [size, path] if path != "" \
		else named(action, player, wanted)


## The four moves drawn: one stick's icon where all four are that stick, else each.
func _moves_drawn(player: int, wanted: String, size: int) -> String:
	var sticks := moves.map(func(one: String) -> String:
		var event := event_for(action_of(one, player), wanted)
		return button_of(event) if event is InputEventJoypadMotion else "")
	if sticks[0] != "" and sticks.all(func(one: String) -> bool: return one == sticks[0]):
		return _drawn(StringName(moves[0]), player, wanted, size)
	return " ".join(moves.map(func(one: String) -> String:
		return _drawn(StringName(one), player, wanted, size)))


## Text for a RichTextLabel with each `[action=jump]` drawn as that action's icon.
func bbcode(text: String, size := 32) -> String:
	var tag := RegEx.create_from_string("\\[action=([A-Za-z0-9_]+)\\]")
	var out := text
	for found in tag.search_all(text):
		var path := icon_path(StringName(found.get_string(1)))
		var drawn := "[img=%d]%s[/img]" % [size, path] if path != "" else found.get_string(1)
		out = out.replace(found.get_string(0), drawn)
	return out
