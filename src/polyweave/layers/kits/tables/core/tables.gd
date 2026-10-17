class_name PolyweaveTables
extends Node
## A game's data tables, typed as their schema declares (polyweave kit "tables", §PW364).
## tables.check holds every row to the project's schema in the gate and writes a typed
## script per table under res://tables/ (or OUT in res://polyweave_tables.gd);
## `PolyweaveTables.shared().get_rows("enemies")` loads one through it, each row an
## object whose fields have the declared types. In a debug build a table whose file
## changes is read again within a second and `changed` names it, so a tuned value shows
## without a restart.

signal changed(table: String)

const HERE := "res://addons/polyweave/tables/tables.gd"
const PROJECT := "res://polyweave_tables.gd"

var out := "res://tables"
var _loaded := {}
var _seen := {}
var _since := 0.0

static var _shared: Node


static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweaveTables"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	if ResourceLoader.exists(PROJECT):
		out = str((load(PROJECT) as GDScript).get_script_constant_map().get("OUT", out))


## each row of a file, its values converted to the types `columns` names
static func values_of(file: String, columns: Dictionary) -> Array:
	var found := []
	if file.get_extension().to_lower() == "json":
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(file))
		if parsed is Dictionary:
			parsed = parsed.get("rows", [])
		for each in parsed if parsed is Array else []:
			found.append(each)
	else:
		var reading := FileAccess.open(file, FileAccess.READ)
		if reading == null:
			return []
		var header := reading.get_csv_line()
		while not reading.eof_reached():
			var line := reading.get_csv_line()
			if line.size() < header.size() or (line.size() == 1 and line[0] == ""):
				continue
			var row := {}
			for i in header.size():
				row[header[i]] = line[i]
			found.append(row)
	var out := []
	for row in found:
		var typed := {}
		for column in columns:
			if row.has(column) and str(row[column]) != "":
				typed[column] = _as(row[column], columns[column])
		out.append(typed)
	return out


static func _as(value: Variant, kind: String) -> Variant:
	match kind:
		"int":
			return int(value)
		"float":
			return float(value)
		"bool":
			return value if value is bool else str(value).to_lower() == "true"
	return str(value)


## a table's rows, loaded the first time through its generated script
func get_rows(table: String) -> Array:
	if not _loaded.has(table):
		_read(table)
	return _loaded.get(table, [])


## the row whose key is `key`, or null
func row(table: String, key: Variant) -> Object:
	var script: GDScript = load("%s/%s.gd" % [out, table])
	for each in get_rows(table):
		if each.get(script.KEY) == key:
			return each
	return null


func _read(table: String) -> void:
	var path := "%s/%s.gd" % [out, table]
	if not ResourceLoader.exists(path):
		push_error("there is no generated table at %s; write it with tables.check write=true" % path)
		return
	var script: GDScript = load(path)
	_loaded[table] = script.read()
	_seen[table] = FileAccess.get_modified_time(script.FILE)


func _process(delta: float) -> void:
	if not OS.is_debug_build():
		return
	_since += delta
	if _since < 0.5:
		return
	_since = 0.0
	for table in _loaded.keys():
		var script: GDScript = load("%s/%s.gd" % [out, table])
		if FileAccess.get_modified_time(script.FILE) != _seen[table]:
			_read(table)
			changed.emit(table)
