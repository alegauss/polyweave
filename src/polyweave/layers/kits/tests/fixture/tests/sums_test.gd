extends "res://addons/polyweave/tests/test.gd"
## A test on the kit's base.


func test_adding() -> void:
	equal(2 + 3, 5, "two and three")
	check([1, 2].has(2), "a list holds what was put in it")
