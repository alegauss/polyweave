extends SceneTree
## Holds a running game still and moves it only when an agent says so (§PW212).
##
## Launched in place of the game's own main loop:
##
##     godot --path <project> --script res://addons/polyweave_driver/driver.gd -- --seed=1
##
## It loads the project's main scene itself, prints one line naming its port and token,
## and answers one JSON object per line on a loopback socket. docs/specs/driving.md is
## the contract. The game is held by blocking the main loop between commands, never by
## pausing the tree: a paused tree still emits process_frame, and a game awaiting it
## moved on while held (§PW211).

const DEFAULT_PROPERTIES := ["name", "visible", "position", "text", "disabled"]

var server := TCPServer.new()
var peer: StreamPeerTCP
var token := ""
var buffer := PackedByteArray()
var main: Node

## Frames let pass since start; every answer carries it.
var frame := 0
## Frames still to pass before holding again, for a `step` or a `wait` in progress.
var running := 0
## The request a `step` or `wait` answers once its frames have passed.
var pending: Dictionary = {}
## A `wait` in progress: what it waits for and how many frames it has spent.
var waiting: Dictionary = {}


func _initialize() -> void:
	var port := 0
	var scene_path := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--port="):
			port = int(arg.get_slice("=", 1))
		elif arg.begins_with("--seed="):
			seed(int(arg.get_slice("=", 1)))
		elif arg.begins_with("--scene="):
			scene_path = arg.get_slice("=", 1)
	var bound := server.listen(port, "127.0.0.1")
	if bound != OK:
		push_error("polyweave_driver: could not listen on port %d (%s)" % [port, bound])
		quit(1)
		return
	token = Crypto.new().generate_random_bytes(16).hex_encode()
	if scene_path != "":
		var packed := load(scene_path) as PackedScene
		if packed == null:
			push_error("polyweave_driver: there is no scene at %s" % scene_path)
			quit(1)
			return
		main = packed.instantiate()
		root.add_child(main)
	print("polyweave_driver: port=%d token=%s" % [server.get_local_port(), token])


func _process(_delta: float) -> bool:
	# Called before any node processes this frame. Returning lets the frame run; not
	# returning holds everything, which is the whole point.
	if not sized:
		_size_headless()
	if running > 0 or not waiting.is_empty():
		frame += 1
		running = maxi(running - 1, 0)
		if not waiting.is_empty():
			waiting["spent"] += 1
			var met := _met(waiting)
			if not met and waiting["spent"] < waiting["budget"]:
				return false
			_answer(pending, {"met": met, "frames": waiting["spent"]})
			waiting = {}
			pending = {}
		elif running > 0:
			return false
		else:
			_answer(pending, {"frames": pending.get("frames", 1)})
			pending = {}
	return _hold()


var sized := false
## Input waiting for the next frame to pass.
var queued: Array = []


func _deliver() -> void:
	for event in queued:
		root.push_input(event, true)
	queued = []


## A headless window is 64 by 64 whatever the project says, and a pointer outside it
## hovers nothing, so a Button takes a click and never fires. The root takes the size the
## project declares, which is the size its layout was made for. Set on the first frame:
## set during _initialize, the headless server put it back.
func _size_headless() -> void:
	sized = true
	if DisplayServer.get_name() == "headless":
		root.size = Vector2i(
			int(ProjectSettings.get_setting("display/window/size/viewport_width", 1152)),
			int(ProjectSettings.get_setting("display/window/size/viewport_height", 648))
		)


## Read commands until one asks for frames to pass; true quits.
func _hold() -> bool:
	while true:
		var request = _next_request()
		if request == null:
			quit()
			return true
		if not (request is Dictionary):
			continue
		var asked: Dictionary = request
		if str(asked.get("token", "")) != token:
			_send({"id": asked.get("id"), "ok": false, "error": "driver.bad-token",
				"message": "the token does not match the one this driver printed"})
			peer.disconnect_from_host()
			quit(1)
			return true
		var outcome := _command(asked)
		if outcome.has("quit"):
			_answer(asked, null)
			quit()
			return true
		if outcome.has("run"):
			_deliver()
			return false
		if outcome.has("error"):
			_send({"id": asked.get("id"), "ok": false, "frame": frame,
				"error": outcome["error"], "message": outcome["message"]})
		else:
			_answer(asked, outcome.get("result"))
	return true


# -- the socket ---------------------------------------------------------------------------


func _next_request():
	while true:
		if peer == null:
			if server.is_connection_available():
				peer = server.take_connection()
			else:
				OS.delay_msec(2)
				continue
		peer.poll()
		if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			return null
		var available := peer.get_available_bytes()
		if available > 0:
			var got: Array = peer.get_data(available)
			if got[0] == OK:
				buffer.append_array(got[1])
		var cut := buffer.find(10) # a newline ends one request
		if cut >= 0:
			var line := buffer.slice(0, cut).get_string_from_utf8()
			buffer = buffer.slice(cut + 1)
			if line.strip_edges() == "":
				continue
			return JSON.parse_string(line)
		OS.delay_msec(2)
	return null


