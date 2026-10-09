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

## A kept flow being replayed: its steps, and which one is next (§PW214).
var flow_path := ""
var flow: Array = []
var flow_at := 0
## The step whose answer is awaited, so the answer can be held to what the flow expects.
var flow_step: Dictionary = {}
var failed := false
## Seconds with no request before the driver quits; 0 waits for ever.
var idle := 0
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
		elif arg.begins_with("--locale="):
			# The language the project declares for its pictures (§PW339).
			TranslationServer.set_locale(arg.get_slice("=", 1))
		elif arg.begins_with("--idle="):
			idle = int(arg.get_slice("=", 1))
		elif arg.begins_with("--flow="):
			flow_path = arg.get_slice("=", 1)
		elif arg == "offscreen":
			# The offscreen route's wish (offscreen.py): a real window, off the desktop.
			DisplayServer.window_set_position(Vector2i(-20000, -20000))
		elif arg == "minimized":
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	if flow_path != "":
		# A kept flow replays inside the game, with no socket (§PW214).
		var text := FileAccess.get_file_as_string(flow_path)
		var parsed = JSON.parse_string(text) if text != "" else null
		if not (parsed is Dictionary) or not (parsed.get("steps") is Array):
			push_error("polyweave_driver: there is no flow to replay at %s" % flow_path)
			quit(1)
			return
		flow = parsed["steps"]
		if parsed.get("seed"):
			seed(int(parsed["seed"]))
		if str(parsed.get("scene", "")) != "":
			scene_path = str(parsed["scene"])
	var bound := server.listen(port, "127.0.0.1") if flow_path == "" else OK
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
		# Current, as the engine makes it for a player, so the game's own
		# change_scene_to_file frees it rather than running a second scene over it
		# (§PW297).
		current_scene = main
	if flow_path == "":
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
				_deliver()
				return false
			_answer(pending, {"met": met, "frames": waiting["spent"]})
			waiting = {}
			pending = {}
		elif running > 0:
			_deliver()
			return false
		else:
			_answer(pending, {"frames": pending.get("frames", 1)})
			pending = {}
	return _hold()


var sized := false
## Input waiting for the next frame to pass.
var queued: Array = []


## Deliver what is due on the frame about to run, and bring the rest a frame nearer.
## An action or a key goes through Input, which is what a game polling
## Input.is_action_pressed reads; a click goes to the viewport, where hovering is.
func _deliver() -> void:
	var later := []
	for item in queued:
		if item["after"] > 0:
			item["after"] -= 1
			later.append(item)
		elif item["via"] == "input":
			Input.parse_input_event(item["event"])
			# Buffered input waits for the next frame's flush; applied now, it lands on
			# the frame about to run, as a viewport event does.
			Input.flush_buffered_events()
		else:
			root.push_input(item["event"], true)
	queued = later


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
			quit(1 if failed else 0)
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
	if flow_path != "":
		if failed:
			return null
		if flow_at >= flow.size():
			print("polyweave_flow: passed steps=%d frame=%d" % [flow.size(), frame])
			return null
		flow_step = flow[flow_at]
		flow_at += 1
		var request: Dictionary = flow_step.duplicate()
		request["token"] = token
		request["id"] = flow_at
		return request
	# A caller may connect once per command (a command line is a process a call), so a
	# connection closing leaves the game held for the next one. Only `close`, or no
	# request for `--idle` seconds, ends the run, so a forgotten session never outlives
	# the conversation that opened it.
	var since := Time.get_ticks_msec()
	while true:
		if idle > 0 and Time.get_ticks_msec() - since > idle * 1000:
			print("polyweave_driver: idle for %d s, quitting" % idle)
			return null
		if peer == null or peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			peer = null
			buffer = PackedByteArray()
			if server.is_connection_available():
				peer = server.take_connection()
			else:
				OS.delay_msec(2)
				continue
		peer.poll()
		if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			continue
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
	if flow_path != "":
		_judge(answer)
		return
	peer.put_data((JSON.stringify(answer) + "\n").to_utf8_buffer())


