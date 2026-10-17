class_name PolyweaveState
extends RefCounted
## A game's state declared for reading (polyweave kit "state", §PW359). Which values
## matter (the player's health, the current scene, the enemy count, the seed) lived in an
## agent's head for one session, so it added a print, ran the game and removed the print,
## and the next session did it again. The project names them once instead, in
## res://polyweave_state.gd:
##
##     const STATE := {
##         "health": {"node": "Player", "property": "health", "type": "int"},
##         "level": {"node": "Level", "method": "snapshot", "type": "Dictionary"},
##     }
##
## A node is a path from the current scene, or from /root where it starts with one; a
## property may be nested, "stats:health". `read(names)` answers each name with its
## value and its type, and why where it cannot; the driver serves it to
## `game.query state=[...]`, and `snapshot()` is every name at once, which a crash dump
## writes and a determinism check compares.

const PROJECT := "res://polyweave_state.gd"


## the names the project declares, each {node, property or method, type}
static func declared(project := PROJECT) -> Dictionary:
	if not ResourceLoader.exists(project):
		return {}
	return (load(project) as GDScript).get_script_constant_map().get("STATE", {})


## each name asked ("*" or none for every one) with its value, its type and whether it
## holds the type declared
static func read(names: Array = []) -> Dictionary:
	var all := declared()
	var asked: Array = all.keys() if names.is_empty() or names == ["*"] else names
	var out := {}
	for name in asked:
		out[name] = _one(str(name), all)
	return out


## every declared name's value, nothing else: what a dump writes and a replay compares
static func snapshot() -> Dictionary:
	var out := {}
	var each := read()
	for name in each:
		out[name] = each[name].get("value")
	return out


static func _one(name: String, all: Dictionary) -> Dictionary:
	if not all.has(name):
		return {"ok": false, "said": "no state is named %s; the names are %s" % [
			name, ", ".join(all.keys())]}
	var entry: Dictionary = all[name]
	var node := _node(str(entry.get("node", "")))
	if node == null:
		return {"ok": false, "said": "%s reads %s, which is not in the running game" % [
			name, entry.get("node", "")]}
	var value: Variant
	if entry.has("method"):
		if not node.has_method(str(entry["method"])):
			return {"ok": false, "said": "%s calls %s on %s, which has no such method" % [
				name, entry["method"], entry["node"]]}
		value = node.call(str(entry["method"]))
	else:
		var property := NodePath(str(entry.get("property", "")))
		value = node.get_indexed(property)
		if value == null and not str(entry.get("property", "")).get_slice(":", 0) in node:
			return {"ok": false, "said": "%s reads %s on %s, which has no such property" % [
				name, entry.get("property", ""), entry["node"]]}
	var kind := type_string(typeof(value))
	var wanted := str(entry.get("type", kind))
	var held := kind == wanted
	return {"ok": held, "value": value, "type": kind,
		"said": "" if held else "%s is %s, not the %s declared" % [name, kind, wanted]}


static func _node(path: String) -> Node:
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null or path == "":
		return null
	if path.begins_with("/root"):
		return tree.root.get_node_or_null(path)
	var scene := tree.current_scene
	return scene.get_node_or_null(path) if scene != null else null
