extends SceneTree
## The menus kit's proof, run in the game it lands in (§PW346), by pad events alone: a
## walk down every menu reaches each button and comes back round, back lands on the item
## each menu declares in every family's convention, a Switch pad's south button goes
## back where an Xbox pad's confirms, and the game's own time stands still while the
## pause menu is open. Prints KIT PROVED, or KIT FAILED with why.

const Menu := preload("res://addons/polyweave/menus/menu.gd")
const Pause := preload("res://addons/polyweave/menus/pause.gd")
const Confirm := preload("res://addons/polyweave/menus/confirm.gd")

var failed := []
var got := []
var main: Menu
var pause: Pause
var confirm: Confirm
var ticker: Node
var frame := 0
var ticks_paused := 0


func _initialize() -> void:
	var counting := GDScript.new()
	counting.source_code = "extends Node\nvar ticks := 0\nfunc _process(_d):\n\tticks += 1\n"
	counting.reload()
	ticker = Node.new()
	ticker.set_script(counting)
	root.add_child(ticker)
	main = Menu.new()
	main.items.assign(["play", "options", "quit"])
	main.back_to = "quit"
	main.chosen.connect(func(item: String) -> void: got.append(item))
	root.add_child(main)
	pause = Pause.new()
	root.add_child(pause)
	pause.chosen.connect(func(item: String) -> void: got.append(item))
	confirm = Confirm.new()
	confirm.question = "quit?"
	confirm.visible = false
	confirm.chosen.connect(func(item: String) -> void: got.append(item))
	root.add_child(confirm)


func _pad(index: int) -> void:
	var event := InputEventJoypadButton.new()
	event.button_index = index as JoyButton
	event.pressed = true
	root.push_input(event)
	var released := event.duplicate() as InputEventJoypadButton
	released.pressed = false
	root.push_input(released)


func _focused() -> String:
	var owner := root.gui_get_focus_owner()
	return str(owner.name) if owner != null else "<none>"


## every button reached walking down by the d-pad, and back to where the walk began
func _walk(menu: Menu, named: String) -> void:
	var all := menu.buttons().map(func(b: Node) -> String: return str(b.name))
	var start := _focused()
	var seen := [start]
	for i in all.size():
		_pad(JOY_BUTTON_DPAD_DOWN)
		seen.append(_focused())
	if not _covers(seen, all):
		failed.append("walking %s by pad reached %s of %s" % [named, seen, all])
	if seen[-1] != start:
		failed.append("walking %s by pad did not come back round to %s" % [named, start])
	_pad(JOY_BUTTON_DPAD_UP)
	if _focused() != all[(all.find(start) - 1 + all.size()) % all.size()]:
		failed.append("up from %s in %s reached %s" % [start, named, _focused()])
	_pad(JOY_BUTTON_DPAD_DOWN)


func _covers(seen: Array, all: Array) -> bool:
	for one in all:
		if not seen.has(one):
			return false
	return true


func _back(menu: Menu, family: String, named: String, expected: String) -> void:
	got.clear()
	menu.family = family
	_pad(Menu.BACK[family])
	if got != [expected]:
		failed.append("back on %s in %s chose %s, not %s" % [family, named, got, expected])


func _process(_delta: float) -> bool:
	frame += 1
	match frame:
		2:
			if _focused() != "play":
				failed.append("the main menu showed with %s focused" % _focused())
			_walk(main, "the main menu")
			for family in ["xbox", "playstation", "switch"]:
				_back(main, family, "the main menu", "quit")
			got.clear()
			main.family = "switch"
			_pad(JOY_BUTTON_A)
			_pad(JOY_BUTTON_B)
			if got != ["quit", "play"]:
				failed.append("a Switch pad's south then east chose %s, not back then play" % [got])
			main.family = "xbox"
			got.clear()
			_pad(JOY_BUTTON_A)
			if got != ["play"]:
				failed.append("an Xbox pad's south chose %s, not play" % [got])
			main.hide()
			pause.open()
		3:
			ticks_paused = ticker.ticks
		4, 5, 6:
			pass
		7:
			if ticker.ticks != ticks_paused:
				failed.append("the game ticked %d times while paused" % (ticker.ticks - ticks_paused))
			if _focused() != "resume":
				failed.append("the pause menu showed with %s focused" % _focused())
			_walk(pause.menu, "the pause menu")
			_back(pause.menu, "switch", "the pause menu", "resume")
			if paused or pause.is_open():
				failed.append("back from the pause menu did not resume the game")
			ticks_paused = ticker.ticks
		9:
			if ticker.ticks == ticks_paused:
				failed.append("the game did not tick again after resuming")
			confirm.show()
		10:
			if _focused() != "no":
				failed.append("the confirm showed with %s focused, not no" % _focused())
			_walk(confirm, "the confirm")
			var answers := []
			confirm.answered.connect(func(yes: bool) -> void: answers.append(yes))
			_back(confirm, "playstation", "the confirm", "no")
			if answers != [false]:
				failed.append("back from the confirm answered %s" % [answers])
			if failed.is_empty():
				print("KIT PROVED")
			else:
				print("KIT FAILED: " + "; ".join(failed))
			return true
	return false