## A replayed step's answer, held to what the flow kept it for: a refusal, a wait that
## must be met and was not, or an expectation that did not hold ends the run.
func _judge(answer: Dictionary) -> void:
	var why := ""
	var result = answer.get("result")
	if not answer.get("ok", false):
		why = "%s: %s" % [answer.get("error"), answer.get("message")]
	elif flow_step.get("cmd") == "wait" and flow_step.get("must", true) and result is Dictionary \
			and not result.get("met", false):
		why = "the wait was not met in %s frames" % result.get("frames")
	elif flow_step.get("cmd") == "expect" and result is Dictionary and not result.get("held", false):
		why = "%s.%s was %s, not %s" % [_named(flow_step), flow_step.get("property"),
			JSON.stringify(result.get("value")), JSON.stringify(flow_step.get("equals"))]
	if why != "":
		print("polyweave_flow: failed step=%d frame=%d why=%s" % [flow_at, frame, why])
		flow = []
		flow_at = 0
		failed = true


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
		"expect":
			return _expect(asked)
		"set":
			return _set_property(asked)
		"selector":
			return _selector_of(asked)
		"locale":
			# The table's language on screen, two frames on so every label relaid out.
			TranslationServer.set_locale(str(asked.get("locale", "")))
			running = 2
			pending = asked
			return {"run": true}
		"text_fit":
			return _text_fit()
		"state":
			return _state(asked)
		"close":
			return {"quit": true}
	return _refused(
		"driver.bad-command",
		"there is no command %s; the commands are query, state, input, step, wait, call, shot, locale, text_fit and close"
		% JSON.stringify(asked.get("cmd"))
	)


## Every visible Label and Button, and whether its text fits where it is drawn (§PW336):
## wider than its box, more lines than it shows, out of its container, or over another.
func _text_fit() -> Dictionary:
	var texts := []
	_texts(get_root(), texts)
	var found := []
	for node: Control in texts:
		var box := _screen_rect(node)
		var shown: String = node.tr(node.text) if node.auto_translate_mode != Node.AUTO_TRANSLATE_MODE_DISABLED else node.text
		var font: Font = node.get_theme_font("font")
		var font_size: int = node.get_theme_font_size("font_size")
		var widest := 0.0
		for line in shown.split("\n"):
			widest = max(widest, font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x)
		var entry := {"path": str(node.get_path()), "class": node.get_class(), "key": node.text,
			"text": shown, "box": [box.position.x, box.position.y, box.size.x, box.size.y],
			"findings": []}
		if node is Label:
			var label := node as Label
			var lines := label.get_line_count()
			var visible_lines := label.get_visible_line_count()
			entry["lines"] = lines
			entry["visible_lines"] = visible_lines
			if lines > visible_lines:
				entry["findings"].append("shows %d of its %d lines" % [visible_lines, lines])
			if label.autowrap_mode == TextServer.AUTOWRAP_OFF and widest > box.size.x + 0.5:
				entry["findings"].append("its text is %d px wide in a %d px box" % [widest, box.size.x])
		elif widest > box.size.x + 0.5:
			entry["findings"].append("its text is %d px wide in a %d px box" % [widest, box.size.x])
		var parent := node.get_parent()
		if parent is Control and not (parent is Container and parent is ScrollContainer):
			var outer := _screen_rect(parent as Control)
			if outer.size.x > 0 and outer.size.y > 0 and not outer.grow(0.5).encloses(box):
				entry["findings"].append("it leaves its container %s" % str(parent.get_path()))
		entry["overlaps"] = []
		found.append(entry)
	for i in found.size():
		for j in range(i + 1, found.size()):
			var a: Control = texts[i]
			var b: Control = texts[j]
			if a.is_ancestor_of(b) or b.is_ancestor_of(a):
				continue
			if _screen_rect(a).grow(-0.5).intersects(_screen_rect(b).grow(-0.5)):
				found[i]["overlaps"].append(found[j]["path"])
				found[j]["overlaps"].append(found[i]["path"])
	for entry in found:
		for other in entry["overlaps"]:
			entry["findings"].append("it lies over %s" % other)
	return {"result": found}


func _texts(node: Node, out: Array) -> void:
	if (node is Label or node is Button) and (node as CanvasItem).is_visible_in_tree() \
			and str(node.text) != "":
		out.append(node)
	for child in node.get_children():
		_texts(child, out)


func _screen_rect(node: Control) -> Rect2:
	var placed := node.get_global_transform_with_canvas()
	return Rect2(placed.origin, node.size * placed.get_scale())


