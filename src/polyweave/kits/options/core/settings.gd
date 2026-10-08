class_name PolyweaveSettings
extends RefCounted
## Every option a player can change, kept in one file under user:// (polyweave kit
## "options", §PW347). Extracted from Starship's SettingsStore and Cottony's settings.
##
## An option is a row, declared once: {tab, key, label, default} and one of `choices`
## (with `names` a player reads), `range` [min, max, step], `opens` (a scene the row
## opens, holding no value), or none, where the default is a bool. A row that holds a
## value also declares `apply`, a Callable that puts the value in force, and `read`, one
## that reads back what is in force, so `unchanging` can say which row changes nothing.
##
## Rows come from every installed kit that keeps an options.gd in its core, then from
## the project's res://polyweave_options.gd, each a script with `static func options()`.
## The project's script may declare `const VERSION` and `static func renamed()`, a
## Dictionary of "tab/key" an older build wrote to the "tab/key" it is now: a file
## from an older version is migrated, a key no row declares is kept, and a value a row
## may not take reads as its default while the file keeps it, so nothing the player
## chose is ever dropped in silence. Loading says each of these in `said`.

signal changed(tab: String, key: String, value: Variant)

const FILE := "user://polyweave_settings.cfg"
const KITS := "res://addons/polyweave"
const PROJECT := "res://polyweave_options.gd"

var path := FILE
var options: Array[Dictionary] = []
## the version of the file's layout this build writes
var version := 1
## "tab/key" an older build wrote -> the "tab/key" it is now
var renamed := {}
## what the last load had to say: a migration, a key kept, a value refused
var said: Array[String] = []
var _values := {}
var _kept := {}


func _init(at := FILE, rows: Array = [], project := PROJECT) -> void:
	path = at
	options.assign(rows if not rows.is_empty() else declared(project))
	if ResourceLoader.exists(project):
		var script: GDScript = load(project)
		version = int(script.get_script_constant_map().get("VERSION", version))
		for method in script.get_script_method_list():
			if method["name"] == "renamed":
				renamed = script.renamed()


## every row: each installed kit's options.gd in turn, then the project's own
static func declared(project := PROJECT) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var kits := DirAccess.open(KITS)
	if kits != null:
		var names := Array(kits.get_directories())
		names.sort()
		for kit in names:
			var script := "%s/%s/options.gd" % [KITS, kit]
			if ResourceLoader.exists(script):
				out.append_array(load(script).options())
	if ResourceLoader.exists(project):
		out.append_array(load(project).options())
	return out


## the tabs, in the order their first row is declared
func tabs() -> Array[String]:
	var out: Array[String] = []
	for each in options:
		if not out.has(each["tab"]):
			out.append(each["tab"])
	return out


func in_tab(tab: String) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for each in options:
		if each["tab"] == tab:
			out.append(each)
	return out


func option(tab: String, key: String) -> Dictionary:
	for each in options:
		if each["tab"] == tab and each["key"] == key:
			return each
	return {}


static func holds_value(row: Dictionary) -> bool:
	return not row.has("opens")


func get_value(tab: String, key: String) -> Variant:
	return _values.get("%s/%s" % [tab, key], option(tab, key).get("default"))


## set, put in force, save and say so; a value the row does not allow changes nothing
func set_value(tab: String, key: String, value: Variant) -> bool:
	var row := option(tab, key)
	if row.is_empty() or not allows(row, value):
		return false
	var at := "%s/%s" % [tab, key]
	_values[at] = value
	_kept.erase(at)
	_apply(row)
	save()
	changed.emit(tab, key, value)
	return true


func allows(row: Dictionary, value: Variant) -> bool:
	if not holds_value(row):
		return false
	if row.has("choices"):
		return (row["choices"] as Array).has(value)
	if row.has("range"):
		var bounds: Array = row["range"]
		return (value is int or value is float) and value >= bounds[0] and value <= bounds[1]
	return typeof(value) == typeof(row["default"])


