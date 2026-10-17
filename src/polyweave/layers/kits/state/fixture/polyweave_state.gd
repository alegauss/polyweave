extends RefCounted
## The state fixture's names: the player's health and position, and the level's own
## account of itself.

const STATE := {
	"health": {"node": "Player", "property": "health", "type": "int"},
	"position": {"node": "Player", "property": "position", "type": "Vector2"},
	"level": {"node": "Level", "method": "snapshot", "type": "Dictionary"},
}
