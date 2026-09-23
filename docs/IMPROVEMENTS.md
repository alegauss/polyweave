# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

### §PW64 One key naming both a kind of outline and a generator's own argument

`outline.resolve` decides what an outline is by which key is present — `shape`, `image`,
`points` or `of` — and it strips all four out of the arguments before dispatching,
because they name the kind rather than describe it. That is right for three of them.

`points` is also the name of a generator's own argument. `star(points, outer, inner)`
takes a point count, so `{ shape = "star", points = 5, outer = 240, inner = 120 }` is
how a declaration asks for a five-pointed star, and `resolve` removes the 5 on its way
past. The generator is called without it and refuses with `geom.unknown-shape: star does
not take those arguments`, naming a missing argument the document plainly supplied.

The review reads the same document correctly — "a star of inner 120.32, outer 240.64,
points 5, extruded with a domed face" — because it never dispatches. The structural read
says the shape is fine and the build says it is not.

This is what stopped Cottony's star being declared, and the star is the shape the whole
concave-cap finding came from.

The fix is small and the choice is which way round. `points` means a literal list only
where no `shape` is named, so reserving it conditionally — strip it for the points
branch, pass it through for the shape branch — keeps every document that works today
working. Renaming the generator's argument instead would change a published vocabulary
to avoid a collision the dispatch already knows how to resolve.

### §PW65 A ring the vocabulary can draw both edges of and cannot state

`solid.annulus(outer, inner, depth)` takes two **radii**, so the only ring the
vocabulary can state is a round one. Cottony's tray rim is a ring between two rounded
rectangles — `round_rect_poly(face_box, RADIUS)` on the outside and that same ring
offset inward by the piping width on the inside — and the vocabulary has both halves of
it already: the `rounded_square` generator draws the outer, and `offset` draws the inner
from it.

What is missing is the op that takes two outlines rather than two numbers. A ring
between any two closed rings is the same construction the round one already is: the two
rings stacked, skinned between at each level, and capped by the gap between them.

The workaround is a boolean and it is worse. Carving an inner plate out of an outer one
gives the same silhouette for a solver call, a Blender round trip and whatever topology
MANIFOLD leaves, where the direct construction is numpy and predictable.

Cottony's own `solid.annulus` already takes two outlines, which is the signal the
format's own rule names: where the same shape appears in a second project it should have
been vocabulary. This is the first place the port meets an op stated more narrowly here
than in the script it replaces.

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

### §PW54 A shape that exists only inside a bake cannot be read, diffed or searched

`tools/art/solid.py` is 283 lines of bmesh primitives working in image coordinates
turned on their side, imported by `tray_model.py`, `star_model.py` and any `builder` a
`Model` carries. It exists for a good reason from its own docstring: the second asset
needed the same four operations as the first, and a second copy of a bevel that took
three attempts is a copy that will drift.

That reasoning now applies one level up. `solid.carve` holds the MANIFOLD lesson —
Blender's EXACT boolean returns an empty mesh with no error at all once the object it
cuts has been bevelled, measured at 2402 faces against 0 — as a second copy of a rule
this plugin also carries.

A program is also not a thing anything can search. A declared shape has ranges a solver
moves; a builder has constants somebody edits and re-renders, and nothing measures
whether the edit was an improvement.

Two routes are in scope and they are different work. The arithmetic models — the tray's
sixty-four seats, the star's five even points — are a declaration each. The panels are
`cloth.cushion`, which inflates a drawn PNG, and that is an outline read off an image
rather than a primitive.

A declaration builds now, and reading the two scripts against it found the vocabulary
two ops short: §PW64 stops a star being asked for with a point count, and §PW65 leaves
the rim, a ring between two rounded rectangles, with no op taking two outlines.

### §PW56 Twelve runners, twelve ways to start Godot, and no check on what applied

`tools/capture_screens.py` drives four scripts under `tools/capture/`;
`tools/measure_frames.py` drives eight more under `tools/perf/`. Both open a real
window, because `--headless` runs on a dummy renderer that draws nothing; both distrust
Godot's exit code; both bound the run by a wall clock; and both count a run as failed
unless its own printed line appears and the file that line names exists. The procedure
is written twice and its reasoning three times, counting `run_tests.py`.

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

Set aside: Godot is not installed here, the work is entirely in Cottony's tree, and
Block E already ships every piece it would use.

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
