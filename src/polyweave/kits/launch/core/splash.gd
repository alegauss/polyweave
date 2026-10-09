class_name PolyweaveSplash
extends Control
## A splash sequence (polyweave kit "launch", §PW349): the project's logos, each for its
## seconds, while the first scene loads on a thread behind them. Any key, mouse button
## or pad button of any family skips the rest; then the first scene is put in place
## through PolyweaveScenes, which records the time from launch to it.

signal finished

const Scenes := preload("res://addons/polyweave/launch/scenes.gd")

## each logo's path, shown in turn; the logos are the project's
@export var logos: Array[String] = []
## how long each logo stays, in seconds; two where unset
@export var seconds: Array[float] = []
## the scene the splash leads to, loaded from the moment the splash starts
@export var next_scene := ""

var skipped := false
var _at := -1
var _left := 0.0
var _ended := false
var _shown: TextureRect


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_shown = TextureRect.new()
	_shown.set_anchors_preset(Control.PRESET_FULL_RECT)
	_shown.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	add_child(_shown)
	if next_scene != "":
		Scenes.shared().prefetch(next_scene)
	_next()


func _next() -> void:
	_at += 1
	if _at >= logos.size():
		_end()
		return
	_shown.texture = _texture(logos[_at])
	_left = seconds[_at] if _at < seconds.size() else 2.0


static func _texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		return load(path)
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(ProjectSettings.globalize_path(path))
	return ImageTexture.create_from_image(image) if image != null else null


func _process(delta: float) -> void:
	if _ended:
		return
	_left -= delta
	if _left <= 0.0:
		_next()


func _input(event: InputEvent) -> void:
	if _ended or not event.is_pressed() or event.is_echo():
		return
	if event is InputEventKey or event is InputEventMouseButton or event is InputEventJoypadButton:
		get_viewport().set_input_as_handled()
		skipped = true
		_end()


func _end() -> void:
	if _ended:
		return
	_ended = true
	finished.emit()
	if next_scene != "":
		Scenes.shared().go(next_scene)
