# Kits

A **kit** is a part every game repeats (rebindable controls, a settings screen, a save
file, a pause menu) made once in the plugin, proved, and installed into a game (§PW340).
Starship's bindings and Cottony's settings each solved the same screen alone. What cost
them was not the typing but the details only a run reveals: an orphaned focus neighbour,
the Switch's swapped face buttons, a filter that leaves a resource out of the export. A
kit is that part with the proof that it holds, so the next game starts from what the
last one learned.

## Where a kit lives

A kit is a folder `kits/<name>/` inside the plugin, at `src/polyweave/kits/<name>/`, so
it ships in the wheel as the Godot addons under `src/polyweave/godot/` do. A kit only in
the repository's root would never reach a project installed from the package, which is
the one place a kit is for. `<name>` is lower case, letters, digits and underscores, and
is the kit's name everywhere: its folder, its `name` in `kit.toml`, its table in a
project's config and its folder in the game.

## The kit.toml

```toml
name = "input"
version = "0.1.0"
summary = "rebindable controls, read from the project's InputMap"
requires = []                 # kits installed before this one, by name

[installs]
core = "core"                 # copied to res://addons/polyweave/<name>/, never edited
scene = "scene/controls.tscn" # copied once into the project, the project's from then on

[declares]                    # the [kit.<name>] table it proposes in polyweave.toml
layouts = ["xbox", "playstation", "switch", "generic", "keyboard"]

[proves]
spec = "proof.accept.toml"    # its acceptance spec, run in the game it lands in
fixture = "fixture"           # a minimal Godot project it is proved in, in this repo
```

- `name`, `version` (major.minor.patch) and a one-line `summary` are required.
- `requires` lists the kits it needs. Each must be a kit the plugin carries, and kits
  never require each other in a loop, since a kit is installed after what it needs.
- `[installs] core` is a folder of the kit copied into the game at
  `res://addons/polyweave/<name>/`. It is the plugin's, replaced whole on an upgrade and
  never edited in the game. `scene` is optional: a scene copied once into the project,
  which the project owns from then on and changes as it likes.
- `[declares]` is the declaration the kit proposes, written into the project's
  `[kit.<name>]` only where the project has none. A kit carries no palette or theme of
  its own: anything that is a game's look is the game's to declare.
- `[proves] spec` is the kit's acceptance spec, the proof that it works in the game it
  lands in. A kit with no proof is refused: it is worth more than a snippet only while
  its proof holds.
- `[proves] fixture` is a folder of the kit holding a minimal Godot project shaped to
  exercise it, where polyweave proves it before any project receives it. A kit with no
  fixture is refused too.

Any other key, a name that is not the folder's, a version in another form, a file the
kit names and does not hold, a kit it requires that does not exist, and a loop of
requirements are each `kits.bad`, with the kit and the key named. `kit.list` reads every
kit the plugin carries through these checks and answers each one's name, version,
summary and requirements, so a broken kit is found here and not in a game.

## The contract every kit keeps

Five steps, the same for every kit:

1. **read the project**: its renderer and main scene, its InputMap, its export presets,
   and which kits it already has;
2. **propose the declaration**: `[declares]`, written where the project has none;
3. **install**: what it requires first, then its core and its scene;
4. **prove**: its acceptance spec, run in the real game;
5. **answer ready to decide**: ok, or the first finding with its remedy, the points of
   the scene meant to be changed, and any question that is a person's.

An agent's whole share is one call and one reading of the answer. A question a kit
leaves is a person's decision (a verdict, a budget), never an analysis for the agent. A
kit assumes no genre. Installing (§PW341) and proving every kit in polyweave's own gate
(§PW342) are the operations this format is read by.

## Installing one, in one call

`kit.install <name>` lands a kit in the Godot project at `root` (§PW341):

1. it reads the game: `project.godot`'s main scene and renderer, the InputMap's actions,
   whether `export_presets.cfg` exists, and the kits already in, each by the version its
   `addons/polyweave/<name>/kit.json` records; a folder with no `project.godot` is
   `kits.no-game`, and a name `kit.list` does not answer is `kits.unknown`;
2. it installs what the kit requires first, in order, then the kit;
3. for each, it writes the `[declares]` table into `polyweave.toml` as `[kit.<name>]`
   only where the project has none, so a project's own declaration is never replaced;
4. it copies the core to `addons/polyweave/<name>/`, replaced whole so an upgrade
   leaves no stale file, and the scene to `kits/<name>/` only where the project has
   none, since the scene is the project's once it lands;
5. it records the kit: `addons/polyweave/<name>/kit.json` holds its name and version,
   with a `borrow` record whose input is the kit's `kit.toml`, so `provenance.read`
   answers what the project carries and from where; the answer's `installed` gives each
   kit's version and the one that `was` there;
6. it copies the kit's proof to `<[paths] specs>/kits/<name>/proof.accept.toml` and runs
   it through `accept.verify` in the game.

The answer is ready to decide: `ok`, `proved` with the first finding where the proof
fails, `declared` (what it proposed), `scenes` and `change` (what is the project's to
change from now on), and `questions`, a person's, never a file for the agent to read.
`write=false` answers the same and writes nothing. An installed kit's proof sits among
the project's specs, so the project's own gate holds it from then on.

## Every kit proved in polyweave's own gate

A proof that runs only after install finds a broken kit in the consumer's tree (§PW342).
`kit.prove` (one kit, or every kit the plugin carries) copies each kit's fixture fresh,
installs the kit into it with what it requires, as `kit.install` does, and runs its
proof there, answering each kit `held`, `failed` with the first finding, or `skipped`
where its proof has a `screen` that needs a running game and no `$GODOT` is set. The
fixture is copied, never written into. `tools/gate.py` runs it after the tests and says
`kits: N held, M failed, K skipped for want of an engine`, naming each that failed, and
a kit that fails turns the gate red, so a Godot upgrade in polyweave re-proves every
kit at once and a kit cannot leave this repository broken. The fixture is also where a
kit's requirements are exercised together, so a kit that only works alone is found here.
