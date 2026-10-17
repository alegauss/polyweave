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

### §PW372 A camera clip the game plays

Met in starship (RK190): a cinema opening before the first phase, with four camera shots
of the city, each a position, a target and a slow drift over about 1.2 s, cut by a
flash, then a glide back to the run's camera. The project's rule is that timing and
curves are declared and built through polyweave, not set by eye.

`clip.new`/`clip.set_key`/`clip.write` author a clip of joints and their properties, and
`motion.bake` bakes one onto a skeleton. Nothing declares a camera move (a shot list
with position, look-at, field of view, hold, drift, ease and cut), and nothing writes
one the game can play, so the shots live in the project's own
`game/ui/opening_shots.json`, read by `game/ui/opening.gd`, with no record and no spec.

What polyweave should do: a camera clip, a clip whose channels are a camera's position,
target and FOV (absolute or relative to a named anchor, here the ship's start on the
ring), with cuts and holds. Plus an export the engine plays, and a capture per shot so a
person accepts the framing on the review page.

Landed: `clip.camera` builds a `*.camera.toml` into a Camera3D scene the game seeks by
time, recorded as kind `camera` (docs/specs/motion.md, "A camera clip"). Not an
Animation track: an anchor placed at run time, on a ring that is not Cartesian, cannot
be baked, so a place stays in its anchor's frame and the game maps it with `place`.
Left: each shot captured onto a sitting, and Starship's opening moved onto it.

### §PW523 The saves proof in a folder of its own run

Found in polyweave on 2026-10-17, shipping PW497. The gate went red once on
`tests/test_kit_saves.py::test_the_saves_kit_lands_alone_and_proves_in_its_fixture`: the
proof said "slot 0 could not be saved; slot 1 could not be saved; slot 0 read back {  };
listed 1 slots of 3". Run alone straight after, the test passed, and the change under
test touched no kit.

The likely cause, read and not yet reproduced: `kits/saves/core/proof.gd` writes its
slots to a fixed `user://polyweave_saves_proof` and empties that folder when it is done.
Godot names the `user://` folder after the project, so every fixture project with the
same name shares one folder. The gate runs pytest beside its own proof of the nineteen
kits, and the pytest test proves the same kit, so two proofs can write into one folder
and one empties it under the other.

What polyweave should do: the saves proof writes under a folder of its own run, such as
`user://polyweave_saves_proof/<a random token>`, and empties only that, so two proofs at
once cannot see each other. A test runs two proofs of the saves kit at once in two
fixtures and holds both to their three slots. Any other kit proof that writes under
`user://` is checked for the same fixed path.

### §PW524 Render tests crash their workers under the parallel gate

On 2026-10-17 the gate went red at 6472f5c with two xdist workers crashed outright (gw5
and gw12) inside `tests/test_render.py`: `test_a_blend_bakes_like_any_other_mesh` and
`test_a_render_that_is_black_to_any_observer_is_refused`. There was no assertion and no
traceback in the log, only "worker crashed". Both passed when run alone, and the whole
file passed sequentially (45 tests). The next gate run, with no code changed, was the
check.

A crashed worker is Blender dying in process. `bpy` is a singleton per interpreter, and
twelve workers each importing it and rendering at once is the likeliest cause: memory,
or a GPU or temp-file contention the in-process route never meets on its own.

Measure first. Run the render tests under `-n 12` ten times and count the crashes, then
again with them marked `serial` (the gate already runs that marker alone after the
rest). If marking them serial makes the crashes go away, mark every test that imports
`bpy` the same way, and let the gate say how many ran serially. If they still crash when
serial, look at Blender's own crash log in the temp folder, which the gate could copy
beside `pytest.log`.

A flaky gate teaches the next run to rerun rather than read; this one cost a full gate
run today.

### §PW525 The crash kit's kill waits on the game, not the clock

`tests/test_kit_crash.py::test_a_game_killed_mid_run_is_read_back_as_an_unclean_exit`
failed twice in the full gate on 2026-10-17, on trees that did not touch the crash kit,
and passed alone both times (10 of 10 in the file). Each time the assertion was the
same: the last line read back was "the crash kit's forced error" where the test expects
"the fixture starts".

So the kill the test sends "mid run" lands late under load: the game has already reached
the line the kit forces, and the read is right about what happened while the test is
wrong about when. The test races a sleep or a fixed point in the run against the
machine's speed.

