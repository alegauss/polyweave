extends SceneTree
## The tables kit's proof, run in the game it lands in (§PW364): every table the project
## generated loads through PolyweaveTables with each value of its declared type, and a
## table file changed while the game runs is read again and named by `changed`. The file
## is put back as it was. Prints KIT PROVED, or KIT FAILED with why.

const Tables := preload("res://addons/polyweave/tables/tables.gd")
const TYPES := {"int": TYPE_INT, "float": TYPE_FLOAT, "bool": TYPE_BOOL, "string": TYPE_STRING}

var failed := []
var tables: Tables
var watched := ""
var file := ""
var before := ""
var heard := ""
var since := 0
var stage := 0


func _initialize() -> void:
	tables = Tables.shared()


func _scripts() -> Array:
	var found := []
	var dir := DirAccess.open(tables.out)
	if dir != null:
		for name in dir.get_files():
			if name.ends_with(".gd"):
				found.append(name.get_basename())
	return found


func _process(_delta: float) -> bool:
	if not tables.is_inside_tree():
		return false
	match stage:
		0:
			var names := _scripts()
			if names.is_empty():
				failed.append("no generated table under %s: run tables.check write=true" % tables.out)
				return _end()
			for name in names:
				_typed(name)
			watched = names[0]
			var script: GDScript = load("%s/%s.gd" % [tables.out, watched])
			file = script.FILE
			before = FileAccess.get_file_as_string(file)
			tables.changed.connect(func(t: String) -> void: heard = t)
			# the file written again, a second on, so its modified time moves
			since = Time.get_ticks_msec()
			stage = 1
		1:
			if Time.get_ticks_msec() - since < 1100:
				return false
			var write := FileAccess.open(file, FileAccess.WRITE)
			write.store_string(before + ("\n" if not before.ends_with("\n") else ""))
			write.close()
			since = Time.get_ticks_msec()
			stage = 2
		2:
			if heard == "" and Time.get_ticks_msec() - since < 3000:
				return false
			if heard != watched:
				failed.append("%s changed on disk and the game did not read it again" % file)
			var put := FileAccess.open(file, FileAccess.WRITE)
			put.store_string(before)
			put.close()
			return _end()
	return false


func _typed(name: String) -> void:
	var script: GDScript = load("%s/%s.gd" % [tables.out, name])
	var rows := tables.get_rows(name)
	if rows.is_empty():
		failed.append("the %s table read no rows from %s" % [name, script.FILE])
	# a typed field refuses a value of another type in silence and keeps its default, so
	# each is held to the value read for it as well as to its type
	var read := Tables.values_of(script.FILE, script.COLUMNS)
	for index in rows.size():
		for column in read[index]:
			var value = read[index][column]
			var wanted: int = TYPES[script.COLUMNS[column]]
			if typeof(value) != wanted or rows[index].get(column) != value:
				failed.append("%s row %d %s reads %s (%s), not a %s" % [name, index + 1,
					column, value, type_string(typeof(value)), script.COLUMNS[column]])
				return


func _end() -> bool:
	print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
	return true
