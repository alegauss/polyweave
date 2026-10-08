class_name PolyweaveMenu
extends VBoxContainer
## A menu a pad can drive (polyweave kit "menus", §PW346): a button per item, each named
## by the item and labelled tr(item), focus linked top to bottom and round again, so no
## control is out of a pad's reach. Confirm and back follow the convention of the
## family in the player's hands: a Switch pad confirms on its east button (A) and goes
## back on its south one (B), every other pad the other way round, and Escape goes back
## on the keyboard. Back chooses the item the menu declares, `back_to`.
##
## The look is the project's Theme: the menu adds buttons and a label, never a style.

signal chosen(item: String)

const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")
## the pad button that confirms, and the one that goes back, in each family
const CONFIRM := {"xbox": JOY_BUTTON_A, "playstation": JOY_BUTTON_A, "switch": JOY_BUTTON_B}
const BACK := {"xbox": JOY_BUTTON_B, "playstation": JOY_BUTTON_B, "switch": JOY_BUTTON_A}

@export var items: Array[String] = []
## the item back chooses; back does nothing where it is unset
@export var back_to := ""
## a line over the buttons, through tr(), such as a confirm's question
@export var question := ""
## the item focused when the menu shows; the first where unset
@export var first := ""
## the family whose convention confirm and back follow; the pad's own where unset
@export var family := ""


func _ready() -> void:
	if question != "":
		var label := Label.new()
		label.text = tr(question)
		add_child(label)
	for item in items:
		var button := Button.new()
		button.name = item
		button.text = tr(item)
		button.pressed.connect(func() -> void: chosen.emit(item))
		add_child(button)
	_link()
	visibility_changed.connect(focus_first)
	focus_first.call_deferred()


## every button a pad can reach, in order
func buttons() -> Array:
	return get_children().filter(func(c: Node) -> bool: return c is BaseButton and c.visible)


func _link() -> void:
	var all := buttons()
	for i in all.size():
		var button: Control = all[i]
		var above := button.get_path_to(all[(i - 1 + all.size()) % all.size()])
		var below := button.get_path_to(all[(i + 1) % all.size()])
		button.focus_mode = Control.FOCUS_ALL
		button.focus_neighbor_top = above
		button.focus_neighbor_bottom = below
		button.focus_previous = above
		button.focus_next = below
		button.focus_neighbor_left = NodePath(".")
		button.focus_neighbor_right = NodePath(".")


func focus_first() -> void:
	if not is_inside_tree() or not is_visible_in_tree():
		return
	var all := buttons()
	if all.is_empty():
		return
	var named := all.filter(func(b: Node) -> bool: return b.name == first)
	(named[0] if not named.is_empty() else all[0]).grab_focus()


## the family a pad event follows: the menu's own, or the one the pad's name says
func family_of(event: InputEvent) -> String:
	return family if family != "" else Prompts.family_of(Input.get_joy_name(event.device))


func back() -> void:
	if back_to != "":
		chosen.emit(back_to)


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree() or not event.is_pressed() or event.is_echo():
		return
	if event is InputEventJoypadButton:
		var held := family_of(event)
		var index := (event as InputEventJoypadButton).button_index
		if index == BACK.get(held, JOY_BUTTON_B):
			_handled()
			back()
		elif index == CONFIRM.get(held, JOY_BUTTON_A):
			_handled()
			var focused := get_viewport().gui_get_focus_owner()
			if focused is BaseButton and is_ancestor_of(focused):
				(focused as BaseButton).pressed.emit()
	elif event is InputEventKey and (event as InputEventKey).physical_keycode == KEY_ESCAPE:
		_handled()
		back()


func _handled() -> void:
	var viewport := get_viewport()
	if viewport != null:
		viewport.set_input_as_handled()
