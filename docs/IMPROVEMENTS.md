# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

### §PW141 A render answered as two digests

A bake answers with its measurements, and `measure.same` compares two renders within the
rung's noise floor. Both answer the question they were asked. Neither leaves behind a
short answer that a later session can compare without the pictures: whether the outline
moved, and whether only the surface did.

Shio's render digest splits exactly there. It keeps a structural hash and an appearance
hash, so "I restyled it" and "I broke the outline" are different answers, and it keeps
its markers out of both, so that a warning appearing does not read as a change of shape.

Here the bake adds a digest to what it returns and to its record. It contains the
silhouette's box and footprint anchor, coverage, luma at the fifth, fiftieth and
ninety-fifth percentile, which is the percentile rule Cottony's pipeline already judges
by, the palette per declared slot and the triangle count. It adds `shape_digest` over
the silhouette figures quantised at the rung's noise floor and `look_digest` over the
tonal and palette figures, so a render that moved only by noise keeps both hashes. The
PNG stays the artefact for a person.

### §PW145 A rung's size is not in the cache key

`render.bake` computes its cache key from the request's `params`, the engine record, the
inputs, the rung, the seed and the sample count. The size of a picture that declares no
world rectangle comes from `[render] preview_size` or `final_size`, and neither is in
any of those. So a project that changes `preview_size` from 256 to 128 and bakes the
same request again is served the 256 px picture from the cache, reported as a hit, and
every measure on it answers for a size nobody asked for.

Found building PW107, which had to put an explicit `size` override into `params` so its
variants key apart. The rung's own size never got the same treatment. engine.md says a
bake that declares nothing "keys exactly as it did", which is true, and that is the
problem.

The fix is to key on the frame that is actually drawn: put the resolved `(width,
height)` into the planned record (as `params["frame"]`, or a top-level field `cache_key`
reads) for every bake, not only the ones that override it. Every existing key changes
once, which the cache survives, since a miss only costs a render. The test is to bake
one request, change `preview_size` in the project file, bake it again, and see a miss
with the new size.

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

### §PW118 A capture that knows what the game loaded

After the stars moved, all four of Cottony's captures reported the same settings making
a different picture, "so something this picture depends on is not declared". It was true
and it did not help: what moved was four sprites, and finding that took a script diffing
the old and new screenshots by hand. `capture._record` passes no inputs, not even the
script, so the record cannot name what changed.

The engine can say what it loaded. A capture run records every resource path the game
opened, from the verbose load log or a probe on the resource loader, and hashes each
file into the record's inputs through `source` in `provenance.py`, which already exists
for renders.

Then a `differs` can name its cause: the inputs whose hashes moved since the record
beside it, and only when none did does it fall back to blaming something undeclared. A
changed sprite becomes an explanation, and a truly unexplained difference stays the
alarm `reproduced` in `provenance.py` meant it to be.

### §PW119 From a changed file to the artefacts that show it

When the stars changed, which of Cottony's four screenshots would change was a guess, so
all four were re-taken and diffed to find out. A project with forty captures cannot do
that, and one that re-takes too few commits a screenshot that no longer shows the game.

Once captures record their inputs (§PW118), every sidecar in the project is an edge from
an artefact to the files it was made from. A reverse read over them answers the question
directly: given a changed file, the artefacts whose recorded inputs include it, captures
and renders alike, with the command each was made by.

That is a read over sidecars already on disk, needing no index and no service, and the
same walk `verify` in `provenance.py` makes. It lets a port say "these three captures
show this sprite" before re-taking them, and lets a gate fail when a file changed and an
artefact that depends on it did not.

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

### §PW114 The claim is about the second change, not the first bake

The stars' ledger says the work was not reduced: 8.6 s the new way against 3.3 s the
old. It will say that for nearly every family, because the before side is a re-bake with
the constants already found, and a re-bake is always cheap. The old rig's cost was never
the first bake. It was the afternoon that found the constants, and it comes back every
time something they were tuned against moves.

