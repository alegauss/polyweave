class_name PromptIcon
extends TextureRect
## An action's prompt, drawn for the device in the player's hands and redrawn the moment
## they pick up another (polyweave kit "prompts", §PW344).

const Prompts := preload("res://addons/polyweave/prompts/prompts.gd")

@export var action: StringName


func _ready() -> void:
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	Prompts.shared().family_changed.connect(_redraw)
	_redraw()


func _redraw(_family := "") -> void:
	texture = Prompts.shared().icon(action)
