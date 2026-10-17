extends VBoxContainer
## A remap screen (polyweave kit "remap", §PW345): a row per rebindable action, its key
## and its pad binding drawn as the prompts kit's icons. Pressing a binding listens for
## the next key, button or stick; a clash is swapped and said; Escape stops listening.
## Under the rows, the stick's deadzone, its inverted vertical, a reset to defaults and
## the pad drawn as a picture to bind on (§PW428).
##
## It listens through the release (§PW432): a press is held on to and binds when it is
## let go, so a stick binds the direction it was pushed; a press held `hold_to_cancel`
## seconds cancels instead, and so does nothing pressed in `listen_seconds`. Each row
## reads the action's declared label, and every word goes through the game's string
## table under REMAP_, with English where it has no row.

const _PwBindings := preload("res://addons/polyweave/remap/bindings.gd")
const _PwPrompts := preload("res://addons/polyweave/prompts/prompts.gd")
## the screen's own words, by the row each is asked under as REMAP_<NAME>
const WORDS := {
	"deadzone": "Deadzone", "invert": "Invert vertical", "reset": "Reset",
	"pad": "Pad", "reset_done": "Every binding is back to the game's own",
	"press_key": "Press the new key for %s, or hold it to cancel",
	"press_button": "Press the new button for %s, or hold it to cancel",
	"cannot": "%s cannot be bound to that", "bound": "%s is bound anew",
	"swapped": "%s took it from %s, which has %s's old binding now",
}

## the actions on the screen; the declaration's labelled ones in its order, else every
## project action but the ui_ ones
@export var actions: Array[String] = []
## seconds a press is held before it cancels instead of binding
@export var hold_to_cancel := 1.0
## seconds the screen listens before it gives up
@export var listen_seconds := 5.0

var bindings: _PwBindings
var _listening := ""
var _listening_pad := false
## the code pressed while listening, bound once it is let go
var _capture := ""
var _held := 0.0
var _left := 0.0
var _said: Label
var _rows: VBoxContainer
var _prompts: Node


## one of the screen's words, as the game's table says it under REMAP_, else English;
## `args` fill its %s marks
static func said(name: String, args: Array = []) -> String:
	var key := "REMAP_" + name.to_upper()
	var text := String(TranslationServer.translate(key))
	text = String(WORDS.get(name, name)) if text == key else text
	return text % args if not args.is_empty() else text


func _ready() -> void:
	bindings = _PwBindings.new(actions)
	bindings.load_kept()
	_prompts = _PwPrompts.new()
	add_child(_prompts)
	_rows = VBoxContainer.new()
	add_child(_rows)
	_said = Label.new()
	add_child(_said)
	var deadzone := HSlider.new()
	deadzone.min_value = bindings.deadzone_least
	deadzone.max_value = bindings.deadzone_most
	deadzone.step = 0.05
	deadzone.value = bindings.deadzone
	deadzone.value_changed.connect(bindings.set_deadzone)
	_row(said("deadzone"), deadzone)
	var invert := CheckButton.new()
	invert.button_pressed = bindings.invert_vertical
	invert.toggled.connect(bindings.set_invert_vertical)
	_row(said("invert"), invert)
	# the game's own pad options (§PW433): a switch for a true or false, a slider over
	# a number's range, each named through the table as REMAP_<NAME>
	for name: String in bindings.declared_options:
		var declared: Array = bindings.declared_options[name]
		var set_to := func(value: Variant) -> void: bindings.set_option(name, value)
		if declared[0] is bool:
			var switch := CheckButton.new()
			switch.button_pressed = bool(bindings.option(name))
			switch.toggled.connect(set_to)
			_row(said(name), switch)
		elif declared.size() >= 3:
			var slider := HSlider.new()
			slider.min_value = float(declared[1])
			slider.max_value = float(declared[2])
			slider.step = 1.0 if declared[0] is int \
				else (slider.max_value - slider.min_value) / 20.0
			slider.value = float(bindings.option(name))
			slider.value_changed.connect(set_to)
			_row(said(name), slider)
	var reset := Button.new()
	reset.text = said("reset")
	reset.icon = _own("reset")
	reset.pressed.connect(func() -> void:
		bindings.reset()
		_said.text = said("reset_done")
		_draw_rows())
	add_child(reset)
	var pad := Button.new()
	pad.text = said("pad")
	pad.pressed.connect(open_pad)
	add_child(pad)
	_draw_rows()


