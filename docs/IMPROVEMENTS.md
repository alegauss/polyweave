# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

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

### §PW53 The rig is the thing being replaced, so it cannot be the thing still running

§PW36 moves one asset and stops there, which is the right size for a first port and the
wrong size for a claim. `tools/art/bake_model.py` is 1023 lines, and its `MODELS` table
holds twelve entries carrying up to fourteen rig parameters each — `fill`, `light`,
`turn`, `ambient`, `key`, `form`, `roughness`, `shadow`, `gloss`, `square`, `scrub`,
`roll`, `plate`, `dust` — every one of them found by hand at about two minutes a sample.
That table is the cost this plugin was written to remove.

One asset ported proves a picture can be made. Eleven left behind prove nobody chose the
plugin over the rig, and the rig is what still runs on a build.

The work is a translation rather than a move, which is why it is one line per asset.
§PW36's audit already found the sharp edge: `light` is a whole-rig multiplier and `form`
is the key's share of it, and neither is a parameter the renderer has. An axis with no
knob is refused before a render is spent, but the conversion stays a person's:
`exposure` is in stops, and a wrong one is a different picture rather than an error.

So each model's constants become an acceptance spec, the spec is what `search` aims at,
and the ledger `docs/specs/adoption.md` defines takes the before side for that asset
before it moves. A comparison with one side recorded is refused, and rightly.

Set aside: it needs a person three times over. The trap a hand conversion walks into is
in `docs/specs/adoption.md`.

### §PW56 Twelve runners, twelve ways to start Godot, and no check on what applied

`tools/capture_screens.py` drives four scripts under `tools/capture/`;
`tools/measure_frames.py` drives one. The other seven under `tools/perf/` have none —
started by hand, from a command line written in a docstring. Both drivers open a real
window, because `--headless` draws nothing; both distrust Godot's exit code; both bound
the run by a wall clock; and both fail a run whose line never came. That procedure is
written twice, and a third time in `run_tests.py`.

Block E is that, generalised and then taken further. `offscreen.py` probes which
offscreen route actually works on this machine instead of assuming one; `engine.py` and
`capture.py` run a script and compare the settings that were asked for against the ones
that applied; `units.py` checks a declared `pixels_per_unit` against the engine's own
number, which here is `const CELL := 112` in `scripts/board.gd`.

That comparison is the part Cottony has no equivalent of at all. `docs/specs/engine.md`
is about the settings a picture was taken under, and today a capture that ran at the
wrong resolution, the wrong locale or the wrong renderer prints its line, writes its
file and passes. The site publishes it.

**Replacing Blender, Godot or the generative service** is a non-goal, and this line
stays inside it: Godot still runs the scene. What changes is who starts it, and what is
checked once it has.

Godot 4.7.1 is installed and the probe answers the machine: `window-offscreen` and
`window-minimised` work, `virtual-display` cannot on Windows, and `headless` drew
nothing. The route exists, so what is left is Cottony's tree.

### §PW57 Five floors in five files, and not one of them is a target

`check_vivid.py`, `check_palette.py`, `check_markings.py`, `check_plush.py` and
`check_pieces.py` are about a thousand lines of measurement, each holding its own floor.
The best of them makes the argument this plugin adopted: `check_vivid.py` exists because
"washed out" was asserted, measured, and found true only at the tail — mean saturation
0.31 against the concept art's 0.32, and the 99th percentile 0.68 against 0.88. A look
is a distribution, and the interesting part is usually not its middle.

`measure.py` closed that vocabulary and `accept.py` turns a bar into a file. The
difference is not tidiness and it is not line count. **A threshold inside a gate can
only answer after the render is spent.** The same number in an acceptance spec is what
`search` moves towards, so the bar stops being a verdict and becomes the target, which
is the whole loop this plugin is.

A second cost is being paid quietly. Five floors in five files are five numbers that
move independently, and `check_vivid.py` already records what that costs: for as long as
only one of the two boards was read, the mesh board sat at 0.776 with nothing saying so.

The end state is one spec per asset, the gates reduced to running them, and the
percentile argument surviving as a measurement name rather than as a paragraph in a
script.

### §PW59 Adopted is an opinion until something fails when it is not

