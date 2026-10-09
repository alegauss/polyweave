class_name PolyweavePresence
extends CanvasLayer
## Nobody left at the controls (polyweave kit "presence", §PW356). When a pad disconnects
## the game pauses through the scene tree and says whose pad left, with the confirm
## button drawn in the family of that pad (the prompts kit's icons); it resumes when the
## pad comes back, or when any pad confirms by its own family's convention (a Switch pad
## on its east button, every other on its south one) or the keyboard on ui_accept. When
## the window loses focus it pauses too, and stays paused when focus returns until the
## player says so; a project meant to run in the background declares PAUSE_ON_FOCUS
## false. A game that was already paused stays paused when this resumes.
##
## The project's res://polyweave_presence.gd may declare PAUSE_ON_FOCUS, and LEFT and
## AWAY, the keys (through tr()) of the two messages; LEFT is given the player's number.

signal left(device: int, family: String)
signal resumed

const HERE := "res://addons/polyweave/presence/presence.gd"
const PROJECT := "res://polyweave_presence.gd"
const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")
## the pad button that confirms in each family, as the menus kit has it
const CONFIRM := {"xbox": JOY_BUTTON_A, "playstation": JOY_BUTTON_A, "switch": JOY_BUTTON_B}
const DEFAULTS := {
	"PAUSE_ON_FOCUS": true,
	"LEFT": "Player %d's controller disconnected",
	"AWAY": "Paused",
}

var declared := {}
var pause_on_focus := true
## why the game is held: "pad", "focus", or "" when it is not
var why := ""
## the pad that left, or -1
var absent := -1
## the family whose confirm the message draws
var family := "xbox"
var message: Label
var confirm_icon: TextureRect
var _names := {}
var _was_paused := false

static var _shared: Node


## the one watcher, made the first time and put in the tree
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweavePresence"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


## what the project declares, each name it leaves out at the kit's default
static func declaration(project := PROJECT) -> Dictionary:
	var out := DEFAULTS.duplicate(true)
	if ResourceLoader.exists(project):
		var map := (load(project) as GDScript).get_script_constant_map()
		for key in map:
			out[key] = map[key]
	return out


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 120
	visible = false
	declared = declaration()
	pause_on_focus = bool(declared["PAUSE_ON_FOCUS"])
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	var row := HBoxContainer.new()
	message = Label.new()
	confirm_icon = TextureRect.new()
	confirm_icon.custom_minimum_size = Vector2(48, 48)
	confirm_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	confirm_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	row.add_child(message)
	row.add_child(confirm_icon)
	panel.add_child(row)
	add_child(panel)


func _ready() -> void:
	for device in Input.get_connected_joypads():
		named(device, Input.get_joy_name(device))
	Input.joy_connection_changed.connect(_connection)


## remember a pad's name, so its family is known once it has gone
func named(device: int, joy_name: String) -> void:
	if joy_name != "":
		_names[device] = joy_name


func family_of(device: int) -> String:
	var name := Input.get_joy_name(device)
	return Prompts.family_of(name if name != "" else str(_names.get(device, "")))


func _connection(device: int, connected: bool) -> void:
	if connected:
		named(device, Input.get_joy_name(device))
		if why == "pad" and device == absent:
			resume()
		return
	if why == "":
		family = family_of(device)
		absent = device
		_hold("pad", tr(str(declared["LEFT"])) % (device + 1))
		left.emit(device, family)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and pause_on_focus and why == "":
		family = Prompts.shared().family if Prompts.shared().family != "keyboard" else "xbox"
		_hold("focus", tr(str(declared["AWAY"])))


func _hold(reason: String, text: String) -> void:
	why = reason
	_was_paused = get_tree().paused
	get_tree().paused = true
	message.text = text
	var button := "east" if CONFIRM.get(family, JOY_BUTTON_A) == JOY_BUTTON_B else "south"
	var path := "%s/%s/%s_64.png" % [Prompts.shared().icons_root, family, button]
	confirm_icon.texture = _picture(path)
	confirm_icon.set_meta("path", path)
	visible = true


## let the game go on, back to however paused it was before
func resume() -> void:
	if why == "":
		return
	why = ""
	absent = -1
	visible = false
	get_tree().paused = _was_paused
	resumed.emit()


func _picture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		return load(path)
	var image := Image.load_from_file(ProjectSettings.globalize_path(path)) \
		if FileAccess.file_exists(path) else null
	return ImageTexture.create_from_image(image) if image != null else null


func _input(event: InputEvent) -> void:
	if why == "" or not event.is_pressed() or event.is_echo():
		return
	var go_on := false
	if event is InputEventJoypadButton:
		var held := family_of(event.device)
		go_on = (event as InputEventJoypadButton).button_index == CONFIRM.get(held, JOY_BUTTON_A)
	else:
		go_on = event.is_action("ui_accept")
	if go_on:
		get_viewport().set_input_as_handled()
		resume()