So the comparison that tests this plugin's claim is a change, not a port. A perturbation
run names one change to an asset that has both ways recorded: a hue in the palette, a
sample count, a renderer version, a geometry parameter. Each way then has to get back to
an accepted look. The plugin's way is a search against the unchanged spec; the old way
is a person retuning the constants, timed as it happens and recorded in person-minutes.

The verdict wording in `docs/specs/adoption.md` stays as it is, including the case where
the plugin loses. What changes is which event it is about, and a ledger that can only
ever measure the first bake cannot falsify the claim either way.

### §PW115 A run recorded rather than reported

`loop.spent` adds whatever its caller says. Recording the stars, the caller charged 32
renders when 28 were rendered, because the four final bakes were the checked pictures
handed back by the cache. The mistake was caught by reading the log, and it went against
the plugin; the next one could go either way, and the ledger is append-only.

`render.bake` already knows: every answer carries `cached`. So a run can be recorded
rather than reported. While a run is open, each bake reports into it, counting fresh
renders and cache hits separately, with their seconds. The caller still judges the run
and closes it, and `spent` stays for what the plugin cannot see, such as a service call
made elsewhere.

A cache hit is not free and not a render, and the ledger should show both numbers, since
a loop that is fast because it repeats itself is the very thing the loop ledger was
written to catch.

### §PW116 What a side did not measure, said as data

Every before side in Cottony's ledger carries the same sentence in its brief: the hand
work that found the constants was never timed, so this side understates the old cost.
`compare` does not read briefs. It sums the numbers as if both sides were complete and
returns a verdict, and "the work was not reduced" is the one it returns for the stars.

A run can declare what it did not measure, by name: `seconds` for the hand search, or
`renders` for work done before recording began. `compare` then says which verdicts the
missing numbers make unreachable. A side with its seconds unmeasured cannot support "no
faster" or "faster"; it can still support the overruling verdict, which only needs the
counts it has.

The same change adds the number the plugin is really about: person-minutes, recorded by
whoever gave the verdict, beside the machine's seconds. The stars cost a person one
sentence, and today the ledger has nowhere to say it.

### §PW117 A second adopter while the boundary is cheap to move

`docs/specs/adoption.md` records that no key had to be added for Cottony, and calls it
the boundary holding. It is the boundary holding for one project. The features of this
block and the last were shaped by Cottony's numbers: a plate at `CELL` pixels, a
`covers` rectangle placed from the board, lights scaled by the square of the subject for
its two star sizes. Each is general in form; none has been used by anybody else.

A second adopter does not need to be a game, only different. This repository's own site
has pictures, and a small fixture project with another unit, another scale and no Godot
would stress the config in the places Cottony never pushed. What to record is the same
as §PW36's: every key it had to set, anything that needed a change inside the plugin,
and anything that turned out to be Cottony's shape compiled in, which the non-goal
already calls a defect.

The point is to find those while they are cheap, before Block H closes and the claim
that the boundary holds is read as settled.

### §PW120 A family stated, not scripted

Cottony has three port scripts, `search_stars.py`, `frame_trays.py` and
`ingest_boosters.py`, about a hundred lines each, and they are one skeleton: build or
ingest the models, search or place them against their specs, check the rest, bake the
accepted ones where the game reads them, and record the run. Every later family (PW77 to
PW81) would be a fourth, fifth and sixth copy, each with its own small mistakes, such as
a cache hit charged as a render.

A family file states what differs: the members, each with its spec, its model or
declaration, what its render fixes and where it is baked; the axes shared; whether the
rig is searched, placed or given. One port operation reads it and runs the skeleton,
using the family search (`search.family`, PW105), recording into the ledger as it goes
(§PW115), and baking only when every member passes.