Today the number is zero. A search for `polyweave` across `D:\Git\viglet\cottony`
returns nothing, against 8,839 lines under `tools/`. Every line in this block moves that
number and none of them defends it.

That matters because the failure mode is not a port that never happens; it is a port
that comes back. A helper reintroduced under deadline, a floor copied into a sixth check
script, a thirteenth GDScript runner written because twelve were there to copy from —
each is one commit, each looks reasonable in review, and nothing fails.

So this block closes with a gate in Cottony rather than a claim in this repository. It
names the surfaces the plugin owns — the rig, the geometry, the fetch, the engine run,
the measurement, the sheet — and fails when one of them is re-implemented beside a call
that already exists.

**The denominator has to be stated or the number is a slogan.**
`tools/art/make_assets.py` is 2,406 lines of drawn 2D generation and is not in it: this
plugin is geometry, surface and motion in three dimensions, and a flat PNG generator is
Cottony's own work. The palette and the fonts are the same. What counts is what the rest
of this block names, and the gate may report a fraction below one for as long as it says
what is left and why. Two of those are already answered in `docs/specs/adoption.md`: the
fetch ledger replays, and the motion Cottony has is two frames and no clip.

### §PW77 A bar that was measured and then left in a comment

The map's props are the family with the best-recorded target in the project and no way
to act on it. `scenery_mushroom` carries this, verbatim: tuned against the drawn sprite
on its cap and stem medians, 223,118,87 and 215,197,173 against 225,127,83 and
214,198,174. Somebody measured the thing the render had to match, wrote it down, and the
only reader is a person.

That makes them the right second family. The work is not finding a bar — it is moving
one that already exists into something a search can aim at, which is a smaller step than
inventing the bar and the port at once.

Four of the five are built from the outlines make_assets.py draws them with, so they
carry the stars' property of costing nothing to re-render. The fifth, the mushroom, is
fetched, and it is here rather than with the boosters because it shares the other four's
settings exactly: one exposure, one gloss, one shadow, differing only in how much of the
canvas each drawing spans. A port that holds across a built prop and a fetched one at
the same numbers is worth more than one that only holds across four siblings.

What it must not lose is the reason the numbers exist: each prop lands on a sheet beside
drawn siblings, and reading as the odd one out is the failure.

### §PW78 Framing that answers to a number the game already holds

The board tray and the booster tray are the two assets whose framing is not a matter of
taste. `board.gd` addresses a cell at `CELL := 112`, so the render has to put its wells
on that grid or the game draws pieces a few pixels off their homes. The bake answers
with `plate`: a world rectangle given outright, which replaces the fitting that `fill`
and `size` do and sets one unit to one pixel.

That is a different kind of hand-tuning from the stars' exposure, and it is why these
two come after the families where the only loose thing was light. An exposure that is
slightly wrong makes a picture somebody may accept. A plate that is slightly wrong makes
a board that does not line up, and the failure is structural rather than a matter of
looking right.

Both are built rather than fetched — the booster tray is a cushion inflated from the
lobed card drawn beside it, the board tray a grid that could not come from a service. So
the geometry is already a declaration and what has to move is the framing contract.

The thing to keep is that the number comes from the game, not from the render. A port
that lets the picture choose its own rectangle has lost the point.

### §PW79 The simplest rig with the hardest bar

The brand marks are the one family where the rig is nearly nothing and the criterion is
nearly everything. Two blends produce three sprites — the Cottony logo is baked twice,
large for the title and small for the board's corner, because a sprite for each beats
one scaled for both — and the whole of the hand-tuning is `light`, at 1.0 and 1.18.

They are deliberately not first. A family with one constant looks like the easy port,
and it is, right up to the point of saying what a correct render is. A wordmark is type:
it either reads or it does not, and the failure is not a median drifting but a letter
losing its edge. Every other family in this list can be stated as a colour and a
contrast against something drawn; this one cannot, and taking it early would mean
inventing an acceptance vocabulary under the pressure of the first port.

By the time the stars, the props and the trays have moved, three bars exist that were
written to be read rather than admired, and the question here is narrower: what does a
search aim at when the subject is a shape that must stay legible.

The marks also leave markings off — a rope round the silhouette of a word is not a thing
this style has.

