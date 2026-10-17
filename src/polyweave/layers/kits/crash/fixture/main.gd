extends Node
## Opens the crash kit's log first thing, as a game does, and then runs.

const _PwLog := preload("res://addons/polyweave/crash/log.gd")


func _ready() -> void:
	_PwLog.shared().info("the fixture starts")