## the pad as a picture over the screen, binding through the same store (§PW428)
func open_pad() -> CanvasLayer:
	var screen: CanvasLayer = load("res://addons/polyweave/remap/pad_screen.gd").new()
	screen.bindings = bindings
	screen.closed.connect(_draw_rows)
	get_tree().root.add_child(screen)
	return screen


## one of the kit's own icons, imported or straight from the file, or null
func _own(named: String) -> Texture2D:
	var path := "res://addons/polyweave/remap/icons/remap/%s_64.png" % named
	if ResourceLoader.exists(path):
		return load(path)
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(ProjectSettings.globalize_path(path))
	return ImageTexture.create_from_image(image) if image != null else null


func _row(named: String, control: Control) -> void:
	var row := HBoxContainer.new()
	var label := Label.new()
	label.text = named
	label.custom_minimum_size.x = 160
	row.add_child(label)
	control.custom_minimum_size.x = 160
	row.add_child(control)
	add_child(row)


func _draw_rows() -> void:
	for child in _rows.get_children():
		child.queue_free()
	for action in bindings.actions:
		var row := HBoxContainer.new()
		var label := Label.new()
		label.text = bindings.label(action)
		label.custom_minimum_size.x = 160
		row.add_child(label)
		for pad in [false, true]:
			var button := Button.new()
			button.custom_minimum_size = Vector2(56, 56)
			button.expand_icon = true
			var family: String = "keyboard" if not pad else (
				_prompts.family if _prompts.family != "keyboard" else "xbox")
			button.icon = _prompts.icon(action, family)
			if button.icon == null:
				button.text = "-"
			if _listening == action and _listening_pad == pad:
				button.icon = _own("listening")
				button.text = "" if button.icon != null else "..."
			button.pressed.connect(_listen.bind(action, pad))
			row.add_child(button)
		_rows.add_child(row)


func _listen(action: String, pad: bool) -> void:
	_listening = action
	_listening_pad = pad
	_capture = ""
	_held = 0.0
	_left = listen_seconds
	_said.text = said("press_button" if pad else "press_key", [bindings.label(action)])
	_draw_rows()


func _input(event: InputEvent) -> void:
	if _listening != "" and capture(event):
		_handled()


## take one input while listening: a press on the half asked is held on to, and its
## release binds it; Escape stops listening. True where the event was the screen's.
func capture(event: InputEvent) -> bool:
	if _listening == "":
		return false
	if _capture == "":
		if event is InputEventKey and event.is_pressed() \
				and (event as InputEventKey).physical_keycode == KEY_ESCAPE:
			_stop("")
			return true
		if not _PwBindings.is_press(event):
			return false
		var code := _PwBindings.encode(event)
		if code == "" or _PwBindings.on_keys(code) == _listening_pad:
			return false
		_capture = code
		_held = 0.0
		return true
	if not _PwBindings.is_release(event, _capture):
		return false
	var action := _listening
	var code := _capture
	_stop(take(action, _PwBindings.decode(code)))
	return true


## run the clocks: a press held long enough cancels, and so does nothing pressed in time
func _process(delta: float) -> void:
	if _listening == "":
		return
	if _capture != "":
		_held += delta
		if _held >= hold_to_cancel:
			_stop("")
		return
	_left -= delta
	if _left <= 0.0:
		_stop("")


func _stop(saying: String) -> void:
	_listening = ""
	_capture = ""
	_said.text = saying
	_draw_rows()


func _handled() -> void:
	var viewport := get_viewport()
	if viewport != null:
		viewport.set_input_as_handled()


## rebind `action` to `event` and say what changed, the swap with it
func take(action: String, event: InputEvent) -> String:
	var code := _PwBindings.encode(event)
	var before := bindings.current()
	var named := bindings.label(action)
	if not bindings.rebind(action, event):
		return said("cannot", [named])
	var after := bindings.current()
	for other in after:
		if other != action and before[other] != after[other] \
				and (before[other] as Array).has(code):
			return said("swapped", [named, bindings.label(other), named])
	return said("bound", [named])
