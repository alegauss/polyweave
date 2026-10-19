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

### §PW565 Rings that follow the normal

Where: spinhold, 2026-10-19, the Playdeck's pizza and strawberry (RK236).

A `sphere` given a flattened `size`, such as `["across * 0.84", "base * 0.5", "across *
0.84"]`, creases at its rim at any `steps`: `sharp_edge_share` read 0.028 at a 3:1
squash with 32 steps and 0.135 on a pepperoni at 3:1 with 28. The mesher lays its rings
evenly in the parameter angle and then scales a unit sphere, so the normal turns faster
than the rings near the flat rim, past the 30-degree crease.

Workaround in spinhold: flattened discs became cylinders under a round `bevel`, and the
cheese became `rounded_box`es, which costs triangles (the pizza is 19,708).

What polyweave should do: space a scaled sphere's rings so the normal turns evenly (for
an ellipsoid of equatorial radius a and polar c, the parameter angle is atan((c / a) tan
theta) for each even normal angle theta), so a flattened sphere is as round as its steps
say.

### §PW566 A bevel for the creases alone

Where: spinhold, 2026-10-19, the Playdeck's arch (RK236): a `torus` (32 steps) cut in
half by a `carve` with `bevel = 0.12`, `segments = 4`, to round the cut ends.