func _send(answer: Dictionary) -> void:
	peer.put_data((JSON.stringify(answer) + "\n").to_utf8_buffer())


func _answer(request: Dictionary, result) -> void:
	_send({"id": request.get("id"), "ok": true, "frame": frame, "result": _plain(result)})


# -- the commands -------------------------------------------------------------------------


func _command(asked: Dictionary) -> Dictionary:
	match str(asked.get("cmd", "")):
		"query":
			return _query(asked)
		"input":
			return _input(asked)
		"step":
			var count := int(asked.get("frames", 1))
			if count < 1:
				return _refused("driver.bad-command", "step takes a number of frames, 1 or more")
			running = count
			pending = asked
			return {"run": true}
		"wait":
			return _wait(asked)
		"call":
			return _call(asked)
		"shot":
			return _shot(asked)
		"close":
			return {"quit": true}
	return _refused(
		"driver.bad-command",
		"there is no command %s; the commands are query, input, step, wait, call, shot and close"
		% JSON.stringify(asked.get("cmd"))
	)


func _refused(code: String, message: String) -> Dictionary:
	return {"error": code, "message": message}


func _found(asked: Dictionary) -> Array:
	if asked.has("path"):
		var path := str(asked["path"])
		var node: Node = root.get_node_or_null(path) if path.begins_with("/") else (
			main.get_node_or_null(path) if main else null
		)
		return [node] if node else []
	if asked.has("group"):
		return get_nodes_in_group(str(asked["group"]))
	if asked.has("class"):
		var out := []
		_collect(root, str(asked["class"]), out)
		return out
	return []


func _collect(node: Node, named: String, out: Array) -> void:
	var script: Script = node.get_script()
	if node.get_class() == named or node.is_class(named) or (
		script != null and script.get_global_name() == named
	):
		out.append(node)
	for child in node.get_children():
		_collect(child, named, out)


func _query(asked: Dictionary) -> Dictionary:
	var nodes := _found(asked)
	if nodes.is_empty():
		return _refused("driver.no-node", "nothing answers %s" % _named(asked))
	var wanted: Array = asked.get("properties", DEFAULT_PROPERTIES)
	var result := []
	for node: Node in nodes:
		var properties := {}
		for name in wanted:
			if str(name) in node:
				properties[str(name)] = node.get(str(name))
		result.append({"path": str(node.get_path()), "class": node.get_class(),
			"properties": properties})
	return {"result": result}


func _input(asked: Dictionary) -> Dictionary:
	var events := []
	var landed = null
	if asked.has("action"):
		for pressed in [true, false]:
			var event := InputEventAction.new()
			event.action = StringName(str(asked["action"]))
			event.pressed = pressed
			events.append(event)
	elif asked.has("key"):
		var code := OS.find_keycode_from_string(str(asked["key"]))
		if code == KEY_NONE:
			return _refused("driver.bad-command", "there is no key called %s" % asked["key"])
		for pressed in [true, false]:
			var event := InputEventKey.new()
			event.keycode = code
			event.physical_keycode = code
			event.pressed = pressed
			events.append(event)
	elif asked.has("click"):
		var click: Dictionary = asked["click"] if asked["click"] is Dictionary else {}
		var at: Vector2
		if click.has("at"):
			at = Vector2(click["at"][0], click["at"][1])
		else:
			var nodes := _found(click)
			if nodes.is_empty() or not (nodes[0] is CanvasItem):
				return _refused("driver.no-node", "nothing on screen answers %s" % _named(click))
			at = _centre(nodes[0])
		var seen := root.get_visible_rect()
		if not seen.has_point(at):
			# A pointer outside the window hovers nothing, so a button there takes the
			# press and never fires; a project with no window size runs at 64 by 64.
			return _refused("driver.off-screen",
				"the click at %s is outside the %d by %d viewport, where nothing is hovered; set display/window/size in project.godot"
				% [at, int(seen.size.x), int(seen.size.y)])
		landed = at
		# The pointer arrives before it presses: a Button fires on release only while
		# the mouse is over it, and hovering is what a motion event sets.
		var moved := InputEventMouseMotion.new()
		moved.position = at
		moved.global_position = at
		events.append(moved)
		for pressed in [true, false]:
			var event := InputEventMouseButton.new()
			event.button_index = MOUSE_BUTTON_LEFT
			event.pressed = pressed
			event.position = at
			event.global_position = at
			events.append(event)
	else:
		return _refused("driver.bad-command", "input takes an action, a key or a click")
	# Delivered when the next frame passes, not now: a signal the input causes then fires
	# inside a `step` or `wait`, where a wait armed for it can see it.
	queued.append_array(events)
	return {"result": {"at": landed} if landed != null else {}}