func _refused(code: String, message: String) -> Dictionary:
	return {"error": code, "message": message}


func _found(asked: Dictionary) -> Array:
	if asked.has("select") and asked["select"] is Dictionary:
		return _selected(asked["select"])
	if asked.has("path"):
		var path := str(asked["path"])
		# Relative to the scene playing now, which a scene change replaces.
		var node: Node = root.get_node_or_null(path) if path.begins_with("/") else (
			current_scene.get_node_or_null(path) if current_scene else null
		)
		return [node] if node else []
	if asked.has("group"):
		return get_nodes_in_group(str(asked["group"]))
	if asked.has("class"):
		var out := []
		_collect(root, str(asked["class"]), out)
		return out
	return []


## The nodes a selector picks out: its class, engine or script, and every other key a
## property the node holds at that value (§PW270). A path Godot generated, such as
## @Node2D@14, is renumbered by any node added before it; what a node is holds.
func _selected(select: Dictionary) -> Array:
	var out := []
	var named := str(select.get("class", "Node"))
	# `under` looks only inside the nodes another selector finds, not at them (§PW277):
	# an unnamed button is the one TextureButton under the screen the game does name.
	if select.get("under") is Dictionary:
		for above: Node in _selected(select["under"]):
			for child in above.get_children():
				_collect(child, named, out)
	else:
		_collect(root, named, out)
	var kept := []
	for node: Node in out:
		var holds := true
		for key in select:
			if str(key) in ["class", "under", "nth"]:
				continue
			if not (str(key) in node) or JSON.stringify(_plain(node.get(str(key)))) \
					!= JSON.stringify(select[key]):
				holds = false
				break
		if holds:
			kept.append(node)
	# `nth` is the node's place among those that match, in tree order.
	if select.has("nth"):
		var at := int(select["nth"])
		return [kept[at]] if at >= 0 and at < kept.size() else []
	return kept


#: The properties a selector may pick a node out by, in the order they are tried.
const SELECTING := ["name", "text", "title", "tooltip_text", "placeholder_text"]


## The selector that picks this one node out now, or null where none does.
func _selector_of(asked: Dictionary) -> Dictionary:
	var nodes := _found(asked)
	if nodes.size() != 1:
		return _refused("driver.no-node", "nothing answers %s" % _named(asked))
	var node: Node = nodes[0]
	var own = _own_selector(node, {})
	if own != null:
		return {"result": {"select": own}}
	# Under the nearest ancestor a selector of its own picks out, then by its place
	# among its like there where nothing else tells them apart (§PW277).
	var above := node.get_parent()
	while above != null and above != root:
		var anchor = _own_selector(above, {})
		if anchor != null:
			var scoped = _own_selector(node, {"under": anchor})
			if scoped != null:
				return {"result": {"select": scoped}}
			var select := {"under": anchor, "class": _class_of(node)}
			var like := _selected(select)
			select["nth"] = like.find(node)
			if select["nth"] >= 0 and _selected(select) == [node]:
				return {"result": {"select": select}}
		above = above.get_parent()
	return {"result": {"select": null}}


func _class_of(node: Node) -> String:
	var script: Script = node.get_script()
	if script != null and script.get_global_name() != "":
		return script.get_global_name()
	return node.get_class()


## A selector of class and properties, within `scope`, that finds this node alone.
func _own_selector(node: Node, scope: Dictionary):
	var select := scope.duplicate()
	select["class"] = _class_of(node)
	if _selected(select) == [node]:
		return select
	for key in SELECTING:
		if not (key in node):
			continue
		var value = _plain(node.get(key))
		if not (value is String) or value == "" or value.begins_with("@"):
			continue
		select[key] = value
		if _selected(select) == [node]:
			return select
	return null


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


## The names the project declares into its state, read through the state kit (§PW359).
func _state(asked: Dictionary) -> Dictionary:
	var kit := "res://addons/polyweave/state/state.gd"
	if not ResourceLoader.exists(kit):
		return _refused("driver.no-state",
			"this game declares no state: install the state kit and name it in res://polyweave_state.gd")
	return {"result": load(kit).read(asked.get("names", []))}


