extends SceneTree
## The prompts kit's proof, run in the game it lands in (§PW344): every action the game
## binds has an icon in every family it is bound for, a pad's name picks its family, and
## an event from another device changes what is drawn. Prints KIT PROVED, or KIT FAILED
## with why.

const _PwPrompts := preload("res://addons/polyweave/prompts/prompts.gd")


## Two players seated on pads 0 and 1, as the players kit would, without needing it.
class Seats:
	var pads := {0: 0, 1: 1}

	func player_of_event(event: InputEvent) -> int:
		for player in pads:
			if pads[player] == event.device:
				return player
		return -1

	func count() -> int:
		return pads.size()


## The language the proof reads names in: one no game's table carries, so only the
## proof's own rows apply and the words it expects are its own (§PW485). A pt-BR game
## read its key names through its own table, correctly, and the proof called that
## ignoring the table.
const PROOF_LOCALE := "zz"


func _initialize() -> void:
	var game_locale := TranslationServer.get_locale()
	TranslationServer.set_locale(PROOF_LOCALE)
	var failed := _proved()
	TranslationServer.set_locale(game_locale)
	if failed.is_empty():
		print("KIT PROVED")
	else:
		# Read in the proof's own language; the game's is said, for a finding on a name.
		print("KIT FAILED (names read in %s, the game's language %s): %s"
			% [PROOF_LOCALE, game_locale, "; ".join(failed)])
	quit()


