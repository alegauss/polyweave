class_name PolyweavePlayers
extends Node
## More than one player on one machine (polyweave kit "players", §PW357), from Starship's
## coop.gd and the coop_device its bindings kept. The first player has the keyboard and
## FIRST_PAD; any other pad joins by pressing JOIN_BUTTON while fewer than MAX_PLAYERS
## play. A player who joins gets a copy of every rebindable action, named `p2_fire` and
## so on, holding the first player's pad bindings on their own pad alone, while the first
## player's pad bindings answer FIRST_PAD alone: an event from one pad never moves another
## player. `rebind(player, action, event)` changes one player's binding and leaves every
## other player's alone, and `leave(player)` frees the pad for the next to join.
##
## How many play, and what a player is in the game, are the project's: its
## res://polyweave_players.gd declares MAX_PLAYERS, FIRST_PAD and JOIN_BUTTON, and the
## game listens for `joined` and `left`.

signal joined(player: int, device: int)
signal left(player: int, device: int)

const HERE := "res://addons/polyweave/players/players.gd"
const PROJECT := "res://polyweave_players.gd"
const Bindings := preload("res://addons/polyweave/remap/bindings.gd")
const DEFAULTS := {"MAX_PLAYERS": 2, "FIRST_PAD": 0, "JOIN_BUTTON": JOY_BUTTON_START}

var declared := {}
## player -> the pad they play on; the first player's is FIRST_PAD, with the keyboard
var pads := {}
var _store: Bindings

static var _shared: Node


## the one seating plan, made the first time and put in the tree
static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweavePlayers"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


## what the project declares, each name it leaves out at the kit's default
static func declaration(project := PROJECT) -> Dictionary:
	var out := DEFAULTS.duplicate(true)
	if ResourceLoader.exists(project):
		var map := (load(project) as GDScript).get_script_constant_map()
		for key in map:
			out[key] = map[key]
	return out


## the action `name` as player `player` reads it: the first player's own, the others' copy
static func action(name: String, player: int) -> String:
	return name if player == 0 else "p%d_%s" % [player + 1, name]


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	declared = declaration()
	pads[0] = int(declared["FIRST_PAD"])
	_store = Bindings.new()


## how many play now
func count() -> int:
	return pads.size()


## the player a device plays for: the keyboard is the first player's, a pad nobody holds -1
func player_of(device: int) -> int:
	if device < 0:
		return 0
	for player in pads:
		if pads[player] == device:
			return player
	return -1


## the player an event comes from, by its device, or -1 for a pad nobody holds
func player_of_event(event: InputEvent) -> int:
	if event is InputEventKey or event is InputEventMouse:
		return 0
	return player_of(event.device)


## seat a pad as the next player, where a seat is free and the pad holds none
func join(device: int) -> int:
	if player_of(device) != -1 or count() >= int(declared["MAX_PLAYERS"]):
		return -1
	var player := 0
	while pads.has(player):
		player += 1
	pads[player] = device
	var now := _store.current()
	for name in _store.actions:
		_apply(action(name, player), _pad_half(now[name]), device)
	_narrow_first()
	joined.emit(player, device)
	return player


## a player leaves: their actions go and their pad is free for the next to join
func leave(player: int) -> void:
	if player == 0 or not pads.has(player):
		return
	var device: int = pads[player]
	pads.erase(player)
	for name in _store.actions:
		if InputMap.has_action(action(name, player)):
			InputMap.erase_action(action(name, player))
	_narrow_first()
	left.emit(player, device)


## bind one player's `name` to `event`, swapping a clash among that player's own actions,
## and leave every other player's bindings alone
func rebind(player: int, name: String, event: InputEvent) -> bool:
	if player == 0:
		var done := _store.rebind(name, event)
		_narrow_first()
		return done
	if not pads.has(player) or Bindings.on_keys(Bindings.encode(event)):
		return false
	var code := Bindings.encode(event)
	var theirs := {}
	for each in _store.actions:
		theirs[each] = _codes(action(each, player))
	var after := Bindings.bind(theirs, name, code)
	for each in after:
		_apply(action(each, player), _pad_half(after[each]), pads[player])
	return true


## the first player's pad bindings answer every pad alone, and FIRST_PAD once others play
func _narrow_first() -> void:
	var device: int = pads[0] if count() > 1 else -1
	var now := _store.current()
	for name in _store.actions:
		_apply(name, now[name], device)


func _codes(name: String) -> Array:
	var out := []
	if InputMap.has_action(name):
		for event in InputMap.action_get_events(name):
			var code := Bindings.encode(event)
			if code != "":
				out.append(code)
	return out


func _pad_half(codes: Array) -> Array:
	return codes.filter(func(c: String) -> bool: return not Bindings.on_keys(c))


func _apply(name: String, codes: Array, device: int) -> void:
	if not InputMap.has_action(name):
		InputMap.add_action(name, _store.deadzone)
	InputMap.action_erase_events(name)
	for code in codes:
		var event := Bindings.decode(code)
		if event == null:
			continue
		# a decoded event answers pad 0 alone; a pad binding is pinned to its player's
		# pad, or answers every pad while one player plays
		if not Bindings.on_keys(code):
			event.device = device if device >= 0 else -1
		InputMap.action_add_event(name, event)


func _input(event: InputEvent) -> void:
	if event is InputEventJoypadButton and event.is_pressed() \
			and (event as InputEventJoypadButton).button_index == int(declared["JOIN_BUTTON"]) \
			and player_of(event.device) == -1 and join(event.device) != -1:
		get_viewport().set_input_as_handled()
