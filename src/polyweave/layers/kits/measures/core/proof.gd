extends SceneTree
## The measures kit's proof, run in the game it lands in (§PW613). Each measure the kit
## carries is run in the engine over the kit's own cases and over every timeline the
## game declares in res://polyweave_measures.gd (`const PRESSURE := [{"events":
## "res://levels/wave1.json", "warp": 0.5, "window": 3.0}]`), and for each the inputs
## and the engine's answer are written beside the game and printed as `KIT MEASURE
## <measure> <inputs> <answer>`. polyweave runs its own measure over the same inputs
## and fails the proof on the first value that differs, so the copy a tool uses in the
## game cannot drift from the one the gate holds the game to. Prints KIT PROVED, or
## KIT FAILED with why.

const _PwPressure := preload("res://addons/polyweave/measures/pressure.gd")
const CASES := "res://addons/polyweave/measures/cases/pressure.json"
const PROJECT := "res://polyweave_measures.gd"
const OUT := ".polyweave/kits/measures"

var failed := []
var written := 0


func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://" + OUT))
	var cases = JSON.parse_string(FileAccess.get_file_as_string(CASES))
	if not (cases is Array) or cases.is_empty():
		_fail("the kit's own cases at %s do not read" % CASES)
		return
	for case in cases:
		_pressure(case, "case-%d" % written)
	if ResourceLoader.exists(PROJECT):
		var declared := (load(PROJECT) as GDScript).get_script_constant_map()
		for one in declared.get("PRESSURE", []):
			var source := str(one.get("events", ""))
			var read = JSON.parse_string(FileAccess.get_file_as_string(source))
			if read is Dictionary:
				read = read.get("events")
			if not (read is Array) or read.is_empty():
				failed.append("the timeline %s declared in %s holds no events" % [source,
					PROJECT])
				continue
			_pressure({"events": read, "warp": one.get("warp", 0.0),
				"window": one.get("window", 0.0)}, source.get_file().get_basename())
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	quit(0 if failed.is_empty() else 1)


## One timeline measured here, written with its inputs for polyweave to measure too.
func _pressure(inputs: Dictionary, name: String) -> void:
	var answer := _PwPressure.measure(inputs["events"], float(inputs.get("warp", 0.0)),
		float(inputs.get("window", 0.0)))
	var stem := "%s/pressure-%s" % [OUT, name]
	_write(stem + ".inputs.json", inputs)
	_write(stem + ".answer.json", answer)
	written += 1
	print("KIT MEASURE pressure %s.inputs.json %s.answer.json" % [stem, stem])


func _write(path: String, value) -> void:
	var file := FileAccess.open("res://" + path, FileAccess.WRITE)
	file.store_string(JSON.stringify(value))
	file.close()


func _fail(why: String) -> void:
	print("KIT FAILED: " + why)
	quit(1)
