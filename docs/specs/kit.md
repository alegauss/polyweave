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