Make the kill wait on the game's own signal instead of on time: the fixture prints a
line it then pauses on, the test waits for that line through the held game's output,
then kills it, so "mid run" is a place in the run rather than a moment. The assertion
then holds at any load. Run the file under `-n 12` with the rest of the gate ten times
to show the race is gone.

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

### §PW371 Cottony onto the settings and save kits

Cottony's scripts/settings.gd, and scripts/save_file.gd with tests/save_test.gd, are a
second instance of what the options and saves kits provide, written without either kit
in mind. Moving Cottony onto them proves the kits against a game they were not extracted
from, which is the non-goal on one project's palette, rig or paths compiled in, checked
in practice rather than asserted.

Players' existing save files must load through the kit's declared migration, so no one
loses progress on the update that swaps the code; that is part of the proof, not a
follow-up.

What Cottony needs that the kits lack is filed as friction and fixed in the kits:
measured on 2026-10-10, the kits read only their own files, so its user://cottony.cfg
needs a door into them (PW398, docs/specs/kit.md: `adopted()` and `ADOPTED`). The game's
own side is Cottony's RK151. Done when Cottony carries neither file, its own save test
is replaced by the kit's acceptance, a save written by the current release loads after
the swap, and its gate passes.

## Block W — A core that grows by layers

### §PW506 The import direction as a test

The package direction landed in `tests/test_layering.py`: kernel imports only itself,
loop the kernel, services the loop and the kernel, a layer those three, surface
anything, with no allowlist. What is left is one layer importing another.

`Layer.uses = ("engine",)` declares each edge, so `capabilities` can say vfx is
unavailable when engine is; the test refuses an undeclared import and any cycle. Today's
graph has three cycles, measured at 73dc9ca:

- engine to geometry to picture to engine: `engine.port` renders a family of models and
  builds them with `make.build_one`, so it belongs in geometry.
- sound to picture to reference to sound, and half of geometry to picture: `mesh_buy`
  and `sound_buy` import picture only for its paid-service plumbing (`_download`,
  `_mime`, `_reached`, `sent_bytes`, `AGENT`, `_price`, `_priced`). PW516 moves that
  into `services/`, which removes both edges.
- geometry and picture both ways, after PW516: picture uses geometry's 2D outline math
  (panel), `render` and `cost` (a style family can hold meshes) and `shape.check`
  (`picture.chosen` picks a picture for a mesh); geometry uses `picture.gate` and
  `from_world` before buying a mesh. Either the outline math becomes shared below both
  and `chosen` moves to geometry, or mesh buying stops reading the gate directly.

`picture.vector` reaching `store._drawn_svg` is picture's own rasterising living in
store, and moves to picture.

Done when the test refuses an undeclared layer import and a cycle, and passes on the
tree.

### §PW512 A whole layer added from a fixture, touching nothing else

Each line before this one ends with a fixture layer exercising its own seam. This line
combines them into one fixture that stands for the next medium,
`tests/fixtures/layers/tone/`, a layer that makes a sine tone from a declaration. It
declares:

- one operation, `tone.make`, with a code of its own, `tone.bad-pitch`;
- a config table `[tone]` with a default and a choice;
- a record kind `tone` and a staleness check for its source role;
- a `Subject` measuring pitch and length, and a `Producer` a search can sweep over pitch;
- a `Judge` that keeps a person's verdict in its own canon;
- its part of the brief, the review page and the report;
- a tool budget and one internal helper.

The test points the layer search at the fixture directory, which is the same mechanism a
project's `[extend]` will use later, and checks that each of those appears where it
should: in `describe`, `tools/list`, `explain`, `project.check`, `accept.check`,
`search.sweep`, `verdict.answer`, `provenance.outdated`, `asset.brief`, `loop.report`
and the census. It then asserts that no file under `kernel/`, `loop/` or `surface/`
names `tone`.

This is the scalability claim as a number: the kernel files a new layer touches, held at
zero. When a later layer needs a kernel edit, this test is where that need is argued, by
extending the fixture rather than by working around it.

Done when the test passes and a deliberately broken seam in the fixture fails it.

### §PW516 A paid service is an adapter; the ledger and the ceiling are the kernel's

Five services are bought from today: Meshy, Tripo and Rodin for meshes, Ideogram for
pictures, ElevenLabs for sound and voice. Each client lives inside its domain module.
`mesh_buy` builds `urllib.request.Request` three times, `sound_buy` has its own `_post`
and two more requests, and `picture` has three. Every copy carries its own timeout,
polling loop, reading of a 402 or 429, and way of naming the plan whose licence the
record keeps. `purchase` holds the ledger, the quote and the ceiling, and each domain
has to remember to call it.

