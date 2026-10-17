extends SceneTree
## A test in Cottony's older style, adopted as it stands.

var ran := 0
var failed := 0


func _initialize() -> void:
	ran += 1
	if "abc".length() != 3:
		failed += 1
		print("  FAIL: a string's length")
	print("checks ran: %d, failed: %d" % [ran, failed])
	quit(1 if failed else 0)