### §PW80 What a fetched object arrives wearing

The boosters are the first family whose hand-tuning is not about light at all. The
hammer and the wand came back from the service, and each needed three separate
corrections that no exposure search would have found.

The service painted edges it saw: a dashed dark line round the hammer's head, a dark rim
on the wand's star, both of which rule 2 forbids on candy and neither of which a prompt
saying so prevented. `scrub` takes them back out of the texture before rendering. The
hammer also returned standing upright where the drawing leans it, so it carries a roll
of -22 degrees, and leaning it widens its box, so its fill had to go up to 0.72 to keep
the drawing's size. Each of those three is a consequence of the one before it.

The shuffle ball is here because it is the counter-example: it is built rather than
fetched, after the service returned a ring instead of a ball. Having both in one task is
the point — what a fetched object needs and what a built one does not is the comparison
this family exists to make.

The risk being carried is that a correction found for one object is a correction fitted
to one object. A port worth having states what the correction is for, not the number it
landed on.

### §PW81 The five that are looked at, and go last

The friends and the mascot carry more hand-found numbers than the other seventeen
sprites together, and they are also the ones a player looks at. Both facts point the
same way: last.

Nothing here is only an exposure. The mesh is dressed in cloth drawn in Python and
projected from the camera, because the service's own texture did not read as cotton. The
face is composited on afterwards, because a sculpted face comes back as dents that shade
and never read as eyes. The mascot needs its sculpted face taken back out first at 0.9,
where 1.0 flattens the cheek's own light; it arrives in 34,391 pieces, so a dust
threshold of 0.01 keeps the head and the lower body while dropping the tongue inside its
open mouth. Its face centre was solved rather than chosen: measured at 0.444 of the
height, then moved up by 0.09 so the mesh's cavity becomes the inside of the mouth we
draw.

The lean frames are the same mesh squashed to 0.93 and re-rendered rather than scaled,
so the light stays where the light is while the body moves under it.

Every earlier family in this list is a rehearsal for this one. If the search cannot hold
here, the honest outcome is that these five stay hand-tuned and the rig shrinks around
them rather than disappearing.

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
ring), with cuts and holds. Plus an export the engine plays (a Godot Animation resource
on a Camera3D, with its record), and a capture per shot so a person accepts the framing
on the review page.

### §PW373 A shot that says when it was not written

