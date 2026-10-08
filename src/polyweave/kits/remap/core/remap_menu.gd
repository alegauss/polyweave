extends VBoxContainer
## A remap screen (polyweave kit "remap", §PW345): a row per rebindable action, its key
## and its pad binding drawn as the prompts kit's icons. Pressing a binding listens for
## the next key, button or stick; a clash is swapped and said; Escape stops listening.
## Under the rows, the stick's deadzone, its inverted vertical and a reset to defaults.

const Bindings := preload("res://addons/polyweave/remap/bindings.gd")
const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")

## the actions on the screen; every project action but the ui_ ones where unset
@export var actions: Array[String] = []

var bindings: Bindings
var _listening := ""
var _listening_pad := false
var _said: Label
var _rows: VBoxContainer
var _prompts: Node


func _ready() -> void:
	bindings = Bindings.new(actions)
	bindings.load_kept()
	_prompts = Prompts.new()
	add_child(_prompts)
	_rows = VBoxContainer.new()
	add_child(_rows)
	_said = Label.new()
	add_child(_said)
	var deadzone := HSlider.new()
	deadzone.min_value = 0.05
	deadzone.max_value = 0.95
	deadzone.step = 0.05
	deadzone.value = bindings.deadzone
	deadzone.value_changed.connect(bindings.set_deadzone)
	_row("deadzone", deadzone)
	var invert := CheckButton.new()
	invert.button_pressed = bindings.invert_vertical
	invert.toggled.connect(bindings.set_invert_vertical)
	_row("invert vertical", invert)
	var reset := Button.new()
	reset.text = "reset"
	reset.icon = _own("reset")
	reset.pressed.connect(func() -> void:
		bindings.reset()
		_said.text = "every binding is back to the game's own"
		_draw_rows())
	add_child(reset)
	_draw_rows()


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
		label.text = action
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
	_said.text = "press the new %s for %s" % ["button" if pad else "key", action]
	_draw_rows()


func _input(event: InputEvent) -> void:
	if _listening == "" or not event.is_pressed() or event.is_echo():
		return
	if event is InputEventKey and (event as InputEventKey).physical_keycode == KEY_ESCAPE:
		_listening = ""
		_said.text = ""
		_draw_rows()
		_handled()
		return
	var code := Bindings.encode(event)
	if code == "" or Bindings.on_keys(code) == _listening_pad:
		return
	_handled()
	_said.text = take(_listening, event)
	_listening = ""
	_draw_rows()


func _handled() -> void:
	var viewport := get_viewport()
	if viewport != null:
		viewport.set_input_as_handled()


## rebind `action` to `event` and say what changed, the swap with it
func take(action: String, event: InputEvent) -> String:
	var code := Bindings.encode(event)
	var before := bindings.current()
	if not bindings.rebind(action, event):
		return "%s cannot be bound to that" % action
	var after := bindings.current()
	for other in after:
		if other != action and before[other] != after[other] and (before[other] as Array).has(code):
			return "%s took it from %s, which has %s's old binding now" % [action, other, action]
	return "%s is bound anew" % action
