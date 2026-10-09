extends SceneTree
## The players kit's proof, run in the game it lands in (§PW357), with simulated pads.
## A second pad joins on its join button and a pad past MAX_PLAYERS does not. Every
## rebindable action answers each player's own pad and no other's, and the keyboard
## stays the first player's. A rebind on either player leaves the other's bindings alone.
## A player leaving frees the pad for the next to join. With the presence kit installed,
## the pad that leaves is named as the player seated on it. Prints KIT PROVED, or KIT
## FAILED with why.

const Players := preload("res://addons/polyweave/players/players.gd")
const PRESENCE := "res://addons/polyweave/presence/presence.gd"
## the pads that join: numbered apart from the seats, so a pad's number is never taken
## for its player's
const SECOND := 3
const THIRD := 4

var failed := []
var players: Players


func _initialize() -> void:
	players = Players.shared()


func _button(device: int, index: int) -> InputEventJoypadButton:
	var event := InputEventJoypadButton.new()
	event.device = device
	event.button_index = index as JoyButton
	event.pressed = true
	return event


func _press(device: int, index: int) -> void:
	root.push_input(_button(device, index))


## an action of the first player's with a pad binding, to drive
func _driven() -> String:
	for name in players._store.actions:
		for event in InputMap.action_get_events(name):
			if event is InputEventJoypadButton:
				return name
	return ""


func _process(_delta: float) -> bool:
	if not players.is_inside_tree():
		return false
	var join := int(players.declared["JOIN_BUTTON"])
	var first := int(players.declared["FIRST_PAD"])
	var name := _driven()
	if name == "":
		failed.append("no rebindable action has a pad binding to drive")
	else:
		_press(first + SECOND, join)
		if players.player_of(first + SECOND) != 1:
			failed.append("a second pad pressing join was seated as %d" % players.player_of(first + SECOND))
		if int(players.declared["MAX_PLAYERS"]) == 2:
			_press(first + THIRD, join)
			if players.player_of(first + THIRD) != -1:
				failed.append("a pad past MAX_PLAYERS joined")
		_apart(name, first)
		_rebinds(name, first)
		_presence(first)
		players.leave(1)
		if players.player_of(first + SECOND) != -1 or InputMap.has_action(Players.action(name, 1)):
			failed.append("a player leaving kept their pad or their actions")
		_press(first + THIRD, join)
		if players.player_of(first + THIRD) != 1:
			failed.append("a pad freed by a leave could not be joined by the next")
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	return true


## each player's pad moves their own action and never the other's
func _apart(name: String, first: int) -> void:
	var index: int = (InputMap.action_get_events(name).filter(
		func(e: InputEvent) -> bool: return e is InputEventJoypadButton)[0] as InputEventJoypadButton).button_index
	var mine := Players.action(name, 1)
	if not InputMap.event_is_action(_button(first + SECOND, index), mine):
		failed.append("player 2's pad does not press %s" % mine)
	if InputMap.event_is_action(_button(first + SECOND, index), name):
		failed.append("player 2's pad presses player 1's %s" % name)
	if not InputMap.event_is_action(_button(first, index), name):
		failed.append("player 1's pad does not press %s" % name)
	if InputMap.event_is_action(_button(first, index), mine):
		failed.append("player 1's pad presses %s" % mine)
	for event in InputMap.action_get_events(name):
		if event is InputEventKey and InputMap.event_is_action(event, mine):
			failed.append("player 1's key presses %s" % mine)


func _rebinds(name: String, first: int) -> void:
	var before := players._codes(name)
	players.rebind(1, name, _button(first + SECOND, JOY_BUTTON_RIGHT_SHOULDER))
	if not InputMap.event_is_action(_button(first + SECOND, JOY_BUTTON_RIGHT_SHOULDER), Players.action(name, 1)):
		failed.append("a rebind of player 2's %s did not take" % name)
	if players._codes(name) != before:
		failed.append("a rebind of player 2's %s changed player 1's to %s" % [name, players._codes(name)])
	var theirs := players._codes(Players.action(name, 1))
	players.rebind(0, name, _button(first, JOY_BUTTON_LEFT_SHOULDER))
	if players._codes(Players.action(name, 1)) != theirs:
		failed.append("a rebind of player 1's %s changed player 2's" % name)
	if not InputMap.event_is_action(_button(first, JOY_BUTTON_LEFT_SHOULDER), name) \
			or InputMap.event_is_action(_button(first + SECOND, JOY_BUTTON_LEFT_SHOULDER), name):
		failed.append("player 1's rebound %s does not answer their pad alone" % name)
	players._store.reset()
	players._narrow_first()


func _presence(first: int) -> void:
	if not ResourceLoader.exists(PRESENCE):
		return
	var presence: Node = load(PRESENCE).shared()
	if presence.player_of(first + SECOND) != 1:
		failed.append("with the presence kit, pad %d is named as player %d, not player 2" % [
			first + SECOND, presence.player_of(first + SECOND) + 1])
