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
  its path and value (§PW351). A picture only the game can draw is held the same way:
  the script writes it with its targets as a JSON list beside it and prints
  `KIT CONTRAST <picture> <targets> <measure> <min> <max>`, which `measure.contrast`
  holds, listed under `contrasts` (§PW355). What a game draws over time needs a screen
  a headless proof lacks, so the script prints `KIT CAPTURE <script> <measure> <min>
  <max> [args]`: the run is taken with `capture.movie` (its environment empty, since
  nothing is committed), measured by `measure.flashes`, and listed under `captures`.
  Where no route draws real pixels it is `skipped`, and said.
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
the store from the file, resets, and drives the screen with a pad button, all on three
actions of its own declared at run time (since 0.2.1), so it holds in a game whatever
actions that game has. A pad binding the store puts in force answers every pad, as the
project's own do, and never pad 0 alone (0.2.2). Since 0.2.0 it contributes the `controls` tab to the options
screen, a row opening its screen.

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
the row are checked. Since 0.2.0 that measure is `PolyweaveLanguage.unfit(node, shown)`,
which any kit's proof may call.

**dialogue** (§PW353, requires prompts and language): a dialogue box. A line is
`{"key", "speaker", "portrait"}`, the last two optional, keys of the string table, so a
translation needs no change here. `PolyweaveDialogue` types a line at `RATE` characters a
second. The first confirm completes a line being typed and the next confirm shows the
next line, using the confirm button of the family in hand as the menus kit has it (east on
a Switch pad, south on every other, `ui_accept` and a click besides); `finished` follows
the last. The project's `res://polyweave_dialogue.gd` declares `RATE` and `SEQUENCES`, a
name to its lines. The kit carries no line and orders none, so it stays clear of writing
a game's story. The box is the project's scene, `kits/dialogue/dialogue_box.tscn`, with
a Label named `Text` and, optionally, a Label `Speaker` and a TextureRect `Portrait`,
wherever it places them. Its proof script checks that a line types at its rate. It walks
every sequence by each family's confirm alone, holding that the other family's button
moves nothing and that the first press leaves the same line whole. Each line must show
the speaker and the portrait it declares, and fit its box in every locale by
`unfit`.

**access** (§PW355, requires options): the accessibility tab. `PolyweaveAccess.shared()`
puts the project's Theme, duplicated with every item kept (or an empty one), on the root
window, and the text scale sets its default font size, so every Label and Button that
sets no size of its own grows with it. `shake(amount)` and `flash(strength)` are what a
game's own effects ask: each answers the amount, or nothing where the player switched it
off. With hold or toggle on, `held(action)` turns on at one press and off at the next
for each action in `HELD` (every action where it lists none). `set_filter(deficiency)`
lays the correction for protanopia, deuteranopia or tritanopia over the whole screen
(`simulating` shows what that player sees, for a person previewing the game). The
correction is Daltonize, over Machado, Oliveira and Fernandes's 2009 simulation at full
severity, in linear light. `filters.gd` holds the numbers the shader is given, so the
proof's sums and the screen are one set. The project's `res://polyweave_access.gd`
declares `SCALES`, `HELD`, `SCREENS`, `SHAKE_RUN` with `RUN_SECONDS`, and
`COLOUR_PAIRS` with `PAIR_DELTA_E`. Its proof script reads back every row. It draws
each colour pair as a player with each deficiency sees it with the correction on, a box
of one colour in a ring of the other, and holds the pair at `PAIR_DELTA_E` (CIEDE2000)
by `measure.contrast`. It lays out the screens at the
largest scale, naming a control that sets its own size (which the scale never reaches)
and one that no longer fits. It runs `SHAKE_RUN` with shake off, where no camera's offset
may move, then with shake on, where one must, so the run is shown to shake at all.
Then it checks hold or toggle. `subtitle(player, key)` shows the key's line at the foot
of the screen while the player plays (the one the audio kit's `say()` answers) and
clears it when the player stops. The proof holds the probe line and each of
`SUBTITLE_KEYS` to its box, to `SUBTITLE_LINES` rows (3) and to a screen of the game's
size. That screen is a SubViewport, since a headless window is 64 pixels square. The
proof also checks the line clears and that nothing shows with subtitles off. Last,
`FLASH_RUN` is asked for as two `KIT CAPTURE`s of `flash_run.gd`, played for
`FLASH_SECONDS`. With flashes off it may hold no more than three flashes a second, and
with them on it must flash at all, so the run is shown to flash.

**presence** (§PW356, requires prompts): nobody left at the controls.
`PolyweavePresence.shared()` pauses the game through the scene tree when a pad
disconnects. It says whose pad left (the project's `LEFT` key, given the player's
number) and draws the confirm button in that pad's family, from the prompts kit's icons,
by the name the pad had while it was connected. The game resumes when that pad returns,
or when any pad confirms by its own family's convention (a Switch pad on its east
button, every other on its south one) or the keyboard on `ui_accept`. Losing the
window's focus pauses too (`AWAY`), and regaining it leaves the game paused until the
player confirms; a game meant to run in the background declares `PAUSE_ON_FOCUS`
false. A game its own menu had paused stays paused when this resumes. Its proof script
drives a PlayStation pad leaving, where the game must stop ticking, name player 1 and
draw the PlayStation confirm, and then its return. Another pad's wrong button, in Xbox's
and in Switch's convention, must hold the game, and that pad's confirm must resume it.
The proof also checks a game paused by its own menu, a lost and regained focus, and
`PAUSE_ON_FOCUS` off. Since 0.2.0 the player it names is the seat the players kit gave
that pad, where that kit is installed.

