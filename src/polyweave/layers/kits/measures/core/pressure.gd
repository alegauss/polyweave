extends RefCounted
## measure.pressure in the engine (§PW613): a wave timeline's threat per second, in its
## two bounding cases, and its gaps, for a tool that runs inside the game, a level
## editor or a balance overlay, and asks it each edit. The same inputs and the same
## answer as the Python measure the gate runs, which the kit's proof holds it to:
##
##     var said := _PwPressure.measure(events, 0.5, 3.0)
##     said["alive_slow"][12]   # the threat alive in second 12 if nothing is killed
##
## `events` are dictionaries {second, kind, weight, until}: weight 1 and until the
## spawn second where unsaid. Kinds and weights are the game's; nothing about waves or
## enemies is built in.


## The events with what each leaves unsaid filled in, as the Python measure reads them.
static func read(events: Array) -> Array:
	var found := []
	for one in events:
		var second := float(one["second"])
		found.append({"second": second, "kind": str(one.get("kind", "")),
			"weight": float(one.get("weight", 1.0)),
			"until": float(one.get("until", second))})
	return found


## Per second, the threat `entering`, `alive_fast` (every enemy killed as it lands,
## after `warp` seconds) and `alive_slow` (nothing killed until its wave ends), and the
## `gaps` a fast player finds the screen empty in, the `longest_gap` and those
## `past_window`.
static func measure(given: Array, warp := 0.0, window := 0.0) -> Dictionary:
	var events := read(given)
	var end := 0.0
	for e in events:
		end = maxf(end, maxf(e["until"], e["second"] + warp))
	var seconds := maxi(1, ceili(end))
	var entering := _zeros(seconds)
	var fast := _zeros(seconds)
	var slow := _zeros(seconds)
	var total := 0.0
	for e in events:
		total += e["weight"]
		entering[mini(int(e["second"]), seconds - 1)] += e["weight"]
		for pair in [[fast, e["second"] + warp], [slow, e["until"]]]:
			var curve: Array = pair[0]
			var stop: float = pair[1]
			for s in range(int(e["second"]), mini(seconds, ceili(stop))):
				# Weighted by how much of that second it is alive for.
				var share := minf(stop, s + 1.0) - maxf(e["second"], float(s))
				if share > 0.0:
					curve[s] += e["weight"] * share
	# The gaps: stretches no fast-case enemy is alive in, from the first spawn on.
	var spans := []
	for e in events:
		spans.append([e["second"], e["second"] + warp])
	spans.sort_custom(func(a, b): return a[0] < b[0] or (a[0] == b[0] and a[1] < b[1]))
	var gaps := []
	var reach: float = spans[0][0] if not spans.is_empty() else 0.0
	for span in spans:
		if span[0] > reach:
			gaps.append([snappedf(reach, 0.001), snappedf(span[0], 0.001)])
		reach = maxf(reach, span[1])
	var longest := 0.0
	var past := []
	for gap in gaps:
		longest = maxf(longest, gap[1] - gap[0])
		if window > 0.0 and gap[1] - gap[0] > window:
			past.append(gap)
	var peak := 0.0
	for value in slow:
		peak = maxf(peak, value)
	return {
		"seconds": seconds,
		"entering": _tidy(entering),
		"alive_fast": _tidy(fast),
		"alive_slow": _tidy(slow),
		"total": snappedf(total, 0.0001),
		"peak_slow": snappedf(peak, 0.0001),
		"longest_gap": snappedf(longest, 0.001),
		"gaps": gaps,
		"past_window": past,
	}


static func _zeros(count: int) -> Array:
	var out := []
	out.resize(count)
	out.fill(0.0)
	return out


static func _tidy(curve: Array) -> Array:
	var out := []
	for value in curve:
		out.append(snappedf(value, 0.0001))
	return out
