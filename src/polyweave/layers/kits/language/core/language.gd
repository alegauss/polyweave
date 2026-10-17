class_name PolyweaveLanguage
extends RefCounted
## The string table on screen in every language (polyweave kit "language", §PW352).
## Block Q holds the table to the world; this is the step from the table to the screen.
##
## The table is Godot's translation CSV, the one `[words] table` names: one key a row,
## one column a locale, a column starting with an underscore skipped. Where the editor
## imported it, Godot has its translations; where nothing has, `start()` reads the CSV
## itself. Either way a cell left empty carries the FALLBACK locale's line, so a key's
## raw name never reaches the screen, and `said` names each cell that did.
##
## FONTS lists the fonts that draw another script, each {"script": an ISO 15924 tag such
## as "Jpan", "Cyrl" or "Arab", "path": the font}: each is added to the fallbacks of the
## font the game draws with (the project theme's default font, or Godot's own), so a
## character the main font lacks is drawn by the declared font and not by a system one.
##
## On first launch the locale is the system's where the table has it, else one of the
## same language, else FALLBACK. The options kit's language row keeps the player's
## choice from then on. The project's res://polyweave_language.gd may declare TABLE,
## FALLBACK, FONTS, FOLLOW_SYSTEM and SCREENS (the scenes the proof lays out).

const PROJECT := "res://polyweave_language.gd"
const DEFAULTS := {
	"TABLE": "res://i18n/strings.csv",
	"FALLBACK": "en",
	"FONTS": [],
	"FOLLOW_SYSTEM": true,
	"SCREENS": [],
}

## what loading the table or a font had to say: a cell filled, a font missing
static var said: Array[String] = []
static var _rows := {}
static var _locales: Array[String] = []
static var _started := false


## what the project declares, each name it leaves out at the kit's default
static func declaration(project := PROJECT) -> Dictionary:
	var out := DEFAULTS.duplicate(true)
	if ResourceLoader.exists(project):
		var map := (load(project) as GDScript).get_script_constant_map()
		for key in map:
			out[key] = map[key]
	return out


## load the table and the fonts, once; with `choose`, set the first launch's locale
static func start(choose := true) -> void:
	if not _started:
		_started = true
		var declared := declaration()
		_read(str(declared["TABLE"]), str(declared["FALLBACK"]))
		_fonts(declared["FONTS"])
	if choose:
		TranslationServer.set_locale(chosen())


## the locales the table carries, in its column order
static func locales() -> Array[String]:
	start(false)
	return _locales


## every key of the table and each locale's line, empty cells already filled
static func rows() -> Dictionary:
	start(false)
	return _rows


## the locale a first launch shows: the system's, one of its language, or the fallback
static func chosen(system := "") -> String:
	var declared := declaration()
	var fallback := str(declared["FALLBACK"])
	if not bool(declared["FOLLOW_SYSTEM"]):
		return fallback
	var asked := system if system != "" else OS.get_locale()
	var held := locales()
	if held.has(asked):
		return asked
	var language := asked.split("_")[0]
	for one in held:
		if one.split("_")[0] == language:
			return one
	return fallback


## the font every Label and Button draws with where it sets none of its own
static func drawing_font() -> Font:
	var theme := ThemeDB.get_project_theme()
	if theme != null and theme.default_font != null:
		return theme.default_font
	return ThemeDB.fallback_font


## whether the font the game draws with, or one of its fallbacks, has a character
static func drawn(character: int) -> bool:
	var font := drawing_font()
	if font.has_char(character):
		return true
	for each in font.fallbacks:
		if each != null and each.has_char(character):
			return true
	return false


## what keeps a line from fitting its control as it is laid out, each said: the
## measure game.text_fit takes of a running game (§PW336), for any kit's proof
static func unfit(node: Control, shown: String) -> Array:
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


static func _read(path: String, fallback: String) -> void:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		said.append("there is no table at %s" % path)
		return
	var header := file.get_csv_line()
	var columns := {}
	for i in range(1, header.size()):
		if not header[i].begins_with("_") and header[i].strip_edges() != "":
			columns[i] = header[i].strip_edges()
			_locales.append(header[i].strip_edges())
	while not file.eof_reached():
		var line := file.get_csv_line()
		if line.size() < 2 or line[0].strip_edges() == "":
			continue
		var cells := {}
		for i in columns:
			cells[columns[i]] = line[i] if i < line.size() else ""
		_rows[line[0]] = cells
	var imported := TranslationServer.get_loaded_locales()
	for locale in _locales:
		var translation := Translation.new()
		translation.locale = locale
		for key in _rows:
			var cells: Dictionary = _rows[key]
			if str(cells[locale]) == "" and str(cells.get(fallback, "")) != "":
				cells[locale] = cells[fallback]
				said.append("%s has no line for %s, and shows %s's" % [locale, key, fallback])
			translation.add_message(key, cells[locale])
		if not imported.has(locale):
			TranslationServer.add_translation(translation)


static func _fonts(fonts: Array) -> void:
	var drawing := drawing_font()
	var chain: Array[Font] = []
	chain.assign(drawing.fallbacks)
	for each in fonts:
		var path := str(each.get("path", ""))
		var font := FontFile.new()
		if (load(path) if ResourceLoader.exists(path) else null) is FontFile:
			font = load(path)
		elif not FileAccess.file_exists(path) or font.load_dynamic_font(path) != OK:
			said.append("the %s font is %s, which is not a font there" % [each.get("script", ""), path])
			continue
		if each.has("script"):
			font.set_script_support_override(str(each["script"]), true)
		chain.append(font)
	drawing.fallbacks = chain
