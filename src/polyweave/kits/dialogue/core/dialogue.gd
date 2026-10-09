class_name PolyweaveDialogue
extends Control
## A dialogue box (polyweave kit "dialogue", §PW353): a line typed at RATE characters a
## second, completed whole on the first press and followed by the next on the second,
## by the confirm button of the family in the player's hands, as the menus kit has it: a
## Switch pad confirms on its east button, every other pad on its south one, and the
## keyboard on ui_accept. A mouse click does the same.
##
## A line is {"key": a key of the string table, "speaker": a key naming who speaks,
## "portrait": a picture}, the last two optional. The box shows the key and Godot
## translates it, so a translation needs no change here. The kit carries no line and
## orders none: the sequences are the project's, in res://polyweave_dialogue.gd as
## SEQUENCES, a name to its lines, with RATE beside them.
##
## The look is the project's: the box is its scene, kits/dialogue/dialogue_box.tscn,
## with a Label named Text, and optionally a Label named Speaker and a TextureRect named
## Portrait, wherever it places them.

signal line_shown(key: String)
signal finished

const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")
const PROJECT := "res://polyweave_dialogue.gd"
## the pad button that confirms in each family, as the menus kit has it
const CONFIRM := {"xbox": JOY_BUTTON_A, "playstation": JOY_BUTTON_A, "switch": JOY_BUTTON_B}
const DEFAULTS := {"RATE": 40.0, "SEQUENCES": {}, "BOX": "res://kits/dialogue/dialogue_box.tscn"}

## characters a second; the declared RATE where unset
@export var rate := 0.0
## the family whose convention confirm follows; the pad's own where unset
@export var family := ""

var lines: Array = []
var at := -1
var _shown := 0.0
var said: Array[String] = []


## what the project declares, each name it leaves out at the kit's default
static func declaration(project := PROJECT) -> Dictionary:
	var out := DEFAULTS.duplicate(true)
	if ResourceLoader.exists(project):
		var map := (load(project) as GDScript).get_script_constant_map()
		for key in map:
			out[key] = map[key]
	return out


## the project's box with a sequence's lines in it, ready to add to the tree
static func box(sequence: String) -> PolyweaveDialogue:
	var declared := declaration()
	var made := (load(str(declared["BOX"])) as PackedScene).instantiate() as PolyweaveDialogue
	made.lines = declared["SEQUENCES"].get(sequence, [])
	return made


func _ready() -> void:
	if rate <= 0.0:
		rate = float(declaration()["RATE"])
	if not lines.is_empty() and at == -1:
		play(lines)


## show `sequence` from its first line
func play(sequence: Array) -> void:
	lines = sequence
	at = -1
	visible = true
	advance()


## whether the line shown is still being typed
func typing() -> bool:
	var text := _text()
	return text != null and text.visible_characters != -1 \
		and text.visible_characters < text.get_total_character_count()


## the key of the line shown, or "" once the sequence is over
func key() -> String:
	return str(lines[at]["key"]) if at >= 0 and at < lines.size() else ""


## complete the line being typed, or show the next; past the last, finish
func press() -> void:
	if typing():
		_text().visible_characters = -1
		return
	advance()


func advance() -> void:
	at += 1
	if at >= lines.size():
		visible = false
		finished.emit()
		return
	var line: Dictionary = lines[at]
	var text := _text()
	text.text = str(line["key"])
	text.visible_characters = 0
	_shown = 0.0
	var speaker := find_child("Speaker", true, false) as Label
	if speaker != null:
		speaker.text = str(line.get("speaker", ""))
		speaker.visible = line.has("speaker")
	var portrait := find_child("Portrait", true, false) as TextureRect
	if portrait != null:
		portrait.texture = _picture(str(line.get("portrait", "")))
		portrait.visible = portrait.texture != null
	line_shown.emit(key())


func _text() -> Label:
	return find_child("Text", true, false) as Label


func _picture(path: String) -> Texture2D:
	if path == "":
		return null
	if ResourceLoader.exists(path):
		return load(path) as Texture2D
	var image := Image.load_from_file(path) if FileAccess.file_exists(path) else null
	if image == null:
		said.append("%s's portrait is %s, which is not a picture there" % [key(), path])
		return null
	return ImageTexture.create_from_image(image)


func _process(delta: float) -> void:
	if not typing():
		return
	_shown += delta * rate
	_text().visible_characters = mini(int(_shown), _text().get_total_character_count())


func _unhandled_input(event: InputEvent) -> void:
	if not is_visible_in_tree() or not event.is_pressed() or event.is_echo():
		return
	var confirm := false
	if event is InputEventJoypadButton:
		var held := family if family != "" else Prompts.family_of(Input.get_joy_name(event.device))
		confirm = (event as InputEventJoypadButton).button_index == CONFIRM.get(held, JOY_BUTTON_A)
	elif event is InputEventMouseButton:
		confirm = (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT
	else:
		confirm = event.is_action("ui_accept")
	if confirm:
		get_viewport().set_input_as_handled()
		press()
