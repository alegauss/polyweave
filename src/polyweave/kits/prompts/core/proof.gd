extends SceneTree
## The prompts kit's proof, run in the game it lands in (§PW344): every action the game
## binds has an icon in every family it is bound for, a pad's name picks its family, and
## an event from another device changes what is drawn. Prints KIT PROVED, or KIT FAILED
## with why.

const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")


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


func _initialize() -> void:
	var failed := []
	var prompts = Prompts.new()
	for action in InputMap.get_actions():
		if str(action).begins_with("ui_"):
			continue
		for family in Prompts.FAMILIES:
			if prompts.event_for(action, family) != null and prompts.icon(action, family) == null:
				failed.append("%s has no icon in %s" % [action, family])
	var named := {
		"DualSense Wireless Controller": "playstation",
		"PS4 Controller": "playstation",
		"Nintendo Switch Pro Controller": "switch",
		"Xbox Series Controller": "xbox",
		"": "xbox",
	}
	for joy_name in named:
		if Prompts.family_of(joy_name) != named[joy_name]:
			failed.append("%s read as %s" % [joy_name, Prompts.family_of(joy_name)])
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
	var second := Prompts.action_of(own, 1)
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
	prompts.free()
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	quit()
