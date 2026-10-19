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
## table under REMAP_, with English where it has no row. A game's declared CONFIRM
## presses the focused button as ui_accept does (§PW542).

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
	"map": "Map", "map_keep": "Keep %s? Press it again within %d s",
	"map_kept": "%s is kept", "map_back": "Back to %s",
	"button_names": "Button names", "automatic": "Automatic", "xbox": "Xbox",
	"playstation": "PlayStation", "switch": "Switch", "generic": "Generic",
}

var _names: Button

## seconds a map picked on the Map row is tried before it goes back, unless kept
@export var keep_seconds := 10.0

## the map the Map row shows, stepped by left and right before it is applied (§PW555)
var map_focus := ""
var _map: Button

## the actions on the screen; the shared store's where unset, which are the
## declaration's labelled ones in its order, else every project action but the ui_ ones
@export var actions: Array[String] = []
## seconds a press is held before it cancels instead of binding
@export var hold_to_cancel := 1.0
## seconds the screen listens before it gives up
@export var listen_seconds := 5.0

## the screen began listening for `action`'s next input (§PW541): a host game keeps its
## own back and tab inputs out of the way until `listened`
signal listening(action: String)
## the screen stopped listening for `action`, bound or cancelled
signal listened(action: String)

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
## action -> [its key button, its pad button], built once and painted in place, so the
## button a pad focused is still there once it binds (§PW541)
var _buttons := {}


## one of the screen's words, as the game's table says it under REMAP_, else English;
## `args` fill its %s marks
static func said(name: String, args: Array = []) -> String:
	var key := "REMAP_" + name.to_upper()
	var text := String(TranslationServer.translate(key))
	text = String(WORDS.get(name, name)) if text == key else text
	return text % args if not args.is_empty() else text


func _ready() -> void:
	# The game's one store (§PW540), so a rebind here is what the game reads at once,
	# and the players kit, listening to it, keeps each player's pad on their own actions.
	if bindings == null:
		bindings = _PwBindings.shared()
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
	# The ready maps (§PW555): left and right step, a press tries one, a second keeps it.
	_map = Button.new()
	_map.pressed.connect(press_map)
	_map.gui_input.connect(_map_input)
	_row(said("map"), _map)
	_paint_map()
	# Which buttons the pad in use has, where its name hides its maker (§PW556).
	_names = Button.new()
	_names.pressed.connect(func() -> void: cycle_names())
	_row(said("button_names"), _names)
	_paint_names()
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
		_paint()
		_paint_map())
	add_child(reset)
	var pad := Button.new()
	pad.text = said("pad")
	pad.pressed.connect(open_pad)
	add_child(pad)
	_draw_rows()


func _map_input(event: InputEvent) -> void:
	for way in [["ui_left", -1], ["ui_right", 1]]:
		if event.is_action_pressed(way[0]):
			step_map(way[1])
			_map.accept_event()


## show the map `step` along on the Map row, not yet applied
func step_map(step: int) -> void:
	map_focus = bindings.map_after(map_focus, step)
	_paint_map()


## try the map the row shows, on a countdown; pressed again while it runs, keep it
func press_map() -> void:
	if bindings.trial_left() >= 0.0:
		bindings.keep_map()
		_said.text = said("map_kept", [bindings.map_label(bindings.map_name)])
	else:
		var name := map_focus if map_focus != "" else bindings.map_name
		if bindings.try_map(name, keep_seconds):
			_said.text = said("map_keep", [bindings.map_label(name), ceili(keep_seconds)])
	map_focus = ""
	_paint()
	_paint_map()


## the pad in use, by the name the system gives it: the first player's, else the first
## connected; "" with no pad
func pad_in_use() -> String:
	var device: int = _prompts.devices.get(0, -1) if _prompts != null else -1
	if device < 0 and not Input.get_connected_joypads().is_empty():
		device = Input.get_connected_joypads()[0]
	return Input.get_joy_name(device) if device >= 0 else ""


## the next button names for `joy_name` (the pad in use where empty), kept and in force
func cycle_names(joy_name := "") -> String:
	var pad := joy_name if joy_name != "" else pad_in_use()
	var choices := _PwPrompts.CHOOSABLE
	var next: String = choices[(choices.find(bindings.pad_family(pad)) + 1) % choices.size()]
	bindings.set_pad_family(pad, next)
	_paint()
	_paint_names()
	return next


