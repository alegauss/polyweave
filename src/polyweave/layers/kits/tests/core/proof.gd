extends "res://addons/polyweave/tests/test.gd"
## The tests kit's proof, run in the game it lands in (§PW362): a test written on the
## kit's base runs every test_ method, counts each check, and names a failure with the
## line of the check that failed, which is what game.test reads. One check here fails on
## purpose. Prints KIT PROVED, or KIT FAILED with why.

var expected_line := 0


func test_a_sum() -> void:
	equal(2 + 2, 4, "two and two")


func test_a_deliberate_failure() -> void:
	expected_line = get_stack()[0]["line"] + 1
	check(false, "the proof's deliberate failure")


func _finished() -> void:
	var said := []
	if checks != 2:
		said.append("%d checks counted of the 2 run" % checks)
	if failures.size() != 1:
		said.append("%d failures counted of the 1 made" % failures.size())
	elif failures[0]["line"] != expected_line or not str(failures[0]["file"]).ends_with("proof.gd"):
		said.append("the failure was placed at %s:%s, not proof.gd:%d" % [
			failures[0]["file"], failures[0]["line"], expected_line])
	print("KIT PROVED" if said.is_empty() else "KIT FAILED: " + "; ".join(said))
	quit()
