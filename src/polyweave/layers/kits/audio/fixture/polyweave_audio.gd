extends RefCounted
## The audio fixture's declaration: the kit's five buses and an ambience bus mixed
## through the effects bus, a shorter crossfade than the kit's, and the two UI sounds.

const BUSES := [
	{"name": "Master"},
	{"name": "Music", "send": "Master", "loudness": -18.0},
	{"name": "SFX", "send": "Master", "loudness": -16.0},
	{"name": "UI", "send": "Master", "loudness": -20.0},
	{"name": "Voice", "send": "Master", "loudness": -16.0},
	{"name": "Ambience", "send": "SFX", "loudness": -22.0},
]
const CROSSFADE := 0.8
const DUCK_DB := -9.0
const UI_SOUNDS := {"focus": "res://sounds/focus.wav", "confirm": "res://sounds/confirm.wav"}
