class_name PolyweavePause
extends CanvasLayer
## A pause menu (polyweave kit "menus", §PW346) that stops the game under it through the
## scene tree's pause: the game's nodes, pausable by default, stop ticking, while this
## layer processes always. The game's pause action opens and closes it, and back resumes.

signal chosen(item: String)

const Menu := preload("res://addons/polyweave/menus/menu.gd")

@export var items: Array[String] = ["resume", "options", "quit_to_menu"]
## the input action that opens and closes it
@export var action := "pause"

var menu: Menu


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	menu = Menu.new()
	menu.items = items
	menu.back_to = "resume"
	menu.visible = false
	menu.chosen.connect(_chose)
	add_child(menu)


func is_open() -> bool:
	return menu.visible


func open() -> void:
	get_tree().paused = true
	menu.show()


func close() -> void:
	menu.hide()
	get_tree().paused = false


func _chose(item: String) -> void:
	if item == "resume":
		close()
	chosen.emit(item)


func _unhandled_input(event: InputEvent) -> void:
	if InputMap.has_action(action) and event.is_action_pressed(action):
		get_viewport().set_input_as_handled()
		if is_open():
			close()
		else:
			open()