Met in starship (RK190), shooting a cutscene's frames through a held game: `game.batch`
with `{"cmd": "shot", "out": ".polyweave/shots/opening/0.png"}`, where the folder
`opening/` did not exist yet. Every shot answered `{"out":
".polyweave/shots/opening/0.png", "size": [1280, 720]}` with `"errors": []`, and no file
was written. Only the session's log said so: `ERROR: Can't save PNG at path:
'.polyweave/shots/opening/0.png'` from the driver's `_shot`. The worker learned it when
`compose.sheet` refused the first tile as missing, then made the folder by hand and
drove the whole sequence again.

What polyweave should do: `game.shot` makes the folder `out` names (as every other
operation that writes does), checks that the file exists after the save, and where it
does not, answers a refusal (`driver.shot-not-written`) carrying the engine's error,
never an `out` for a file that is not there. A test shoots into a folder that does not
exist yet and expects the file.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

### §PW376 Verify answers for the project alone

Met in spinhold on 2026-10-07. `python -m polyweave provenance.verify` answered 46
`changed` and 11 `missing` entries, which read as the project's models and site pictures
having drifted from their records. Every one of them was a record under
`.polyweave/cost/trees/<commit>/...`: the checked-out copies `frame_cost.py` keeps of
older commits (`work / "cost" / "trees" / commit[:12]`). Their records are compared
against the project's current files, so any artefact rebuilt since that commit shows as
changed, and one moved since (art/vfx to game/vfx) shows as missing. The project's own
937 records were all fine. Telling the two apart took `--json` and a filter by hand.

What polyweave should do: `provenance.verify` skips the work area's copies of other
trees, as it skips any path that is not the project's own; a snapshot's record is
checked against the snapshot, if at all. Where the work area is walked on purpose, its
entries are reported apart from the project's, so `changed` and `missing` mean the
project and nothing else.

### §PW386 Targets for a contrast taken with the other measures

Spinhold RK200 measured how well a fight's targets stand out from the ring behind them.
`python -m polyweave measure.take --subject art/renders/legibility-neon.png --measures
'["contrast_min", "contrast_median"]'` is refused with spec.no-targets, whose remedy
says "pass targets, each {at: [x, y], radius} or {box: [l, t, r, b]}, or a log whose
lines say `target: <x> <y>`". But measure.take publishes no such parameter: passing
`--targets art/renders/legibility-neon.targets` is refused by the CLI as an unrecognised
argument, and `describe` lists subject, measures, region, alpha_floor, rung, root,
target, against, display and delta only.

The measure works inside an acceptance spec, where a predicate may carry `targets =
"<log>"` (accept.py's ARGUMENTS), and measure.contrast takes the same log as `--log`.
Learning that took reading src/polyweave/accept.py and contrast.py.

Expected: measure.take takes `targets` (a list or a log path) and `ring`, as the spec's
predicate does, so contrast_min and contrast_median can be asked for beside the other
measures; or the refusal's remedy names measure.contrast and the spec key, rather than a
parameter the operation does not have. Workaround used: measure.contrast --log for the
reading, and the predicate's `targets` key in art/accept/legibility-*.accept.toml.

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

### §PW180 Canon pictures as style references

PW166 declared a style as a palette and a skeleton, and a canon a person grows. Its
design also named `references`: which canon pictures go to the service as style
references, and one character reference per recurring character. That part did not land,
because no model this client sends to takes a reference picture together with a
structured prompt.

3.0 takes `style_reference_images` and `character_reference_images`, as uploaded files,
but only with a text prompt, and a text prompt has nowhere to carry the skeleton or the
palette. The 4.0 generate reference, read when PW166 shipped, lists no reference field.

**Build it where a model takes both.** Add `references` to `[style.<family>]`, naming
canon pictures by file name. Send them as repeated file fields: `_send` currently maps
one field to one file, so it needs a list. Record each reference's digest on the
picture's record, so a regeneration sends the same pictures. Until a model takes both, a
family with references should refuse a structured call rather than drop them.

Check first whether 4.0 has gained a reference field, and learn it by the schema probe,
since a reference the service ignores is dropped without an error.

## Block O — A person sees and answers

### §PW375 A sitting answered by name, from chat

Met in spinhold on 2026-10-07. Four sittings were open on the review page
(`art/review/title-life`, `rk190-opening`, `rk157-menu-sound`, `ptbr-screens`); the
owner looked at them and said in chat "está tudo certo, pode continuar" rather than
clicking each family's button. No verdict landed, and the agent had to carry it.

`verdict.judge` takes `members` (name, spec, new...), so carrying that sentence means
reading each `sitting.json`, copying every family's member list into a JSON argument and
calling judge once per family, then `verdict.record_answer` by hand so `verdict.answers`
sees it. The page does exactly that in `review.answer(root, body)`, which takes a
sitting and a family by name, but `describe` lists no operation for it, so the
workaround was a throwaway driver calling that internal function.

What polyweave should do: an operation, say `verdict.answer`, taking `sitting` (the
manifest the page lists), `family` (one, or every family when left out), `choice` and
`why`, which runs the page's own write for each. A family already answered is skipped
and named, not judged twice. The answer records the person's words as given, so the
ledger cannot tell a click from a sentence carried from chat, which is the point.

### §PW383 A transcription sheet a person reviews row by row

Found in spinhold (RK178): before any TOML is written, the agent writes a sheet from the
video (per stretch: second, side, count, formation, rail, ending) and the owner reviews
it, because a wrong count is cheaper to fix in prose. Today the sheet is free prose, its
lines do not say which frames they were read from, and the owner's corrections live only
in a conversation.

What polyweave should do:

- **A transcription sheet as an artefact**: a TOML or JSON whose columns the project
  declares, where each row cites the timestamp range and the frames (or track ids from
  §PW379) that support it, with a `.prov.json` naming the reference.
- **A sitting from it** through `verdict.sitting`: each row shown with its cited frames
  cropped beside it, so the owner checks a count against the picture without opening the
  video, and answers per row (right, wrong with the correct value, unsure).
- The answers carried by `verdict.judge` onto the rows, so a corrected count is recorded
  with who corrected it, and the sheet counts as accepted only when every row has a
  person's answer.

The agent never accepts its own transcription; this only puts the evidence beside each
row and keeps what the person said.

## Block P — Music and sound a game can ship

### §PW192 Cottony's audio made through polyweave

The block is proven when its first consumer uses it. Cottony's music and effects are
declared in its `polyweave.toml`, made by `music.render` and `sound.synth`, and held to
`*.accept.toml` bounds, and its own audio scripts are removed. Anything Cottony needs
that a second game would not becomes configuration.

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
the first twenty make.

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

### §PW379 Objects counted and tracked across a reference video's frames

Found in spinhold (RK178): rebuilding Resogun's first phase from a gameplay video needs,
per stretch, the second each group appears, its count, formation, rail and how it ends.
Even with `reference.frames`' frames and contact sheets, an agent counts twenty small
enemies by eye in each sheet, and a miscount reaches the written sheet the owner
reviews.

What polyweave should do:

- **`reference.objects`**: over `reference.frames`' frames, find what moves in the play
  area, each detection labelled by a kind the project declares (a colour range, a size, a
  few sample crops per kind), with its position and the frame it was seen in. No genre and
  no game built in: the kinds are the project's.
- **Tracks**: join detections across frames into tracks, each with its first and last
  second, its path and how it ended (left the frame, was destroyed, still alive at the end).
- **Groups**: tracks born within a short window and moving together are one group, with
  a count and a rough formation (line, ring, cluster).
- A JSON written beside the frames, with a `.prov.json` naming the frames and the kinds
  it used, and a contact sheet with each track's id drawn on, so the agent checks the
  data against the picture instead of producing it.

The transcription into the project's wave format stays the agent's and the owner's work;
this only turns pixels into counts and paths an agent can check.

### §PW380 Regions of a reference video, and its minimap read as positions

Found in spinhold (RK178): in Resogun the radar strip at the top of the screen shows the
whole cylinder, and it is the only place an agent learns what spawns off camera and on
which side. In a full frame it is a few dozen pixels high, so reading it by eye from a
contact sheet guesses more than it reads. The score, multiplier and humans counter sit
in fixed places too.

`reference.frames` offers a crop per call. What is missing is a declaration and a
reading:

- **Regions declared once** in `polyweave.toml` for a reference (say `[reference.<name>]`
  with `radar`, `hud`, `play` as rectangles in source pixels), checked against the video's
  resolution, so every later call names a region instead of repeating numbers.
- **Each region sampled and enlarged** on its own sheet, nearest-neighbour so the dots
  stay dots.
- **`reference.minimap`**: inside a region the project declares as a minimap, find each
  blip per frame and map it to a position on the declared shape of the map (a strip that
  wraps, for a cylinder; a rectangle, for a flat level), giving each blip's angle or
  position over time as JSON with its `.prov.json`. The player's own blip, declared by
  colour, is what the others are measured from, so "left" and "right" of the player come
  out as data.

Nothing here knows Resogun: the region names, the map's shape and the blip colours are
the project's declaration.

### §PW384 A reference registered and kept internal

Found in spinhold (RK178): the reference is a commercial game's gameplay, recorded by
the owner, and it must stay an internal reference: never committed, never published with
the site, and the frames taken from it neither. Today that rests on the agent
remembering to keep the files out of git.

What polyweave should do:

- **A reference registered, not copied**: `reference.register` records a video by path
  and hash in the work area (`.polyweave/references/`), with its duration, resolution and
  frame rate, and every later reference call names it instead of a path. A video whose
  hash changed is refused with a remedy.
- **Kept out of the repository**: everything derived from a registered reference (frames,
  sheets, tracks, timelines) is written under the work area and carries `internal: true`
  in its `.prov.json`. `provenance.verify`, and `project.check`, fail when a file tracked
  by git is derived from an internal reference, naming the file.
- **Kept out of what ships**: `capture.run` and `store.capsules` refuse an input whose
  record is internal.

This is about a project not leaking what it was given to study, not about deciding
whether a use is allowed; that stays the owner's.

### §PW381 A timeline of events read from a reference video

Found in spinhold (RK178): a gameplay video has no markers, so an agent reading it
stretch by stretch has nothing to anchor "the second wave starts here" except watching
frames. The game's own signals already say it: the score jumps, a counter of humans
changes, a burst of explosions fills the screen, a sound plays when a wave begins.

What polyweave should do, as **`reference.events`** over a reference video:

- **Numbers read from a declared HUD region** (§PW380) per sampled frame:
  score, multiplier, any counter the project names, with the frames where reading failed
  listed rather than guessed.
- **Visual peaks**: frames where the play area's brightness or the share of changed
  pixels spikes, marked as candidate explosions or screen flashes.
- **Audio onsets**: loud onsets in the soundtrack, and where the music changes section,
  using the audio measures polyweave already has for its own sound.
- One timeline JSON of all of these, in seconds from the start of the video, with a
  `.prov.json`, and a sheet that draws the timeline under the matching frames.

The agent then splits the video into stretches at those events and reads each stretch,
instead of finding the boundaries by eye. Which event means a new wave is the agent's
reading, not polyweave's.

### §PW382 A rebuilt level compared with its reference video

Found in spinhold (RK178): the deliverable is as much the list of places the rebuilt
phase plays differently from the reference as the phase itself. Today that comparison is
an agent looking at a capture of the game and the reference's frames separately and
remembering both.

What polyweave should do, as **`reference.compare`**:

- Take a reference video (with `reference.frames`' frames) and a capture of the project's game
  playing the rebuilt level (`capture.movie`, or a kept `game.replay`), and align them in
  time from an anchor each side declares (the first enemy appearing, an event from
  §PW381, or a plain offset).
- A **side-by-side sheet** per stretch: the reference frame and the game's frame at the
  same second, with timestamps on both.
- **Curves** from both sides on one chart: objects on screen per second (from §PW379
  on the reference, and from the game's own trace or the same detection on its
  capture), and, where `measure.pressure` has the declared wave, its pressure curve beside them.
- The seconds where the curves differ by more than a bound the call is given, listed
  with the two frames, so each gap becomes a line an agent can file.

polyweave shows and measures the difference; whether a difference is a bug or a choice
is the owner's call through a sitting.

### §PW385 Worlds of a tier held level

Spinhold made its shift a chart of worlds (RK210): tiers in order, each a choice of
worlds, and a run flies one path through it. Arcade's score table is one table, so every
world on a tier must be worth the same: the same whole threat within a band the owner
sets, and the same number of Holders to save, which caps the multiplier (RK212).

Nothing in polyweave answers that. PW330 measures one wave timeline's threat per second;
it does not total a world, count what a world gives to rescue, or hold one world against
another. Spinhold extended its own stand-in for PW330, dev/pressure.gd, with
`Pressure.level(world)`, which sums the owner's weights in game/waves/threat.toml over
the events of a phase's waves and counts its Gleaners as Holders, and with
`Pressure.unlevel(chart, rule)`, which names every world of a tier whose threat is more
than `[rules] tier_band` away from the tier's first world's, or whose Holders differ.
The check lives in dev/check.gd as check_routes_level.

What polyweave should do: an operation that takes several wave timelines declared as one
tier (or a chart's tiers) with the project's threat weights, reports each one's total
threat, peak and count of a named kind, and refuses any outside a declared band of a
reference, naming the world, its value, the reference and the band. A refusal should
carry the share it is off by. Then the project deletes level and unlevel along with the
rest of the PW330 stand-in.

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

### §PW374 Built effects land where the game ships

Met in spinhold (RK189). Its effect declarations live in `art/vfx/*.vfx.toml`, and
`art/` carries a `.gdignore` and is in the export preset's `exclude_filter`, as a
project's sources should be. `vfx.build --source art/vfx/trails.vfx.toml` with no `out`
wrote each scene beside the declaration, `art/vfx/<effect>.tscn`, the game loaded them
from there, and every check passed because the editor reads a text scene straight off
the disk. An exported build has no `art/`, so the first trail or title effect would have
stopped it.

The workaround: every call now passes `out=game/vfx`, and the declarations' header
comments say so. Nothing stops the next call from forgetting it, and a scene left beside
its source would load in the editor again.

What polyweave should do: let `polyweave.toml` name where a project's built effects go
(a `[vfx] out`, as other kinds bind their folders), used whenever a call passes no
`out`. Where neither is given and the source sits under a folder the project's Godot
export leaves out (a `.gdignore`, or an `exclude_filter` in `export_presets.cfg`),
refuse with a remedy naming `out`, rather than writing a scene the shipped game cannot
load. PW363, which launches an exported build, would catch the result; this catches it
at the build.

### §PW387 A style borrowed from another project

Spinhold RK201 declares a style for a ring drawn in another game's colours: the Quilt is
Cottony's world, so `[style.quilt]` in spinhold/polyweave.toml should take its palette
from Cottony, not from a copy that drifts.

`python -m polyweave style.read --root D:/Git/viglet/cottony` answers family "default"
with an empty palette and skeleton: Cottony declares no `[style]`, because its palette
lives in its own tools/art/palette.py (the single source its art generator and
scripts/pieces.gd are checked against). A style also has no field that names another
project's style or palette, so Spinhold cannot say "Cottony's palette, at dusk".

Workaround: spinhold/polyweave.toml's `[style.quilt]` holds a snapshot of Cottony's hex
values, with a comment naming palette.py and the date it was copied. Nothing tells
Spinhold when Cottony's palette moves.

What polyweave should do: let a style borrow from another project's style by reference
(`from = { root = "../cottony", family = "..." }`), with a transform for the borrowing
game (a value shift for dusk, say), and let style.drift report when the source moved;
and give a project whose palette lives in code a way to declare it as a style, so a game
like Cottony can be borrowed from at all.

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

### §PW377 The decision screen drawn natively, from typed operations

PW305 hosts the review page in an iframe, which keeps one verdict path, but the window
cannot draw the decision screen itself. Half of what the page shows is no operation: the
sitting list (`review.sittings`), gate lanes with ceilings (`review.looked_at`),
turntables, the canon board (`style.board`), the old/new difference and the stale-code
check. Its write, `review.answer`, turns drawn boxes into a mask tied to a digest before
`verdict.judge`, and that is no operation either. In the owner's screenshot the page
also spoke English inside a pt-BR window.

Build, in parts:
1. Operations for every fact: `review.state` (the `/api/state` payload),
   `review.compare`, and `review.answer` (masks, then `verdict.judge`, refused on
   stale code as the page is).
2. A typed SDK: `gui/packages/core/src/operations.generated.ts`, generated from
   `describe` (parameters, ranges, choices, payloads), with a test that fails when it
   is stale, like `site/src/lib/roadmap.generated.ts`.
3. The decision screen in React with viglet in `gui/packages/ui`: cards, mask drawing,
   compare, sentence, lanes, canon. `tests/test_review_page.py` is the checklist of
   behaviour it must keep (PW287 to PW293).
4. One implementation: the same bundle, built into `src/polyweave/review_page/` and
   checked fresh by a test, is what `python -m polyweave review` serves. The browser
   and the window then run one code, which is what PW305 protected.

The iframe and `?member=` stay until step 4 lands.

### §PW378 A revision's shell writes seen too

PW309 holds a revision's session to its item through the revision's `PreToolUse` hook,
which sees the file a `Write`, `Edit`, `MultiEdit` or `NotebookEdit` names. A shell
command names no file the hook can read, so `sed -i` on `polyweave.toml` or a script
that rewrites a canon goes through without the question, and the closed revision's
`touched` list does not name it either.

Build: while a revision's session runs, the window watches the project root recursively,
as roadkeep's session watch does (RG247), ignoring the plugin's work area. A change
outside `_scope` that no hook announced appears in the conversation as a write outside
the item, naming the file and why, so the person can tell the session to undo it. The
revision gets a `touched` event for it, so the close lists it. A Bash write cannot be
paused before it lands, so this answer comes after the fact, and it says so.

A test runs the fake claude with a shell write outside the scope and expects both the
line in the window and the file in `touched`.

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
two.

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

What Cottony needs that the kits lack is filed as friction and fixed in the kits. Done
when Cottony carries neither file, its own save test is replaced by the kit's
acceptance, a save written by the current release loads after the swap, and its gate
passes.