What came back: 18,356 triangles and a `sharp_edge_share` of 0.086, worse than the
unbevelled cut's 0.059. `solver.bevel` bevels every edge of the mesh (`geom = verts +
edges + faces`), so the torus's smooth facets, each turning under 23 degrees, were each
split into bevel strips: the round body multiplied and grew creases of its own.

Workaround in spinhold: the arch was redrawn as a curve of overlapping spheres, with no
cut and no bevel.

What polyweave should do: a `bevel` (and a carve's) rounds only edges sharper than a
stated crease angle, 30 degrees unless the node says, and leaves a smooth surface alone.
Where that changes an existing build, a `crease` field on the node can keep the old
every-edge behaviour by setting it to 0.

### §PW567 A build owns what it wrote

Where: spinhold, 2026-10-19, the Playdeck's kit (RK236). `playdeck_hex.toml` first
declared materials `tile`, `lip` and `stud`, then was redrawn with `pink`, `cream` and
`violet`; `playdeck_arch.toml` lost its `arch` material the same way.

What came back: `geometry.build --out assets/pieces` wrote the new
`playdeck_hex.pink.tres` and the rest, and left `playdeck_hex.tile.tres`,
`playdeck_hex.lip.tres`, `playdeck_hex.stud.tres` and `playdeck_arch.arch.tres`, each
with its `.prov.json`, beside them. Nothing said they were orphans; they were found by
listing the folder and matching each file's material against the declaration by hand.

What polyweave should do: a build owns what it writes for a document. On a rebuild it
removes the `<name>.<material>.tres` / `.gdshader` (and records) it wrote before for a
material the document no longer declares, and says which in its answer;
`provenance.outdated` names any it finds whose material is gone.

### §PW568 One call from a kit to its sitting

Where: spinhold, 2026-10-19, the Playdeck's kit of twelve pieces (RK236).

What was done by hand, twelve times over, in a shell loop: `geometry.build` each
declaration; `cost.read` each `.glb`; `render.bake --rung final` each; write each
`art/accept/<piece>.accept.toml` from its measured triangles (a margin over them) and a
`sharp_edge_share` bound; `accept.check` each; then build a members JSON by hand for
`verdict.sitting`. spinhold's `tools/art/look.py` does the same for its five models, as
a project script.

What polyweave should do: one call over a folder of declarations (`geometry.kit` or a
`sitting` flag on `geometry.build_all`) that builds each, renders it at a stated rung,
writes a first spec where none exists from the costs it measured (`triangles` with a
margin, and any bounds the call names, such as `sharp_edge_share <= 0.02`), checks each,
and lays the lot out as one family on the review page, answering which passed and where
the sitting is.

### §PW569 A finish opened to the game

Where: spinhold, 2026-10-19, RK231: the Playdeck's pieces stand on a MultiMesh of their
own (RK230), each in the finish the owner accepted on the kit's sitting (RK236), and the
ring must (a) show one piece in several hues, one per instance, and (b) dim under the
play by the project's `backdrop_dim`, as every background does.

What came back: `finish.write_godot` writes a closed material, a StandardMaterial3D or,
with a sheen, a ShaderMaterial over a fixed shader. Neither reads an instance's custom
data nor any project uniform. The first workaround was a `plastic.gdshader` in the game,
re-implementing polyweave's shading with the hue and the hold added and copying the
numbers in from the .tres: the owner refused it, since the work belongs in polyweave.

Built: an optional `[finish]` table (geometry layer): `hue = "instance"` turns each
instance's colour by INSTANCE_CUSTOM.x turns of the wheel; `include` and `hold` pass the
colour through a function of the project's, `hold(colour, amount)`, with `amount` an
instance uniform (default `backdrop`, 1 unless set). With it, every finish is written as
the spatial shader with the same numbers; without it, as before. Refusals for a bad hue,
an include without a hold, a non-name hold and a non-res:// include. Spec in
`geometry.md` and `project-config.md`; tests in `test_finish.py`, one of which has Godot
parse the shader with a project include.

### §PW570 Imported in the judged look

Where: spinhold, 2026-10-19, RK231. The Playdeck's pieces were built with their finish
written beside them as `<piece>.<material>.tres` (PW495), but Godot imports each `.glb`
with the glTF's own materials, colour and roughness only. To draw the accepted look the
game would have to walk each mesh's surfaces, match each material's name to a `.tres`
and swap it in, which is a game holding code for what the build already knows.

Built: in a Godot project, the build writes `<mesh>.glb.import` with
`_subresources.materials.<material>.use_external/{enabled,path}` naming each written
`.tres`, so Godot imports the mesh wearing them. An existing import keeps its other
settings; one whose `_subresources` holds more than materials is left alone. Tests in
`test_finish.py`, one importing a built mesh through Godot and reading the surface's
material back.

### §PW571 One shader for one finish

Where: spinhold, 2026-10-19, RK231. With `[finish]` opened (PW569) every material of the
Playdeck's twelve pieces is written as a ShaderMaterial, and `finish.write_godot` writes
each one's shader beside it as `<piece>.<material>.gdshader`: 50 files with identical
code, each with its `.prov.json` and Godot's `.uid`, 150 files where one shader would
do. Godot compiles each as its own shader, so the ring holds 50 programs for one finish.

What polyweave should do: write the finish's shader once, where its code is the same
(per build folder, or under a path the project names in `[finish]`), and have every
material reference it; a material whose shader differs (a project's own hold, a future
look) keeps its own. A rebuild that changes the shared code rewrites it once.

### §PW574 A finish that gives

Where: spinhold, 2026-10-19, RK234: the Playdeck's course should squash and jiggle back
where a kill lands, the higher pieces swinging more. Its pieces wear the opened finish
(PW569) a person accepted. vfx's `kind = "struck"` (PW496) gives a struck piece its own
mesh and its own albedo-only shader, so a course piece could either keep its judged
finish or give, not both, and the game would have had to splice the two shaders.

Built: `[finish] struck = { give, wobble, lifetime, falloff, height, radius, amount }`
puts the struck give's uniforms and vertex body in the opened finish, the numbers as vfx
sets them (`settle_rate`), and writes `finish_strikes.gd` beside the materials: `watch`
each material, `strike(at, strength)` ages the strikes and hands them to all. Refusals
for an unknown key, a missing one, a zero give, lifetime, height or radius and more than
16 strikes. Spec in `geometry.md`; tests in `test_finish.py`, one in which Godot parses
the composed shader and the script hands a strike to the material.

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

### §PW560 One seam measure for the loop and its spec

Where: spinhold, 2026-10-19, the intro's instrumental (`sound.stems` no_vocals, 64.8 s)
cut into a loop.

The calls, on the same track and the same cut (23 bars at 123.98 BPM, 44.528 s):

- `sound.loop --out loop.wav`: seam_step 0.045, seam_change 0.937, passed true.
- `sound.loop --out loop.ogg`: seam_step 0.012, seam_change 1.714, passed false, "the
  seam stands out from the track: listen across it before using this".
- `sound.measure --subject loop.ogg`: seam_step 0.0118, seam_flux 0.2472, seam_grid
  0.0207, where the WAV reads seam_flux 0.233.

So the two operations answer the same question about the same file differently:
sound.loop's own `_seam` divides the flux across the wrap by the track's 90th-percentile
flux, and sound.measure's `seam_flux` by its strong onsets. One says the Ogg seam stands
out, the other says it is as ordinary as the WAV's. An agent cannot tell which to
believe without reading both sources, and the person is told to listen to a seam a spec
would pass.

What polyweave should do: one seam measure, the one `sound.measure` and a sound bound
read, used by `sound.loop` for its verdict and reported under the same names
(`seam_flux`, not `seam_change`), so the loop's `passed` is what an acceptance spec over
the same file would answer. If the Vorbis encode really does change the wrap, say so as
the difference between the cut and the encoded file, not as a second scale.

### §PW573 A Surge render that fails on a label's codepage

Where: polyweave's own gate, 2026-10-19, during PW559.

`tests/test_music_render.py::test_a_surge_patch_renders_through_the_plugin` failed once
in the parallel gate and passed run alone a minute later, on the same code. The failure
is inside Pedalboard, not polyweave: `load_plugin` reads Surge XT's parameters while
`music_render.py:158` opens the plug-in, and `_pedalboard.py:256` raised
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe3 in position 9`. 0xe3 is `ã` in
Windows-1252, so the bytes were most likely a label in the machine's pt-BR codepage, not
UTF-8, and which label comes back can depend on what else is loading at the time.