func _paint_names() -> void:
	if _names != null:
		_names.text = said(bindings.pad_family(pad_in_use()))


func _paint_map() -> void:
	if _map != null:
		_map.text = "<  %s  >" % bindings.map_label(
			map_focus if map_focus != "" else bindings.map_name)


## the pad as a picture over the screen, binding through the same store (§PW428)
func open_pad() -> CanvasLayer:
	var screen: CanvasLayer = load("res://addons/polyweave/remap/pad_screen.gd").new()
	screen.bindings = bindings
	screen.closed.connect(_paint)
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


## a row per action, built once; `_paint` fills them
func _draw_rows() -> void:
	for action in actions if not actions.is_empty() else bindings.actions:
		var row := HBoxContainer.new()
		var label := Label.new()
		label.name = "label"
		label.custom_minimum_size.x = 160
		row.add_child(label)
		var pair := []
		for pad in [false, true]:
			var button := Button.new()
			button.custom_minimum_size = Vector2(56, 56)
			button.expand_icon = true
			button.pressed.connect(_listen.bind(action, pad))
			row.add_child(button)
			pair.append(button)
		_rows.add_child(row)
		_buttons[action] = pair
	_paint()


## every row's label and icons as they are now, changed in place: no button is freed,
## so focus stays where the player left it
func _paint() -> void:
	for action in _buttons:
		var pair: Array = _buttons[action]
		(pair[0] as Button).get_parent().get_node("label").text = bindings.label(action)
		for pad in [false, true]:
			var button: Button = pair[1 if pad else 0]
			var family: String = "keyboard" if not pad else (
				_prompts.family if _prompts.family != "keyboard" else "xbox")
			button.icon = _prompts.icon(action, family)
			button.text = "-" if button.icon == null else ""
			if _listening == action and _listening_pad == pad:
				button.icon = _own("listening")
				button.text = "" if button.icon != null else "..."


## whether the screen is listening for a binding now
func is_listening() -> bool:
	return _listening != ""


## the button `action`'s key half (or pad half) is drawn on, or null
func button_of(action: String, pad: bool) -> Button:
	return _buttons[action][1 if pad else 0] if _buttons.has(action) else null


func _listen(action: String, pad: bool) -> void:
	if _listening != "" and _listening != action:
		listened.emit(_listening)
	_listening = action
	_listening_pad = pad
	_capture = ""
	_held = 0.0
	_left = listen_seconds
	_said.text = said("press_button" if pad else "press_key", [bindings.label(action)])
	_paint()
	listening.emit(action)


func _input(event: InputEvent) -> void:
	if _listening != "":
		if capture(event):
			_handled()
	elif not bindings.confirm.is_empty() and bindings.pressed_on_screen(event) \
			and confirm_focused():
		_handled()


## press the button of this screen that has the focus, as a declared CONFIRM does where
## ui_accept has no pad button (§PW542); false where no button of its own is focused
func confirm_focused() -> bool:
	var focused: Control = get_viewport().gui_get_focus_owner() \
		if get_viewport() != null else null
	if not (focused is BaseButton) or not is_ancestor_of(focused):
		return false
	var button := focused as BaseButton
	if button.toggle_mode:
		button.button_pressed = not button.button_pressed
	else:
		button.pressed.emit()
	return true


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


## run the clocks: a press held long enough cancels, and so does nothing pressed in time;
## a map on trial counts down, and goes back once its time runs out
func _process(delta: float) -> void:
	if bindings != null and bindings.trial_left() >= 0.0:
		var trying := bindings.map_name
		if bindings.tick(delta):
			_said.text = said("map_back", [bindings.map_label(bindings.map_name)])
			_paint()
			_paint_map()
		else:
			_said.text = said("map_keep", [bindings.map_label(trying),
				ceili(bindings.trial_left())])
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
	var was := _listening
	_listening = ""
	_capture = ""
	_said.text = saying
	_paint()
	if was != "":
		listened.emit(was)


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
