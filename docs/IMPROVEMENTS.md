# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

### §PW582 A mesh prepared by declared steps

Found closing PW82 in Cottony on 2026-10-20. `tools/art/bake_model.py` is gone, but its
preparation half survives as `tools/art/prep.py`, driven by three exporters
(`export_props.py`, `export_boosters.py`, `export_friends.py`) before `port.run`.

Landed: `render.bake` takes `prepare`, a list of steps run on the mesh after it loads
and before it is decimated or placed. `dedust { below }` drops every piece under that
share of the largest's vertices, where a piece shares an edge or a position (a glTF
splits vertices at seams). `settle { squash }` keeps volume about the base. `custom { fn
= "file.py:fn", ...args }` calls a project function with the object. Each step is in the
key and the record, a custom one with its source's digest, and the answer says what each
did. A family sets them through `fixes`, which already reaches `render.bake`. Joining
needs no step: `load_mesh` joins every part a file holds.

Left, in Cottony: each exporter's work as prepare steps, then the exporters and
`prep.py` deleted. Two pieces need care. `cloth.dress` projects drawn cloth from the
orthographic camera `prep.frame` builds, so it becomes a custom step that builds its own
camera from the object's bounds. The exporters also scale each mesh to a fill of its
frame (`FILLS`), which the bake's `margin` or `covers` should express; compare a render
before and after for each family, as PW76 to PW81 did, before deleting anything.

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

Site copies, left by PW585 on 2026-10-21: `picture.copies` cuts a `*.copies.toml`, and a
trial on Cottony's hero and favicon came out pixel for pixel equal to `site/assets/`.
Cottony moves IMAGES into `site/assets.copies.toml` (`into`, `quality = 88`, and
`quality = 86` on `og.jpg`), runs it once, deletes `tools/site_assets.py`, and lets CI's
`provenance.outdated` replace `--check`.

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

### §PW638 Line widths in a panel are not whole pixels

Met in Spinhold, RK184 (2026-10-25), declaring the holo panel the owner accepted. The
hand-written shader drew its inner hairline where `abs(depth - 9.0) < 0.6`, a line 1.2
pixels wide. `panel.build` refused `hairline = { inset = 9, width = 1.2, ... }` with
`compose.bad-panel: hairline.width is 1.2`, remedy "write hairline.width as a whole
number from 1". The panel was declared at 1, a thinner line than the look accepted.

The shader route already does the sum in floats (`abs(dist - hairline_inset) <
hairline_width * 0.5`), and the nine-patch is drawn four times larger and brought down,
so a fraction of a pixel is drawable on both. Widths that are a line's thickness (the
hairline, the edge, the bracket, the tick, the piping) should take any number from a
small floor, say 0.5, while the sizes and margins a nine-patch cuts on stay whole. Done
when the 1.2 declaration builds and both routes draw the same width.

### §PW639 Moving one Control between a panel's states

Met in Spinhold, RK184 (2026-10-25). `panel.build(shader=true)` writes one
`<name>.<state>.material.tres` per state, each `resource_local_to_scene`. A Control
whose state changes at run time (a card gaining focus, a button disabled) cannot simply
assign one: a loaded material is shared by every panel that loads it, so a per-instance
`set_shader_parameter` (a tint, a cut) would leak to all of them. Spinhold's
`game/ui/kit/holo_panel.gd` works round it by keeping its own `ShaderMaterial` and, on
every state change, looping over `SHADER.get_shader_uniform_list()` to copy each uniform
from the chosen state's material, then reapplying its tint.

`tint` also surprised: it multiplies `bracket_colour`, so a crew family's gold over the
kit's cyan comes out green. Spinhold sets `bracket_colour` itself instead.

polyweave should ship the switch with the build: a small GDScript (in the kit's addon,
or written beside the shader) that holds a panel's states and moves one Control between
them, keeping per-instance overrides, with the state precedence declared (disabled over
pressed over focus). And `tint` should say whether it replaces or multiplies, or offer
both. Done when HoloPanel's copy loop can be deleted for it.

