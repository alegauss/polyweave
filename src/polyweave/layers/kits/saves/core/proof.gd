extends SceneTree
## The saves kit's proof, run in the game it lands in (§PW348), all of it automatic:
## every slot filled and read back with Godot's own types; a save stopped after its
## write and after its move loads the last good one; a corrupt save falls back to the
## one before and never pushes it out; a save from each older version comes up through
## the project's migrations; one from a newer build is refused and left on disk; and a
## game's older save is taken into slot 0 once (§PW398). Prints KIT PROVED, or KIT FAILED with why.

const _PwSaves := preload("res://addons/polyweave/saves/saves.gd")
## A folder of this run's own (§PW523). Godot names user:// after the project, so two
## proofs at once in fixtures of one name shared one fixed folder and emptied it under
## each other.
var dir := ""

var failed := []


func _data(n: int) -> Dictionary:
	return {"level": n, "score": 1000.5 + n, "at": Vector2(n, -n), "seen": [n, "x", true],
		"nested": {"inner": PackedInt32Array([n, n + 1])}}


func _same(a: Variant, b: Variant) -> bool:
	return var_to_str(a) == var_to_str(b)


func _initialize() -> void:
	dir = "user://polyweave_proof/saves_%d_%d" % [OS.get_process_id(), Time.get_ticks_usec()]
	var saves := _PwSaves.new(dir)
	saves.adopt = Callable()
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

	# The cases below each run on the last slot the game declares, cleared before them
	# (§PW534): a game keeping one save proves on slot 0 alone, never on a slot it lacks.
	var last := saves.slots - 1
	_clear()
	saves.save(last, _data(20))
	saves.save(last, _data(21))
	# the data changed under a sum that still reads, as a disk or a hand edit leaves it
	var envelope: Variant = JSON.parse_string(FileAccess.get_file_as_string(saves.path_of(last)))
	if not envelope is Dictionary:
		failed.append("slot %d holds no save that reads after two saves" % last)
		envelope = {"data": ""}
	envelope["data"] = str(envelope["data"]).replace("21", "99")
	FileAccess.open(saves.path_of(last), FileAccess.WRITE).store_string(JSON.stringify(envelope))
	if not _same(saves.load_slot(last), _data(20)) or not "; ".join(saves.said).contains("save before"):
		failed.append("a corrupt save did not fall back to the one before: %s" % [saves.said])
	saves.save(last, _data(22))
	if not _same(saves._read(saves.path_of(last) + ".bak"), _data(20)):
		failed.append("saving over a corrupt save pushed the last good one out")
	saves.save(last, _data(23))
	if not _same(saves.load_slot(last), _data(23)):
		failed.append("saving over a corrupt save lost the new one")
	if not FileAccess.file_exists(saves.path_of(last) + ".bak"):
		failed.append("no save before was kept")

	for from in range(1, saves.version):
		if not saves.migrations.has(from):
			failed.append("no migration brings a version %d save to %d" % [from, from + 1])
			continue
		_clear()
		var old := _PwSaves.new(dir, "res://none.gd")
		old.version = from
		old.slots = saves.slots
		old.save(last, _data(30))
		var brought := saves.load_slot(last)
		if brought.is_empty():
			failed.append("a version %d save did not come up: %s" % [from, saves.said])

	_clear()
	var newer := _PwSaves.new(dir, "res://none.gd")
	newer.version = saves.version + 1
	newer.slots = saves.slots
	newer.save(last, _data(40))
	var text := FileAccess.get_file_as_string(saves.path_of(last))
	saves.load_slot(last)
	if not "; ".join(saves.said).contains("newer than this build"):
		failed.append("a save from a newer build was not refused: %s" % [saves.said])
	if FileAccess.get_file_as_string(saves.path_of(last)) != text:
		failed.append("loading a save from a newer build changed it on disk")

	# A game's older save (§PW398): with no slot saved, what its `adopted` reads is taken
	# into slot 0 once and said; a slot deleted afterwards stays empty. The proof's own
	# Callable stands in for the game's, so the game's real older file is never read here.
	_clear()
	var adopting := _PwSaves.new(dir)
	adopting.adopt = func() -> Dictionary: return _data(50)
	if not _same(adopting.load_slot(0), _data(50)):
		failed.append("an older save was not taken into slot 0: %s" % [adopting.said])
	elif not "; ".join(adopting.said).contains("older save"):
		failed.append("taking an older save was not said")
	adopting.delete(0)
	if not adopting.load_slot(0).is_empty() or not adopting.listed().is_empty():
		failed.append("an older save was taken again after its slot was deleted")
	var played := _PwSaves.new(dir)
	_clear()
	played.save(last, _data(60))
	played.adopt = func() -> Dictionary: return _data(50)
	played.load_slot(0)
	if FileAccess.file_exists("%s/%s" % [dir, _PwSaves.ADOPTED]) \
			or not _same(played.load_slot(last), _data(60)):
		failed.append("an older save was taken over a game already saved in the kit")

	_clear()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(dir))
	if failed.is_empty():
		print("KIT PROVED")
	else:
		print("KIT FAILED: " + "; ".join(failed))
	quit()


func _clear() -> void:
	var at := ProjectSettings.globalize_path(dir)
	var here := DirAccess.open(at)
	if here == null:
		return
	for name in here.get_files():
		DirAccess.remove_absolute(at.path_join(name))