A `Service` under `services/<name>.py` declares:

- `media`: what it sells (mesh, picture, sound, voice);
- `quote(request) -> Price` in the unit the project's `[budget.<name>]` counts;
- `submit`, `poll` and `fetch`, the three halves of an asynchronous purchase, with a single kernel-owned HTTP helper for timeouts, retries and reading a refusal into a `PolyweaveError` with the service's own message;
- `plan(answer)`: the tier and whether it permits a sold game, for the record.

The kernel's `buy(service, request)` is the only path that spends. It checks the
ceiling, writes the ledger before submitting and reconciles it after fetching, so no
domain can buy without the bound. Spending stays a person's call: the adapter never
decides a purchase is worth it.

Done when `mesh_buy`, `sound_buy` and `picture` import no `urllib`, the purchase,
ledger, quote and service tests pass, and a fixture service is quoted, bought, refused
over its ceiling and reconciled.

### §PW517 [extend.measures]: a project's measure, declared, run apart and recorded

`measurements.md` keeps a closed list, and `spec.unknown-measure` refuses everything
else. That rule is right for the vocabulary polyweave ships. It leaves a project with a
look only it needs, such as Cottony's glow at a rim or Spinhold's hull readability,
three options: a script beside polyweave, which `project.adoption` then reports as work
done outside it; a fork; or a line here that waits its turn.

`polyweave.toml` gains:

```toml
[extend.measures.rim_glow]
fn        = "tools/art/rim.py:glow"
subject   = "picture"
unit      = "ratio"
range     = [0, 1]
direction = "higher"   # which way a search moves it
about     = "light at the silhouette over light in the body"
```

The name in a spec is `x.<project>.rim_glow`. The prefix keeps it from colliding with a
built-in and makes it plain that it is not polyweave's. `describe` and
`measure.available` list it from the TOML alone, so the kernel never imports project
code to describe it. It runs through the job worker in the project's environment, the
way a job's target runs today. Its source file is hashed into the provenance record as
`geometry/custom.py` does for a node, so a changed function makes the measures it
produced stale.

A measure whose function returns a value outside its declared range or unit is refused,
never clamped.

Done when a fixture project's measure is bounded in a spec, aimed at by `search.sweep`,
recorded, and found stale after its source changes.

### §PW518 [extend.operations]: a project's generator on the surface and in the search

A job's target may already be `path/to/file.py:name`, and `describe.for_target` returns
None for it "as the ordinary answer". That is safe, but it means a project's own
generator is invisible: no `describe`, no tool, no flags, no `produces`. Even a search
over its parameters has to be written by hand. Cottony's `bake_model.py` rig, the cost
this plugin exists to remove, is exactly that kind of script.

`polyweave.toml` gains, beside measures:

```toml
[extend.operations.tile_sheet]
fn       = "tools/art/tiles.py:sheet"
about    = "cut a sprite sheet into tiles"
produces = "picture"
kind     = "build"          # asynchronous, so it runs as a job
[extend.operations.tile_sheet.params]
source = { type = "str", about = "the sheet" }
size   = { type = "int", about = "tile edge", lo = 8, hi = 256, unit = "px" }
```

It is served as `x.<project>.tile_sheet`, described, validated and turned into flags
from the TOML alone, and run in the project's environment through the worker. Its file
is hashed into the record of whatever it produces. With `producer = true` and a range on
a parameter, `search.sweep` turns it like any layer's `Producer`, so a project's
generator joins the loop with no Python registered inside polyweave.

`layer.off` and the session tool budget count these the same way as built-ins, so a
project cannot grow its own surface without the number showing it.

Done when a fixture project's operation is listed, described, called, run as a job,
swept and recorded.

### §PW519 Extensions are reported as what polyweave does not yet do

The vocabulary grew because every gap a consumer hit became a line here, through the
polyweave-friction skill and `project.adoption`'s `[adoption.own]`, which names each
project file doing polyweave's work and why it is kept. Extensions (the two lines before
this) make a gap cheap to work around, and a cheap workaround is a gap nobody files.
`geometry/custom.py` already states the rule: "where the same custom node appears in
three projects, that is the signal it should have been vocabulary". Nothing yet sees
that signal.

So an extension is accounted for in three places:

- `project.adoption` lists every `[extend.*]` entry beside `[adoption.own]`, with how often the provenance records show it used and when it was first declared, under a `not_yet_polyweave` heading;
- each entry must carry `why`, one sentence on what built-in it stands in for, and `project.check` fails on an entry without one, as it does for `[adoption.own]`;
- `asset.brief` mentions when an asset's bar or build depends on an extension, so the agent working on it sees the dependency.

The polyweave-friction skill is updated to read `not_yet_polyweave` and file an
extension used across many assets, or one whose `why` names a built-in that exists by
then, as a line here. Promotion is still a person's decision. The signal is no longer
hidden.

Done when a fixture project's extensions appear in adoption, brief and check, and the
skill's text names the field.

### §PW520 polyweave migrate: one command across the break

The block breaks code and config on purpose, and it does not break data. Spinhold's 443
provenance records name only `tool` and `version` under `producer`, never a module path,
and 30 of them carry a person's verdicts. That was checked before this line was written.
So records, specs, canon and ledgers carry over unchanged. Two things do not:

- **Imports.** Cottony has 10 Python files that import polyweave (`polyweave.errors`, `.testing`, `.pack`, `.geometry`, `.render`, `.image`) and Spinhold has 4 (`polyweave.config`, `.geometry.voxel_fit`). Each path changes when its module moves to its layer.
- **The project file.** It needs `[layers] on`, and it needs any table whose owner or name a line in this block changed.

`python -m polyweave migrate --root <project>` reads a table of old module paths to new
ones, written by the layout line as a file of data, and rewrites the project's own
imports. It writes `[layers] on` from what `project.init` detects, moves any renamed
table, and clears `.polyweave/jobs` and the cache, whose keys name the old version. By
default it reports a diff; `--write` applies it. It never touches a provenance record, a
verdict or a canon. A record whose kind no layer declares is reported as unreadable, not
rewritten.

Done when a fixture copy of each consumer's config and imports migrates, and
`project.check`, `project.adoption` and `provenance.outdated` answer the same before and
after.

### §PW521 Cottony across the break

Cottony (`D:\Git\viglet\cottony`) is the first consumer and the one that reaches
deepest. Ten of its Python files import polyweave modules directly, it carries 57
provenance records and 55 acceptance specs, and its `tools/art/` still holds scripts
that `[adoption.own]` lists as kept on purpose.

The move, done in Cottony as one commit and recorded here when this line ships:

1. `polyweave migrate --root .` reviewed as a diff, then written. Each import it rewrote is read once, and one it could not map becomes a defect in the migration table, not a hand edit.
2. `[layers] on` checked against what the game actually makes, and the session's `tools/list` size written down before and after. That pair is this block's headline number.
3. Cottony's gates pass, along with `project.check`, `project.adoption` and `provenance.outdated`, and each answers as it did before the move.
4. One script from `[adoption.own]` whose job a declaration can state becomes an `[extend.operations]` or `[extend.measures]` entry, the first real use of the extension lines. If none can, the reason is filed as a line here.
5. The skills and `CLAUDE.md` in Cottony that name a polyweave module path or a tool are updated, so the next session does not read a path that no longer exists.

Done when Cottony's own gates pass on the new polyweave and the before and after
tool-list sizes are in the changelog entry.

### §PW522 Spinhold across the break

Spinhold (`D:\Git\viglet\spinhold`, still called Starship in older lines here) has the
most at stake. It holds 443 provenance records, 30 of them carrying a person's verdicts,
19 verdict, canon and ledger files, and 12 acceptance specs. Its Python reaches into
polyweave in four files, one of them importing `polyweave.geometry.voxel_fit` directly,
which the representation line moves.

The move, in Spinhold as one commit:

1. Before anything changes, `provenance.outdated`, `provenance.verify`, `loop.report` and `verdict.answers` are written to a file as the baseline.
2. `polyweave migrate --root .`, reviewed as a diff, then written.
3. The same four reads again, compared with the baseline. Any difference is a defect in this block, filed here and fixed before the move is committed. Changing Spinhold's data to make the comparison pass is never the fix.
4. `[layers] on` checked against what the game makes (pictures, voxels, sound, voice, words, vfx, engine), and the session's `tools/list` size written down before and after.
5. Spinhold's gates and `game.test` pass. Its skills and `CLAUDE.md` stop naming moved module paths.

Spinhold is the second consumer, and the test of whether the block generalised beyond
Cottony. A seam that only one consumer used will show up here as an unused contribution,
and that is worth a note in the changelog entry.

Done when the four reads match their baseline and Spinhold's gates pass.
