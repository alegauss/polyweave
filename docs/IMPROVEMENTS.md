# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

### §PW495 The declared finish as a Godot material

Found in Spinhold on 2026-10-17, for the plastic city of PW498
(`docs/specs/geometry.md`). When the finish PW494 shipped (`docs/specs/geometry.md`) is
accepted on a sitting, the game must draw the same thing. A built model reaches Godot as
a `.glb`, and the importer keeps what glTF and its own mapping keep: a coat, a rim, a
subsurface tint or a sheen may come in at other numbers or not at all, and the game's
city is drawn on a MultiMesh in its own shader, which takes no material from a mesh.
Then the accepted look is re-made in game code by eye, which is what the project's rule
forbids.

What polyweave should do: write the declared material beside the build as a Godot
material (a `.tres` StandardMaterial3D, or a generated `.gdshader` where a feature the
standard one lacks is asked for), with the same numbers the bake used and a provenance
record, so the game loads what was judged. A capture of the game against the bake of the
same model at one rig says whether the two agree.

## Block H — Proof on a real game

### §PW36 Cottony adopts it without a fork

Cottony is the first consumer and the test of whether the configuration boundary in
Block A actually holds. Its pipeline uses everything this backlog proposes: a
script-built mesh, a fetched mesh re-dressed in drawn cloth, a cushion inflated from a
drawing, a fourteen-parameter rig, a paid service with a lock file, and four engine
captures. If all of that can move onto the plugin with a configuration file and no fork,
the boundary is real. If any of it needs a change inside the plugin that only Cottony
would ever want, that is the defect, and it is much cheaper to find here than via a
second adopter. The migration is also what keeps this from being a rewrite for its own
sake: each piece moves only once the plugin's version passes the same check the existing
one does, and the pieces that are better left alone stay where they are. What this line
delivers is the adoption plus a written list of everything that had to be configured,
which is the plugin's real interface, discovered rather than designed.

### §PW57 One floor of five is a target now, and one more is a floor

A threshold inside a gate can only answer after the render is spent. The same number in
an acceptance spec is what `search` moves towards, so the bar stops being a verdict and
becomes the target. That was the reason for this line, and the vivid floor is now that:
`docs/design/accept/board_drawn.accept.toml` and `board_mesh.accept.toml` in Cottony,
read by `saturation_hsv_p99`, with `check_vivid.py` reduced to running them. It needed a
measure: at a whole screen's tail HSL saturation reads 1.0 on every picture, so the
claim in `docs/specs/acceptance-spec.md` that it needed nothing new was wrong.

Reading the other four corrected the count. Only one more is a floor on a picture.
`check_palette.py` checks that `pieces.gd` mirrors `palette.py`. `check_plush.py` and
`check_markings.py` draw a synthetic body through Cottony's own 2D code and assert
ratios between two materials drawn in one run. They are unit tests of drawing code, no
asset is under them, and no search turns their parameters. They stay where they are.

What is left is `check_pieces.py`, which holds the committed sheet
`docs/design/screenshot-pieces3d.png` to three rules: ink on the faced kinds, no pale
ring of marks round a rim (rope or thread), and the kinds' radial silhouettes kept
apart. None of the three is a measure in `docs/specs/measurements.md`. The ring rule is
a property of a set of marks, which the script argues at length, and porting it is
either a measure that counts marks forming a ring on a subject, or a person deciding it
stays a test.

### §PW82 The rig has to actually go

This is the task PW53's objection was about. Setting it aside said that one asset moving
leaves bake_model.py standing for the rest, so the rig the plugin exists to remove is
still the thing that runs — and that stays true of two families, or five. It stops being
true only when the file is gone.

So the sequence needs an end that is checkable rather than assumed. After PW76 through
PW81 there should be no `tools/art/bake_model.py`, nothing importing it, and every
sprite under docs/design/art/ produced by the plugin. Until then Cottony has two routes
to the same picture, and the older one keeps working, which is exactly how a replaced
rig survives its replacement.

It is filed separately rather than folded into the last family because the failure it
guards against is not any one port going wrong. It is six ports going right and the file
remaining, with a handful of constants nobody moved and no reason left to look at them.

