extends SceneTree
## One scene measured as engine.perf runs it (§PW365): the time to load and put it in
## place, every frame's wall-clock time with vsync off after a short settling, and the
## peaks of static memory and node count. Prints one line, `PERF load_ms=… p95_ms=…
## p99_ms=… memory_mb=… nodes=… frames=…`, percentiles and never a mean, so one hitch is
## not averaged away. Takes `scene=res://…` and `frames=N` after `--`.

const SETTLE := 10

var frames := 300
var times := PackedFloat64Array()
var last := 0
var seen := 0
var load_ms := 0.0
var nodes := 0


func _initialize() -> void:
	var scene := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("scene="):
			scene = arg.get_slice("=", 1)
		elif arg.begins_with("frames="):
			frames = int(arg.get_slice("=", 1))
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var started := Time.get_ticks_usec()
	var packed := load(scene) as PackedScene
	if packed == null:
		print("PERF failed: the scene %s does not load" % scene)
		quit(1)
		return
	var made := packed.instantiate()
	root.add_child(made)
	current_scene = made
	load_ms = (Time.get_ticks_usec() - started) / 1000.0


func _process(_delta: float) -> bool:
	var now := Time.get_ticks_usec()
	seen += 1
	if seen > SETTLE and last > 0:
		times.append((now - last) / 1000.0)
	last = now
	nodes = maxi(nodes, int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)))
	if times.size() < frames:
		return false
	var sorted := times.duplicate()
	sorted.sort()
	print("PERF load_ms=%.2f p95_ms=%.3f p99_ms=%.3f memory_mb=%.2f nodes=%d frames=%d" % [
		load_ms, _at(sorted, 0.95), _at(sorted, 0.99),
		Performance.get_monitor(Performance.MEMORY_STATIC_MAX) / 1048576.0, nodes, sorted.size()])
	return true


func _at(sorted: PackedFloat64Array, share: float) -> float:
	return sorted[mini(sorted.size() - 1, int(ceil(share * sorted.size())) - 1)]
