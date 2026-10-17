extends CanvasLayer
## The pad as a picture (polyweave kit "remap", §PW428): every button, trigger, stick
## direction and d-pad direction of the pad in use, named in its layout's glyphs where it
## sits on the pad, each with a leader line to the action it holds, or "free". Opened
## from the remap screen; extracted from Starship's pad screen.
##
## Pressing a real button lights it here, so the player learns the pad by touching it. Up
## and down pick a place; accept on it chooses an action for it, left and right go
## through them, and accept binds it through `PolyweaveBindings.rebind`, the same swap
## rule as the remap screen: never shared, always swapped. Cancel backs out of the
## choice, and out of the screen.
##
## Where each place sits is a layout's spots table, `pads/<layout>.json` beside this
## script, read as {"slots": [{"code", "at": [x, y] from 0 to 1 across the pad, "side":
## -1 or 1, the side its label stands on}]} in the order up and down go through them.
## `pads/<layout>.png`, drawn by picture.vector from the kit's `pads/<layout>.svg` whose
## spots group the table is held to, is the pad behind the places: over it each place is
## a ring and its glyph stands in its label. A layout with no table of its own stands on
## the Xbox one, named in its own glyphs.

signal closed

const _PwBindings := preload("res://addons/polyweave/remap/bindings.gd")
const _PwPrompts := preload("res://addons/polyweave/prompts/prompts.gd")
const PADS := "res://addons/polyweave/remap/pads"
const LAYOUTS: Array[String] = ["xbox", "playstation", "switch"]
const DIM := Color(0.55, 0.65, 0.8)
const LIT := Color(1, 0.85, 0.3)
const PRESSED := Color(0.4, 1.0, 0.9)
const FREE := Color(0.4, 0.45, 0.55)
## what the screen says where the game's string table has no PAD_ row for it
const WORDS := {
	"title": "Pad", "free": "free",
	"help": "up and down pick a place, accept chooses what it does, cancel leaves",
	"choose": "left and right go through the actions, accept binds, cancel backs out",
}

## seconds a pressed button stays lit
@export var lit_for := 0.5
## the layout drawn; empty follows the pad in use
@export var layout := ""

## the store the screen binds through; one of its own where none is given
var bindings: _PwBindings
## the layout's places, as its spots table lists them
var slots: Array = []
## the place picked, an index into `slots`
var picked := 0
## while choosing an action for the picked place, the action offered, else ""
var choosing := ""
## code -> seconds it stays lit
var _lit := {}
var _board: Control
var _picture: TextureRect
## where each place sits on the screen now, the leaders' far ends
var _spots: Array[Vector2] = []
var _over: Control
var _labels: Array[Label] = []
var _marks: Array[Label] = []
var _help: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 11
	if bindings == null:
		bindings = _PwBindings.new()
		bindings.load_kept()
	if layout == "":
		var family: String = _PwPrompts.shared().family
		# a generic pad keeps its own names over the Xbox places, with no picture
		layout = family if family != "keyboard" else "xbox"
	slots = spots(layout)
	var shade := ColorRect.new()
	shade.color = Color(0, 0.01, 0.04, 0.92)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(shade)
	var heading := Label.new()
	heading.text = said("title")
	heading.set_anchors_preset(Control.PRESET_TOP_WIDE)
	heading.offset_top = 40
	heading.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	heading.add_theme_font_size_override("font_size", 48)
	add_child(heading)
	_board = Control.new()
	_board.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_board)
	_picture = TextureRect.new()
	_picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_picture.texture = picture(layout)
	_board.add_child(_picture)
	# the leaders and rings are drawn over the picture, under the words
	_over = Control.new()
	_over.set_anchors_preset(Control.PRESET_FULL_RECT)
	_over.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_over.draw.connect(_draw_leaders)
	_board.add_child(_over)
	for slot: Dictionary in slots:
		_spots.append(Vector2.ZERO)
		var mark := Label.new()
		mark.add_theme_font_size_override("font_size", 20)
		mark.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_board.add_child(mark)
		_marks.append(mark)
		var label := Label.new()
		label.add_theme_font_size_override("font_size", 24)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT \
			if int(slot["side"]) < 0 else HORIZONTAL_ALIGNMENT_LEFT
		_board.add_child(label)
		_labels.append(label)
	_help = Label.new()
	_help.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_help.offset_top = -80
	_help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_help.add_theme_font_size_override("font_size", 26)
	_help.add_theme_color_override("font_color", DIM)
	add_child(_help)
	show_pad()


## a layout's places, read off its spots table, or the Xbox one's where it has none
static func spots(of_layout: String) -> Array:
	for named in [of_layout, "xbox"]:
		var path := "%s/%s.json" % [PADS, named]
		if FileAccess.file_exists(path):
			var read: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
			if read is Dictionary:
				return (read as Dictionary).get("slots", [])
	return []


## a layout's picture of the pad, imported or straight from the file, or null where it
## has none
static func picture(of_layout: String) -> Texture2D:
	var path := "%s/%s.png" % [PADS, of_layout]
	if ResourceLoader.exists(path):
		return load(path)
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(ProjectSettings.globalize_path(path))
	return ImageTexture.create_from_image(image) if image != null else null


## what a place is called on a layout's pad, as the prompts kit names a code (§PW431)
static func glyph(code: String, of_layout: String) -> String:
	return _PwPrompts.named_code(code, of_layout) if _PwBindings.decode(code) != null else ""


## the action `code` is bound to, or "" where it is free
func holder(code: String) -> String:
	var now := bindings.current()
	for action in now:
		if (now[action] as Array).has(code):
			return action
	return ""


## whether the place `code` names is lit by a press now
func lit(code: String) -> bool:
	return _lit.has(code)