If a family turns out not to port — the friends and the mascot are the candidates — then
this is where that is recorded honestly: what still runs by hand, and why the rig shrank
instead of disappearing. An outcome worth having, stated, beats the same outcome
unstated.

### §PW546 The dialogue proof ends on the game's signal

On 2026-10-18 the gate went red at 98ea6d5 on
`test_kit_dialogue.py::test_a_broken_dialogue_box_fails_the_proof_by_name`, in its
`_shown += 100000.0` case (a box that types every character at once). The proof came
back `no-signal`: it printed no KIT line before the engine run's timeout, so the test
found no "characters typed in" to read. The file passed four runs out of four alone, and
the change under test touched no dialogue code.

So under the full gate's twelve workers this proof, with that mutation, runs past the
time it is given, where alone it finishes. Like PW525, the proof is racing the clock.

Measure first: run the file under `-n 12` beside the render and kit tests ten times and
count `no-signal`, and read the dialogue proof for a wait counted in wall-clock time or
in frames that the mutation can stretch. Then make the proof end on the game's own
signal. Each typed-in check waits for the box's own `finished` or a frame count it sets,
not a time, and a proof that cannot finish says which step it was on. Done when the file
holds ten runs of ten under the gate's load.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

### §PW449 Driven from a second MCP client

The server is MCP and nothing in the protocol ties it to Claude Code, but everything
that teaches an agent to use it arrives with the Claude Code plugin: the skill, and the
hook that guards derived files. Another client, such as Cursor or Codex, gets the tools
list and nothing else. Whether an agent there gets a call right the first time, which is
the project's one test of a feature, has never been tried.

MCP directories in 2026 compare Blender, Godot and Unity servers side by side, and they
are where a developer looks for one. Being listed there is free reach, but only honest
once the surface has been driven from a client without the skill.

The run is the line: set the server up in Claude Desktop, the client the owner has
(2026-10-15), ask it for one asset end to end, and file what it got wrong as friction.
Two findings are expected and are the reason to do it before any listing. Whatever the
skill alone teaches has to move into tool descriptions or `describe`. And every promise
that relies on the skill or a hook, rather than the server, is named; PW443 is the first
of those.

Evidence that it landed: a second client builds, checks and offers one asset for a
verdict, and each gap it met is a filed line.

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

### §PW450 Buying a picture from Scenario

Block N holds pictures to a canon: a family's approved members, its palette and its
style block. The services behind it today are FLUX and Ideogram, which take the style as
words, and PW180 sends one canon picture as a style reference on Ideogram 3.0. Scenario
takes a different route: a model trained on a team's own art, which reviews in 2026 name
as the strongest answer to style consistency for game art.

A canon is exactly the training set such a model wants, already chosen by a person's
verdicts. This line is an adapter behind the existing `picture.buy` surface: the same
ceiling, quote, ledger and provenance, and a record naming the trained model and which
canon members trained it, so a model trained before a member joined reads as outdated.

Training spends money, so it is a purchase like any other, quoted and bounded by the
ceiling, and never started on the agent's own judgement. The pictures it returns are
held to the canon and the gate like any service's; being trained on the style earns no
pass.

Evidence that it landed: one family's canon trains a Scenario model within the ceiling,
a picture bought from it passes or fails the family's gate, and its record names the
model and the members.

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

## Block Q — Words held to the world

## Block R — Levels measured before a person plays them

### §PW201 Whether a bot's win rate says how hard a level feels

The block rests on one premise: that a cheap simulated player, run headlessly over many
seeds, ranks a game's levels by difficulty the way a person playing them would. If it
does, a level's difficulty becomes a number a search can aim at. If it does not, every
later line tunes against noise.

The spike ran in Cottony on 2026-09-28. A throwaway bot, gitignored at Cottony's
.polyweave/spike/bot.gd, played the 20 shipped levels over 200 seeds each, first taking
the hint's swap and then greedily. Both won 95 to 100% of deals on every level. Their
moves left fell from 25 and 30 at level 1 to 12 and 18 at level 20, in the same order.
The owner, playing, felt no difference.