**players** (§PW357, requires remap): more than one player on one machine, from
Starship's `coop.gd`. `PolyweavePlayers.shared()` seats the first player on the keyboard
and `FIRST_PAD`. Any other pad joins by pressing `JOIN_BUTTON` (Start) while fewer than
`MAX_PLAYERS` (2) play. A player who joins gets a copy of every rebindable action,
`p2_fire` and so on. Each copy holds the first player's pad bindings on that player's
pad alone, and the first player's pad bindings then answer `FIRST_PAD` alone, so an
event from one pad never moves another player. `player_of(device)` and
`player_of_event(event)` answer whose a device is. `rebind(player, action, event)`
changes one player's binding, swapping a clash among that player's own actions only.
`leave(player)` drops their actions and frees the pad. How many play and what a player
is in the game are the project's (`res://polyweave_players.gd`, and the `joined` and
`left` signals); the kit assumes no genre and no split screen. Its proof script seats a
second pad, numbered apart from its seat, and refuses one past `MAX_PLAYERS`. It holds
each player's pad to their own actions and the keyboard to the first player's, and a
rebind on either player to leave the other's alone. A leave must free the pad for the
next to join, and with the presence kit installed, a pad that leaves must be named as
the player seated on it.

**state** (§PW359): a game's state named once for reading. The project's
`res://polyweave_state.gd` declares `STATE`, each name a `node` (a path from the current
scene, or from `/root`) with a `property` (nested as `stats:health`) or a `method`
answering a Dictionary, and the `type` its value must be, by Godot's own type names
(`int`, `Vector2`, `Dictionary`). `PolyweaveState.read(names)` answers each name with
its `value`, `type` and `ok`, and `said` where its node, property or method is gone or
its value is of another type. `snapshot()` holds every name's value at once, the one
surface a crash dump writes and a determinism check compares. The driver serves it as
`state`, so `game.query state=["health"]` (or `["*"]`) reads it with no path and no
print. Its proof script runs the main scene and holds every name to its declared type.

**determinism** (§PW360, requires state): the same run twice. `PolyweaveRandom` holds one
seed for a run: the run's `--seed=N` (the driver's, so a driven session and a replayed
flow reach it), else `SEED` in `res://polyweave_random.gd`, else one drawn and printed
as `polyweave_random: seed=N`. The project's code draws from named streams,
`PolyweaveRandom.randf("enemies")`, each seeded from the seed and its own name, so a draw
added in one never shifts another, and the global random functions are seeded too.
`PolyweaveRecorder` records each action's press and release by physics frame, and saves
`{seed, events}`. `game.record_flow` turns a saved record into a `game.keep` flow, ending
on the `expect` given, so a bug seen once is a flow `game.replay` runs in the gate. The
proof script plays the declared `RUN` for `RUN_TICKS` physics frames twice, from `SEED`
and with `RECORD` fed at its frames, and holds the state kit's snapshot of the two runs
to agree after every physics frame. It names the first frame and name that differ,
usually a draw made outside the streams, and refuses a run in which nothing the state
kit names ever changed.