For the caller this plugin is designed for, that is twenty lines of TOML instead of a
hundred of Python, and a port that reads the same across families. The scripts that
exist stay until their family is re-expressed; the point is that the next one is never
written.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

### §PW109 One sheet to look at, one call to answer it

The stars waited a day for one sentence from a person, and to get it an agent had to
point at `.polyweave/stars/compare.png`, explain a 99th percentile against a ceiling,
and then edit a spec comment and a ledger entry by hand from the reply. The judgement
was quick; everything around it was not.

A review sheet is one PNG per family: for each member the old artefact beside the new
one at the size the game shows it, the crop of the latest capture where it stands if one
is recorded, and under each the predicates that failed in words, with the origin of the
bound (PW106, in `docs/specs/acceptance-spec.md`). The two readings are stated as
choices: the look is wrong, or the number is.

A `judge` operation takes the family and one of those choices with a sentence. It writes
the person's verdict into the loop ledger with the values (`loop.judged`'s `check` and
`named`, in docs/specs/adoption.md), and where the number was wrong it rewrites the
bound with origin `person`, the date and the sentence. One reply becomes one call.

A sheet and a command, never an editor, so "A graphical editor" is not touched: the
person looks at a picture and says one word, and the agent does the rest. Nor is
"Spending money on the agent's own judgement": the verdict stays the person's, and the
agent only carries it.

### §PW110 A person's time asked for once

Six of Cottony's families (PW77 to PW82) are set aside for a person's look, and they are
chained, so each one is prepared, presented and answered before the next is even
rendered. A person who could judge all six in ten minutes is asked six times over
several days.

Pending is a read over what is already on disk: the loop ledger, the specs and the
sidecars. An asset is pending when it has a candidate made the new way and no person's
verdict on it. The answer lists each with its state, which is the row §PW59 needs
anyway: made by the old way or the plugin, spec present, before side recorded, after
side recorded, waiting on a person.

With the list, candidates can be prepared ahead of the verdicts they wait on, as far as
their dependencies allow, and every pending sheet (§PW109) is gathered into one sitting.
Verdicts come back as a batch of `judge` calls. The queue does not decide anything and
does not reorder the chain; it makes sure a person's time is asked for once, not once
per family.

### §PW111 The specs as a gate, with no render

`[paths] specs` is declared, defaults to `docs/accept`, and is read by nothing. A spec
is consulted only while a search runs, so the four star specs Cottony now carries stop
protecting the stars the moment the search exits. A sprite overwritten by a generator,
or re-exported by hand, is not checked against the bar it was accepted at.

Checking needs no render: `accept.check` measures any PNG. So a verify walks the specs
directory, finds each spec's artefact, checks it at the rung the spec states, and
returns one verdict per spec with the predicates that failed, shaped for a CI job to
fail on. That is the gate §PW57 reduces Cottony's five check scripts to, available
before any of them move.

The spec needs to say where its artefact is. Today the `asset` name is all it has and
the artefact path is in the caller's script. An optional `artefact` field, relative to
the project, is the smallest addition; without it the verify reports the spec as
unanchored rather than guessing a path from the name, which would be one project's
layout compiled in.

### §PW112 The same bar, on the screen the player sees

Cottony's style guide says it outright: once the game loads a mesh, the Godot material
is what the player sees, and the bake becomes a reference. Its `material_match.gd`
exists to measure the gap by hand. Every spec here is checked against a Blender render,
which is the intermediate artefact, and the picture on screen is never held to the bar
at all.

The plugin already has the three pieces. `capture` takes the screen, `accept.check`
takes any PNG and a region, and the measures do not care which renderer made the pixels.
What is missing is saying where an asset stands in a capture: a capture declares named
rectangles, and a spec may be checked against one of them as well as against its bake.

So the same spec gets a second answer, on screen, and the two can disagree. A sprite
that passes baked and fails in the capture means the engine is drawing it differently,
which is the finding `material_match.gd` was built to make and could only make for one
star. The bar stays one file, so moving it moves both checks.

