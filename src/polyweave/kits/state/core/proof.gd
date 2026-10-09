extends SceneTree
## The state kit's proof, run in the game it lands in (§PW359): the main scene runs a few
## frames, and every name the project declares answers with the type it declares. A name
## whose node is gone, whose property or method is missing, or whose value is of another
## type is a finding naming it. Prints KIT PROVED, or KIT FAILED with why.

const State := preload("res://addons/polyweave/state/state.gd")

var failed := []
var frames := 0


func _initialize() -> void:
	if State.declared().is_empty():
		print("KIT FAILED: res://polyweave_state.gd declares no STATE to read")
		quit(1)
		return
	var main := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if main == "" or change_scene_to_file(main) != OK:
		print("KIT FAILED: the main scene %s does not load" % main)
		quit(1)


func _process(_delta: float) -> bool:
	frames += 1
	if frames < 3:
		return false
	var each := State.read()
	for name in each:
		if not each[name]["ok"]:
			failed.append(each[name]["said"])
	if State.snapshot().size() != State.declared().size():
		failed.append("the snapshot holds %d of the %d names" % [State.snapshot().size(),
			State.declared().size()])
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	return true
