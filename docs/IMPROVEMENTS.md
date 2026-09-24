# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

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
using the family search (§PW105), recording into the ledger as it goes (§PW115), and
baking only when every member passes.

For the caller this plugin is designed for, that is twenty lines of TOML instead of a
hundred of Python, and a port that reads the same across families. The scripts that
exist stay until their family is re-expressed; the point is that the next one is never
written.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

### §PW105 One rig for the whole family, or the conflict that prevents it

`search()` takes one spec and one evaluator, so Cottony's stars were fitted on the 96 px
gold and the other three were checked afterwards in hope. That is the right test of a
found look and the wrong way to find one: the rig that holds on all four was reachable
directly, and when none did, the search could only say the fitted one failed elsewhere.

A family is a list of members, each a spec plus what its render fixes (colour, size,
model), sharing the searched axes. One sample renders every member, and its score is the
worst member's, so the search climbs towards the rig the whole family accepts. Members
can run through `search.in_parallel` since they are independent renders.

When no sample passes on every member, the answer is the conflict, not a score: the pair
of predicates on different members that no sample satisfied together, and the nearest
sample to each side. "No rig satisfies the gold's median tone and the dim's hot facet at
once; here is the closest to each" is exactly the question a person has to answer, asked
by the tool instead of reconstructed by an agent from four verdicts.

Fit on one and check on the rest stays possible, as the held-out test it is.

### §PW106 A number that says where it came from

The dim star's hot-facet ceiling was 0.37: the shipped 0.344 plus a margin somebody
chose. It blocked the port for a day, and the fix was a person saying the margin was the
wrong number. Nothing in the spec could have said so first, because a bound read off
pixels, a margin put over one and a value a person agreed to are all spelled `max =
0.37`.

A bound gets an optional origin: `measured` (read off an artefact, with the value it was
read at), `margin` (put around a measured value by hand), or `person` (agreed on a look,
with the date). A TOML inline table beside the number keeps old specs valid, and an
origin outside those three is refused like any unknown field.

What changes is the failure. A predicate missed on a `margin` bound says the bound is a
guess and names the measured value it guards, so the next question is whether the look
or the number is wrong. A miss on a `person` bound says the look moved. That distinction
is what an agent needs to decide between re-searching and asking, and today it can only
be recovered from a comment.

### §PW107 Margins measured from the noise

Every margin in Cottony's star specs was chosen by eye: roughly a tenth above the
shipped value, the same for a median as for a 99th percentile. But a tail moves more
than a median under the same harmless change, so one margin rule is too loose on one
predicate and too tight on the next, which is how 0.37 came to refuse a star a person
accepted.

Renders are cheap enough to measure the noise instead. Calibration takes the accepted
artefact's request and re-renders it under changes that should not change the look: the
seed, the sample count one rung down, the size one step either way. The spread of each
measure across those is its noise, and the proposed bound is the accepted value plus a
stated multiple of it, written with origin `measured` and the spread beside it.

It proposes and never writes silently: the answer is the old bound, the new one and the
spread per predicate, and applying it is a separate call. A bound with origin `person`
is left alone, since a person's verdict outranks a statistic.

### §PW108 Every verdict is evidence about a bound

`loop.judged` stores `tool_passed`, `person_accepted` and a sentence, per run. So the
ledger can count how often a person overruled the tool and never which bound the tool
was wrong about, and the number the loop exists for cannot improve the specs it judges.

A verdict records the measured value of every predicate at the moment it was given, and
the ids a person named when they overruled, if they named any. Nothing about the call
changes for a caller that names none.

With that, per-predicate counts are arithmetic: for each bound, how often a result it
passed was rejected, and how often a result it failed was accepted, and on which side of
the bound. A bound overruled twice in the same direction is reported as the wrong
number, with the values that overruled it, which is the evidence a calibration or a
person needs.

This is counting over a file, not a model of taste, so it stays inside "Spending money
on the agent's own judgement": no call is made and no judgement is delegated. It becomes
worth more with every verdict, which no other part of the plugin does.

### §PW109 One sheet to look at, one call to answer it

The stars waited a day for one sentence from a person, and to get it an agent had to
point at `.polyweave/stars/compare.png`, explain a 99th percentile against a ceiling,
and then edit a spec comment and a ledger entry by hand from the reply. The judgement
was quick; everything around it was not.

A review sheet is one PNG per family: for each member the old artefact beside the new
one at the size the game shows it, the crop of the latest capture where it stands if one
is recorded, and under each the predicates that failed in words, with the origin of the
bound (§PW106). The two readings are stated as choices: the look is wrong, or the number
is.

A `judge` operation takes the family and one of those choices with a sentence. It writes
the person's verdict into the loop ledger with the values (§PW108), and where the number
was wrong it rewrites the bound with origin `person`, the date and the sentence. One
reply becomes one call.

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
