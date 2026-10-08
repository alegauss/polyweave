extends SceneTree
## The saves kit's proof, run in the game it lands in (§PW348), all of it automatic:
## every slot filled and read back with Godot's own types; a save stopped after its
## write and after its move loads the last good one; a corrupt save falls back to the
## one before and never pushes it out; a save from each older version comes up through
## the project's migrations; and one from a newer build is refused and left on disk.
## Prints KIT PROVED, or KIT FAILED with why.

const Saves := preload("res://addons/polyweave/saves/saves.gd")
const DIR := "user://polyweave_saves_proof"

var failed := []


func _data(n: int) -> Dictionary:
	return {"level": n, "score": 1000.5 + n, "at": Vector2(n, -n), "seen": [n, "x", true],
		"nested": {"inner": PackedInt32Array([n, n + 1])}}


func _same(a: Variant, b: Variant) -> bool:
	return var_to_str(a) == var_to_str(b)


func _initialize() -> void:
	_clear()
	var saves := Saves.new(DIR)
	for slot in saves.slots:
		if not saves.save(slot, _data(slot)):
			failed.append("slot %d could not be saved" % slot)
	for slot in saves.slots:
		var back := saves.load_slot(slot)
		if not _same(back, _data(slot)):
			failed.append("slot %d read back %s" % [slot, back])
	if saves.save(saves.slots, _data(0)):
		failed.append("a slot past the last was saved")
	if saves.listed().size() != saves.slots:
		failed.append("listed %d slots of %d" % [saves.listed().size(), saves.slots])

	for step in ["written", "moved"]:
		saves.save(0, _data(10))
		saves.stop_after = step
		saves.save(0, _data(11))
		saves.stop_after = ""
		if not _same(saves.load_slot(0), _data(10)):
			failed.append("a save stopped once %s did not load the last good one" % step)
		saves.save(0, _data(10))

	saves.save(1, _data(20))
	saves.save(1, _data(21))
	# the data changed under a sum that still reads, as a disk or a hand edit leaves it
	var envelope: Variant = JSON.parse_string(FileAccess.get_file_as_string(saves.path_of(1)))
	if not envelope is Dictionary:
		failed.append("slot 1 holds no save that reads after two saves")
		envelope = {"data": ""}
	envelope["data"] = str(envelope["data"]).replace("21", "99")
	FileAccess.open(saves.path_of(1), FileAccess.WRITE).store_string(JSON.stringify(envelope))
	if not _same(saves.load_slot(1), _data(20)) or not "; ".join(saves.said).contains("save before"):
		failed.append("a corrupt save did not fall back to the one before: %s" % [saves.said])
	saves.save(1, _data(22))
	if not _same(saves._read(saves.path_of(1) + ".bak"), _data(20)):
		failed.append("saving over a corrupt save pushed the last good one out")
	saves.save(1, _data(23))
	if not _same(saves.load_slot(1), _data(23)):
		failed.append("saving over a corrupt save lost the new one")
	if not FileAccess.file_exists(saves.path_of(1) + ".bak"):
		failed.append("no save before was kept")

	for from in range(1, saves.version):
		if not saves.migrations.has(from):
			failed.append("no migration brings a version %d save to %d" % [from, from + 1])
			continue
		var old := Saves.new(DIR, "res://none.gd")
		old.version = from
		old.slots = saves.slots
		old.save(2, _data(30))
		var brought := saves.load_slot(2)
		if brought.is_empty():
			failed.append("a version %d save did not come up: %s" % [from, saves.said])

	var newer := Saves.new(DIR, "res://none.gd")
	newer.version = saves.version + 1
	newer.slots = saves.slots
	newer.save(2, _data(40))
	var text := FileAccess.get_file_as_string(saves.path_of(2))
	saves.load_slot(2)
	if not "; ".join(saves.said).contains("newer than this build"):
		failed.append("a save from a newer build was not refused: %s" % [saves.said])
	if FileAccess.get_file_as_string(saves.path_of(2)) != text:
		failed.append("loading a save from a newer build changed it on disk")

	_clear()
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	quit()


func _clear() -> void:
	var at := ProjectSettings.globalize_path(DIR)
	var here := DirAccess.open(at)
	if here == null:
		return
	for name in here.get_files():
		DirAccess.remove_absolute(at.path_join(name))