What to build: a gate that does not go red on a third party's decode. Two ways, and the
choice is open:

- open the plug-in in `music_render.py` with the decode guarded: catch
  `UnicodeDecodeError` around `load_plugin`, retry once, and only then refuse with a
  named code (`music.no-engine`, with the error in the message), so a render on a
  pt-BR machine says what happened instead of raising a traceback;
- or mark the Surge render tests `serial`, if a second run shows they only fail under
  load.

Reproduce first: run the gate on a pt-BR Windows machine a few times and count how often
it fails. If it never fails alone, it is contention; if it fails alone too, it is the
codepage.

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

## Block W — A core that grows by layers

## Block X — The site on the shared design system

### §PW572 The site on the shared design system

`site/src` carries `components/Nav.tsx`, `components/Footer.tsx` with the sponsor block,
`components/sections/Hero.tsx`, `pages/Feature.tsx` and `components/ui/CopyButton.tsx`,
`ThemeToggle.tsx`, `Rich.tsx` and `RawSvg.tsx`, plus `scripts/prerender.mjs` and
`scripts/og-image.mjs`: the template seven other alegauss product sites copy under the
same names. `index.css` declares its own `--bg*`, `--panel*`, `--violet*` and
`--accent*` tokens for both colour modes.

The move, after the pilot (claude-tray T389):

- `data-tone="cool"`: the ground is a violet-tinted white (`#f8f7fd`) and near-black
  (`#0b0916`), not clay, so the warm tone would change the page.
- The accent from the hub's `projects.json`. The two disagree today: the hub's card says
  teal (`33,193,166`, bright `#5fe0c9`) and the page is violet (`#5a3fd6`). One value is
  settled in `projects.json` first and the page takes it; if that is teal, the change is
  listed as intended in the screenshot comparison.
- The shared components come from `./site`; `Session`, `Brand`, `Icon`, `Lattice`, the
  product sections, `pages/Specs.tsx` and `lib/` (with `roadmap.generated.ts`) stay in
  `site/src`.
- The build calls the `./vite` helpers instead of the two scripts; `scripts/roadmap.mjs`
  stays.
- Google Analytics loads only after consent, the same flow as the hub (AG1).

Done when `site/src` has none of the files `./site` provides; the prerendered HTML of
every route holds the same text as before; light and dark screenshots of each route are
compared before and after with the differences listed in the commit; and the site
appears in the design system's `consumers.json`.
