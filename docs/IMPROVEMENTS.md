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

## Block F — Motion

## Block G — Geometry as a declaration

### §PW146 A declaration refuses a key it does not read

Found shipping PW123, whose design assumed a `geom.unknown-field` refusal existed. It
does not. `geometry.parse` checks a name, the nodes, their ids, the output and cycles,
and reads nothing else. So a document with `colour_of = 1` at the top level, or a
primitive with `sizee = 9` beside its `size`, parses, builds and describes itself with
no warning. The shape that comes out is the one without the misspelt field, which is the
silent drop section 3 of tool-surface.md says no surface here makes.

The acceptance spec already works this way: every table has its closed list of keys, and
a key outside it is refused where it is written, with the list in the remedy. The
geometry equivalent has two halves. The document's own keys are fixed (name, output,
params, materials, voxels, variants and the rest the reader already consumes). Each op's
fields are what its builder reads, so the op table in `geometry/build.py` or `voxels.py`
should declare them as data beside the function, not leave them implicit in the code.
`parse` refuses a key in neither, with the nearest real one named, as
`geom.unknown-field`.

The test is a document with one misspelt key at each level, refused before anything is
built. Then every fixture under tests/fixtures/cottony has to parse unchanged, which is
the check that the lists are complete.

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

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

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

### §PW160 A clip baked by name

Found finishing PW124's census. A clip's own document is a plain table, so creating,
reading, keying, retiming and writing one are operations, and so are the skeleton's plan
and the reads of a rigged file. What turns a clip into something a game plays is not
reachable by name. `clip.compile`, `clip.frames`, `sprites.bake`, `sprites.both`,
`skeleton.fit`, `skeleton.weights` and `skeleton.write` each take a mesh and a fitted
rig as objects in memory, `(rig, bound)` from `skeleton.fit`, that a JSON call cannot
carry. So the census lists them internal, and baking a clip still needs a Python script.

The shape of the fix is the one `port.run` took. One operation, `motion.bake`, takes the
clip file, the mesh file and the body plan by name. It fits the skeleton, weights it,
compiles the animation, bakes the sprite sheet at the project's `[sprites]` settings,
and returns the paths written and `sprites.matched`'s verdict on the pair. It is of kind
`bake`. The fit's own numbers (pull, influences, falloff) come from `[rig]`, as they do
now.

The test is a clip written by `clip.write` and a small mesh, baked by name with Blender
present, and skipped where it is not, as the render tests are.

## Block L — What a run leaves as evidence

### §PW136 The gates run where the pin is read

`.github/workflows` holds `roadkeep.yml` and `site.yml`. The suite and the linter run
when someone types them, on a machine that has Blender and Godot, and nowhere else.
Cottony's `requirements.txt` installs this repository at a commit hash, so its CI builds
against code that no machine but this desk ever tested, while the editable install here
means the pin is never exercised locally either.

A workflow runs ruff and the suite on the lowest and highest Python the plugin supports.
Without `bpy` or `$GODOT` the render path skips, so the job prints the stamp
`tools/gate.py` writes, including how many tests skipped for each absent engine, and the
summary says outright that CI proves the pure half. Whether a runner gets Blender is a
later decision with its own cost; a green job that claims less than it proved is not.

The same job runs `claude plugin validate` on the manifest in `.claude-plugin/`, as
roadkeep's gate does against a pinned CLI.

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
