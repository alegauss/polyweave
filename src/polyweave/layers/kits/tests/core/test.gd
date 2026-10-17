extends SceneTree
## A game's test (polyweave kit "tests", §PW362): extend this, write `test_*` methods, and
## use `check` and `equal`; game.test runs it headless and reads what it prints. Every
## `test_*` method runs once, on the first frame, so what a test adds to the root is in
## the tree and gets its _ready. A failure prints `  FAIL: <what> (res://file:line)` with
## the line of the check, and the run ends on `checks ran: N, failed: M`, exiting non-zero
## when anything failed. That is Cottony's convention, so its older tests and these are
## read the same way.

var checks := 0
## each failure: {what, file, line}
var failures: Array[Dictionary] = []
var _ran := false


func _process(_delta: float) -> bool:
	if _ran:
		return true
	_ran = true
	for method in get_method_list():
		var name: String = method["name"]
		if name.begins_with("test_"):
			call(name)
	_finished()
	return true


## the end of the run; a subclass may say more before it quits
func _finished() -> void:
	print("checks ran: %d, failed: %d" % [checks, failures.size()])
	quit(1 if not failures.is_empty() else 0)


func check(ok: bool, what: String) -> bool:
	checks += 1
	if not ok:
		var at: Dictionary = get_stack()[1] if get_stack().size() > 1 else {}
		_fail(what, at)
	return ok


func equal(got: Variant, want: Variant, what: String) -> bool:
	checks += 1
	if got != want:
		var at: Dictionary = get_stack()[1] if get_stack().size() > 1 else {}
		_fail("%s -- got %s, wanted %s" % [what, got, want], at)
		return false
	return true


func _fail(what: String, at: Dictionary) -> void:
	var failure := {"what": what, "file": at.get("source", ""), "line": at.get("line", 0)}
	failures.append(failure)
	print("  FAIL: %s (%s:%d)" % [what, failure["file"], failure["line"]])