## Block I — Voxel models from a declaration

### §PW642 A text symbol that fills its icon

Met in Spinhold, RK265 (2026-10-26), building the stage editor's toolbar from
`art/editor/tools.icons.toml` (sizes 32 and 64, `rounded` faces). Two icons took a text
symbol: `new_wave` with `symbol = "+"` and `delete_wave` with `symbol = "-"`. The build
measured them at `symbol_share` 0.024 and 0.004 of the face, a speck, where the glyph
icons beside them (`left`, `square`, `ring`, `view`) came out at 0.11 to 0.18. Nothing
in the declaration sets how large a text symbol is drawn, and no `[accept]` bound was
asked for that would have caught it, so the set passed on contrast alone at first.

The workaround was to give up the meaning: `new_wave` became `menu` (three bars) and
`delete_wave` a `cross`, the same glyph as `delete`, told apart only by its fill.

What polyweave should do: draw a text symbol to fill the face as a glyph does, its
height fitted to the face's inner box whatever the characters are, with a declared
`symbol_scale` to change it; and say in `measured` when a symbol's share is far under
the set's median, even with no `symbol_share_min` declared, since a speck is never what
was meant. A `plus` and a `minus` glyph would also serve editors and menus.

## Block J — A bar a person sets once

### §PW637 A picture's first spec, written from its measurements

Met in Spinhold, RK184 (2026-10-25). The menu kit's holo panel became polyweave's
(`panel.build` from `art/panels/holo.panel.toml`), and its design asked for a spec that
holds the built still. No operation writes one. `geometry.kit` writes a first spec for a
model, with its `bounds` parameter, but a picture gets nothing: the agent ran
`measure.take --subject game/ui/kit/holo/holo.normal.png --measures [...]`, read the
values, worked out each bound by hand in the project's `margin` convention (min at 0.8
of the measured value, max at the measured value plus 0.1, copied from other specs), and
wrote `art/accept/holo-panel.accept.toml` itself, `measured` and `origin` included.

That is the step a person's bar is meant to be spared: a number an agent picks, written
in a file that then reads as polyweave's. PW107 derives a margin from how far a measure
moves on its own, but nothing applies it to a new picture spec.

polyweave should write a picture's first spec the way `geometry.kit` writes a model's:
given the artefact, the measures and a region each, it measures, sets each bound with
its origin from PW107's margin, and writes `<specs>/<asset>.accept.toml` with the
measured values recorded, refusing to overwrite one that exists. A `panel.build` could
offer it for its normal state. Done when Spinhold's holo spec could have been written by
that call and `accept.verify` passes on it.

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

### §PW608 A level schema's reader and field metadata for the engine

Found in spinhold while planning its stage editor (RK264, RK269, RK281). The keys of a
level file, their bounds, units and what each means live in three places in that game:
the reader's list of accepted keys and its refusals, the editor's table of bounds and
steps, and the doc comments a person reads. Each new key is added three times, and they
already disagree on what a person may type.

§PW203 makes the schema a project's declaration (`[levels] schema`) and checks a level
against it. That covers the checking. What the engine still lacks is the rest of what a
declared schema knows:

- **a typed reader**: `tables.check --write` already writes a typed script from a
  declared table; the same for a nested level document (tables of arrays of tables, inline
  tables, enumerations, cross-references to other entries), refusing a key by name as
  the schema does;
- **field metadata for tools**: per field its type, bounds, step, unit, default, the
  values an enumeration allows and a one-line help, exported as a resource or JSON a
  game's own editor or debug panel builds its inspector from;
- **help in every locale**: the help text routed through the string table, so
  `words.check` holds it like any other line.

A level editor is the game's, not polyweave's (non-goal "A graphical editor"); this
gives that editor its fields from the one declaration. Proven on two genres' schemas, as
§PW205 asks of the level contract.

### §PW609 A draft level from an accepted transcription