func _centre(item: CanvasItem) -> Vector2:
	var middle := Vector2.ZERO
	if item is Control:
		middle = (item as Control).size / 2.0
	return item.get_global_transform_with_canvas() * middle


func _wait(asked: Dictionary) -> Dictionary:
	var budget := int(asked.get("frames", 60))
	var condition := {"spent": 0, "budget": budget, "asked": asked, "fired": false}
	if asked.has("signal"):
		var nodes := _found(asked)
		if nodes.is_empty():
			return _refused("driver.no-node", "nothing answers %s" % _named(asked))
		var source: Node = nodes[0]
		if not source.has_signal(str(asked["signal"])):
			return _refused("driver.bad-command",
				"%s has no signal %s" % [source.get_path(), asked["signal"]])
		source.connect(str(asked["signal"]), func(_a = null, _b = null, _c = null, _d = null):
			condition["fired"] = true, CONNECT_ONE_SHOT)
	elif not (asked.has("node") or asked.has("property")):
		return _refused("driver.bad-command",
			"wait takes a signal, a node, or a property and the value it should equal")
	if _met(condition):
		return {"result": {"met": true, "frames": 0}}
	if budget < 1:
		return {"result": {"met": false, "frames": 0}}
	waiting = condition
	pending = asked
	return {"run": true}


func _met(condition: Dictionary) -> bool:
	var asked: Dictionary = condition["asked"]
	if asked.has("signal"):
		return condition["fired"]
	if asked.has("node"):
		var named := str(asked["node"])
		if named.begins_with("/") or named.contains("/"):
			return _found({"path": named}).size() > 0
		return _found({"path": named}).size() > 0 or not get_nodes_in_group(named).is_empty()
	var nodes := _found(asked)
	if nodes.is_empty() or not (str(asked["property"]) in nodes[0]):
		return false
	var value = _plain(nodes[0].get(str(asked["property"])))
	var wanted = asked.get("equals")
	# JSON gives every number as a float, and a node's int is still the same number.
	if typeof(value) in [TYPE_INT, TYPE_FLOAT] and typeof(wanted) in [TYPE_INT, TYPE_FLOAT]:
		return is_equal_approx(float(value), float(wanted))
	return JSON.stringify(value) == JSON.stringify(wanted)


func _call(asked: Dictionary) -> Dictionary:
	var nodes := _found(asked)
	if nodes.is_empty():
		return _refused("driver.no-node", "nothing answers %s" % _named(asked))
	var method := str(asked.get("method", ""))
	if not nodes[0].has_method(method):
		return _refused("driver.no-method", "%s has no method %s" % [nodes[0].get_path(), method])
	return {"result": nodes[0].callv(method, asked.get("args", []))}


func _shot(asked: Dictionary) -> Dictionary:
	if DisplayServer.get_name() == "headless":
		return _refused("driver.no-picture",
			"a headless run draws nothing; launch with a display to take a shot")
	var image := root.get_texture().get_image()
	var out := str(asked.get("out", "user://driver_shot.png"))
	if out.begins_with("res://") or out.begins_with("user://"):
		out = ProjectSettings.globalize_path(out)
	image.save_png(out)
	return {"result": {"out": out, "size": [image.get_width(), image.get_height()]}}


func _named(asked: Dictionary) -> String:
	for key in ["path", "group", "class"]:
		if asked.has(key):
			return "%s %s" % [key, asked[key]]
	return "no path, group or class"


## A value as JSON can carry it (docs/specs/driving.md, "The protocol").
func _plain(value):
	match typeof(value):
		TYPE_VECTOR2, TYPE_VECTOR2I:
			return [value.x, value.y]
		TYPE_VECTOR3, TYPE_VECTOR3I:
			return [value.x, value.y, value.z]
		TYPE_COLOR:
			return [value.r, value.g, value.b, value.a]
		TYPE_STRING_NAME, TYPE_NODE_PATH:
			return str(value)
		TYPE_OBJECT:
			if value == null:
				return null
			if value is Node:
				return str(value.get_path()) if value.is_inside_tree() else value.get_class()
			return value.get_class()
		TYPE_ARRAY, TYPE_PACKED_STRING_ARRAY, TYPE_PACKED_INT32_ARRAY, \
		TYPE_PACKED_FLOAT32_ARRAY, TYPE_PACKED_VECTOR2_ARRAY:
			var out := []
			for one in value:
				out.append(_plain(one))
			return out
		TYPE_DICTIONARY:
			var out := {}
			for key in value:
				out[str(key)] = _plain(value[key])
			return out
		TYPE_NIL, TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING:
			return value
	return var_to_str(value)
