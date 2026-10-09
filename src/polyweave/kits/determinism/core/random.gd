class_name PolyweaveRandom
extends RefCounted
## One seed for a whole run (polyweave kit "determinism", §PW360). The project's code draws
## from named streams here instead of the global randf: `PolyweaveRandom.randf("enemies")`.
## Each stream is seeded from the run's seed and its own name, so a draw added in one
## never shifts another, and the global random functions are seeded from it too, so a
## call someone forgot still repeats while the calls come in the same order.
##
## The seed is the run's `--seed=N` (the driver's, so a driven session and a kept flow
## reach it), else SEED in res://polyweave_random.gd, else one drawn and printed as
## `polyweave_random: seed=N`, so a run that showed a bug says how to run it again.

const PROJECT := "res://polyweave_random.gd"

static var _seed := -1
static var _streams := {}


## the run's seed, chosen the first time anything asks
static func seed_of() -> int:
	if _seed == -1:
		reseed(_chosen())
	return _seed


## start every stream over from `value`, as a run beginning again would
static func reseed(value: int) -> void:
	_seed = value
	_streams.clear()
	seed(value)
	print("polyweave_random: seed=%d" % value)


static func _chosen() -> int:
	for arg in OS.get_cmdline_user_args() + OS.get_cmdline_args():
		if arg.begins_with("--seed=") or arg.begins_with("seed="):
			return int(arg.get_slice("=", 1))
	if ResourceLoader.exists(PROJECT):
		var declared: Dictionary = (load(PROJECT) as GDScript).get_script_constant_map()
		if declared.has("SEED"):
			return int(declared["SEED"])
	return int(Time.get_unix_time_from_system() * 1000.0) % 2147483647


## a stream of its own, seeded from the run's seed and the stream's name
static func stream(name := "default") -> RandomNumberGenerator:
	var key := name
	if not _streams.has(key):
		var made := RandomNumberGenerator.new()
		made.seed = hash([seed_of(), name])
		_streams[key] = made
	return _streams[key]


static func randf(name := "default") -> float:
	return stream(name).randf()


static func randf_range(from: float, to: float, name := "default") -> float:
	return stream(name).randf_range(from, to)


static func randi_range(from: int, to: int, name := "default") -> int:
	return stream(name).randi_range(from, to)


## one of `among`, drawn from the stream
static func pick(among: Array, name := "default") -> Variant:
	return among[stream(name).randi_range(0, among.size() - 1)] if not among.is_empty() else null
