class_name PolyweaveSaves
extends RefCounted
## A game's saves in slots, kept through a crash and an update (polyweave kit "saves",
## §PW348). What is saved is the game's: a Dictionary the kit never names a field of.
##
## A slot is user://saves/<slot>.save, JSON written from Godot's own types (an int stays
## an int, a Vector2 a Vector2) inside an envelope with the version, the time and a
## SHA-256 of the data. It is written to <slot>.save.tmp first; the save it replaces
## becomes <slot>.save.bak; and only then is the new one renamed into place, so a crash
## at any step leaves the last good save where `load_slot` finds it. A save that is
## missing, does not parse or fails its sum falls back to the previous one, and says so.
##
## The project's res://polyweave_saves.gd may declare `const VERSION` and
## `static func migrations()`, a Dictionary of version -> Callable(data) -> data that
## brings a save from that version to the next. A save from an older version is brought
## up step by step; one with a step missing, or from a newer build, is refused and left
## on disk untouched, never read as a fresh start over the player's progress.

const DIR := "user://saves"
const PROJECT := "res://polyweave_saves.gd"

var dir := DIR
var version := 1
var migrations := {}
## how many slots there are; a slot is 0 to slots - 1
var slots := 3
## what the last load had to say: a fallback, a migration, a refusal
var said: Array[String] = []
## for the proof: stop a save after "written" (the .tmp) or "moved" (the old to .bak)
var stop_after := ""


func _init(at := DIR, project := PROJECT) -> void:
	dir = at
	if ResourceLoader.exists(project):
		var script: GDScript = load(project)
		var constants := script.get_script_constant_map()
		version = int(constants.get("VERSION", version))
		slots = int(constants.get("SLOTS", slots))
		for method in script.get_script_method_list():
			if method["name"] == "migrations":
				migrations = script.migrations()


func path_of(slot: int) -> String:
	return "%s/%d.save" % [dir, slot]


static func _sum(text: String) -> String:
	return text.sha256_text()


## write `data` to `slot` through a temporary file and a rename; false where it cannot
func save(slot: int, data: Dictionary) -> bool:
	if slot < 0 or slot >= slots:
		return false
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	var body := JSON.stringify(JSON.from_native(data))
	var envelope := {"version": version, "saved": Time.get_unix_time_from_system(),
		"sum": _sum(body), "data": body}
	var target := path_of(slot)
	var file := FileAccess.open(target + ".tmp", FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(JSON.stringify(envelope))
	file.flush()
	file.close()
	if stop_after == "written":
		return false
	if FileAccess.file_exists(target):
		# a save that reads becomes the one before; one that does not is kept as .bad,
		# so it never pushes the last good save out
		var kept := said.duplicate()
		var aside := ".bak" if _read(target) != null else ".bad"
		said = kept
		DirAccess.remove_absolute(_global(target + aside))
		DirAccess.rename_absolute(_global(target), _global(target + aside))
	if stop_after == "moved":
		return false
	return DirAccess.rename_absolute(_global(target + ".tmp"), _global(target)) == OK


static func _global(path: String) -> String:
	return ProjectSettings.globalize_path(path)


## the data a file holds, brought up to this version, or null with why in `said`
func _read(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		said.append("%s is not there" % path.get_file())
		return null
	var envelope: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not envelope is Dictionary or not (envelope as Dictionary).has("data"):
		said.append("%s does not parse" % path.get_file())
		return null
	var body: String = str(envelope["data"])
	if _sum(body) != str(envelope.get("sum", "")):
		said.append("%s fails its sum" % path.get_file())
		return null
	var data: Variant = JSON.to_native(JSON.parse_string(body))
	if not data is Dictionary:
		said.append("%s holds no dictionary" % path.get_file())
		return null
	var from := int(envelope.get("version", 0))
	if from > version:
		said.append("%s is from version %d, newer than this build's %d, and is left as it is"
			% [path.get_file(), from, version])
		return null
	while from < version:
		if not migrations.has(from):
			said.append("%s is from version %d, and no migration brings it to %d"
				% [path.get_file(), from, from + 1])
			return null
		data = (migrations[from] as Callable).call(data)
		said.append("%s brought from version %d to %d" % [path.get_file(), from, from + 1])
		from += 1
	return data


## a slot's data, from the save or, where it fails, the one before; {} where neither
## reads, which `said` explains
func load_slot(slot: int) -> Dictionary:
	said.clear()
	var target := path_of(slot)
	var found: Variant = _read(target)
	if found == null and FileAccess.file_exists(target + ".bak"):
		found = _read(target + ".bak")
		if found != null:
			said.append("slot %d is read from the save before it" % slot)
	return found if found != null else {}


## whether a save in `slot` could not be read and is kept on disk for that reason
func refused(slot: int) -> bool:
	return FileAccess.file_exists(path_of(slot)) and load_slot(slot).is_empty()


## every slot that holds a save, with when it was saved and its version
func listed() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for slot in slots:
		var path := path_of(slot)
		if not FileAccess.file_exists(path):
			continue
		var envelope: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
		if envelope is Dictionary:
			out.append({"slot": slot, "saved": envelope.get("saved", 0),
				"version": int(envelope.get("version", 0))})
		else:
			out.append({"slot": slot, "saved": 0, "version": -1})
	return out


func delete(slot: int) -> void:
	for suffix in ["", ".bak", ".tmp", ".bad"]:
		DirAccess.remove_absolute(_global(path_of(slot) + suffix))
