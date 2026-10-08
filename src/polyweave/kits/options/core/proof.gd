extends SceneTree
## The options kit's proof, run in the game it lands in (§PW347): every row changes what
## it says it changes, read back in the running game; every value survives a restart; a
## file an older build wrote is migrated, a key no row declares is kept and a value a
## row may not take is said, never a crash and never a silent reset; each installed
## kit's tab is on the screen; and a pad walks every row, changes tab and goes back.
## Prints KIT PROVED, or KIT FAILED with why.

const Settings := preload("res://addons/polyweave/options/settings.gd")
const Screen := preload("res://addons/polyweave/options/options_screen.gd")
const KEPT := "user://polyweave_settings_proof.cfg"

var failed := []
var settings: Settings
var screen: Screen
var closed := 0
var frame := 0


func _initialize() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
	settings = Settings.new(KEPT)
	if settings.options.is_empty():
		failed.append("no kit and no polyweave_options.gd declares a row")
	for problem in settings.unchanging():
		failed.append(problem)
	_older_file()
	_restart()
	_tabs()
	_a_row_that_changes_nothing_is_named()
	screen = Screen.new()
	screen.settings = settings
	screen.family = "switch"
	screen.closed.connect(func() -> void: closed += 1)
	root.add_child(screen)


## a file an older build wrote, with a renamed key, one no row declares and a bad value
func _older_file() -> void:
	var rows := settings.options.filter(func(r: Dictionary) -> bool: return Settings.holds_value(r))
	if rows.is_empty():
		return
	var old := ConfigFile.new()
	old.set_value("meta", "version", 0)
	old.set_value("legacy", "thing", 7)
	var renamed := {}
	for was in settings.renamed:
		renamed[settings.renamed[was]] = was
	var row: Dictionary = rows[0]
	var at := "%s/%s" % [row["tab"], row["key"]]
	var chosen: Variant = settings._other(row)
	var written: String = renamed.get(at, at)
	old.set_value(written.split("/")[0], written.split("/")[1], chosen)
	var refused: Dictionary = rows[-1]
	old.set_value(refused["tab"], refused["key"], {"not": "a value"})
	old.save(KEPT)
	settings.load_file()
	if settings.get_value(row["tab"], row["key"]) != chosen:
		failed.append("%s was not taken from the older file as %s" % [at, chosen])
	elif row.has("read") and str(row["read"].call()) != str(chosen):
		failed.append("%s was loaded but not put in force" % at)
	var said := "; ".join(settings.said)
	for expected in ["migrated from version 0", "legacy/thing is no option", "may not take"]:
		if not said.contains(expected):
			failed.append("loading the older file did not say %s: %s" % [expected, said])
	var after := ConfigFile.new()
	after.load(KEPT)
	if after.get_value("legacy", "thing", null) != 7:
		failed.append("a key no row declares was dropped from the file")
	if int(after.get_value("meta", "version", 0)) != settings.version:
		failed.append("the migrated file was not written at version %d" % settings.version)


func _restart() -> void:
	var values := {}
	for row in settings.options:
		if Settings.holds_value(row):
			var other: Variant = settings._other(row)
			settings.set_value(row["tab"], row["key"], other)
			values["%s/%s" % [row["tab"], row["key"]]] = other
	var again := Settings.new(KEPT)
	again.load_file()
	for at in values:
		var parts: PackedStringArray = at.split("/")
		if again.get_value(parts[0], parts[1]) != values[at]:
			failed.append("%s did not survive a restart" % at)
		var row := again.option(parts[0], parts[1])
		if row.has("read") and str(row["read"].call()) != str(values[at]):
			failed.append("%s came back but was not put in force" % at)


func _tabs() -> void:
	var kits := DirAccess.open(Settings.KITS)
	for kit in kits.get_directories():
		var script := "%s/%s/options.gd" % [Settings.KITS, kit]
		if ResourceLoader.exists(script):
			var tab: String = load(script).TAB
			if not settings.tabs().has(tab):
				failed.append("the %s kit's tab %s is not on the screen" % [kit, tab])


func _a_row_that_changes_nothing_is_named() -> void:
	var idle := Settings.new("user://polyweave_settings_idle.cfg", [{
		"tab": "t", "key": "idle", "default": false,
		"apply": func(_v: bool) -> void: pass,
		"read": func() -> bool: return false,
	}])
	if not "; ".join(idle.unchanging()).contains("t/idle changes nothing"):
		failed.append("a row that changes nothing was not named")
	DirAccess.remove_absolute(ProjectSettings.globalize_path("user://polyweave_settings_idle.cfg"))


func _pad(index: int) -> void:
	var event := InputEventJoypadButton.new()
	event.button_index = index as JoyButton
	event.pressed = true
	root.push_input(event)
	var released := event.duplicate() as InputEventJoypadButton
	released.pressed = false
	root.push_input(released)


func _focused() -> Control:
	return root.gui_get_focus_owner()


## every row of the tab shown reached walking down, and back round to the first
func _walk() -> void:
	var all := screen.controls(screen.tabs.get_current_tab_control())
	var start := _focused()
	var seen := [start]
	for i in all.size():
		_pad(JOY_BUTTON_DPAD_DOWN)
		seen.append(_focused())
	var named: String = screen.tabs.get_current_tab_control().name
	for one in all:
		if not seen.has(one):
			failed.append("walking %s by pad never reached %s" % [named, one.get_parent().name])
	if _focused() != start:
		failed.append("walking %s by pad did not come back round" % named)


func _process(_delta: float) -> bool:
	frame += 1
	var count := screen.tabs.get_tab_count()
	if frame <= count * 2 and frame % 2 == 0:
		if _focused() == null or not screen.is_ancestor_of(_focused()):
			failed.append("tab %d showed with nothing focused" % screen.tabs.current_tab)
		else:
			_walk()
		_pad(JOY_BUTTON_RIGHT_SHOULDER)
		return false
	if frame == count * 2 + 2:
		if screen.tabs.current_tab != 0:
			failed.append("the shoulders did not come round to the first tab")
		var choice := _choice()
		if choice != null:
			choice[1].grab_focus()
			var before: Variant = settings.get_value(choice[0]["tab"], choice[0]["key"])
			_pad(JOY_BUTTON_B)
			if settings.get_value(choice[0]["tab"], choice[0]["key"]) == before:
				failed.append("a Switch pad's east button did not change %s" % choice[0]["key"])
		_pad(JOY_BUTTON_A)
		if closed != 1:
			failed.append("a Switch pad's south button did not close the screen")
		DirAccess.remove_absolute(ProjectSettings.globalize_path(KEPT))
		if failed.is_empty():
			print("KIT PROVED")
		else:
			print("KIT FAILED: " + "; ".join(failed))
		return true
	return false


## the first row of choices and its control, its tab shown, or null
func _choice() -> Variant:
	for row in settings.options:
		if row.has("choices"):
			var rows := screen.tabs.get_node(NodePath(row["tab"]))
			screen.tabs.current_tab = rows.get_index()
			return [row, rows.get_node("%s/value" % row["key"])]
	return null