Found in spinhold (RK198, RK258, and the library of pieces RK274 plans). A reference
video is read with `reference.frames`, `reference.events` and `reference.objects`, laid
out with `reference.transcription`, and a person answers it row by row. What comes next
is by hand: an agent reads the accepted rows (what arrives, how many, from where, in
what formation, at what second) and retypes them into the game's level file. Two stages
have been carried over this way, each a long session of retyping and a source of slips
the transcription had already settled.

polyweave should take that step: `reference.draft` (or a mode of `level.compile`) turns
an accepted transcription into a draft level in the project's own declared schema
(§PW203). The mapping is the project's, declared once beside the schema: which column of
a row becomes which field, how a row's time becomes the level's clock, how a named
formation or kind maps to the project's names, what a row with no mapping becomes. No
genre is compiled in: a shooter maps rows to spawn groups, a rhythm game to notes, a
platformer to placed objects.

The draft is written with its provenance naming the transcription, its verdicts and the
mapping, marked as a draft so a person still tunes it; rows a person corrected carry
their corrected value, and a row nobody answered is refused, not guessed.

### §PW641 Enemies told from a city that moves by parallax

Met in Spinhold, RK198 (2026-10-25), after PW480 shipped. Resogun's phase 1
(`.polyweave/references/resogun_p1`, 170 frames at 2 a second), area `[0, 180, 1920,
1080]`. The pod kind came from the new `reference.sample` (4.5 s, box `[503, 698, 587,
762]`, colour `#846ea8`, body share 0.726), and `reference.objects` was called with it:

- tol 0.12, match 0.25, motion 0.15: 2756 tracks; motion 0.3: 1857;
- tol 0.08, match 0.5, motion 0.5: 1485 tracks;
- tol 0.10, match 0.6, motion 0.7: 2 tracks.

The sheets (`objects_002.png`) show the 15.5 to 18.5 s lull, which the owner's accepted
sheet says has nothing new, full of tracks on tower edges and the ring. The city is not
a flat scrolling backdrop: its towers stand at many depths, so parallax moves them
against the scroll as much as an enemy moves, and the motion filter keeps them. Between
the settings that keep the city and the ones that keep nothing there is no step.

What polyweave should do: tell an enemy from the scene by what parallax cannot fake.
Each Resogun enemy warps in with a white flash a second before it is live and dies in a
burst; it keeps its shape while it moves, where a tower's edge changes as the view
turns; and it moves independently of its neighbours, where a building moves with the
buildings beside it. Until then `reference.objects` and `reference.compare` cannot count
this reference, and RK198's re-count and its comparison with `phase_poc` stay deferred.

## Block S — Playing the game, not only rendering it

### §PW640 A run flown back at another frame rate

Met in Spinhold, RK263 (2026-10-25). A player's kept run did not fly back to its score.
Spinhold's proof (`dev/replay.gd`) runs under `--fixed-fps 60`, one tick a frame, so it
passed over four causes of drift that show only when frames and ticks part:

- `Engine.time_scale` is read once per frame, so a scale set during a tick reaches the
  next tick only if that tick starts a new frame;
- a hit stop counted down in `_process`;
- a camera held in `_process` whose view culled the ship's shots;
- a map flight (an idle-mode AnimationPlayer) the run waited on.

The workaround is in the project: `dev/replay.gd --scene --fps=<recorded>,<watched>`
records on the real clock at one `max_fps`, watches at another, samples both on the
recorder's tick (score, ship, enemies, shots) and names the first tick they differ. Each
run takes minutes, and it was run by hand several at once, since the drift was
intermittent and showed under load.

polyweave's game layer should own it: given a scene, a recording driver and a sampler
(node paths and properties), fly it at two frame rates, repeated N times, and answer the
first tick and fields that differ. `engine.find` could flag the hazards statically:
`_process` writing what `_physics_process` reads, `time_scale` set inside a physics
step, play waiting on an idle-mode AnimationPlayer or Tween.

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
