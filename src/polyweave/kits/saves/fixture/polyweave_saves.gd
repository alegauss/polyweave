extends RefCounted
## The saves fixture's own declaration: three slots, and a second version of its save in
## which "gold" was renamed "coins".

const VERSION := 2
const SLOTS := 3


static func migrations() -> Dictionary:
	return {1: func(data: Dictionary) -> Dictionary:
		if data.has("gold"):
			data["coins"] = data["gold"]
			data.erase("gold")
		return data}