func _apply(row: Dictionary) -> void:
	if row.has("apply"):
		(row["apply"] as Callable).call(get_value(row["tab"], row["key"]))


## every row's value put in force
func apply_all() -> void:
	for row in options:
		if holds_value(row):
			_apply(row)


## read the file and put every value in force; a missing file is every default
func load_file() -> void:
	_values.clear()
	_kept.clear()
	said.clear()
	var file := ConfigFile.new()
	if not FileAccess.file_exists(path):
		apply_all()
		return
	if file.load(path) != OK:
		DirAccess.copy_absolute(ProjectSettings.globalize_path(path),
			ProjectSettings.globalize_path(path + ".bad"))
		said.append("%s could not be read, so it is kept as %s.bad" % [path, path])
		apply_all()
		return
	var from := int(file.get_value("meta", "version", 0))
	for tab in file.get_sections():
		if tab == "meta":
			continue
		for key in file.get_section_keys(tab):
			_take("%s/%s" % [tab, key], file.get_value(tab, key))
	if from < version:
		said.append("migrated from version %d to %d" % [from, version])
		save()
	apply_all()


func _take(at: String, value: Variant) -> void:
	if renamed.has(at):
		said.append("%s is %s now" % [at, renamed[at]])
		at = renamed[at]
	var parts := at.split("/", true, 1)
	var row := option(parts[0], parts[1]) if parts.size() == 2 else {}
	if row.is_empty():
		said.append("%s is no option of this build, and is kept" % at)
		_kept[at] = value
	elif not allows(row, value):
		said.append("%s held %s, which it may not take, so it reads its default" % [at, value])
		_kept[at] = value
	else:
		_values[at] = value


## write what the player set and what the file held that this build does not read
func save() -> void:
	var file := ConfigFile.new()
	file.set_value("meta", "version", version)
	for held in [_kept, _values]:
		for at in held:
			var parts: PackedStringArray = at.split("/", true, 1)
			file.set_value(parts[0], parts[1], held[at])
	file.save(path)


## every option of `tab` back to its default, in force and kept
func reset_tab(tab: String) -> void:
	for row in in_tab(tab):
		_values.erase("%s/%s" % [tab, row["key"]])
	save()
	for row in in_tab(tab):
		if holds_value(row):
			_apply(row)
			changed.emit(tab, row["key"], row["default"])


## a value the row may take other than the one it has
func _other(row: Dictionary) -> Variant:
	var now: Variant = get_value(row["tab"], row["key"])
	if row.has("choices"):
		for each in row["choices"]:
			if each != now:
				return each
		return null
	if row.has("range"):
		var bounds: Array = row["range"]
		return bounds[1] if now != bounds[1] else bounds[0]
	if now is bool:
		return not now
	return null


## each row that changes nothing it says it changes, by name: set to another value, its
## `read` must answer that value; a row with no read, or one opening a scene that is
## not there, is said too. Every value is put back as it was.
func unchanging() -> Array[String]:
	var out: Array[String] = []
	for row in options:
		var named := "%s/%s" % [row["tab"], row["key"]]
		if not holds_value(row):
			if not ResourceLoader.exists(row["opens"]):
				out.append("%s opens %s, which is not there" % [named, row["opens"]])
			continue
		if not row.has("read") or not row.has("apply"):
			out.append("%s declares no apply and read, so nothing can say it works" % named)
			continue
		var was: Variant = get_value(row["tab"], row["key"])
		var had := _values.has(named)
		var other: Variant = _other(row)
		if other == null:
			continue
		set_value(row["tab"], row["key"], other)
		var read: Variant = (row["read"] as Callable).call()
		var same: bool = is_equal_approx(float(read), float(other)) if (
			other is float or other is int) else read == other
		if not same:
			out.append("%s changes nothing: set to %s, it reads %s" % [named, other, read])
		if had:
			set_value(row["tab"], row["key"], was)
		else:
			_values.erase(named)
			_apply(row)
			save()
	return out
