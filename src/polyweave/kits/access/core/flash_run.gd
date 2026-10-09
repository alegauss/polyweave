extends SceneTree
## A run the access kit captures with capture.movie (§PW355): the project's FLASH_RUN,
## played for FLASH_SECONDS with flashes switched as its argument says, `flashes=off` or
## `flashes=on`, between the two marks capture.movie keeps. measure.flashes then counts
## what the frames hold, so a game's flashes are held to the switch on the screen and
## not on the code's word.

const Access := preload("res://addons/polyweave/access/access.gd")

var access: Access
var run: Node
var played := 0.0
var from := -1


func _initialize() -> void:
	access = Access.shared()
	var path := str(access.declared["FLASH_RUN"])
	var packed := load(path) as PackedScene if path != "" else null
	if packed == null:
		print("KIT FAILED: the flash run %s does not load" % path)
		quit(1)
		return
	access.flashing = not OS.get_cmdline_user_args().has("flashes=off")
	print("environment: ")
	run = packed.instantiate()
	root.add_child(run)


## game time, which Movie Maker steps at its own fixed rate whatever the wall clock does
func _process(delta: float) -> bool:
	var frame := Engine.get_process_frames()
	if from == -1:
		from = frame + 2
		print("movie: from %d" % from)
		return false
	if frame >= from:
		played += delta
	if played >= float(access.declared["FLASH_SECONDS"]):
		print("movie: to %d" % frame)
		return true
	return false