So the bot and the person agree that nothing here is hard. That cannot answer the
premise, since a set with no spread tests no ranking. It also suggests that moves left
is not what a player feels, and a chance of losing is. Cottony filed RK150 to give its
curve a loss within reach.

Once RK150 lands, rerun the bot. The owner then plays eight levels spread across its
ranking, and says whether the order matches what they felt and where it does not. An
agent does not judge the proxy it built.

If yes, the findings go into the designs below: which bot, how many seeds, and which
percentile carries the feel. If no, the open lines are retired with the spike as the
reason.

### §PW202 A level probe the game runs and polyweave reads

A match-3 bot and a shooter's threat count have nothing in common except their shape. A
script inside the game takes a level and some seeds, plays or analyses it, and returns
numbers. polyweave cannot own that script, since it would be one genre compiled in. It
can own the handshake, the way the capture environment already does.

`[levels] probe` in `polyweave.toml` names the script and the measures it reports, each
with a unit and a direction. `level.probe` runs it through the existing engine runner.
The level file and the seeds are passed after `--`, the same as capture settings. The
script prints one `level: name=value ...` line per seed. polyweave checks that every
declared measure came back and that nothing undeclared did, and a line missing a measure
is a refusal rather than a zero.

Across the seeds, polyweave aggregates each measure at the percentiles the project asks
for, because a level's feel lives in its bad runs as much as its median, the same lesson
that measures a look at a percentile. The result is written beside the level with its
seeds, the probe's hash and the engine version. A later run is compared against that
record, so a change in the rules that moves a level's difficulty is reported, not
rediscovered by a player.

### §PW203 A level declaration compiled by the game's own step

Both consumers already treat levels as data. Cottony has 20 JSON files written by
`make_levels.py` from a difficulty curve. Starship has 15 `.tres` waves under three
phases, and its own comment says a harder wave is a different file, never a multiplier
in code. What neither has is a layer that checks a level before the engine sees it, ties
it to the world, and records how it was made.

A `*.level.toml` is the source a person or an agent edits. Its schema is the project's,
declared in `[levels] schema` as a JSON Schema, because the plugin must not know what a
wave or a goal is. `level.validate` checks it against that schema. Where the project
declares a world (`docs/specs/world.md`), every field the schema marks as an entity
reference must name one of its ids, so a wave that spawns an enemy the world never
declared fails with the line and a remedy.

`level.compile` runs the project's declared compile command, which turns the source into
the engine's own resource: Starship's `.tres` or Cottony's JSON. It then writes a
provenance sidecar naming the source, the schema and the command's hash. The compiled
file is still what the game loads, so nothing at runtime depends on polyweave. A
hand-tuned level, like the files `make_levels.py` refuses to overwrite, stays a source
file a person owns.

### §PW204 Difficulty bounds and a search over a level's parameters

Once a probe reports measures and a level compiles from a declaration, a level's
difficulty works like any other asset property. The acceptance spec already states
bounds on measures. A `*.accept.toml` for a level bounds the probe's measures at a
percentile: win rate at the median between 0.45 and 0.70, and moves left at the tenth
percentile no lower than one. `accept.check` reads the probe's record and passes or
fails.

A level set needs one more kind of bound, because a game's difficulty is a curve and not
a single level. A set spec names its levels in order and states the shape: difficulty
never falls by more than a declared step between neighbours, rises across each region,
and dips after a boss. Each is checked against the measures and reported as the pair of
levels that broke it.

`search.sweep` then searches a level's declared parameters (Cottony's target and moves,
a wave's count and interval) for values that pass. Every candidate is compiled and
probed, and all of them run locally at no cost. What the search returns is a proposal.
Which candidate ships, and whether a level that passes also feels right, are decided on
the verdict page with the bot's numbers shown next to it, because the bot is a proxy
that PW201 tested once and a person holds to account afterwards.

### §PW205 A second genre: Starship's waves measured without a bot