**crash** (§PW361): what a crash leaves behind. `PolyweaveLog.shared()`, opened first
thing, writes every line the game logs (`info`, `warn`, `error`) to
`user://polyweave_log/log.jsonl`, one JSON object a line: its time, level, physics frame,
current scene and words, rotated past `MAX_KB` into `KEEP` older files. A Godot
`Logger` it registers hears every error the engine raises, with the script and line: a
script error names them, and a pushed error is placed by its backtrace's first script
frame. Each of the first `CAPTURES` errors packs a capture in
`user://polyweave_log/captures/`: the error, the log's last `LINES`, the state kit's
snapshot and the determinism kit's seed where the game carries them. A run that never
closed its log (killed, frozen, a crash of the engine itself) leaves its marker, and the
next launch packs the log as an `unclean-exit`. `game.crash_read` reads a capture back,
a file a person sent or the newest in this machine's user:// for the project, and
answers the error, its script and line, the state, the seed and the last lines. Its
proof script forces an error and finds the capture naming its own script and line with
the log's lines, stages a marker for the next log to pack as an unclean exit, and
checks a clean close leaves none.

**tests** (§PW362): one way to run a game's tests. `game.test` imports the project
headless, then runs each test script the project's convention finds, headless at a fixed
60 fps, bounded by frames and by `timeout` seconds. It reads each run's output for its
summary and its failure lines, and answers the counts first, then each failure with its
script, file, line and words. A test that does not parse or raises is a failure at the
line the engine names. One that never prints its summary is a failure, and one still
running at `timeout` is stopped and named as hanging; none is ever a silent pass. The
convention is Cottony's, so its tests are adopted as they stand: `tests/*_test.gd`,
`  FAIL: <words>` a failure and `checks ran: N, failed: M` the summary. A project whose
tests speak otherwise declares `[kit.tests]` `scripts`, `summary` and `failure` (named
groups `ran`, `failed` and `said`) and `timeout`; Starship's `dev/check.gd` is
`summary = "^CHECK (?:OK|FAILED (?P<failed>\d+))$"` and `failure = "^FAIL (?P<said>.+)$"`.
The kit installs `PolyweaveTest`, a base a new test extends: every `test_*` method runs
on the first frame, `check` and `equal` name a failure with the line of the check
(`(res://file:line)`), and the run ends on the summary, exiting non-zero on a failure.
`python -m polyweave game.test` exits 1 when a test failed, so a project's own gate runs
its game's tests with one line. Its proof script runs a test on the base with one check
failing on purpose, and holds the counts and the failure's line.

**tables** (§PW364): a game's data tables held to the schema of one row. The project
declares each table in the TOML file `[kit.tables] schema` names (`data/tables.toml`):
its `file`, a CSV with a header or a JSON list of objects, its `key`, and each column's
`type` (`int`, `float`, `bool` or `string`), `required`, `choices`, `min` and `max`. The
tables are the project's own and assume no genre. `tables.check` holds every row to its
schema in the gate, each finding naming the file, the row (the CSV line, or the JSON
place) and the column. A value of another type (a JSON `"10"` in an int column
included), a required column missing, a column the schema does not declare, a choice
outside its set, a number outside its bounds and a key used twice are each a finding.
`write=true` writes one typed script per table under `[kit.tables] out` (`tables/`): a
`Row` class with a typed field per column and a `read()` that loads the file. A script
that no longer matches its schema is a finding too. `PolyweaveTables.shared()` loads a
table through its script (`get_rows`, `row(table, key)`), and in a debug build reads a
changed file again within a second and emits `changed`, so a tuned value shows without a
restart. Its proof script loads every generated table and holds each field to its
declared type and to the value read for it, since a typed field refuses a value of
another type in silence. It then writes a table file again and waits for `changed`.

**graphics** (§PW366, requires options): graphics presets and a renderer that falls
back. `PolyweaveGraphics.shared()` reads whether the main scene is 3D, and `watch(scene)`
notes which costly effects (SDFGI, SSAO, volumetric fog) the game's environments switch
on. A 3D preset sets the root viewport's render scale and upscaler (bilinear, FSR or FSR
2, Godot's own), MSAA, TAA, FXAA, positional shadow atlas and the frame cap, and switches
off or back on only the effects the game uses. A 2D preset sets the stretch mode and
integer scaling. `in_force()` reads each back in a preset's own terms. A first launch
takes the lightest preset on an integrated or software adapter, and the middle one where
the adapter is unknown (or `FIRST`). The kit contributes the `graphics/preset` row, and
the project's `res://polyweave_graphics.gd` may declare `PRESETS`. Vulkan failing is
Godot's to survive: the project keeps `rendering/rendering_device/fallback_to_opengl3`
on, and on Windows Godot reaches Direct3D 12 first. Vendor SDKs (DLSS, Reflex, XeSS)
stay out; Godot builds in none of them. Its proof script runs the main scene and reads
every preset back. It checks that no effect the game left off is ever switched on, that
the row reads back each preset, and that the fallback is on. A test hides Vulkan's
drivers and sees the game reach its scene on another driver.
