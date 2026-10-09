class_name PolyweaveCredits
extends ScrollContainer
## A credits screen (polyweave kit "credits", §PW350) drawn from the file
## provenance.credits writes at build time: the people and roles the project declares,
## then every credit a licence requires, with nothing typed by hand, so it lists
## exactly what the records hold. It scrolls at `rate` pixels a second, and any key,
## mouse button or pad button of any family ends it.
##
## The look is the project's Theme: the screen adds labels, never a style.

signal finished

## the file provenance.credits wrote, out=
@export var file := "res://credits.json"
## how fast it scrolls, in pixels a second
@export var rate := 40.0

var lines: Array[String] = []
var _list: VBoxContainer
var _offset := 0.0
var _ended := false


func _ready() -> void:
	fill()


## build the lines from `file`, once
func fill() -> void:
	if _list != null:
		return
	set_anchors_preset(Control.PRESET_FULL_RECT)
	horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_child(_list)
	for line in read(file):
		var label := Label.new()
		label.text = line
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_list.add_child(label)
		lines.append(line)


## the lines the screen shows: each person with their role, then each credit owed
static func read(path: String) -> Array[String]:
	var out: Array[String] = []
	var held: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not held is Dictionary:
		push_error("credits: %s is not a file provenance.credits wrote" % path)
		return out
	for person in held.get("people", []):
		out.append("%s — %s" % [person.get("role", ""), person.get("name", "")]
			if str(person.get("role", "")) != "" else str(person.get("name", "")))
	for owed in held.get("owed", []):
		out.append(str(owed.get("credit", "")))
	return out


func _process(delta: float) -> void:
	if _ended or _list == null:
		return
	_offset += rate * delta
	scroll_vertical = int(_offset)
	var bottom := _list.size.y - size.y
	if bottom > 0.0 and _offset >= bottom:
		_end()


func _input(event: InputEvent) -> void:
	if _ended or not event.is_pressed() or event.is_echo():
		return
	if event is InputEventKey or event is InputEventMouseButton or event is InputEventJoypadButton:
		get_viewport().set_input_as_handled()
		_end()


func _end() -> void:
	if not _ended:
		_ended = true
		finished.emit()