### §PW113 Is the spec wider than the renderer?

Nothing in the acceptance spec is 3D. A predicate is a measure over a region of pixels,
and `accept.check` takes a PNG from anywhere. Cottony already writes the same kind of
bar outside this plugin, three times: `check_vivid.py` holds the board's saturation at
the 99th percentile, `loop_music.py` fails a loop whose seam stands out spectrally, and
`make_assets.py` draws 2,406 lines of 2D sprites with no bar at all.

§PW59 puts that 2D generator outside the denominator on purpose, because this plugin is
geometry, surface and motion in three dimensions. That is a scope decision, and this
line asks whether it still holds for the spec alone: the renderer stays 3D, but should a
drawn sprite, a screenshot or a sound be held to a spec in the same format, searched
where it has parameters and checked where it does not?

Answering yes widens the measures (audio has none) and nothing else. Answering no is
worth writing down as a non-goal, so the next agent that notices does not file this
again.

## Block K — Reached without reading the source

### §PW123 A typo is not a file that is not a shape

`build_all` in `cli.py` reads each `*.toml` under the folder and, on any
`PolyweaveError` from `G.read`, continues, so that a project config, a spec or a lock in
the same tree is passed over. The same except clause catches `geom.unknown-field`, the
refusal that section 3 of tool-surface.md exists to guarantee: a declaration with a
misspelt key disappears from the build, nothing is printed, and the exit status is 0. A
project's asset step is one line, `build --all`, so this is the path an agent actually
runs, and it is the path where a typo is least visible.

The two cases differ before any refusal: a file that is not a shape carries no shape
table at all, and a shape that fails carries one and fails inside it. So the walk
decides *is this a declaration* from the document's top-level keys, skips only the files
that are not, and answers a declaration that fails with the same `refused` entry a
single build gives, with a non-zero exit. `test_cli.py` covers only the non-shape case;
the missing test is a folder holding one good declaration and one with an unknown key.

### §PW124 Every operation declared, and the census before the fixes

`describe.MODULES` is `("polyweave.render",)` and `@operation` decorates one function in
the package. `capabilities()["operations"]` therefore lists the bake, and the rest of
the surface an agent needs, from `search.run` to `geometry.build` and the voxel checks,
is known only to a reader of docstrings. That is the failure CLAUDE.md names: a feature
that needs a source read to use has not landed.

Shio's lesson (SH338) is about order. Eleven of its lints guarded internal consistency
and none guarded reachability, so a consistency defect became a permanent guard and a
reachability defect a one-off fix that came back. `test_errors.py` here is the same
shape: it proves every code is declared and used, and nothing proves an operation can be
found.

So the instrument lands first. A test walks the public functions of the plugin's modules
and classifies each as a registered operation or as an entry in an exact list of
exceptions, each with its reason; an exception that is no longer needed fails too. A
second test starts from what `capabilities()` returns and asserts every operation, code
area and measure is named within two reads. Then the operations are registered, one
module per commit, against a list that can only shrink.

### §PW125 A command line derived from the registry

`python -m polyweave` answers `build` and nothing else. `capabilities`, `explain`,
`describe`, the job verbs, `search`, `accept.check`, `verify`, `sweep` and
`godot.install` are reachable from Python only, so an agent in Cottony that wants to
know whether Blender is present writes and runs a script, and a person reading its
transcript cannot tell the question from the answer.

Once every operation is registered (§PW124), its declaration already says everything a
subcommand needs: the name, each parameter's type, range, default and sentence, and
which parameters are required. So the command line is derived from the registry rather
than written beside it, one subcommand per operation, and a parameter added to an
operation is a flag without a second edit.

Roadkeep paid for doing this late. Its verbs printed text and JSON from separate code
until one migration, forty commits long, made each handler return one answer object that
both renderings read. The cheap version is to start there: an operation returns data,
one renderer prints it, `--json` prints the same fields, and a test asserts that the
text never says something the JSON lacks.