## what the label of place `index` reads: the action it holds, as the table says it
func held_text(index: int) -> String:
	var code: String = slots[index]["code"]
	var action := choosing if index == picked and choosing != "" else holder(code)
	return _PwPrompts.said("ACTION_", action) if action != "" else said("free")


## a word of the screen's own, as the game's string table says it under PAD_, else its
## English one
static func said(name: String) -> String:
	var key := "PAD_" + name.to_upper()
	var text := String(TranslationServer.translate(key))
	return WORDS.get(name, name) if text == key else text


func show_pad() -> void:
	if _board == null:
		return
	var size := _board.get_viewport_rect().size
	var pad := Rect2(size.x * 0.24, size.y * 0.18, size.x * 0.52, size.y * 0.62)
	_picture.position = pad.position
	_picture.size = pad.size
	# each side's labels stand one under another, in the order of their places down the pad
	var row := {}
	for side in [-1, 1]:
		var mine := range(slots.size()).filter(func(i: int) -> bool:
			return int(slots[i]["side"]) == side)
		mine.sort_custom(func(a: int, b: int) -> bool:
			return _at(a).y < _at(b).y or (_at(a).y == _at(b).y and _at(a).x < _at(b).x))
		for k in mine.size():
			row[mine[k]] = pad.position.y + pad.size.y * k / maxf(mine.size() - 1, 1)
	for i in slots.size():
		var code: String = slots[i]["code"]
		var side := int(slots[i]["side"])
		var mark := _marks[i]
		mark.text = glyph(code, layout)
		mark.visible = _picture.texture == null
		_spots[i] = pad.position + pad.size * _at(i)
		mark.size = Vector2(130, 30)
		mark.position = _spots[i] - mark.size * 0.5
		var tint := PRESSED if lit(code) else (LIT if i == picked else DIM)
		mark.add_theme_color_override("font_color", tint)
		var label := _labels[i]
		label.text = held_text(i)
		var free := label.text == said("free")
		if not mark.visible:
			# the glyph stands beside the action, on the side nearer the pad
			label.text = "%s  %s" % ([label.text, mark.text] if side < 0
				else [mark.text, label.text])
		label.size = Vector2(size.x * 0.2, 30)
		label.position = Vector2(
			pad.position.x - label.size.x - 60 if side < 0 else pad.end.x + 60,
			float(row[i]) - 15)
		label.add_theme_color_override("font_color", PRESSED if lit(code)
			else (LIT if i == picked else (FREE if free else DIM)))
	_help.text = said("choose" if choosing != "" else "help")
	_over.queue_redraw()


func _at(index: int) -> Vector2:
	var at: Array = slots[index]["at"]
	return Vector2(float(at[0]), float(at[1]))


## a line from each label to the place it names; over the picture, a ring on the place
func _draw_leaders() -> void:
	var drawn := _picture.texture != null
	for i in slots.size():
		var side := float(slots[i]["side"])
		var label := _labels[i]
		var from := Vector2(label.position.x + label.size.x + 8, label.position.y + 15) \
			if side < 0 else Vector2(label.position.x - 8, label.position.y + 15)
		var spot := _spots[i]
		# over the picture the line stops at the ring; over nothing, short of the glyph
		var to := spot + (spot.direction_to(from) * 14.0 if drawn
			else Vector2(-45 * side, 0))
		var pressed := lit(slots[i]["code"])
		var tint := PRESSED if pressed else (LIT if i == picked
			else Color(0.3, 0.45, 0.7, 0.6))
		var bold := i == picked or pressed
		_over.draw_line(from, to, tint, 2.0 if bold else 1.0, true)
		if drawn:
			_over.draw_arc(spot, 14, 0, TAU, 32, tint if bold
				else Color(tint, 0.35), 3.0 if bold else 1.5, true)


func _process(delta: float) -> void:
	for code: String in _lit.keys():
		_lit[code] -= delta
		if _lit[code] <= 0.0:
			_lit.erase(code)
			show_pad()


## a real button pressed lights its place on the pad; the screen's own moves are the
## project's ui_ actions, so it is worked by whatever pad or keys the game has
func _input(event: InputEvent) -> void:
	var pressed := (event is InputEventJoypadButton and event.is_pressed()) \
		or event is InputEventJoypadMotion
	if pressed:
		# a stick inside the press threshold encodes to nothing, and lights nothing
		var code := _PwBindings.encode(event)
		if code != "" and slots.any(func(slot: Dictionary) -> bool: return slot["code"] == code):
			_lit[code] = lit_for
			show_pad()
	if event.is_echo():
		return
	for move in ["ui_up", "ui_down", "ui_left", "ui_right", "ui_accept", "ui_cancel"]:
		if InputMap.has_action(move) and event.is_action_pressed(move):
			press(move)
			var viewport := get_viewport()
			if viewport != null:
				viewport.set_input_as_handled()
			return


## what one move does on the screen
func press(move: String) -> void:
	if slots.is_empty():
		close()
		return
	var all: Array = bindings.actions
	match move:
		"ui_up", "ui_down":
			if choosing == "":
				picked = posmod(picked + (1 if move == "ui_down" else -1), slots.size())
		"ui_left", "ui_right":
			if choosing != "":
				var step := 1 if move == "ui_right" else -1
				choosing = all[posmod(all.find(choosing) + step, all.size())]
		"ui_accept":
			var code: String = slots[picked]["code"]
			if choosing == "":
				var held := holder(code)
				choosing = held if held != "" else all[0]
			else:
				bindings.rebind(choosing, _PwBindings.decode(code))
				choosing = ""
		"ui_cancel":
			if choosing != "":
				choosing = ""
			else:
				close()
				return
	show_pad()


func close() -> void:
	closed.emit()
	queue_free()