func _input(asked: Dictionary) -> Dictionary:
	var events := []
	var landed = null
	# A tap presses on one frame and releases on the next, so a game polling
	# is_action_just_pressed sees it pressed; `hold` sends only the press and `release`
	# only the release, for a game that polls is_action_pressed across frames (§PW216).
	var halves := [[true, 0], [false, 1]]
	if asked.get("hold", false):
		halves = [[true, 0]]
	elif asked.get("release", false):
		halves = [[false, 0]]
	if asked.has("action"):
		for half in halves:
			var event := InputEventAction.new()
			event.action = StringName(str(asked["action"]))
			event.pressed = half[0]
			event.strength = 1.0 if half[0] else 0.0
			events.append({"event": event, "via": "input", "after": half[1]})
	elif asked.has("key"):
		var code := OS.find_keycode_from_string(str(asked["key"]))
		if code == KEY_NONE:
			return _refused("driver.bad-command", "there is no key called %s" % asked["key"])
		for half in halves:
			var event := InputEventKey.new()
			event.keycode = code
			event.physical_keycode = code
			event.pressed = half[0]
			events.append({"event": event, "via": "input", "after": half[1]})
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
		events.append({"event": moved, "via": "viewport", "after": 0})
		for pressed in [true, false]:
			var event := InputEventMouseButton.new()
			event.button_index = MOUSE_BUTTON_LEFT
			event.pressed = pressed
			event.position = at
			event.global_position = at
			events.append({"event": event, "via": "viewport", "after": 0})
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
	return _same(_plain(nodes[0].get(str(asked["property"]))), asked.get("equals"))


## Whether a value is the one a flow expects: numbers as numbers wherever they sit.
## JSON gives every number as a float, and a node's int is still the same number, in a
## Dictionary or an Array too, which JSON text alone compared as 1 against 1.0 (§PW278).
func _same(value, wanted) -> bool:
	if typeof(value) in [TYPE_INT, TYPE_FLOAT] and typeof(wanted) in [TYPE_INT, TYPE_FLOAT]:
		return is_equal_approx(float(value), float(wanted))
	if value is Dictionary and wanted is Dictionary:
		if value.size() != wanted.size():
			return false
		for key in value:
			if not wanted.has(str(key)) or not _same(value[key], wanted[str(key)]):
				return false
		return true
	if value is Array and wanted is Array:
		if value.size() != wanted.size():
			return false
		for index in value.size():
			if not _same(value[index], wanted[index]):
				return false
		return true
	return JSON.stringify(value) == JSON.stringify(wanted)


## Whether a node's property holds a value now, no frame passing: what a kept query
## becomes in a flow (§PW214).
func _expect(asked: Dictionary) -> Dictionary:
	var nodes := _found(asked)
	if nodes.is_empty():
		return _refused("driver.no-node", "nothing answers %s" % _named(asked))
	var named := str(asked.get("property", ""))
	if not (named in nodes[0]):
		return _refused("driver.bad-command", "%s has no property %s" % [nodes[0].get_path(), named])
	var held := _met({"asked": asked, "fired": false})
	return {"result": {"held": held, "value": _plain(nodes[0].get(named))}}


## Set a property for setup, a nested one written as `rng:seed`: how a flow seeds a
## generator the game made itself, which --seed does not reach (§PW217).
func _set_property(asked: Dictionary) -> Dictionary:
	var nodes := _found(asked)
	if nodes.is_empty():
		return _refused("driver.no-node", "nothing answers %s" % _named(asked))
	var named := str(asked.get("property", ""))
	var head := named.get_slice(":", 0)
	if named == "" or not (head in nodes[0]):
		return _refused("driver.bad-command", "%s has no property %s" % [nodes[0].get_path(), head])
	var before = nodes[0].get_indexed(NodePath(named))
	var value = asked.get("value")
	# JSON gives every number as a float; an int property keeps being an int.
	if typeof(before) == TYPE_INT and typeof(value) == TYPE_FLOAT:
		value = int(value)
	nodes[0].set_indexed(NodePath(named), value)
	return {"result": {"was": _plain(before), "now": _plain(nodes[0].get_indexed(NodePath(named)))}}


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
	return {"result": {"out": out, "size": [image.get_width(), image.get_height()],
		"locale": TranslationServer.get_locale()}}


func _named(asked: Dictionary) -> String:
	for key in ["select", "path", "group", "class"]:
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
