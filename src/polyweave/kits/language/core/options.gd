extends RefCounted
## The language row the language kit contributes to the options kit's screen (§PW352):
## one choice per locale the table carries, each by the name Godot gives it, and the
## first launch's choice as its default, so a player who never opens the screen still
## sees their system's language.

const TAB := "general"
const Language := preload("res://addons/polyweave/language/language.gd")


static func options() -> Array[Dictionary]:
	var locales := Language.locales()
	return [{
		"tab": TAB, "key": "language", "label": "language", "default": Language.chosen(),
		"choices": locales,
		"names": locales.map(func(l: String) -> String: return TranslationServer.get_locale_name(l)),
		"apply": func(v: String) -> void: TranslationServer.set_locale(v),
		"read": func() -> String: return TranslationServer.get_locale(),
	}]