### §PW126 A served surface that is a shape over the registry

Roadkeep moved to a served surface on its second day, because arguments written in prose
are guessed; the plugin here has none, and its `.mcp.json` serves only roadkeep. An
agent reads a skill or a docstring, composes a call, and learns the range of `elevation`
from `op.out-of-range`.

The same registry that yields the command line (§PW125) yields a tool per operation:
`description` from the operation's docstring, one property per parameter with its
sentence, `minimum` and `maximum` from the declared range, `enum` from its choices, and
`additionalProperties: false`, so a misspelt argument is refused by the client. A call
runs the operation in-process and answers with the fields `--json` prints. Nothing about
an operation is written a second time, which is Shio's tenth law: the server is a shape
over the services, never a third contract.

Two budgets come with it from the first day, because both projects that went before paid
for adding them late: characters per tool and for the whole list, held by a test, each
raise argued where the number is set. A tool whose operation needs Blender is listed
only where `capabilities` found one, and still answers elsewhere with the refusal that
names what is missing.

### §PW127 A door is a call, and every door is run

`PolyweaveError` refuses a code without a remedy, which is stronger than either sibling
project began with. What it cannot check is the remedy itself: "pass `glaze: {roughness:
0.22}`" names an argument by memory, and when that argument is renamed the sentence
keeps offering it. Roadkeep lived with this for four hundred commits, one call site at a
time, before one type turned a command into text and a census ran every door it could
build.

So a remedy that names a call carries it as data: the operation and the arguments filled
in, plus a blank where only the caller can supply the value. The prose is rendered from
that, as a command line, a tool call or a Python call, whichever surface asked. The
codes table's `doors` take the same form.

The census that holds it parses every complete door against the derived command line
(§PW125) and fails on an operation or a flag that does not exist. It also takes the
lesson Shio pinned as SH1074: where a refusal teaches a form, a test asserts that the
form it teaches is accepted.

### §PW128 The four fields a refusal is missing

The wire form is `code`, `message`, `remedy` and `detail`. When the refusal is about a
name, the set of names that would have worked is known at the raise site and thrown
away: `config.py` runs `difflib` and folds the result into prose, and
`geom.unknown-shape` or an unknown measure says only what was not found. An agent then
reads the source or guesses again.

Shio's teaching errors carry four more fields, each omitted when empty: `allowed`, the
sorted set the value is checked against; `did_you_mean`, the nearest of them; `example`,
the smallest correct fragment; and `at`, a path into the document, such as
`parts[3].bevel`. Its rule for the suggestion is worth taking whole: case- and
separator-insensitive, deterministic on ties, and silent when nothing is close, because
a wrong guess costs more than none.

A test holds it: every raise under a code whose meaning is an unknown name passes
`allowed`, and every `example` a refusal prints is accepted when fed back.

### §PW129 A ceiling on the reads every session makes

Registering every operation (§PW124) is the right move, and it multiplies the size of
`describe()` and of `capabilities()`, which carries it. Both are read at the start of a
session, so their size is paid on every one. Shio treats tokens as a measured budget: a
properties file sets a ceiling per response and per tool, a test estimates at four
characters a token, and a raise is argued in the file where the number lives.

Here it is one file under `tests/`: ceilings for `describe()`, `capabilities()` split
into the cheap check and the probe that renders, the largest error a code can produce,
the `--help` of each verb, and the answer of a search run. The test prints its table on
a green run too, because a figure seen only when the build breaks goes stale. Headroom
is bounded by the smallest regression the test must catch, never a flat percentage, so
an eleventh operation with a padded description is refused and a typo fix is not.

### §PW130 A canonical task, and a naive client beside it

The plugin's claim is about an agent's first call, and no test makes a first call. Every
test was written by someone who had read the implementation. Shio found its worst class
this way: an unrecognised argument reported success and did something else, and only a
client written to use plausible wrong names counted it.

Two instruments, both cheap. A canonical task, "declare a small prop and reach a passing
verdict", is driven through the derived command line (§PW125) and counted in calls,
renders, cache hits and estimated tokens, with an exact figure for calls and a loose one
for the rest. A naive client then replays it with the spellings a model reaches for
first, such as `size` for `extent` or `samples` as a string, and asserts that each one
is refused with an `allowed` set, never accepted and ignored.

Shio retired its headline ratio because the baseline got leaner and the ratio fell with
no change to the agent's path. So the floors here are per mechanism: what the cache
saves, what a preview rung saves, what a parallel search saves.

### §PW131 An asset's brief in one read

Roadkeep's `brief` starts a task in one call, and Shio's context pack replaced the reads
a session opened with. The unit here is an asset, and its state is spread over the
geometry declaration, the acceptance spec, the provenance record beside the artefact and
the loop ledger.

`polyweave brief <asset>` answers in one bounded payload: the declaration as one line
per part; each predicate of the spec with its bound and where that bound came from,
which PW106 now records; the last verdict and which predicates it failed; whether the
artefact on disk still matches its record; the cache entries held; what the budget has
left if the asset was bought; and, from the codes table, the doors for the failures it
names. A `digest` over the whole answer lets a session that already holds it ask whether
anything moved.

It is a read over files that exist and writes nothing, so it can land before the rest of
Block J, whose verdicts it will later report.

### §PW132 Installed as a plugin, and announced in one line

Everything under `.claude/` here serves a session changing this repository: the roadkeep
skill, the audit, the scanner and verifier. Nothing serves a session driving the plugin
from another one. Cottony installs it from a pinned commit through `requirements.txt`,
and its art-pipeline skill never mentions it.

Both sibling projects answer this the same way. A `.claude-plugin` manifest, with this
repository as its own marketplace, carries a skill for a *driving* session: a short
orientation built around the loop of four calls (brief, build, search, check) with the
rest on reference pages opened on demand, and size ceilings held by a test. Shio's rule
keeps the two sets apart: a plugin skill serves a session driving the tool, a project
skill a session changing it, and no name appears on both sides.

A SessionStart notice of one line, under a character budget a test holds, says which
declarations and specs this project has and which call answers instead of opening them.
A launcher that finds the engine, as roadkeep's does, reports which copy answered, since
Cottony's pin and the editable install on this desk are already two copies.

### §PW133 The declaration is the source, and the guard says so

The plugin's premise is roadkeep's in another material: the declaration is the source
and the mesh is derived from it, just as a roadmap line is derived from its fields.
Roadkeep holds that with a hook, not a rule in a skill. A `Write` or `Edit` on a
governed file is denied, and the denial names the command to run instead.

The same hook fits here. A `PreToolUse` guard denies an edit to a file that has a build
stamp or a provenance record beside it, and names the declaration to change and the
`build` to run. A `Stop` hook checks only the artefacts this turn touched against their
records, which is the at-the-write form of the check §PW111 asks for.

Roadkeep's constraints come with it. The screen before any import uses the standard
library only, so numpy and Blender are never loaded to decide a write. Any failure
inside the hook allows the edit. A shell command gets `ask`, not `deny`, because nobody
parses it to see what it writes.

## Block L — What a run leaves as evidence

### §PW134 One gate that keeps its log and stamps what ran

`python -m pytest` with `-q` prints a count and a dot per test. On a machine without
Blender the whole render path skips, and "passed" says nothing about whether a picture
was drawn. Shio met the same thing with its database tests, which report zero seconds
without Docker, so a green verify claimed a proof it never made.

A small script runs the gate instead of the bare command. It does four things:

- keeps the whole output in a fixed-name log, and copies a red one aside, because the next run, made to see whether it reproduces, truncates it
- writes an untracked stamp with the commit, the exit code, and the counts passed, failed and skipped
- counts the real-renderer tests that actually ran, so "Blender tests: 0 ran" is part of the result
- holds a lock while it runs

The lock is there because two overlapping runs share `.polyweave/`, and Shio measured
what that costs: a false red of three errors against a tree that was green. The exit
code always survives; a gate piped into `grep` reports `grep`'s.

### §PW135 A log is evidence, not source

`.gitignore` covers the plugin's working state, the Python caches and the build output,
and nothing an agent writes while it waits on a gate. The suite takes about five minutes
with Blender and Godot present, so an agent runs it in the background and redirects it
to a file it reads afterwards. Shio's root holds seventy-four such files, and the rule
that ignores them was added only after one was committed with the fix it was taken for,
because the commit tool stages the whole tree.

The fix is one line, `/*.log`, plus the directory the gate stamps of §PW134 will use. It
goes first because it is the cheapest item in this block, and every other item here
writes a file of this kind.

### §PW136 The gates run where the pin is read

`.github/workflows` holds `roadkeep.yml` and `site.yml`. The suite and the linter run
when someone types them, on a machine that has Blender and Godot, and nowhere else.
Cottony's `requirements.txt` installs this repository at a commit hash, so its CI builds
against code that no machine but this desk ever tested, while the editable install here
means the pin is never exercised locally either.

A workflow runs ruff and the suite on the lowest and highest Python the plugin supports.
Without `bpy` or `$GODOT` the render path skips, so the job prints the gate stamp of
§PW134, including how many real-renderer tests ran, and the summary says outright that
CI proves the pure half. Whether a runner gets Blender is a later decision with its own
cost; a green job that claims less than it proved is not.

The same job runs `claude plugin validate` once §PW132 ships a manifest, as roadkeep's
gate does against a pinned CLI.

### §PW137 A status is derived, never typed

`prerender.test.mjs` fails unless the landing page states that there is no
implementation, and `site-content.ts` says so. `README.md` lists eight blocks and says
the rest is design, `CLAUDE.md` says Block A has started, the specs index calls three
specs ahead of code that shipped as PW8 to PW12, and `capabilities()` still names PW14
and PW23 as pending. The test that was written to keep the page honest now keeps it
wrong.

Both sibling projects reached the same rule. Roadkeep's site commits nothing generated
and builds every figure from the CLI. Shio fails a build on a number in its agent
documents that does not cite the run that measured it (SH974). Here the roadmap module
is already generated; what is typed is the claim about status.

So the page and the README take the status from roadkeep's block list, which already
says which blocks are finished, the test asserts the page agrees with it, and the
`pending` entries are dropped once a test finds that the line they name has shipped.

### §PW138 The specs read against the code

Section 3 of tool-surface.md lists the areas a code is namespaced by: twelve of them.
`codes.AREAS` declares nineteen; engine, units, capture, rig, clip, texture and loop
were added with their lines and never reached the spec. No test reads a spec file for
names, except one that parses the acceptance-spec example, and the geometry test copies
its tray out of `geometry.md` rather than reading it.

Shio's docs gate is the model. For each kind of name a document may spell, a reader
extracts it from the documents and another from the source, and the test fails on either
difference. Here the kinds are error codes and areas, registered operations, measures,
config keys and CLI flags, read out of `docs/specs/*.md` and the published skill.

Two of its rules are what keep it honest. Each reader is tested against a fixture that
plants a name only it can find, and a reader that finds nothing throws instead of
passing, because an empty population makes every check against it pass.

### §PW139 A capacity check held until the record exists

`JobStore.start` counts the jobs that are not terminal and refuses with
`job.at-capacity` at the bound, then allocates an id, writes the record and spawns the
worker. Between the count and the record nothing is held. A search in parallel starts
its samples in a loop, and two sessions on one project, which roadkeep and Shio both run
as a matter of course, can each count three of four and each start a fourth.

Roadkeep fixed its version by holding one lock from the read that decides to the write
that records: an `O_EXCL` lock file keyed on the project, a token so only its owner
releases it, and a stale lock reaped after a bound. The same lock here spans the count
and the record. The spawn can happen after release, because the record already counts.
The test starts two jobs on threads against a bound of one and expects exactly one
refusal.

### §PW140 One answer to what a build was made from

The `stamp` function in `cli.py` hashes the declaration, the `--set` values and every
file the document names. It does not hash the plugin's version, so after a fix to the
builder `build --all` answers `cached` and keeps the output the defect produced. It does
not hash `--preview`, so a second run that asks for a preview returns before writing
one.

Beside it, provenance defines a cache key for renders, and `verify` walks `paths.meshes`
for `.glb` files. The geometry build and the voxel writer produce `.glb` files without a
record, so a project whose meshes directory holds them is told its own outputs are
unrecorded.

Roadkeep's rule applies: a list a second place has to be joined to is derived from the
first. The build writes a provenance record like every other producer, the stamp becomes
that record's key with the plugin version and every flag that changes an output in it,
and one test builds twice across a changed version and expects a rebuild.

## Block M — What a game needs beyond the look

### §PW142 Draw the skin, keep the volume

The Godot addon of PW102 reads `<name>.voxels.json` into packed arrays and offers
`multimesh()`, which sets one instance per entry in `centres`. The file already carries
`depth` per cell, 1 on the surface, because a hit chips cells in that order. A solid
model eight cells across has 512 cells and 296 on its skin, so the helper draws about
1.7 times what can be seen, and the ratio grows with the cube of the size.

The helper can draw only the cells at depth 1 and expose the rest for the game's own
shattering, which needs them. When a hit removes surface cells, the ones beneath are
revealed by depth, which is the order the data already states.

It is an idea and not a measured failure: no Cottony model has been profiled, and how
the game draws stays the game's own code, as the addon says. What would promote it is
one frame time measured with and without the buried cells on the target device.

### §PW143 A cost bar beside the look bar

An acceptance spec is a set of predicates over measures, and every measure today reads
pixels. The plugin already knows the numbers a game pays at run time, because the
post-conditions of section 2 of tool-surface.md measure them: the face count of a mesh,
its material slots, a texture's dimensions and bit depth, and the cell count of a voxel
model. None of them can be a predicate.

So the measures gain a cost family, read off the artefact rather than the render:
triangles, materials, draw calls implied by them, texture memory, and cells drawn. A
spec bounds them like any other, `triangles <= 1200`. A search that finds a better look
at twice the cost then answers with the predicate it broke rather than a pass.

It is an idea: Cottony bakes most of its art to sprites, where the cost is the sprite's
and not the mesh's. The voxel models that Block I brought to Godot are the first
artefacts drawn as meshes in the game, and they are where a first bar would be measured.

### §PW144 A rig as data a project can apply

Shio's blueprints are appliable starting points. A package reuses the formats that
already exist, takes named parameters with no conditionals, is validated when it loads,
and carries a `verify` promise that runs after it is applied. Re-applying it with the
recorded parameters reproduces the result.

The nearest thing here is the rig a search settles on, and today it is not kept. PW76
made the stars a search rather than a set of constants: `search_stars.py` fits the rig
on one sprite with a budget of sixty renders, checks it on the other three and bakes.
The rig it found exists only in that run's answer, so the next run searches it again,
with the cache as the only thing standing between that and sixty renders. The half the
search may not turn, the fixed angles, the material and the cell size, sits in the
script as constants.

A recipe would be a directory holding a geometry declaration with parameters, the rig
the search found as data together with its fixed half, an acceptance spec and the
measures that must pass after apply. `apply <recipe> --set height=0.6` builds, bakes and
checks, re-searching only when a check fails, and records the recipe and its parameters
in provenance. It is an idea that PW120's port skeleton and PW117's second adopter would
each test.
