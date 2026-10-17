extends RefCounted
## The dialogue fixture's one sequence: three lines, two speakers, one portrait.

const RATE := 60.0
const SEQUENCES := {
	"intro": [
		{"key": "INTRO_1", "speaker": "NAME_LUNA", "portrait": "res://art/luna.png"},
		{"key": "INTRO_2", "speaker": "NAME_OWL"},
		{"key": "INTRO_3"},
	],
}
