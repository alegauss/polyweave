class_name PolyweaveAccess
extends Node
## The accessibility options a game consults (polyweave kit "access", §PW355), each one
## a row of the options kit's accessibility tab:
##
## - the text scale, applied through the project's Theme (its default font size, or
##   Godot's fallback size where it has none), so every Label and Button that sets no
##   size of its own grows with it;
## - shake and flashes, two switches the game's own effects ask through `shake(amount)`
##   and `flash(strength)`, which answer the amount, or nothing where the player
##   switched it off;
## - a colourblind filter over the whole screen, the correction for protanopia,
##   deuteranopia or tritanopia (filters.gd), or "off";
## - subtitles: `subtitle(player, key)` shows the key's line, through tr(), at the foot
##   of the screen while the player plays (the one the audio kit's say() answers, for a
##   line on the Voice bus), and clears it when the player stops;
## - hold or toggle: with it on, `held(action)` turns on at one press and off at the
##   next, for each action the project lists in HELD (every action where it lists none).
##
## The project's res://polyweave_access.gd may declare SCALES, HELD, SCREENS (the
## scenes the proof lays out at the largest scale), and SHAKE_RUN with RUN_SECONDS (a
## scene that shakes the camera through `shake`, which the proof runs with shake off), and
## COLOUR_PAIRS, colours that must stay told apart, with PAIR_DELTA_E, how far apart
## (CIEDE2000) each must stay under every filter, and SUBTITLE_KEYS, lines the proof
## lays out as subtitles, each held to its box and to SUBTITLE_LINES rows (3), and
## FLASH_RUN with FLASH_SECONDS, a scene whose effects flash through `flash`, which the
## proof has captured and counted with flashes off and on.

const HERE := "res://addons/polyweave/access/access.gd"
const PROJECT := "res://polyweave_access.gd"
const DEFAULTS := {
	"SCALES": [1.0, 1.25, 1.5, 2.0],
	"HELD": [],
	"SCREENS": [],
	"SHAKE_RUN": "",
	"RUN_SECONDS": 1.0,
	"COLOUR_PAIRS": [],
	"PAIR_DELTA_E": 15.0,
	"SUBTITLE_KEYS": [],
	"SUBTITLE_LINES": 3,
	"FLASH_RUN": "",
	"FLASH_SECONDS": 2.0,
}
const Filters := preload("res://addons/polyweave/access/filters.gd")

var text_scale := 1.0
var shaking := true
var flashing := true
var toggling := false
var filter := "off"
var subtitles := true
var _caption: Label
var _speaking: AudioStreamPlayer
var _layer: CanvasLayer
var _veil: ColorRect
var declared := {}
var _base := -1
var _theme: Theme
var _toggled := {}

static var _shared: Node


## the one service every option goes through, made the first time
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweaveAccess"
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
	declared = declaration()
	var project := ThemeDB.get_project_theme()
	# the project's own Theme, every item kept, on the root window where every control
	# without a theme of its own finds it first; Godot's empty one where it has none
	_theme = project.duplicate() as Theme if project != null else Theme.new()
	_base = project.default_font_size if project != null and project.default_font_size > 0 \
		else ThemeDB.fallback_font_size


## the font size a control that sets none of its own draws at, at scale 1
func base_size() -> int:
	return _base


func _ready() -> void:
	get_tree().root.theme = _theme
	set_text_scale(text_scale)


func set_text_scale(scale: float) -> void:
	text_scale = scale
	_theme.default_font_size = int(round(_base * scale))


## the shake an effect asked for, or none where the player switched shake off
func shake(amount: Variant) -> Variant:
	return amount if shaking else amount * 0


## the flash an effect asked for, or none where the player switched flashes off
func flash(strength: float) -> float:
	return strength if flashing else 0.0


## put a deficiency's correction over the screen, or with `simulating` what it sees;
## "off" takes the filter away
func set_filter(deficiency: String, simulating := false) -> void:
	filter = deficiency
	if _layer == null:
		_layer = CanvasLayer.new()
		_layer.layer = 128
		_veil = ColorRect.new()
		_veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_veil.set_anchors_preset(Control.PRESET_FULL_RECT)
		_layer.add_child(_veil)
		add_child(_layer)
	_layer.visible = deficiency != "off"
	if deficiency != "off":
		_veil.material = Filters.material(deficiency, simulating)


## show `key`'s line while `player` plays, where the player keeps subtitles on
func subtitle(player: AudioStreamPlayer, key: String) -> void:
	if not subtitles or player == null:
		return
	var label := caption()
	label.text = key
	label.get_parent().visible = true
	_speaking = player
	if not player.finished.is_connected(_quiet):
		player.finished.connect(_quiet)


## the label a subtitle is shown in: at the foot of the screen, four fifths of its width
func caption() -> Label:
	if _caption == null:
		var layer := CanvasLayer.new()
		layer.layer = 100
		var panel := PanelContainer.new()
		panel.name = "Subtitle"
		panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
		panel.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
		panel.anchor_left = 0.1
		panel.anchor_right = 0.9
		panel.offset_left = 0
		panel.offset_right = 0
		panel.offset_top = -96
		panel.offset_bottom = -16
		panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
		panel.visible = false
		_caption = Label.new()
		_caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		panel.add_child(_caption)
		layer.add_child(panel)
		add_child(layer)
	return _caption


## the subtitle shown now, or "" where none is
func subtitled() -> String:
	return _caption.text if _caption != null and _caption.get_parent().visible else ""


func _quiet() -> void:
	if _caption != null:
		_caption.get_parent().visible = false
	_speaking = null


func _process(_delta: float) -> void:
	if _speaking != null and not _speaking.playing:
		_quiet()


func set_toggling(on: bool) -> void:
	toggling = on
	_toggled.clear()


## whether an action is held: pressed now, or, with hold or toggle on, toggled on
func held(action: String) -> bool:
	if toggling and _toggles(action):
		return _toggled.get(action, false)
	return Input.is_action_pressed(action)


func _toggles(action: String) -> bool:
	var listed: Array = declared["HELD"]
	return listed.is_empty() or listed.has(action)


func _input(event: InputEvent) -> void:
	if not toggling or event.is_echo():
		return
	for action in InputMap.get_actions():
		if not str(action).begins_with("ui_") and _toggles(action) \
				and event.is_action_pressed(action):
			_toggled[action] = not _toggled.get(action, false)
