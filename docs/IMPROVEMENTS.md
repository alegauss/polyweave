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

## Block I — Voxel models from a declaration

### §PW93 Voxel output

A document gains `[voxels]` with `cell` (a size) or `across` (cells along the longest
axis), and its build answers occupancy instead of triangles. Starship is the consumer:
its actors are declared here and drawn and shattered as cells.

Evaluation is grid-native. Each op answers an inside-test at cell centres: `primitive`
analytically, `prism` as the ring test `solid._inside` times its depth range, `plate` as
a rounded rectangle, `transform` by inverse-transforming the sample points, `union` and
`carve` as set operations. Exact, no Blender and no MANIFOLD, in milliseconds, so a
search can afford thousands. Ops with no inside-test (`inflate`, `crowned`, `annulus`,
`custom`) are voxelized from their mesh by ray parity along one axis.

A cell wears the material of the last node in build order that covers it, so a later
node paints: a cockpit over a hull.

The build writes `<name>.voxels.json`: cell size, dimensions, origin, the palette (each
material's resolved table, keys passed through untouched, since `glow` means something
to a game and nothing here), and the cells as flat arrays of x, y, z, palette index and
node. Beside it, the same cubes as a `.glb` with material groups, so `bake`, the look
and every render take it unchanged. The readback says `a voxel model 16 by 7 by 5, 312
cells in 3 materials`. Provenance and cache key as a mesh's do.

This is the compiler answering another question about the same declaration. It generates
nothing a service would, so the non-goals hold.

### §PW94 Voxel contact sheet

Cells are already an image. An orthographic view along an axis is the nearest cell per
pixel column in its palette colour; an isometric view is cube tops and two sides shaded
by face. Both are numpy and Pillow at a fixed number of pixels per cell, with no light
and no engine.

One PNG contact sheet per build: front, side, top and isometric, with an optional grid
and node labels, written beside the json. The agent reads the PNG, edits the declaration
and looks again, inside one turn.

It stays inside "Replacing Blender, Godot or the generative service": it replaces no
renderer, only skips one for a draft, with flat colours, no neon and no bloom. The final
look stays the engine's and the render ladder's. It is to a voxel model what the
readback in words is to a declaration: the cheapest look that can still be disagreed
with.

### §PW95 Cells written as text

`op = "cells"`: `layers` is a list of slices along z, each a list of strings, one
character per cell; `legend` maps a character to a material and `.` is empty. The cell
size and origin are the document's `[voxels]`, and `at` places the block as on any node.

It mixes with the other ops. A hull from a `prism`, a canopy painted over it from
`cells`, a vent carved out with `carve`. In mesh mode the same node builds as cubes, so
it is not voxel-only.

Text because it diffs, reviews in a pull request and is what an agent writes fluently.
It is where the creative half of a model lives, while the grid, the booleans and the
painting order stay the compiler's.

The readback: `cockpit: 3 layers of 8 by 5, 41 cells in hull and glass`.

### §PW96 Mirror

`op = "mirror"` with `of` (a node id), `axis` and `plane` (default 0). On a mesh it
reflects, flips the winding so normals stay outward, and joins the two halves; on cells
it reflects the indices, and a centre column that lies on the plane is kept once rather
than doubled.

It is an op rather than a flag, so the half can still be carved or painted before it is
mirrored, and something asymmetric (a single antenna, a damage scar) can be added after.

The readback: `ship: hull_half mirrored across x = 0`. A mirror of something already
symmetric is a review warning, since it doubles the cells or faces for nothing.

### §PW97 Voxel checks

`post.check("voxels", …)`, run by every voxel build and reported with the readback:

- connected components: one body, unless the document declares separate parts;
- cells joined to the rest only through an edge or a corner, which read as broken off;
- threads one cell thick longer than a set length, which vanish at a distance;
- the cell count against a budget;
- symmetry, as the share of cells with a mirror partner;
- bounds against a target extent.

Every finding names its cells, so the fix is a local edit rather than a hunt. The
budget, the thread length and the extent come from the project's config, because a game
decides how many cubes it can afford and the plugin must not.

### §PW98 Search a voxel model against a reference

The reference is a drawing's alpha, or a mesh (a Meshy fetch) projected the way
`normalise.project` already does. The measure is the overlap of the model's projected
cells with the reference mask at the grid's resolution, per view, with the voxel checks
as constraints: a sample that floats cells or breaks the budget scores zero.

The search sweeps the ranges the document declares, as it does for any shape parameter.
Each sample is a voxel build, milliseconds and not a render, so thousands of samples
take seconds. The answer is the best parameters, their contact sheet and the score per
view.

This is the split of work: the author declares the parts, what they mean and how far
each may move, and the search finds the proportions. A Meshy model bought for a ship
then becomes a target the declared ship is fitted to, not a mesh to chop into cubes.

### §PW99 Fracture plan

An optional `[voxels.fracture]` with a fragment size range in cells and a seed. The
build partitions the cells into fragments of connected cells in that range, preferring
not to cross a material or node boundary, so a cockpit flies off whole. Each fragment
carries its cells, centre and mass.

The same pass ranks every cell by its depth from the surface, a distance transform over
the grid, which is the order damage takes: a hit chips the outermost cells nearest it
first.

Both go in the json. A game spawns one piece per fragment instead of one per cell, which
divides its debris count by the mean fragment size, and chipping on hit becomes a
lookup. Deterministic from the seed, so the same model always breaks the same way and a
test can say where.

### §PW100 A mesh as a node

`op = "mesh"` with `path` to a `.glb` imports it as a node in the project's frame. In
voxel mode it is filled by ray parity, so a closed hull comes out solid rather than as a
shell, and each cell takes the texture colour at its nearest surface point.

An idea, held until a model declared from parts alone has been tried: fitting a
declaration to a mesh by search may make importing it unnecessary, and a voxelized scan
tends to come out as a blob at the ten to twenty cells a game can afford.

### §PW101 A build command

`python -m polyweave build <doc.toml>` with `--out <dir>`, `--set name=value`
(repeatable) and `--preview`. It prints the readback, the report, warnings and check
findings, and exits non-zero on a refusal. `--json` gives the same as data.

`--all <dir>` builds every declaration under a folder and skips cache hits, so a
project's asset step is one line that costs nothing when nothing changed.

It runs on the caller's interpreter, and needs `bpy` only when a node in the document
needs Blender, which a voxel build of the grid-native ops never does.

### §PW102 Godot importer for voxel models

An addon, `addons/polyweave_voxels/`, that polyweave installs into a Godot project. An
`EditorImportPlugin` turns `*.voxels.json` into a `VoxelModel` resource holding packed
cell transforms, palette colours, the palette's other keys as a Dictionary, fragments
and erosion order, plus a MultiMesh ready to assign.

How the game draws, lights and shatters the model stays the game's own code. The
importer ends where the data becomes Godot's.

`engine.py`'s headless import proves it in the tests. The addon carries the json schema
version it reads and refuses another.

### §PW103 Variants

`[variants.<name>]` tables of parameter overrides in one document; the build writes one
output per variant, named after it, and the readback lists them side by side.

An idea until a consumer has three members of one family. `--set` covers one-off
overrides already.
