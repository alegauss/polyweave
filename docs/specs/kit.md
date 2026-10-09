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
- `tab` names the tab the kit contributes to the options kit's screen (§PW347). A kit
  that declares one keeps `options.gd` in its core, a script with `const TAB` and
  `static func options()` answering its rows, and a kit that keeps one declares its
  tab; either alone is `kits.bad`.
- `[proves] spec` is the kit's acceptance spec, the proof that its pictures hold in the
  game it lands in.
- `[proves] fixture` is a folder of the kit holding a minimal Godot project shaped to
  exercise it, where polyweave proves it before any project receives it. A kit with no
  fixture is refused.
- `[proves] script` is a GDScript inside the core, run headless in the game after the
  spec holds, for what only a running game can say (every bound action has an icon in
  every family, say). It prints `KIT PROVED`, or `KIT FAILED: <why>`, and the answer
  carries that line; with no `$GODOT` it is `skipped` and said (§PW344). What a running
  game mixes is heard only while it runs, so a script may write what it heard beside the
  game and print `KIT SOUND <path> <measure> <min> <max>`, the path under the game: the
  answer holds that file to its bounds with `sound.measure`, the measure a track is held
  to, lists it under the script's `sounds`, and a sound outside them fails the script by
  its path and value (§PW351).
- A kit proves with a spec, a script or both, and one with neither is refused: it is
  worth more than a snippet only while its proof holds. A kit with no picture to hold,
  such as a menu, proves by its script alone, and `kit.prove` then answers it `skipped`
  where no engine is set, never `held` on nothing (§PW346).

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
6. it copies the kit's spec, where it has one, to
   `<[paths] specs>/kits/<name>/proof.accept.toml` and runs it through `accept.verify`
   in the game, then the kit's script.

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

## A kit that has fallen behind

`kit.install` records in `kit.json` the SHA-256 of every core file it laid down, and a
kit may say what each version changed under `[changes]`, `"0.2.0" = "the sentence"`
(§PW343). `provenance.outdated` answers `kits`: every kit a project carries that the
plugin now has in a newer version, with the version installed, the one carried and the
changes between them, so a fix reaches every game that carries the kit rather than the
next one only.

`kit.update <name>` brings one up. The core is the plugin's and the project never edits
it, so a core file whose hash differs from the one recorded is a finding, `edited`
naming the files, and nothing is overwritten. The scene is the project's and is left
alone; `scene.differs` is a unified diff from the project's copy to the new version's,
for the agent to carry over. The core is replaced and the proof run again, and an
upgrade whose proof fails is put back, the old core restored, so an upgrade lands proved
or not at all. `write=false` answers the same and writes nothing. A fix a project makes
that belongs in the kit is filed against polyweave and ships as a new version here.

## The kits it carries

**prompts** (§PW344): button prompts for the pad in the player's hands. A service,
`PolyweavePrompts.shared()`, knows the family in use (`xbox`, `playstation`, `switch`,
`keyboard`) from `Input.get_joy_name` and the last event, switches the moment the player
picks up another device (`family_changed`), and answers an action's binding as an icon:
`icon(action)`, a `PromptIcon` node for menus, and `bbcode(text)` turning
`[action=jump]` into the icon for a RichTextLabel. A pad's icons are named by where the
button sits (`south`, `east`, `lt`, `dpad_up`), so a Switch pad's south button reads B
where an Xbox pad's reads A. The four sets are drawn by `icons.build` from declarations
the kit keeps beside them, each held to its legibility bounds, and are the kit's own;
`icons_root` points the service at another set, such as a platform holder's glyphs,
which polyweave never carries. Its proof script holds every bound action to an icon in
every family it is bound for, a pad's name to its family, and a key after a pad to the
keyboard's icons. The kit reads a game's `project.godot` as Godot writes it, a value
over several lines included.

