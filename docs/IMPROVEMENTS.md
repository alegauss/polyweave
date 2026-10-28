# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

### §PW654 Enlarged boxes of a capture

Spinhold, RK302 (the run's HUD redrawn in the menu kit), 2026-10-27. The HUD's new icons
(a Holder's face rendered in a 60x58 SubViewport, a row of the tender's own model at
60x44 per icon) sit in the corners of a 1920x1080 capture. Read whole, the picture shows
each as a few pixels: whether the Holder faced the camera or showed the back of its
head, and whether the tender pointed left or right, could not be told.

What was done instead: a one-off PIL line run by hand, `Image.open(png).crop((1650, 8,
1890, 86)).resize((960, 312), Image.NEAREST).save(...)`, into the session scratchpad,
three times over the iteration, once per corner.

What polyweave should do: an operation that takes a picture, one or more named boxes (in
the picture's pixels, or as a fraction, or by a Control's path when the capture logged
its rects), and an enlargement, and writes one sheet of the boxes side by side at
nearest-neighbour scale, with a record naming the source picture and each box. A capture
should be able to declare its inspection boxes, so the same corners come back enlarged
on every retake without the boxes being typed again. The seam exists: `compose.sheet`
takes tiles but no box, while `verdict.sheet` and `reference.regions` each crop and
enlarge already. A tile `{path, box, scale}` there, with boxes read from the `region:`
lines a capture record keeps, covers it.

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

### §PW646 icons.build says what it did with a symbol and a folder

Met in Spinhold, RK266 and RK294 (2026-10-26), adding icons to
`art/editor/tools.icons.toml`, a set already built into `game/editor/icons/tools/` (its
records say so). Each run answered `passed: true`:

1. `symbol = "camera"` is no glyph (`GLYPHS`, `layers/store/icons.py:70`), so the word
   was drawn as text (`:330`), a low `symbol_share` the only hint. A word suits a
   keycap; on any other shape an unknown symbol should be refused with `allowed` and
   `did_you_mean`.
2. A top-level `out` was ignored: `read()` checks `[icon.*]` and `[accept]` keys but
   neither the top level nor `[style]` (`:112-143`).
3. With no `out`, the set lands beside the declaration (`:494`), not where its records
   say it was built (PW645, folded here). `--out game/editor/icons/tools` wrote
   `.../tools/tools/`: `out` is the parent the set's name is appended to, while
   `describe` says "the folder it lands in" (`:460`). Each wrong run left a copy to
   delete.
4. The sitting went to polyweave's work folder, away from the project's other
   sittings. No config key says where sittings go: `art/review` is Spinhold's own
   convention, and `geometry.kit` takes a `sitting` folder that icons does not.

What polyweave should do: refuse unknown keys at every level; let the declaration carry
`out`, and with none, build where the records say, refusing with the choice where they
disagree; make `out` the folder itself, as `panel.build` does, or name the path written
in `describe` and the answer; and add a `paths.sittings` key that every operation
opening a sitting honours.

### §PW647 game.text_fit judges only the text that is drawn, as it is drawn

Met in Spinhold, in pt-BR. RK295: five inspector rows "lie over" the panel below, though
a ScrollContainer clips them away, and rows off the screen get no finding. RK166 (PW649,
folded here): a Label drawn through `label_settings` reads "397 px wide in a 344 px box"
yet shows whole, the remap kit scaled to 0.64 is unfit on all 15 labels by that factor,
and a modal's labels "lie over" the HUD it covers.

All of it is one function: the driver's `_text_fit` and `_screen_rect`
(`addons/polyweave_driver/driver.gd:357-424`).

- No ancestor's clip is applied: only the direct parent is checked, and a
  ScrollContainer parent is skipped. PW589 names a SubViewport but does not map its box.
- Nothing tests the box against the visible rect, though `driver.off-screen` does for
  input targets (`:717`).
- The width is measured with the theme font (`:364`), never `label_settings`' font,
  size or outline, nor a Button's icon and margins.
- The box is scaled (`:424`), the text width is not.
- Overlap is any two texts in one viewport; what is drawn over them is not asked.

What polyweave should do: one visible-rect function that transforms the box, intersects
every clipping ancestor and the viewport, scales the text width with it and leaves out
text an opaque Control or a higher CanvasLayer covers. Wholly clipped text is reported
as clipped, and text past the screen edge gets a finding of its own. Tests: rotated
Controls, a hidden CanvasLayer, a nested SubViewport.

### §PW655 A sweep of captures

Spinhold, RK298 (the Neon fight's legibility), 2026-10-27. The task measures five
habitat variants on three seeds each: fifteen runs of one capture script,
`dev/legibility.gd`, which saves a frame and a `.targets` log that `contrast_median`
reads.

The call was `engine.sweep --script dev/legibility.gd --pattern SHOT --frames 2000
--args ["--world=waist", "--wave=4", "--out=.polyweave/rk298/{habitat}-{seed}.png"]
--grid {"habitat": [five res:// paths], "seed": ["LEGIBLEA", "LEGIBLEB", "LEGIBLEC"]}`.
Every run came back `script-error`: "Cannot call method 'save_png' on a null value". The
sweep flies headless, where the root viewport has no texture, so no capture script can
save a picture under it, and nothing in `describe` says so.

What was done instead: a PowerShell loop in the session scratchpad calling `python -m
polyweave capture.run` fifteen times, one `--args=` per item, judging each run by
whether its `.targets` file appeared (the CLI's text answer carries no `"ok"` to match).

What polyweave should do: `engine.sweep` takes `display: true` (as `game.open` does),
and then flies each run through `capture.run`'s offscreen route, with its environment
and record; or `capture.run` takes a `grid` of its own. Either way a run's produced
files are listed per combination, so a sweep of captures is one call. Until then, a
sweep whose script reads the root texture should be refused up front with that remedy,
not flown fifteen times to fail. `engine.perf` already switches between headless and a
drawing route (`frame_cost.py:139`). The sweep's cache key holds only script and build,
so it must take the route and the loaded inputs too.

## Block I — Voxel models from a declaration

### §PW644 Icons a game tints, with a filled and an empty state

Found in spinhold, RK253 (2026-10-26): each world's map card shows three marks, a
hexagonal pip each: a star, a Holder figure and a shield. A mark earned is filled in the
world's colour with a white glyph; one still to earn is a dark socket, its glyph faint.
There are five worlds, each in its own colour.

`icons.build` (art/editor/tools.icons.toml is the project's one set) could not make
them:

- its symbols have no star, no figure and no shield;
- an icon has one fill and one symbol colour, so a pip in five world colours is five
  declarations, and its empty state five more;
- no state is declared beside the icon (filled and empty, or earned and not), so a game
  showing a count of marks cannot take both from one declaration.

The workaround is `game/ui/world_marks.gd` in spinhold: a Control that draws the
hexagons, facets and glyphs with `draw_colored_polygon` at runtime, tinted by a `colour`
it is given. It also draws the flare (a ring and six rays) as a mark lights.

What polyweave should do: let an icon set declare a `tint` placeholder that the game
sets at runtime (a white mask plus a facet layer, say), declare states per icon
(`filled`, `empty`) with how each reads, and grow the symbol vocabulary with star,
figure and shield. `[accept]`'s legibility bounds would then check both states, and a
game draws the built textures modulated by its colour. On ship, `record move PW644
--to-block H`, where icons live.

## Block J — A bar a person sets once

### §PW656 A first bound's room near zero

Found shipping PW637 (2026-10-28). `accept.first` sets each bound `room` of the measured
value away, a share, and that is scale-free only away from zero. Re-writing Spinhold's
holo panel spec with it, the glass's `luma_p99` measured 0.0049 and its max came out
0.006 at a fifth of room: a hair. Spinhold's own spec, written by hand, put it at
0.1049, the value plus a tenth of the measure's whole range. The panel redrawn with one
more scan line would fail the first.

`calibrate.run` is the honest room, but only for a picture `render.bake` made: it
renders the accepted request again. A panel, an icon or a capture has no request to
repeat, so its first spec keeps the rule's room for good.

What to build: the room a first bound leaves is the larger of the share of the value and
a share of the measure's own range, where the vocabulary declares one. `measurements.md`
already gives each measure a range column (0–1 for luma, saturation, edge and coverage,
0–100 for `delta_e`); the registry should carry it, and a measure without one keeps the
share alone, and the answer names each bound whose room came from the range. Done when
the holo glass gets a max near Spinhold's 0.1049 from `accept.first` without a
per-predicate number, and `geometry.kit`'s triangle budget is unchanged. The seam is
`accept.first` and the measure registry in `loop/measure.py`; a per-predicate `room` an
agent types is the guess PW637 removed, so it is not the fix.

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

### §PW653 A retake after an edit hashes the script that was edited

Spinhold, RK302 (the run's HUD redrawn in the menu kit), 2026-10-27. The loop was: edit
`game/ui/hud.gd`, `capture.run --script dev/shot.gd --expect SHOT` into
`.polyweave/rk302/hud_en.png`, look, edit again. The second capture came back
`reproduced.holds: false`, "the same declared settings produced different bytes ... so
something this picture depends on is not declared". The workaround was `record: false`
on every later capture, which drops provenance.

The record does hash what the run loaded (`capture.inputs`, PW622's class scripts
included), so an edit should have read as different work. It did not because the record
hashed the wrong file: `hud_en.png.prov.json` lists `hud.gd` as
`.polyweave/cost/trees/0dfd6457f0fa/game/ui/hud.gd`, a copy `engine.cost` left behind.
`capture.reached` (`layers/engine/capture.py:129`) indexes every `class_name` with
`rglob("*.gd")`, skipping only `.godot`, and `setdefault` keeps the first in sorted
order, where `.polyweave/` comes before `game/`. The edited script was never hashed.

The class: three walks over a project's scripts each skip a different set, `capture`
only `.godot`, `engine/states.py` its `_SKIP`, `words.py` hidden folders. What polyweave
should do: one walk of the project's own files, skipping what Godot skips (a folder
whose name starts with a dot, one holding `.gdignore`), used by all three; a
`class_name` declared twice named in the answer rather than resolved by sort order; and
the unexplained-difference verdict saying how many inputs matched and which were
`unread`, rather than concluding a setting is undeclared. Done when Spinhold's
edit-and-capture loop reads as different work naming `game/ui/hud.gd`.

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

Met in Spinhold, RK198 (2026-10-25), after PW480. Resogun's phase 1
(`.polyweave/references/resogun_p1`, 2 frames a second, area `[0, 180, 1920, 1080]`, the
pod kind from `reference.sample`): `reference.objects` keeps 1485 to 2756 tracks, or 2,
and the 15.5 to 18.5 s lull the owner's sheet calls empty is full of tower edges. The
towers stand at many depths, so parallax moves them as much as an enemy moves.

Measured 2026-10-28, and not kept: three track filters, dropping a track that moved with
a patch of the scene round it, one whose area varied, and one seen in too few frames. At
2 fps all three together still left 28 tracks born in the lull against 1295 elsewhere.
The 11 to 23 s window was read again at 10 fps, and the best setting gave 9 to 32 tracks
born every second with no dip at the lull. Where its colour and size match, a tower edge
moves against its local patch as an enemy does, so these filters do not separate them.

What is left untried is what the city never does. A Resogun enemy warps in with a small
white flash a second before it is live, and dies in a burst. `reference.events` finds
flashes over the whole frame only. A local flash, a bright island that appears and fades
within a few frames, would gate a track's birth, keeping only tracks born at one. Done
when the lull counts no new track and RK198's re-count matches the owner's sheet.

## Block S — Playing the game, not only rendering it

### §PW650 text_fit inside a batch

Spinhold, RK166, 2026-10-26: checking ten screens meant, for each, a game.batch (input,
step, shot) and then a game.text_fit of its own, since `game.batch` refuses it: "command
2 is {'cmd': 'text_fit'}, not one a batch sends; make each a table with cmd, one of
query, input, step, wait, call, set, expect, shot".

A screen-by-screen language pass is exactly a batch: move to a screen, let it settle,
read its fit, shoot it. The project wrote a throwaway driver for it (scratchpad
`ptbr_screens.py`, a Python loop over CLI calls), which is the workaround this should
remove.

What polyweave should do: let a batch carry `text_fit` (answered in the batch's answers
like any query), or give `game.text_fit` a list of moments ({inputs, frames, shot}) and
answer each screen's fit and shot together. `locale` is missing from a batch too. The
`passed` and `unfit` summary lives in the Python wrapper (`driving.py:520`), so it moves
to one helper both answers share.

### §PW651 an MCP server on a stale copy

Spinhold, 2026-10-26. The polyweave plugin's MCP server (enabled from the
alegauss/polyweave marketplace, `python -m polyweave serve`) answered `game_open` with
code `game.not-listening`: the game failed to load
`.../Python313/site-packages/polyweave/layers/engine/godot/addons/polyweave_driver/driver.gd`,
"File not found". The same call through the CLI (`python -m polyweave game.open`), which
imports the editable checkout (`pip install -e D:\Git\alegauss\polyweave`), works. The
server was started before the editable install and keeps the old installed copy, whose
driver path no longer exists; earlier in the session its icons.build also refused
`model` keys the checkout takes.

Expected: the server says which copy of polyweave it runs and refuses with a remedy
("restart the MCP server; it runs <path>, the CLI runs <path>") when the two differ, or
it reloads. The workaround was to use the CLI for every call in the session.

The stale copy answers every tool, not only `game_open`, and `serverInfo` carries a
fixed `__version__` of 0.1.0 that cannot tell two copies apart. It should carry the
package path and its newest file time, reusing `review.staleness()`, which already
refuses a page whose code changed under it. And `_driver_for` (`driving.py:71`) should
check that the driver it falls back on exists before Godot starts.

### §PW652 the remap kit in a longer language

Spinhold, RK166, 2026-10-26: the remap kit (`addons/polyweave/remap`, installed by
kit.install) on Spinhold's Controls tab, in pt-BR at 1280x720 (shot: spinhold
art/review/ptbr-small/options_0.png). Its option labels keep one width that English
fits: "Zona morta do analógico" runs into the deadzone slider, "Nomes dos botões"
touches its value "Automático", and "Mapa de botões" its "< Padrão >". The kit is also
taller than the options panel's rows, so the game scales it to about 0.64, which leaves
its text near 11 px tall at 1280x720.

Expected: the kit sizes its label column to the longest label in the locale set, and can
lay itself out in the width it is given (two columns, or a shorter row height) so a host
need not scale it below a readable size. The game cannot change the kit's layout from
outside, so nothing was worked round; the shot is on the owner's sitting.

The cause is in `layers/kits/remap/core/remap_menu.gd:228-241`: each row is its own
HBoxContainer with a 160 px label, so rows share no column and a longer label pushes its
controls out of line. One shared column, a GridContainer sized to the longest label in
the locale set, fixes both; `pad_screen.gd:233` hardcodes its sizes the same way.

### §PW657 Frame-timed play named in the scripts

Split from PW640 (2026-10-28). `game.replay_rates` now flies the determinism kit's run
at several frame rates and names the first tick and state name that part. That finds a
drift the state kit can see, but only after the run has drifted, and only in what the
kit's `STATE` names. Spinhold's four causes were each a pattern in a script:

- `_process` writing what `_physics_process` reads (a hit stop counted down per frame);
- `Engine.time_scale` set inside a physics step, which reaches the next tick only if that
  tick starts a new frame;
- a camera held in `_process` whose view decides what the physics culls;
- play waiting on an AnimationPlayer or Tween in its idle process mode.

What to build: a pass in `engine.check` over each `.gd` that flags a member a `_process`
body assigns and a `_physics_process` body reads, `Engine.time_scale =` inside a physics
step, and an `await` on an AnimationPlayer or Tween left in idle process mode. Each
finding names the file, line and member, and says to move the write into
`_physics_process` or set the player's process callback to physics. Done when Spinhold's
four hazards, restored in a fixture, are each named and `game.replay_rates` parts on the
same run. The parse is pattern work, so the check says what it could not read rather
than calling a file clean.

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
