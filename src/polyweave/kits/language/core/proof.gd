extends SceneTree
## The language kit's proof, run in the game it lands in (§PW352). The project's screens
## (SCREENS, or the main scene) are laid out in every locale the table carries, and in
## each: every visible Label and Button shows that locale's line for its key, and one
## whose text is no key, which would never change language, is named; no key shows its
## raw name; every character a line needs is drawn by the game's font or a declared
## fallback, which is what words.glyphs asks of the files, here on the chain the game
## draws with; and every line fits its control as laid out. Then the first launch picks
## each locale the table has, one of the same language, and the fallback for a language
## it lacks, and the options kit's language row reads back each locale it sets. Prints
## KIT PROVED, or KIT FAILED with why.

const Language := preload("res://addons/polyweave/language/language.gd")
const Options := preload("res://addons/polyweave/language/options.gd")
## what a layout draws without a glyph
const LAID_OUT := [" ", "\n", "\r", "\t", " "]

var failed := []
var screens := []
var locales: Array[String] = []
var at := 0
var frames := 0


func _initialize() -> void:
	Language.start(false)
	locales = Language.locales()
	for line in Language.said:
		if not line.contains("has no line for"):
			failed.append(line)
	if locales.is_empty():
		failed.append("the table carries no locale")
	var declared := Language.declaration()
	var paths: Array = declared["SCREENS"]
	if paths.is_empty():
		var main := str(ProjectSettings.get_setting("application/run/main_scene", ""))
		if main != "":
			paths = [main]
	for path in paths:
		var packed := load(path) as PackedScene
		if packed == null:
			failed.append("the screen %s does not load" % path)
			continue
		var screen := packed.instantiate()
		root.add_child(screen)
		screens.append(screen)


func _process(_delta: float) -> bool:
	if at >= locales.size():
		_first_launch()
		_row()
		print("KIT PROVED" if failed.is_empty() else "KIT FAILED: " + "; ".join(failed))
		return true
	if frames == 0:
		TranslationServer.set_locale(locales[at])
	frames += 1
	# two frames on, so every label has been relaid out in the new language
	if frames < 3:
		return false
	_held(locales[at])
	at += 1
	frames = 0
	return false


func _held(locale: String) -> void:
	var rows := Language.rows()
	for key in rows:
		var line := str(rows[key][locale])
		if TranslationServer.translate(key) == key and line != key:
			failed.append("%s shows the raw key %s" % [locale, key])
		for character in line + line.to_upper():
			if not LAID_OUT.has(character) and not Language.drawn(character.unicode_at(0)):
				failed.append("%s %s needs %s (U+%04X), which no declared font draws" % [
					locale, key, character, character.unicode_at(0)])
				break
	var texts := []
	for screen in screens:
		_texts(screen, texts)
	for node: Control in texts:
		var key := str(node.text)
		if not rows.has(key):
			failed.append("%s shows %s, which is no key of the table, so it never changes language" % [
				node.get_path(), key])
			continue
		var shown := node.tr(key) if node.auto_translate_mode != Node.AUTO_TRANSLATE_MODE_DISABLED else key
		if shown != str(rows[key][locale]):
			failed.append("%s %s shows %s, not its line" % [locale, node.get_path(), shown])
		for unfit in _unfit(node, shown):
			failed.append("%s %s %s" % [locale, key, unfit])


func _texts(node: Node, out: Array) -> void:
	if (node is Label or node is Button) and (node as CanvasItem).is_visible_in_tree() \
			and str(node.text) != "":
		out.append(node)
	for child in node.get_children():
		_texts(child, out)


## what keeps a line from fitting its control, as it is laid out: the measure
## game.text_fit takes of a running game (§PW336)
func _unfit(node: Control, shown: String) -> Array:
	var out := []
	var font: Font = node.get_theme_font("font")
	var size: int = node.get_theme_font_size("font_size")
	var widest := 0.0
	for line in shown.split("\n"):
		widest = maxf(widest, font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x)
	var wraps := node is Label and (node as Label).autowrap_mode != TextServer.AUTOWRAP_OFF
	if not wraps and widest > node.size.x + 0.5:
		out.append("is %d px wide in a %d px box" % [widest, node.size.x])
	if node is Label and (node as Label).get_line_count() > (node as Label).get_visible_line_count():
		out.append("shows %d of its %d lines" % [(node as Label).get_visible_line_count(),
			(node as Label).get_line_count()])
	var parent := node.get_parent()
	if parent is Control and not parent is ScrollContainer:
		var outer := (parent as Control).get_global_rect()
		if outer.size.x > 0 and not outer.grow(0.5).encloses(node.get_global_rect()):
			out.append("leaves its container %s" % parent.get_path())
	return out


func _first_launch() -> void:
	var declared := Language.declaration()
	if not bool(declared["FOLLOW_SYSTEM"]):
		return
	for locale in locales:
		if Language.chosen(locale) != locale:
			failed.append("a first launch on %s chose %s" % [locale, Language.chosen(locale)])
		var kin := locale.split("_")[0] + "_ZZ"
		if Language.chosen(kin).split("_")[0] != locale.split("_")[0]:
			failed.append("a first launch on %s chose %s, not a locale of its language" % [
				kin, Language.chosen(kin)])
	if Language.chosen("zz_ZZ") != str(declared["FALLBACK"]):
		failed.append("a first launch on a language the table lacks chose %s, not %s" % [
			Language.chosen("zz_ZZ"), declared["FALLBACK"]])


func _row() -> void:
	var row: Dictionary = Options.options()[0]
	if Array(row["choices"]) != Array(locales):
		failed.append("the language row offers %s, not %s" % [row["choices"], locales])
	for locale in locales:
		row["apply"].call(locale)
		if str(row["read"].call()) != locale:
			failed.append("the language row set %s and read back %s" % [locale, row["read"].call()])