**remap** (§PW345, requires prompts): rebinding the controls, extracted from Starship's
bindings. `PolyweaveBindings` stores a binding as codes a settings file holds
(`key:<physical keycode>`, `mouse:<n>`, `button:<n>`, `axis:<n>:<-1 or 1>`); keys and
pad are two halves replaced apart, so a key leaves the pad's binding alone; a code
another action holds on that half is swapped, never shared; a reset goes back to the
bindings `project.godot` declares; and the stick's deadzone and inverted vertical are
kept beside them in `user://polyweave_bindings.cfg`. The actions are the game's own,
every project action but the `ui_` ones unless the screen names them. Its scene, a
remap screen, draws each binding as the prompts kit's icon for the device in use,
listens on the half pressed for the next input, says a swap, and holds a deadzone
slider, the inverted vertical and a reset. Its proof script rebinds, swaps, restarts
the store from the file, resets, and drives the screen with a pad button. Since 0.2.0
it contributes the `controls` tab to the options screen, a row opening its screen.

**menus** (§PW346, requires prompts): a main menu, a pause menu and a yes-or-no confirm
a pad can drive. `PolyweaveMenu` makes a button per item, named by the item and
labelled `tr(item)`, links focus top to bottom and round again, and follows the family
in hand for confirm and back: a Switch pad confirms on its east button and goes back on
its south one, every other pad the other way round, and Escape goes back. Back chooses
the item the menu declares (`back_to`). `PolyweavePause` stops the game through the
scene tree's pause while its own layer processes always, opens and closes on the game's
`pause` action, and resumes on back; `PolyweaveConfirm` focuses "no" first and answers
no on back. The main menu is the project's scene; the look is the project's Theme, as
panel.build declares it, and the kit adds no style. Its proof is a script alone, by pad
events: every menu walked down reaches each button and comes back round, back lands
where each menu says in every family's convention, and the game does not tick while
paused.

**options** (§PW347, requires menus): one settings file and the screen over it, from
Starship's SettingsStore and Cottony's settings. `PolyweaveSettings` keeps every option
in `user://polyweave_settings.cfg` under `[meta] version`. A row is
`{tab, key, label, default}` with `choices` (and `names`), `range` `[min, max, step]`,
`opens` (a scene, holding no value) or a bool default, and every row holding a value
declares `apply`, which puts it in force, and `read`, which reads back what is in
force. Rows come from each installed kit's `options.gd`, then from the project's
`res://polyweave_options.gd`, which may declare `const VERSION` and
`static func renamed()` mapping an older build's "tab/key" to today's. Loading an older
file migrates it, keeps a key no row declares, and lets a value a row may not take read
as its default while the file keeps it; `said` names each, so nothing a player chose is
dropped in silence. `unchanging()` sets each row to another value and names every row
whose `read` does not answer it, every row with no `read`, and every `opens` whose
scene is missing; a game's own tests may call it too. `PolyweaveOptionsScreen` draws a
tab per tab, a slider, switch, choice or button per row; the d-pad walks the rows and
round again, left and right move a value, the shoulders change tab, and confirm and
back follow the menus kit's convention. Its proof script runs `unchanging`, a restart,
an older file and a pad walk of every tab.

**saves** (§PW348): a game's saves in slots, kept through a crash and an update, from
Cottony's save file. `PolyweaveSaves` takes a Dictionary and never names a field. A
slot is `user://saves/<slot>.save`, JSON written from Godot's own types inside an
envelope with the version, the time and a SHA-256 of the data. A save is written to
`.tmp`, the save it replaces moves to `.bak` (or to `.bad` where it does not read, so a
corrupt save never pushes the last good one out), and only then is the new one renamed
into place. `load_slot` falls back to `.bak` where the save is missing, does not parse
or fails its sum, and `said` says so. The project's `res://polyweave_saves.gd` declares
`const VERSION`, `const SLOTS` and `static func migrations()`, version to a Callable
that brings a save to the next; a save from an older version comes up step by step,
and one with a step missing or from a newer build is refused and left on disk. Its
proof script fills and reads back every slot, stops a save after its write and after
its move, corrupts the data under a sum, and loads saves from every older version and
from a newer one.