func _proved() -> Array:
	var failed := []
	var prompts = _PwPrompts.new()
	for action in InputMap.get_actions():
		if str(action).begins_with("ui_"):
			continue
		for family in _PwPrompts.FAMILIES:
			if prompts.event_for(action, family) != null and prompts.icon(action, family) == null:
				failed.append("%s has no icon in %s" % [action, family])
	var named := {
		"DualSense Wireless Controller": "playstation",
		"PS4 Controller": "playstation",
		"Nintendo Switch Pro Controller": "switch",
		"Xbox Series Controller": "xbox",
		"XInput Gamepad": "xbox",
		"8BitDo Pro 2": "generic",
		"": "xbox",
	}
	for joy_name in named:
		if _PwPrompts.family_of(joy_name) != named[joy_name]:
			failed.append("%s read as %s" % [joy_name, _PwPrompts.family_of(joy_name)])
	var pressed := InputEventJoypadButton.new()
	pressed.button_index = JOY_BUTTON_A
	pressed.pressed = true
	prompts.note(pressed)
	var on_pad: String = prompts.family
	var key := InputEventKey.new()
	key.physical_keycode = KEY_SPACE
	key.pressed = true
	prompts.note(key)
	if on_pad == "keyboard" or prompts.family != "keyboard":
		failed.append("a pad then a key left the family at %s" % prompts.family)
	# Before any input the first connected pad is the one in hand, the keyboard where
	# none is, and once an input is noted a pad found again changes nothing (§PW545).
	var couch = _PwPrompts.new()
	couch.start([3], {3: "DualSense Wireless Controller"})
	if couch.family != "playstation" or couch.devices.get(0) != 3:
		failed.append("a launch with a PlayStation pad plugged in started on %s" % couch.family)
	var desk = _PwPrompts.new()
	desk.start([])
	desk.note(key)
	desk.start([2], {2: "Xbox Series Controller"})
	if desk.family != "keyboard":
		failed.append("a pad found after a key was pressed moved the family to %s" % desk.family)
	couch.free()
	desk.free()
	for action in InputMap.get_actions():
		var on_xbox: String = prompts.icon_path(action, "xbox")
		if on_xbox != "" and prompts.icon_path(action, "switch") == on_xbox:
			failed.append("%s draws the same icon on switch as on xbox" % action)
	var south_xbox := "%s/xbox/south_64.png" % prompts.icons_root
	var south_switch := "%s/switch/south_64.png" % prompts.icons_root
	if not FileAccess.file_exists(south_xbox) or not FileAccess.file_exists(south_switch):
		failed.append("the south button's icons are missing")
	# A help line in words (§PW394), on actions of the proof's own so it holds in any
	# game: each family names a pad's button as the pad prints it, a key as the string
	# table says it, and a second player's copy is their own.
	var own := &"pw_prompts_proof"
	var second := _PwPrompts.action_of(own, 1)
	for made in [own, second]:
		InputMap.add_action(made)
	var space := InputEventKey.new()
	space.physical_keycode = KEY_SPACE
	var south := InputEventJoypadButton.new()
	south.button_index = JOY_BUTTON_A
	var east := InputEventJoypadButton.new()
	east.button_index = JOY_BUTTON_B
	InputMap.action_add_event(own, space)
	InputMap.action_add_event(own, south)
	InputMap.action_add_event(second, east)
	var words := {"xbox": "PRESS A", "playstation": "PRESS CROSS", "switch": "PRESS B"}
	for family in words:
		var line: String = prompts.fill("PRESS {%s}" % own, 0, family)
		if line != words[family]:
			failed.append("a south button on %s reads %s" % [family, line])
	var spoken := Translation.new()
	spoken.locale = TranslationServer.get_locale()
	spoken.add_message("KEYNAME_SPACE", "BARRA")
	TranslationServer.add_translation(spoken)
	if prompts.named(own, 0, "keyboard") != "BARRA":
		failed.append("a key's name ignores the string table: %s"
			% prompts.named(own, 0, "keyboard"))
	TranslationServer.remove_translation(spoken)
	if prompts.named(own, 1, "xbox") != "B":
		failed.append("the second player's binding reads %s" % prompts.named(own, 1, "xbox"))
	for made in [own, second]:
		InputMap.erase_action(made)
	# Each player's own device (§PW395): with two pads seated, the second pad's input
	# moves the second player's family and leaves the first's, and a pad unplugged hands
	# its player's prompts to a free pad still in, or to the keyboard.
	var seated = Seats.new()
	prompts.seats = seated
	prompts.families.clear()
	prompts.devices.clear()
	var first_pad := InputEventJoypadButton.new()
	first_pad.button_index = JOY_BUTTON_A
	first_pad.pressed = true
	first_pad.device = 0
	prompts.note(first_pad)
	var other_pad := first_pad.duplicate()
	other_pad.device = 1
	prompts.note(other_pad)
	if prompts.devices.get(0) != 0 or prompts.devices.get(1) != 1:
		failed.append("two seated pads read as players %s" % prompts.devices)
	var stranger := first_pad.duplicate()
	stranger.device = 5
	prompts.note(stranger)
	if prompts.devices.get(0) != 0:
		failed.append("a pad nobody holds moved the first player's prompts")
	prompts.unplugged(1, false, [0, 1, 3])
	if prompts.devices.get(1) != 3:
		failed.append("an unplugged pad did not hand its prompts on: %s" % prompts.devices)
	prompts.unplugged(3, false, [0])
	if prompts.devices.get(1) != -1 or prompts.family_for(1) != "keyboard":
		failed.append("with no pad free the prompts did not go to the keyboard")
	if prompts.fill("no marks here") != "no marks here":
		failed.append("a line with no marks was changed")
	# Every button named, bound or not, in every family (§PW431): a code as the remap kit
	# stores it, a generic pad's face by where it sits and through the string table, the
	# clicks as each family prints them, and a name with no word in it left as it is.
	var codes := {
		["button:3", "xbox"]: "Y", ["button:3", "playstation"]: "TRIANGLE",
		["button:3", "switch"]: "X", ["button:0", "generic"]: "SOUTH",
		["button:7", "playstation"]: "L3", ["button:7", "xbox"]: "LS",
		["button:6", "generic"]: "START", ["axis:5:1", "switch"]: "ZR",
		["axis:2:-1", "xbox"]: "RS LEFT", ["button:12", "xbox"]: "D-DOWN",
		["button:5", "xbox"]: "GUIDE", ["key:%d" % KEY_SPACE, "xbox"]: "SPACE",
	}
	for asked in codes:
		var reads: String = _PwPrompts.named_code(asked[0], asked[1])
		if reads != codes[asked]:
			failed.append("%s on %s reads %s, not %s" % [asked[0], asked[1], reads,
				codes[asked]])
	var row: String = _PwPrompts.describe(["key:%d" % KEY_SPACE, "button:1"], "playstation")
	if row != "SPACE   |   CIRCLE":
		failed.append("a binding's codes read %s" % row)
	if _PwPrompts.describe(["button:1"]) != "-   |   B":
		failed.append("a binding with no key does not say so: %s" % _PwPrompts.describe(["button:1"]))
	var table := Translation.new()
	table.locale = TranslationServer.get_locale()
	table.add_message("PAD_SOUTH", "SUL")
	table.add_message("PAD_A", "never")
	TranslationServer.add_translation(table)
	if _PwPrompts.named_code("button:0", "generic") != "SUL":
		failed.append("a generic pad's south button ignores the string table")
	if _PwPrompts.said("PAD_", "A") != "A":
		failed.append("a one-letter glyph was translated")
	TranslationServer.remove_translation(table)
	# A label kept filled (§PW434): filled from its table row, and filled again when the
	# player's device moves, a binding changes and the language changes; a follower runs
	# on each, and a label freed is let go.
	var watched := &"pw_prompts_watch"
	InputMap.add_action(watched)
	var watch_key := InputEventKey.new()
	watch_key.physical_keycode = KEY_SPACE
	var watch_pad := InputEventJoypadButton.new()
	watch_pad.button_index = JOY_BUTTON_A
	InputMap.action_add_event(watched, watch_key)
	InputMap.action_add_event(watched, watch_pad)
	var help := Translation.new()
	help.locale = TranslationServer.get_locale()
	help.add_message("PW_HELP", "PRESS {pw_prompts_watch}")
	TranslationServer.add_translation(help)
	prompts.seats = null
	prompts.families = {0: "xbox"}
	prompts.family = "xbox"
	var shown := Label.new()
	var runs := [0]
	prompts.follow(func() -> void: runs[0] += 1)
	prompts.watch(shown, "PW_HELP")
	if shown.text != "PRESS A":
		failed.append("a watched label first read %s" % shown.text)
	var typed := InputEventKey.new()
	typed.physical_keycode = KEY_ENTER
	typed.pressed = true
	prompts.note(typed)
	if shown.text != "PRESS SPACE":
		failed.append("a watched label did not follow the keyboard: %s" % shown.text)
	InputMap.action_erase_event(watched, watch_key)
	var other_key := InputEventKey.new()
	other_key.physical_keycode = KEY_Q
	InputMap.action_add_event(watched, other_key)
	prompts.refresh()
	if shown.text != "PRESS Q":
		failed.append("a watched label did not follow a rebind: %s" % shown.text)
	TranslationServer.remove_translation(help)
	var spoken_help := Translation.new()
	spoken_help.locale = TranslationServer.get_locale()
	spoken_help.add_message("PW_HELP", "APERTE {pw_prompts_watch}")
	TranslationServer.add_translation(spoken_help)
	prompts._notification(NOTIFICATION_TRANSLATION_CHANGED)
	if shown.text != "APERTE Q":
		failed.append("a watched label did not follow the language: %s" % shown.text)
	if runs[0] < 3:
		failed.append("a follower ran %d times over three changes" % runs[0])
	shown.free()
	prompts.refresh()
	if not prompts._watched.is_empty():
		failed.append("a freed label was kept watched")
	TranslationServer.remove_translation(spoken_help)
	InputMap.erase_action(watched)
	prompts.free()
	return failed