A bot that plays a shooter well is a project of its own, so Starship cannot prove the
level contract by playing. It can prove it by analysis, and that is the useful test: a
probe that reads a wave without running it has to fit the same handshake as one that
plays a board over 200 seeds.

Starship's probe loads a compiled wave `.tres` headlessly. From each group's count, delay and interval it lays the spawns on a timeline and reports four measures:
- the peak and median enemies alive at once, per second of the wave;
- a threat total weighted per enemy kind, with the weights in the project's config;
- the share of the `time_limit` that the last spawn leaves for clearing;
- how many humans a keeper wave puts at risk at once.

Seeds are irrelevant here and pass as one, which the contract must allow without special
cases.

`check_phase_waves` already asserts that the enemy total rises each phase. A set spec
over these measures states that rule and the ones it misses, such as no spike of more
than a declared factor between neighbouring waves. The line is done when both genres
pass through `level.probe` and `level.compile` with no change to polyweave between them,
and the set spec follows once §PW204 lands. A change needed for the second genre is the
evidence that the first one leaked in, which is what the non-goal "One genre's level
format built in" forbids.

### §PW206 Cottony's levels made through polyweave

Cottony is where the level loop pays for itself first. Its 20 shipped levels are JSON
files generated from curve constants that `make_levels.py` reads out of `level_set.gd`
with a regular expression. Any level without a file falls back to that same curve at
runtime, so level 900 is only as good as a curve nobody has measured.

Adoption is done when:
- Each of the 20 levels is a `*.level.toml` under a schema Cottony declares, and `level.compile` writes the JSON the game already loads.
- The match-3 probe from PW201 is Cottony's declared `[levels] probe`, and every level carries a probe record.
- A set spec holds the 20 levels to the curve a person agreed on the verdict page, and `accept.check` passes on all of them.
- `make_levels.py` is deleted, and the runtime fallback curve is fitted from the accepted levels rather than typed.

The census from Block H counts which of Cottony's levels are made this way. The fallback
curve is the part to watch: it is still a formula for levels nobody declared, and the
probe can at least sample it. Probing levels 21 to 200 from the curve and reporting
where they leave the set spec's bounds says whether the endless tail keeps the promise
the first twenty make. Cottony's RK150 (2026-10-16) set that bar by hand: the careless
spike bot, swept with engine.sweep, put level 20 at 64 to 66% wins, against the owner's
60%.

### §PW327 Playtest traces measured beside the declared curve

Found in starship while planning its Block V (RK176, RK177): the owner finds the waves
unbalanced and wants balance measured, not felt.

§PW205 measures what a wave declares. It cannot measure what happened when a person
played it, and it still reads `.tres`: starship's waves are now authored in
`game/waves/phase_<n>.waves.toml` (RK122), and Block V adds formations, rails, `follow`
and `sway` (RK172 to RK174), so a probe must read the compiled spawn timeline, not the
file format.

What starship needs from polyweave:

