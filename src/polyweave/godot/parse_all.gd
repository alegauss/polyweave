extends SceneTree
## Every script of a project loaded once, as engine.check runs it after an import has
## built the class cache (§PW358). Godot prints each parse error with its file and line;
## this prints PARSED and the path of each script it tried, so the run says how many it
## read. Directories starting with a dot, and those holding a .gdignore, are skipped.


func _walk(dir: String, out: Array) -> void:
	var here := DirAccess.open(dir)
	if here == null or here.file_exists(".gdignore"):
		return
	for file in here.get_files():
		if file.ends_with(".gd"):
			out.append(dir.path_join(file))
	for sub in here.get_directories():
		if not sub.begins_with("."):
			_walk(dir.path_join(sub), out)


func _initialize() -> void:
	var all := []
	_walk("res://", all)
	for path in all:
		var script := ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE) as GDScript
		print("PARSED %s %s" % [path, "ok" if script != null and script.can_instantiate() else "bad"])
	quit()