**launch** (§PW349): from launch to the first scene, and every change of scene after.
`PolyweaveSplash` shows the project's logos, each for its seconds, while the first
scene loads on a thread behind them; any key, mouse button or pad button of any family
skips the rest. `PolyweaveScenes.shared().go(path)` is the one way every change of
scene goes: the scene loads on a thread (`ResourceLoader.load_threaded_request`) while
a loading screen is up (the project's `loading_scene`, told the share loaded through
`progress`, or a plain dark screen), and each change measures its frame times. `last`
answers the path, whether it loaded, its seconds, its frames, the 95th percentile and
the longest frame, a percentile and never a mean, so one hitch is not averaged away;
`launch_ms` is the time from the engine's start to the first scene. The project's
`res://polyweave_launch.gd` declares `LAUNCH_MS` and `FRAME_MS`, and the proof script
holds the fixture to both, with a skip from every family and a change to a scene of
four thousand nodes. A proof script runs on the wall clock with no frame budget of the
runner's, since headless frames run unbounded and a threaded load is counted in time;
the engine's timeout stops a proof that hangs.

**credits** (§PW350): a credits screen drawn from the records, with nothing typed by
hand. `provenance.credits out=credits.json` writes, at build time, the people and roles
the project declares under `[kit.credits] people` and every credit a record owes (a
sound's instruments, or a file borrowed with `credit=`), with a digest;
`check=true` answers whether that file still matches the records, so an asset recorded
after the last build cannot ship uncredited. `PolyweaveCredits` shows each person with
their role, then each credit owed, scrolls at `rate` pixels a second, and any key,
mouse button or pad button of any family ends it. Its proof script walks the project's
own records and finds every credit they owe on the screen, nothing on it the file does
not hold, the scroll at its rate, and a press from every family ending it.

**audio** (§PW351, requires menus): the audio runtime, from Cottony's `music.gd` and
`sound.gd`. The project's `res://polyweave_audio.gd` declares `BUSES`, each a `name`, the
bus it `send`s to (Master where unset, and one declared before it, since Godot mixes a bus
only into one ahead of it), an optional `volume_db` and its `loudness`, the RMS dBFS a
track mastered for it plays at; Master, Music, SFX, UI and Voice where it declares none.
`PolyweaveAudio.shared()` adds each missing bus and routes every one as declared, saying in
`said` what it could not. `play_music` crossfades at equal power over `CROSSFADE` seconds,
and music ducks by `DUCK_DB` while the Voice bus is heard. `play(stream, bus)` takes a
player from a pool of `POOL`, the oldest where none is free, its pitch varied by up to
`PITCH`. `UI_SOUNDS` `{"focus": path, "confirm": path}` play on the UI bus as a control
takes focus and a focused button is pressed, which is how the menus kit's pad navigation
sounds. The kit carries no sound of its own. It contributes the `audio` tab: a volume row
for each declared bus. Its proof script checks that every bus exists and routes as
declared. It plays a tone mastered to each bus's loudness through that bus, writes what
the Master bus heard to `.polyweave/kits/audio/<bus>.wav` and prints it as a `KIT SOUND`
line held to `loudness` ± `LOUDNESS_TOLERANCE`. A crossfade's level must stay within 1.5 dB
throughout, with no gap and no clip; the music ducks under a voice and comes back; more
sounds than the pool holds all play, at differing pitches; a pad's focus and confirm in a
menu play the UI sounds; and every bus's row reads back what it sets.

**language** (§PW352): the string table `words.check` holds, on screen in every language.
The project's `res://polyweave_language.gd` declares `TABLE` (the CSV `[words] table`
names), `FALLBACK`, `FONTS`, `FOLLOW_SYSTEM` and `SCREENS`. `PolyweaveLanguage.start()`
uses the translations Godot imported and, where nothing was imported, reads the CSV
itself, a column starting with an underscore skipped. A cell left empty carries the
fallback locale's line, and `said` names each one. Each of `FONTS`,
`{"script": "Jpan", "path": ...}` with an ISO 15924 tag, is added to the fallbacks of the
font the game draws with (the project theme's default font, or Godot's own), so a
character the main font lacks is drawn by a declared font and not a system one. A first
launch shows the system's locale where the table has it, else one of the same language,
else the fallback. The kit contributes a `general/language` row whose default is that
choice. Its proof script lays out the screens (the main scene where `SCREENS` names
none) in every locale. In each, every visible Label and Button must show its key's line,
and a control whose text is no key, which never changes language, is named. No key may
show its raw name. Every character a line needs, upper case included, must be drawn by
the font chain, which is the question `words.glyphs` asks of the files. Every line must
fit its control, by the measure `game.text_fit` takes. Then the first-launch choice and
the row are checked.
