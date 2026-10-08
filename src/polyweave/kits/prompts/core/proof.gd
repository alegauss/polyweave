extends SceneTree
## The prompts kit's proof, run in the game it lands in (§PW344): every action the game
## binds has an icon in every family it is bound for, a pad's name picks its family, and
## an event from another device changes what is drawn. Prints KIT PROVED, or KIT FAILED
## with why.

const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")


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
	prompts.free()
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	quit()
