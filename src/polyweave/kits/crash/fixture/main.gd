extends Node
## Opens the crash kit's log first thing, as a game does, and then runs.

const Log := preload("res://addons/polyweave/crash/log.gd")


func _ready() -> void:
	Log.shared().info("the fixture starts")
