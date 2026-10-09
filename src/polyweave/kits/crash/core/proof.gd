extends SceneTree
## The crash kit's proof, run in the game it lands in (§PW361). An error forced here leaves
## a capture naming this script and the line that raised it, with the log's last lines;
## a run whose marker was left behind is packed as an unclean exit by the next log to
## open; and a log closed as it should leaves no marker. Prints KIT PROVED, or KIT FAILED
## with why.

const Log := preload("res://addons/polyweave/crash/log.gd")

var failed := []
var log: Log
var expected := {}
var frames := 0


func _initialize() -> void:
	log = Log.shared()


## the error a game would raise, at a line this proof knows
func _force() -> void:
	expected = {"script": get_stack()[0]["source"], "line": get_stack()[0]["line"] + 1}
	push_error("the crash kit's forced error")


func _read(path: String) -> Dictionary:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


func _process(_delta: float) -> bool:
	if not log.is_inside_tree():
		return false
	frames += 1
	if frames == 1:
		log.info("the proof begins")
		_force()
		return false
	if frames < 4:
		return false
	var packed := _read(log.last_capture)
	var error: Dictionary = packed.get("error", {})
	if packed.get("reason") != "error":
		failed.append("a forced error left no capture")
	elif error.get("script") != expected["script"] or int(error.get("line", 0)) != expected["line"]:
		failed.append("the capture names %s:%s, not %s:%s" % [error.get("script"),
			error.get("line"), expected["script"], expected["line"]])
	elif not str(error.get("said", "")).contains("forced error"):
		failed.append("the capture says %s, not the error forced" % error.get("said"))
	if not (packed.get("lines", []) as Array).any(
			func(l: Dictionary) -> bool: return l.get("said") == "the proof begins"):
		failed.append("the capture holds none of the log's last lines")
	_unclean()
	log.close()
	if FileAccess.file_exists(Log.DIR + "/running"):
		failed.append("a log closed as it should left its marker behind")
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	return true


## a run that never closed its log, as a crash leaves it, found by the next to open
func _unclean() -> void:
	var marker := FileAccess.open(Log.DIR + "/running", FileAccess.WRITE)
	marker.store_string("0")
	marker.close()
	var next: Log = load(Log.HERE).new()
	if _read(next.last_capture).get("reason") != "unclean-exit":
		failed.append("a marker left behind was not packed as an unclean exit")
	next.close()
	next.free()