- **A trace contract.** The game writes one event per line, each stamped with phase, wave and second: `spawn` (kind, weight), `kill` (kind, time alive), `hit` and `life_lost`. polyweave reads one trace or many and gives, per second, damage taken, kills and enemies alive, averaged across runs.
- **The declared curve beside it.** From the spawn timeline and the per-kind weights (§PW205), the pressure entering and alive in the two bounding cases (every enemy killed on landing; nothing killed until the time limit), and the longest gap with nothing to shoot.
- **A spec over both.** Bounds such as "alive pressure never above N", "never more than 2.5 s with nothing to shoot" (starship's multiplier window) and "each phase's peak above the one before", checked by `accept.check` and failing with the rule named. A person sets the bounds; the feel stays a verdict.

Until it lands, starship keeps the pass in `dev/` as the thinnest workaround, named
against this line.

### §PW480 Objects told from a scene of their own colour

Found in Spinhold on 2026-10-16 (RK198), re-reading Resogun's phase 1 from the owner's
capture (`reference.register` as `resogun_p1`, 170 frames from `reference.frames`).

The enemies are violet and blue-violet, and so is the city behind them: a violet ring,
navy towers, pink-lit edges. `reference.objects` was called three times on
`.polyweave/references/resogun_p1`, area `[0, 180, 1920, 1080]`:

- pod `#604ba0` tol 0.12, samples (two 76 px crops), match 0.25, and chain `#282670`
  tol 0.10, one sample: 9595 tracks, the city counted everywhere.
- pod alone, tol 0.06, match 0.12: 0 tracks.
- pod alone, tol 0.10, match 0.20: 987 tracks; `objects_004.png` shows most of them on
  buildings and the ring, while the stack of pods at 0:28.5 is partly missed.

No step between those settles it: hue and an average colour distance to a sample cannot
tell a lit studded sphere from a lit window of the same hue. Colours were also taken by
a throwaway PIL snippet, since nothing picks a kind's colour or sample from a point.

What polyweave should do: separate objects from a busy scene by more than colour, using
what the footage gives: motion against the scrolling background (frame differencing
after aligning the scene), shape (a sample's silhouette, not its mean colour), and the
white warp-in each enemy makes a second before it is live. And `reference.sample(frames,
at, box, name)` to cut a kind's sample and read its colour from a frame. Until then
Spinhold's RK198 cites frames, not tracks, and its comparison with `phase_poc` waits on
this line.

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

## Block U — A window on everything a project governs

### §PW311 The window proved on Starship

Every block here that reached a person was finished only when a real owner used it.
PW287 through PW295 were each found by Starship's owner on a review page that passed
every test. The window is the same kind of surface, so it is proved the same way.

On Starship, the owner does the following in their own language:
- opens the project in the window;
- finds one generated picture and one sound through the inventory, without typing a path;
- marks where the picture is wrong;
- asks for a change in their own words;
- answers the session's questions;
- judges the result in the sitting it ends on.

One of the two revisions should need a paid call, so the price stop (PW308) is exercised
on a real balance under a small ceiling. One should reach a dependent, so the scope
question (PW309) is seen.

The evidence is the two closed revision records, the screenshots of each step taken
before handing the window over, and every friction filed as its own line in this block.
It is not a test run. A change of plan that the owner asks for mid-way ("undo, try the
other palette") is part of what is being proved, because a revision a person refines
several times is the case this block exists for.

## Block V — Parts every game repeats, installed already proved

### §PW368 Declared states and transitions

Menus, characters and the flow of a game are each a state machine written by hand, and
the failure is structural: a state no transition reaches, or one with no way out that
was not meant to be final, found only by a person who walks into it.

A kit could let the project declare its states and transitions, generate the skeleton
the code fills in, and check in the gate that every state is reachable from the start
and has an exit unless it is declared final. The check is the valuable half, since it
needs no run.

It is the most opinionated kit in this block: games structure their state very
differently, and a skeleton that suits one may fight the next. So it stays an idea until
Starship and Cottony both show code it would replace, at which point the shape it should
take is read off that code rather than invented here.

### §PW370 Starship onto the input kits

The prompt, remap and co-op kits (the prompts, remap and players kits, in
docs/specs/kit.md) are extracted from Starship's game/core/bindings.gd, controls.gd and
coop.gd. Starship then adopts them, which is the decision that every project adapts to
polyweave rather than the other way round: its actions and options become the kit's
declaration, its own input code is removed, its Controls tab becomes the kit's screen
under Starship's Theme, and the checks in dev/check.gd that cover the same ground give
way to the kits' acceptance specs.

Whatever Starship needs that the kits lack is filed here as friction and fixed in the
kit, never patched in the game, so the extraction ends with one copy of the code and not
two. Measured on 2026-10-10 against Starship's bindings.gd, prompts.gd and coop.gd: the
prompts in words per player (PW394, docs/specs/kit.md), prompts per player's device
(PW395, docs/specs/kit.md), a join the game answers (PW396, docs/specs/kit.md) and
bindings taken from the game's older file (PW397, docs/specs/kit.md). The game's own
side, Controls.MAP into project.godot and its input code gone, is Spinhold's RK216.

Done when Starship carries no input code the kits provide, its gate passes on the kits'
proof, and provenance.read names each kit with its version.

### §PW534 The saves proof within the slots a game declares

Found moving Cottony onto the saves kit (PW371, Cottony RK151). Cottony keeps one save,
so it declared `SLOTS := 1` in `polyweave_saves.gd`, and the kit's proof failed: "slot 1
holds no save that reads after two saves", "a save from a newer build was not refused:
2.save is not there", "an older save was taken over a game already saved in the kit".
`saves/core/proof.gd` writes to slots 1 and 2 by number, so it proves a game with three
slots or more and refuses one with fewer. Cottony now declares three slots and uses slot
0 alone, which is a declaration that lies to pass a proof.

What polyweave should do: the proof works within the slots the game declares. The
corrupt-save and newer-build cases use the last slot rather than a fixed one, and where
a case needs two slots and the game has one, it runs on slot 0 in turn, clearing it
between cases, never skipping them. Done when the saves fixture proves with `SLOTS := 1`
and with three, and Cottony goes back to declaring one.

### §PW535 The options store installed without its screen

Found moving Cottony onto the options kit (PW371, Cottony RK151). Cottony keeps its own
settings card and wanted only the store: rows, apply and read, the file and the one-time
adoption. `kit.toml` says the options kit requires `menus`, and menus requires
`prompts`. So the install brought the menus scripts, three kit scenes under `kits/` and
the prompts kit's 69 icon PNGs. Cottony's `check_export.py` then failed on all 69 as
assets imported from outside its art, and the game had to add
`addons/polyweave/prompts/icons/*,kits/*` to its export's exclude filter to keep a
six-megabyte build lean.

The store (`options/core/settings.gd`) does not use the menus or the prompts; only the
screen does. What polyweave should do: the options kit's screen is its own part, and a
game can install the store alone. One way is a `[installs] store` beside `screen`, with
`requires` on the screen only; another is `kit.install --name options --without screen`.
`kit.prove` then proves the store in a fixture with no screen too. Done when Cottony
reinstalls options as a store alone, its export filter drops the two patterns, and
`check_export` holds.

### §PW536 Adoption resolved against the store's own folder

Found moving Cottony onto the options and saves kits (PW371, Cottony RK151). A game's
tests must never adopt the player's real older file, so Cottony's tests point the game
at a folder of their own. But `ADOPTED` in `polyweave_options.gd` is a const of absolute
`user://` paths, and `adopted()` in `polyweave_saves.gd` takes no argument. To aim
adoption at a test folder, Cottony's game.gd overwrites `settings.adopted` and
`saves.adopt` after building both stores. Both are public and the kits' own proofs do
the same, but it is the game reaching into a kit's state to make it testable.

What polyweave should do: an older file named in `ADOPTED`, or read by `adopted()`, is
resolved against the store's own folder when it is relative. So a store built on a test
folder adopts the older file in that folder, and the real game, built on `user://`,
adopts the real one. The same for the saves kit, whose `adopted(folder)` is handed the
store's folder. Done when Cottony's tests seed a folder and build the stores on it, and
game.gd no longer overwrites either field.

### §PW540 The remap screen rebinds through the players kit

Found moving Spinhold onto the input kits (PW370, Spinhold RK216). The remap screen
keeps a bindings store of its own, and it does not know about the players kit:

- a rebind on its pad half applies to every pad, which undoes the players kit narrowing
  player 1's pad bindings to player 1's pad during co-op;
- a rebind is not passed on to player 2's copied actions;
- `PolyweaveBindings.shared()` goes stale, so the game's twin-stick and invert read the
  old values until something reloads it.

Spinhold works around all three in game/ui/options.gd: on leaving the screen, where
anything changed, it calls `load_kept()` on the shared store and has player 2 leave and
join again (`OptionsScreen.keep_seats()`).

What polyweave should do: the remap screen rebinds through the shared store, and where
the players kit is installed, through `players.rebind(player, ...)`, so the narrowing,
the copies and the shared values stay right with no game code. Done when Spinhold drops
`keep_seats` and a rebind mid-co-op leaves each player's pad on their own actions.

### §PW541 The remap screen says when it listens and keeps focus

Found moving Spinhold onto the input kits (PW370, Spinhold RK216). A game hosting the
remap screen inside its own options needs to know when the screen is listening for a
binding, so its own back and tab keys stay out of the way. The screen says nothing, and
Spinhold reads the private `remap._listening`. The screen also rebuilds its rows on
every listen and every bind, so the focused row is freed and a pad is left with nothing
focused. Spinhold puts focus back itself in game/ui/options.gd.

What polyweave should do: the remap screen emits `listening(action)` and `listened()`
and exposes `is_listening()`, and it updates a row in place rather than rebuilding the
list, keeping focus on the row that was bound. Done when Spinhold reads neither private
field nor restores focus, and a pad walks the screen after a bind without a lost focus.

### §PW542 The pad screen in the game's own labels and buttons

Found moving Spinhold onto the input kits (PW370, Spinhold RK216). The remap kit's drawn
pad screen (PW428) has three gaps a game's own words and buttons fall into:

- it labels each place with an `ACTION_<name>` row, where the remap screen uses the
  declared `LABELS`, so Spinhold, whose labels are its `OPT_` rows, shows raw names
  such as "move_left" on the drawn pad;
- its `PAD_HELP` and `PAD_CHOOSE` lines are drawn as plain text, with no `{action}`
  marks filled through the prompts kit, so they cannot name the buttons that work them;
- both kit screens confirm and go back on `ui_accept` and `ui_cancel` only. In Godot 4.7
  those have no pad buttons by default, so Spinhold added pad buttons 0 and 1 to them in
  project.godot, and its own rebindable fire and bomb cannot work the screens.

What polyweave should do: the pad screen labels a place from the same `LABELS` the remap
screen reads; its help lines are filled by the prompts kit as every other kit line is;
and a declared `CONFIRM` and `BACK` (actions) replace `ui_accept` and `ui_cancel` where
a game names them. Done when Spinhold's drawn pad reads its own labels and its help
names the buttons, with no ui_* edit of its own.

### §PW543 Bindings load quietly where a key is absent

Found moving Spinhold onto the input kits (PW370, Spinhold RK216). A file the game's
older build wrote holds a key only for each action the player changed. Loading it,
`bindings.gd` reads every rebindable action with `get_value(section, action, null)`, and
Godot prints an engine ERROR for each key that is not there. So a player's first launch
on the kits logs one error per action they never changed, which looks like a broken
build in a crash log and in `game.boot`.

What polyweave should do: the store asks `has_section_key` before it reads, and an
action with no key keeps its default in silence. Done when loading a file that names one
action of eleven prints no engine error, which a check in the remap proof holds.

### §PW544 The install writes the store the game declares

Found moving Spinhold onto the input kits (PW370, Spinhold RK216). `kit.install` writes
a `[kit.remap]` table into polyweave.toml with `file = "user://polyweave_bindings.cfg"`,
the kit's own file, though Spinhold's `polyweave_remap.gd` declares `STORE :=
["user://settings.cfg", "controls"]` and the store keeps everything there. Spinhold
corrected the table by hand. A reader of polyweave.toml, an agent among them, is told
the bindings live in a file the game never writes.

What polyweave should do: where the project's declaration names a `STORE`, the install
writes that file, with the section beside it, into the table, and `kit.update` keeps it.
Done when installing remap into a game with a STORE writes its file into the table, and
Spinhold's hand correction is the table install would have written.

### §PW545 Prompts start on the first connected pad

Found moving Spinhold onto the input kits (PW370, Spinhold RK216). The prompts kit
starts every player on the keyboard family and moves only on an input. Spinhold's rule
(its RK146) is that, before any input, the prompts show the first pad that is plugged
in, since a game launched from a couch is played with the pad in hand. Spinhold sets
`family` itself at boot in game/core/settings.gd to keep that rule.

What polyweave should do: the prompts kit, before a player's first input, takes the
family of the first connected pad where one is connected, and the keyboard where none
is, and says which in its proof. Done when Spinhold's boot no longer sets the family and
its prompts still name the pad on a launch with a pad plugged in.

## Block W — A core that grows by layers
