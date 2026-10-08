class_name PolyweaveOptionsScreen
extends VBoxContainer
## An options screen (polyweave kit "options", §PW347): a tab per tab the rows name, a
## row per option, drawn as a slider, a switch, a choice or a button that opens a scene.
## A pad drives it whole: the d-pad walks the rows top to bottom and round again, left
## and right move a slider or a choice, the shoulders change tab, and confirm and back
## follow the family in hand as the menus kit's do. Back closes it; the look is the
## project's Theme.

signal closed
signal opened(scene: String)

const Settings := preload("res://addons/polyweave/options/settings.gd")
const Menu := preload("res://addons/polyweave/menus/menu.gd")

## the family whose convention confirm and back follow; the pad's own where unset
@export var family := ""

var settings: Settings
var tabs: TabContainer


func _ready() -> void:
	if settings == null:
		settings = Settings.new()
		settings.load_file()
	tabs = TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(tabs)
	for tab in settings.tabs():
		var rows := VBoxContainer.new()
		rows.name = tab
		tabs.add_child(rows)
		tabs.set_tab_title(tabs.get_tab_count() - 1, tr(tab))
		for row in settings.in_tab(tab):
			rows.add_child(_row(row))
		_link(rows)
	tabs.tab_changed.connect(func(_i: int) -> void: focus_first.call_deferred())
	visibility_changed.connect(focus_first)
	focus_first.call_deferred()


func _row(row: Dictionary) -> Control:
	var line := HBoxContainer.new()
	line.name = row["key"]
	var label := Label.new()
	label.text = tr(row.get("label", row["key"]))
	label.custom_minimum_size.x = 200
	line.add_child(label)
	var tab: String = row["tab"]
	var key: String = row["key"]
	var now: Variant = settings.get_value(tab, key)
	var control: Control
	if row.has("opens"):
		var button := Button.new()
		button.text = tr(row.get("label", key))
		button.pressed.connect(func() -> void: opened.emit(row["opens"]))
		control = button
	elif row.has("choices"):
		var choice := OptionButton.new()
		var names: Array = row.get("names", row["choices"])
		for i in names.size():
			choice.add_item(tr(str(names[i])), i)
		choice.selected = (row["choices"] as Array).find(now)
		choice.item_selected.connect(func(i: int) -> void:
			settings.set_value(tab, key, row["choices"][i]))
		control = choice
	elif row.has("range"):
		var slider := HSlider.new()
		slider.min_value = row["range"][0]
		slider.max_value = row["range"][1]
		slider.step = row["range"][2] if row["range"].size() > 2 else 0.0
		slider.value = now
		slider.value_changed.connect(func(v: float) -> void:
			settings.set_value(tab, key, v if row["default"] is float else int(v)))
		control = slider
	else:
		var switch := CheckButton.new()
		switch.button_pressed = bool(now)
		switch.toggled.connect(func(on: bool) -> void: settings.set_value(tab, key, on))
		control = switch
	control.name = "value"
	control.focus_mode = Control.FOCUS_ALL
	control.custom_minimum_size.x = 200
	line.add_child(control)
	return line


## every row's control, in order, linked top to bottom and round again
func controls(rows: Node) -> Array:
	return rows.get_children().map(func(line: Node) -> Node: return line.get_node("value"))


func _link(rows: Node) -> void:
	var all := controls(rows)
	for i in all.size():
		var control: Control = all[i]
		var above := control.get_path_to(all[(i - 1 + all.size()) % all.size()])
		var below := control.get_path_to(all[(i + 1) % all.size()])
		control.focus_neighbor_top = above
		control.focus_neighbor_bottom = below
		control.focus_previous = above
		control.focus_next = below
		if not control is Range:
			control.focus_neighbor_left = NodePath(".")
			control.focus_neighbor_right = NodePath(".")


func focus_first() -> void:
	if not is_inside_tree() or not is_visible_in_tree() or tabs.get_tab_count() == 0:
		return
	var all := controls(tabs.get_current_tab_control())
	if not all.is_empty():
		all[0].grab_focus()


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree() or not event.is_pressed() or event.is_echo():
		return
	var focused := get_viewport().gui_get_focus_owner()
	if event is InputEventJoypadButton:
		var held := family if family != "" else Menu.Prompts.family_of(Input.get_joy_name(event.device))
		var index := (event as InputEventJoypadButton).button_index
		if index == Menu.BACK.get(held, JOY_BUTTON_B):
			_handled()
			closed.emit()
		elif index == Menu.CONFIRM.get(held, JOY_BUTTON_A):
			_handled()
			_confirm(focused)
		elif index in [JOY_BUTTON_LEFT_SHOULDER, JOY_BUTTON_RIGHT_SHOULDER]:
			_handled()
			var step := 1 if index == JOY_BUTTON_RIGHT_SHOULDER else -1
			tabs.current_tab = posmod(tabs.current_tab + step, tabs.get_tab_count())
		elif focused is OptionButton and index in [JOY_BUTTON_DPAD_LEFT, JOY_BUTTON_DPAD_RIGHT]:
			_handled()
			_cycle(focused, 1 if index == JOY_BUTTON_DPAD_RIGHT else -1)
	elif event is InputEventKey and (event as InputEventKey).physical_keycode == KEY_ESCAPE:
		_handled()
		closed.emit()


func _confirm(focused: Control) -> void:
	if focused is OptionButton:
		_cycle(focused, 1)
	elif focused is CheckButton:
		(focused as CheckButton).button_pressed = not (focused as CheckButton).button_pressed
	elif focused is BaseButton:
		(focused as BaseButton).pressed.emit()


func _cycle(choice: OptionButton, step: int) -> void:
	choice.select(posmod(choice.selected + step, choice.item_count))
	choice.item_selected.emit(choice.selected)


func _handled() -> void:
	var viewport := get_viewport()
	if viewport != null:
		viewport.set_input_as_handled()
