extends SceneTree
## The dialogue kit's proof, run in the game it lands in (§PW353), by pad events alone.
## A line types at the declared rate. Every line of every declared sequence is reached
## by the confirm of each family, a Switch pad's east button and every other pad's south
## one, while the other family's button moves nothing. The first press completes a line
## being typed, whole and still the same line, and the second shows the next. Each line
## shows its speaker and its portrait where it declares them. Every line fits its box in
## every locale the table carries, by the measure game.text_fit takes. Prints KIT PROVED,
## or KIT FAILED with why.

const Dialogue := preload("res://addons/polyweave/dialogue/dialogue.gd")
const Language := preload("res://addons/polyweave/language/language.gd")
const PRESS := {"xbox": [JOY_BUTTON_A, JOY_BUTTON_B], "switch": [JOY_BUTTON_B, JOY_BUTTON_A]}

var failed := []
var sequences := {}
var locales: Array[String] = []
var stage := "type"
var box: Dialogue
var since := 0
var fits := []
var frames := 0


func _initialize() -> void:
	Language.start(false)
	locales = Language.locales()
	sequences = Dialogue.declaration()["SEQUENCES"]
	if sequences.is_empty():
		failed.append("res://polyweave_dialogue.gd declares no SEQUENCES to walk")
		stage = "done"
		return
	if locales.is_empty():
		locales.assign([TranslationServer.get_locale()])
	TranslationServer.set_locale(locales[0])
	for name in sequences:
		for line in sequences[name]:
			for locale in locales:
				fits.append([locale, name, line])
	box = Dialogue.box(sequences.keys()[0])
	root.add_child(box)
	since = Time.get_ticks_msec()


func _pad(index: int) -> void:
	var event := InputEventJoypadButton.new()
	event.button_index = index as JoyButton
	event.pressed = true
	root.push_input(event)
	var released := event.duplicate() as InputEventJoypadButton
	released.pressed = false
	root.push_input(released)


func _process(_delta: float) -> bool:
	match stage:
		"type":
			_typed()
		"walk":
			for family in PRESS:
				for name in sequences:
					_walk(family, name)
			box = Dialogue.box(sequences.keys()[0])
			root.add_child(box)
			stage = "fit"
		"fit":
			_fit()
		"done":
			print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
			return true
	return false


## the first line, typed on its own at the declared rate
func _typed() -> void:
	var text := box.find_child("Text", true, false) as Label
	if text == null:
		failed.append("the box has no Label named Text")
		stage = "done"
		return
	var total := text.get_total_character_count()
	if box.typing():
		return
	var took := (Time.get_ticks_msec() - since) / 1000.0
	var expected := total / box.rate
	if total > 1 and (took < expected * 0.6 or took > expected * 1.5 + 0.1):
		failed.append("%d characters typed in %.2fs, not the %.2fs a rate of %.0f declares" % [
			total, took, expected, box.rate])
	box.queue_free()
	box = null
	stage = "walk"


## every line of a sequence by one family's confirm alone, the other family's ignored
func _walk(family: String, name: String) -> void:
	var walking := Dialogue.box(name)
	walking.family = family
	root.add_child(walking)
	var lines: Array = sequences[name]
	var seen := []
	var done := [false]
	walking.finished.connect(func() -> void: done[0] = true)
	var confirm: int = PRESS[family][0]
	var other: int = PRESS[family][1]
	for step in lines.size() * 2 + 2:
		if done[0]:
			break
		var key := walking.key()
		if seen.is_empty() or seen[-1] != key:
			seen.append(key)
			_shows(walking, lines[seen.size() - 1])
		var was_typing := walking.typing()
		_pad(other)
		if walking.key() != key or walking.typing() != was_typing:
			failed.append("%s's other button moved %s on" % [family, key])
			break
		_pad(confirm)
		if was_typing:
			var text := walking.find_child("Text", true, false) as Label
			if walking.key() != key:
				failed.append("a %s press while %s was typed moved on before it was whole" % [
					family, key])
				break
			if walking.typing() or text.visible_characters != -1:
				failed.append("a %s press while %s was typed left %d of %d characters" % [
					family, key, text.visible_characters, text.get_total_character_count()])
				break
	var keys := lines.map(func(l: Dictionary) -> String: return str(l["key"]))
	if seen != keys:
		failed.append("%s by %s's confirm reached %s of %s" % [name, family, seen, keys])
	if not done[0]:
		failed.append("%s by %s's confirm never finished" % [name, family])
	for line in walking.said:
		failed.append(line)
	walking.queue_free()


func _shows(walking: Dialogue, line: Dictionary) -> void:
	var speaker := walking.find_child("Speaker", true, false) as Label
	if line.has("speaker") and (speaker == null or not speaker.visible
			or speaker.text != str(line["speaker"])):
		failed.append("%s does not show its speaker %s" % [line["key"], line["speaker"]])
	var portrait := walking.find_child("Portrait", true, false) as TextureRect
	if line.has("portrait") and (portrait == null or not portrait.visible):
		failed.append("%s does not show its portrait %s" % [line["key"], line["portrait"]])
	if not line.has("portrait") and portrait != null and portrait.visible:
		failed.append("%s shows a portrait it does not declare" % line["key"])


## each line whole in each locale, two frames on so it is laid out, held to its box
func _fit() -> void:
	if fits.is_empty():
		stage = "done"
		return
	var locale: String = fits[0][0]
	var line: Dictionary = fits[0][2]
	if frames == 0:
		TranslationServer.set_locale(locale)
		box.play([line])
		box.press()
	frames += 1
	if frames < 3:
		return
	var text := box.find_child("Text", true, false) as Label
	for unfit in Language.unfit(text, text.tr(str(line["key"]))):
		failed.append("%s %s %s" % [locale, line["key"], unfit])
	fits.pop_front()
	frames = 0
