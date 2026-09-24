# Geometry as a declaration

Binds **PW30–PW34**. A shape stated as data, compiled to a mesh.

The reasoning is §PW30 and is not repeated here. The short form: a shape that exists only as
the result of executing statements cannot be read without running it, cannot be varied by
anything else, and cannot be reviewed before it is built.

## Why data and not a new language

A language needs a grammar, a parser, error messages and an editor story before it renders
its first triangle. A document in a format everything already reads needs none of that.

But plain data cannot do arithmetic, and the shapes that matter here are arithmetic — a
sixty-four seat tray is a loop over a cell size the game holds as a constant. So the format
adds exactly three things to TOML: **named parameters**, **expressions over them**, and a
**repeat** construct. Three features, not a language.

## A flat graph, not a nested tree

Nodes are a flat list. Each has an `id`, and refers to its inputs by id. Three consequences,
all of which were the reason for choosing it:

- **It diffs.** A change touches one table, not a re-indented subtree.
- **It is addressable.** PW32's search points at a node's parameter, and PW33's review points
  at a node, by name.
- **A node can be used twice.** It is a graph, not a tree, which a boolean against a shared
  cutter needs anyway.

## A document

```toml
name    = "board_tray"
version = 1
output  = "tray"     # above the first [[nodes]], because TOML puts a bare key after a
                     # table header inside that table — written below, it would name
                     # the last node's own field instead

[params]
cell       = 112
board      = 8
pad        = 16
face_depth = 6.0
seat_depth = 4.0
bevel      = 2.0

[materials.cushion]
colour    = "#F2E4D0"
roughness = 0.62

[[nodes]]
id       = "face"
op       = "plate"
material = "cushion"
rect     = ["0", "0", "board * cell + pad * 2", "board * cell + pad * 2"]
depth    = "face_depth"
corner   = 28

[[nodes]]
id      = "seat"
op      = "prism"
outline = { shape = "rounded_square", size = "cell * 0.82", corner = 18 }
depth   = "seat_depth"
at      = ["pad + col * cell + cell / 2", "pad + row * cell + cell / 2", "0"]
repeat  = [
  { var = "row", from = 0, to = "board - 1" },
  { var = "col", from = 0, to = "board - 1" },
]

[[nodes]]
id     = "tray"
op     = "carve"
into   = "face"
cutter = "seat"
bevel  = "bevel"
```

**`output` goes above the first `[[nodes]]`.** TOML puts a bare key written after a table
header *inside that table*, so an `output` at the foot of the file names the last node's
own field and not the document's output — which is quiet enough that this spec's first
example had it wrong. A node carrying an `output` key is refused with that explanation
rather than read as though it meant the document. Where nothing names an output, the last
node is it.

## Values and expressions

A value is a number, a string holding an expression, or a boolean. **Where any element of an
array is an expression, write them all as strings** — that keeps a caller from having to
reason about mixed-type arrays.

The expression grammar is deliberately small: numeric literals, parameter names, repeat
variables, `+ - * / %`, parentheses, and `min`, `max`, `abs`, `round`, `floor`, `ceil`,
`sqrt`, `sin`, `cos`, `radians`. **Nothing evaluates arbitrary code.** That is a determinism
requirement before it is a security one: an expression whose value can depend on anything but
its parameters breaks the cache key in [provenance.md](provenance.md). Python's own parser
produces the tree and every node of it is then checked against that list, so a call, an
attribute, a comparison, a subscript, a lambda or a string literal is refused where it is
read rather than where it is evaluated.

**What is in scope decides whether a string is an expression or a name, all or nothing.**
`depth = "face_depth"` resolves to a number because `face_depth` is a parameter; `shape =
"rounded_square"` stays a string because nothing declares that name. Every name in it must
be in scope, and **a path is why**: `art/star.png` parses as a division of two names, so a
rule that took any `/` for arithmetic would evaluate an image path and break a working
document.

The cost of that rule is a typo inside an expression — `"pad + cel"` — which now reads as
a name rather than as a mistake. That is a **warning** from the review rather than a
refusal, and it belongs there: it reads reasonable and it is wrong, which is the class of
error §PW33 exists for. A parameter and a generator sharing a name is a document that
should rename one of them; the parameter wins.

## Repeat

`repeat` is a list of variable ranges. The node is instanced once per point of their
cartesian product, with each variable in scope for every expression on that node. `to` is
inclusive; `step` defaults to 1.

**A repeated node's id names the whole set.** `cutter = "seat"` above means all sixty-four
instances, which is what makes the tray one boolean rather than sixty-four.

## The vocabulary

Read off what Cottony's scripts already do, because a format covering only cubes and spheres
would leave every real asset in code (§PW31).

### Outlines (2D)

| `op` / field | What it is |
|---|---|
| `shape` | A named generator — `circle`, `rounded_square`, `star`, `lobed` — with its own parameters |
| `image` | An alpha mask from a project image, traced to an outline |
| `radial` | Points arrayed about a centre, `steps` of them |
| `offset` | An outline grown or shrunk by a distance |

An outline appears inline on a solid node, as in `seat` above, or as its own node when two
nodes share one.

**`points` means a literal list of them only where no `shape` is named** (§PW64). It is
also a generator's own argument — `star` takes a point count — so `{ shape = "star",
points = 5, outer = 240, inner = 120 }` passes the 5 through to the generator, and
`{ points = [[0, 0], [10, 0], [5, 8]] }` is the ring itself. Which key is present decides
the kind, and the same key can be an argument to the kind it did not name.

**An outline is a closed ring in XY, and a solid extrudes it along Z** — the plane the
camera faces at azimuth zero, which is what a sprite-baked asset wants: the drawn shape
stays the drawn shape and the depth goes away from the viewer.

**`offset` moves each corner along its miter, not its bisector.** A unit step along the
bisector grows a ten-unit square to 11.4 rather than to 12, because a corner has to travel
the diagonal. It is not a clipping offset: shrink a shape past its own width and the edges
cross rather than the shape disappearing.

**Tracing is Moore-neighbour boundary walking, then Ramer-Douglas-Peucker.** Every point
it returns is a pixel really on the edge, and the simplification is what stops a drawing
traced at one point per pixel becoming a thousand-point outline of a shape with eight
corners. The y axis is flipped on the way out, because an image counts rows downward and §6
counts y upward — an outline that came back mirrored is a sprite extruded backwards.

### Solids (3D)

| `op` | What it is |
|---|---|
| `primitive` | `sphere`, `cube`, `cylinder`, `plane` — the cheap shapes the preview rung needs |
| `prism` | An outline extruded along the depth axis |
| `plate` | A rounded plate: a rectangle with a corner radius and a depth |
| `crowned` | A plate with a domed face |
| `annulus` | A ring between two edges: two radii for a round one, two outlines for any other |
| `inflate` | A drawing given volume, as a stuffed cushion is — from an `outline` or from a `drawing` |
| `carve` | Boolean difference: `into` minus `cutter` |
| `union` | Boolean union of a list of ids |
| `bevel` | A bevel applied to an existing node |
| `transform` | Translate, rotate and scale an existing node |
| `custom` | A project function — see below |

`inflate` is the operation that gives a drawn panel its volume while keeping the drawn
silhouette to the pixel. `prism` over an `image` outline is the other half of the same idea:
a star's silhouette becomes a mesh that is not merely similar to the drawn sprite but is the
drawn sprite, extruded.

**A `crowned` dome shrinks its rings by whichever rule keeps the silhouette** (§PW66) —
the same question the cap below asks, with the same answer. `offset` moves a corner along
its miter, which points inward at a convex corner and *outward* at a reflex one, so a
concave outline's inner vertices travel outward while the ring is supposed to be
shrinking: Cottony's star came back reaching 82 units past its own silhouette. A concave
ring is scaled toward its centroid instead, which nests by construction. A convex one
keeps the miter, because that holds a corner radius constant as it shrinks where a scale
would not.

**A concave cap is triangulated and a convex one is not.** Cottony's first star came back
with black triangles laid across its arms, which is a cap filled as though its points were
a convex hull. Whether the outline is convex decides it, so a rounded rectangle keeps its
single n-gon cap — which is what keeps the tray's topology, and therefore its committed
render, from moving.

**The boolean solver is MANIFOLD, and the assertion is what actually protects the build.**
Cottony measured Blender's EXACT solver returning an empty mesh, with no error, for a cut
against a bevelled object — 2402 faces before the bevel and 0 after — and moved to MANIFOLD
because of it.

**That failure does not reproduce on Blender 5.2.1.** Rebuilt on the same shape: the tray's
plate bevelled and then cut by all sixty-four seats returns 3210 faces under EXACT and 3206
under MANIFOLD, and a single pocket returns 966 against 884. Neither empties. MANIFOLD is
kept because it is the solver measured to work on the case that broke and it costs nothing
here, not because this version still shows the symptom — and a finding about one version of
one solver is exactly the kind of thing to date rather than to inherit.

So what the build actually relies on is the **non-empty assertion** (§PW2), which holds
whichever solver runs and whichever Blender is installed. Where a bevel and a boolean both
appear on a node, the boolean still runs first.

**An `annulus` takes two edges and walks them in step** (§PW65). A number is a circle's
radius, which is all a round ring needs; an outline is that outline, which is what a rim
that is not round needs — Cottony's tray rim is a rounded rectangle with the same rounded
rectangle offset inward by the piping width inside it, and the vocabulary drew both of
those rings long before an op would take them. The two edges must have the same number of
points, which is not a burden but the construction: an inner edge is an `offset` of the
outer one, so it keeps its count and its order by definition. Two rings generated apart do
not correspond and are refused rather than skinned into a twist. A boolean between two
plates gives the same silhouette for a solver call, a Blender round trip and whatever
topology the solver leaves.

**`inflate` keeps the silhouette to the point.** Every boundary vertex stays exactly where
the outline put it, at zero depth, and only the inside swells — by a function of each
point's distance from the edge, which is what makes a panel look stuffed rather than
extruded. A cushion made from a traced drawing therefore still has the drawn outline.

**`inflate` has two profiles, and what the node was given decides which** (§PW68). An
`outline` knows only where the shape stops, so the swell is distance from the edge. A
`drawing` carries what is *inside* it, so its alpha is blurred and the blur is the height:
a hole drawn in the middle is a hole in the surface rather than something filled in. The
two agree on a plain blob and differ everywhere else, which is why it is one op with two
rules rather than two names for giving a drawing volume.

```toml
[[nodes]]
id        = "panel"
op        = "inflate"
drawing   = "art/booster_tray.png"
thickness = 60.0
size      = 984          # the longer side, in the project's units
soften    = 0.40         # the blur, as a share of the drawing's shorter side
```

`soften` is what domes the face, and its useful range is bounded at both ends. Measured on
a disc half its canvas across: at 0.06 nearly a third of the mesh sits within a tenth of
full height, which is a flat top with a narrow fall-off — the reading that says "the
cushion read as the flat card it was drawn as". At 0.20 a tenth does, and the face is
domed. Past that the blur is wider than the shape, the field it samples is near-uniform
inside before it is normalised, and the face flattens again.

The drawn profile is a **relief and not a pillow**: one lifted surface, because that is
what a panel seen front-on is. A cell whose corners are all below `floor` is dropped,
which is the drop shadow's faintest tail — built down to it, the panel showed a pale
rectangle the size of the canvas.

### Surfaces

A material is a table under `[materials.<name>]` and a node wears one by name. **Its values
are expressions over the document's own parameters**, resolved like a node's, so a surface
joins PW32's search on the same terms a shape does. A node naming a material nothing
declares keeps its colour and loses everything else quietly, so the review warns about it.

A fuzzy surface — plush, fur, moss, velvet — is **shell texturing**: the same surface drawn
many times, each copy a little further out, each keeping only the strands tall enough to
reach it, so the silhouette breaks into tufts rather than into single hairs. Cottony
describes its own in eight constants, every one found by eye at two minutes a sample.

**Those constants are the answer, not the way to ask** (§PW50). A table of eight keys would
be one project's look compiled in — the non-goal exactly — and would help nobody who wanted
fur instead of cotton. So a declaration states two numbers:

```toml
[params]
fluff_depth      = 3.0
fluff_coarseness = 0.62

[materials.cotton]
colour = "#F2E4D0"
fuzz   = { depth = "fluff_depth", coarseness = "fluff_coarseness" }
```

| field | What it is |
|---|---|
| `depth` | How far the fuzz stands off the body, in the declaration's own units |
| `coarseness` | Nought is fibres alone, one is clumps alone, and a plush surface is between them |

**The coarseness axis is the two readings, not an invention.** Cottony measured both of its
ends as failures: fibres grown straight off a smooth ball read as velvet rather than as
sherpa, and clumps alone gave hard beads. What worked has both fields at once, which is why
the fibre field's weight is simply one minus the coarseness — at either end one field stands
alone, and in between they multiply.

Everything else is derived from those two: the shell count, the cut sharpness, the clump and
fibre scales, how far strand lengths wander, how far the body pushes out under a clump, and
how far a tip leans towards its clump's crown. A declaration naming one of them by name is
refused with `geom.bad-surface` and told what to state instead, because a key silently
dropped is a surface that came back at a coarseness nobody chose.

**The shell count is a function of coarseness and not of depth.** A strand needs the same
number of samples along its length whether it is long or short, and reading the count off
fineness keeps it free of the declaration's units — nothing in the format knows how big one
of them is. Depth still sets the *spacing*, which is what decides whether the stack reads as
one surface or as stripes, and it is reported rather than assumed against a screen.

A surface reads back in words with the shape that wears it: `a plate 928 by 928 at 0 by 0
(corner 28, depth 6), in cotton, fuzzy 3 deep, clumped`. The coarseness bands are named for
what was measured at them — `fine`, `fibrous`, `clumped`, `beaded` — so a declaration that
reads back `beaded` has been told what it asked for.

What is **not** here is the noise field itself, which is a shader's and not a format's. The
declaration fixes the stack the field is drawn onto and the threshold each shell cuts it at,
which is the half that is reproducible from the two numbers that asked for it.

## The escape hatch is a node, not a mode

Any format eventually meets a shape it cannot state, and forcing that shape into the format
produces worse geometry than the script it replaced (§PW34).

```toml
[[nodes]]
id     = "rope"
op     = "custom"
fn     = "tools/art/rope.py:build"
inputs = { along = "face" }
args   = { thickness = "bevel * 1.5", twist = 12 }
```

The function receives resolved arguments and **named inputs as meshes, not as ids** — it is
handed the geometry, so it never has to know how the graph is stored. Three properties
survive, and each is checked rather than hoped for:

- The parameters stay **declared**. `args` are expressions over the document's own
  parameters, resolved before the call like every other field, so PW32's search still
  reaches `thickness` by turning `bevel`.
- The function's source is **hashed into provenance**, so changing it invalidates the cache.
  A custom node whose file changed and whose parameters did not would otherwise come back
  from the cache as the shape it used to be. A function that is a module on the path rather
  than a file in the tree is not hashable, and the record says so instead of guessing.
- The rest of the shape stays **data**. A declaration does not become a script because one
  node in it is custom.

A function that does not load, raises, or returns something that is not geometry is a typed
refusal naming what it was handed — `geom.no-function` and `geom.not-geometry`. The address
is the same `path/to/file.py:name` a job's target uses, resolved by the same code.

Where the same custom node appears in three projects, that is the signal it should have been
vocabulary, and it gets filed as a roadmap line rather than copied a fourth time.

## What a build returns

```python
from polyweave.geometry import build, write

made = build(document, root=".", board=8)   # parameters given here reach the shape
made["output"]      # the mesh the document names
made["built"]       # every node's mesh, by id
made["report"]      # what came out, per node

out = write(document, "assets/tray.glb", root=".")   # the same, put on disk
out["artefact"]     # what `bake(model=…)` takes from here
```

**A build ends in a file, and that is a decision** (§PW69). `bake` takes its model as a
path, and the cache key and the provenance record key off a file and its hash already — a
mesh in memory has no sha256 until something defines a canonical serialisation for it,
which would be a second format to keep true. So a build writes what it made and the rest
of the plugin takes it unchanged, and a search that rebuilds per sample pays one file per
sample beside the render it was going to pay for anyway.

Everything the build worked out goes with it: the texture coordinates, and a material per
group built from the document's own `[materials]` table. What does not survive is the
n-gons — glTF stores triangles, so an 86-face star comes back as 156. That is the file
format and not a difference in the shape.

**`colour` is translated on the boundary.** A declaration writes `colour = "#F2E4D0"`
because a person authors that file; the renderer's names are Blender's own shader sockets,
discovered at runtime, where it is `base_color` and four floats. `blender.as_inputs` maps
the one onto the other and passes through every name the shader already has, in the same
place and for the same reason the Z-up conversion happens there.

A mesh, and a report — because a shape that can only be checked by looking at a render is
one whose construction errors are found in the expensive place (§PW33). Two wrong
constructions of Cottony's tray seats each looked entirely reasonable while being written.

**One table decides what an `op` is** (§PW60). `build.BUILDS` maps each op to the adapter
that shapes a node's own fields into the call, and it is the only list of op names in the
package that decides anything — the review reads it rather than keeping a second, so a
document naming an op nothing builds is a **warning** from the structural read and a typed
refusal at the build, and the two cannot disagree. An op nobody declared is
`geom.unknown-op`, whose remedy names the declared ops and the `custom` door.

**A mesh may carry `uv`, one pair per vertex** (§PW68), and most do not. A shape has no
way to say where a picture goes on it otherwise, which is the whole of a drawn panel: the
drawing that gave it its outline is also the picture on its face. Absent unless something
worked the coordinates out, by the rule above — a mesh carrying zeros claims a corner of
the picture for every face of itself.

`inflate` fills them, because a stuffed panel is the drawing given volume, and the
projection is planar over the outline's own bounds so the silhouette touches 0 and 1 on
each axis. `planar_uv` takes a `[x, y, width, height]` instead where the drawing's frame
is larger than the shape in it. It is not applied to a prism's walls: a plane projected
onto a face perpendicular to it smears.

A `transform` carries them, since it reorders nothing. A `union` carries them **only
where every operand has them** — filling a part that has none with zeros would place that
part's picture wrongly rather than leave it unplaced. `post.check("mesh", …)` refuses an
array that does not line up with the vertices, because a picture placed by one that is a
pair short is on the wrong part of the shape from there on and the render does not say so.

**A build says which faces wear which material** (§PW67). A material sits on a node and a
document names one output, so a model in two materials — Cottony's cream rope rim on its
cushion face — could only be handed back as a `union`, and the join kept one material or
none. The output now carries `groups`, one `{ material, faces: [start, stop] }` per run of
faces, absent where nothing was dressed:

```json
"groups": [
  { "material": "cushion", "faces": [0, 38] },
  { "material": "rope",    "faces": [38, 182] },
  { "material": "cushion", "faces": [182, 2599] }
]
```

Faces, because that is the one thing a join really knows: `union` lays its operands out in
order, so where each one's faces landed is arithmetic. It is also the shape a renderer
wants — a material slot is assigned per polygon, which Blender has always had — and
`apply_material` takes a mapping of name to inputs beside the groups.

**A boolean keeps what it cut into and nothing finer.** The cutter is gone from the result
and the solver does not preserve face correspondence, so a carve or a bevel over one
material is one group and over several is none. Claiming a range the solver reordered
would be worse than saying nothing.

**A repeated node's id names the whole set at build time too.** Sixty-four seats build as
sixty-four meshes and are joined into the one mesh their id stands for, which is what lets
`cutter = "seat"` be one boolean rather than sixty-four. **`at` places an instance and is
applied last**, since it is the field a repeat varies — a seat differs from its sixty-three
siblings in nothing but where it sits. `transform` is the exception, because `at` is its own
argument there.

```json
{
  "output": "tray",
  "params": { "cell": 112, "board": 8, "…": "…resolved values…" },
  "nodes": [
    { "id": "face", "op": "plate", "faces": 38, "instances": 1 },
    { "id": "seat", "op": "prism", "faces": 2432, "instances": 64 },
    { "id": "tray", "op": "carve", "faces": 56778, "instances": 1, "manifold": true }
  ],
  "bounds": [0, 0, 0, 928, 928, 6.0],
  "warnings": []
}
```

Those counts are **what this document actually produces**, measured once the builder existed
rather than sketched before it did. The bounds are the arithmetic: eight cells of 112 with 16
of padding either side, six deep.

The report is readable before a render exists, and the per-node face count is what catches a
boolean that silently returned nothing.

**But the cheapest check is the one that costs no build at all.** Two wrong constructions of
the tray's seats were built before the right one, and both looked entirely reasonable while
being written. So a declaration also reads back **in words**, one sentence per node, in the
order they build:

```
face: a plate 928 by 928 at 0 by 0 (corner 28, depth 6), in cushion
seat: a rounded_square of corner 18, size 91.84, extruded (depth 4) — 64 of them, in an 8 by 8 grid
tray: face with seat cut out of it (bevel 2)
```

That is a sentence somebody can disagree with, which a render is not until it exists. Beside
it come the things that are **odd rather than wrong**: a node nothing uses, a parameter no
node reads, a repeat larger than a document usually means, and a field that reads as
arithmetic over a name nothing declares. None of them stops a build. All of them are shapes
the mistake takes when the code did exactly what it said and what it said was wrong.

The manifold check is **opt-in**, because it walks every edge of every face and on a dense
mesh costs more than the operation that produced it — the same line §2 draws between a cheap
assertion and an expensive one.

## Cells instead of triangles

A document may ask for cells (§PW93). A game that draws its actors as cubes and breaks them
apart when they are hit reads which cells exist and what each one wears, and a mesh says
neither.

```toml
[voxels]
across = 16          # cells along the longest side; or `cell = 0.5`, a size, never both
```

Either value may be an expression over `[params]`, and `voxelize(document, cell=…)` or
`across=…` overrides the table for one call. Neither or both is `geom.bad-voxels`.

**Evaluated on the grid.** The grid is centred on what the output covers and a cell is
filled where its centre is inside. `primitive`, `prism` and `plate` answer that by their own
formula, `transform` by moving the sample points backwards, `union` and `carve` as set
operations: exact, no Blender and no solver. `inflate`, `crowned`, `annulus` and `custom`
have no test of their own and are built as meshes and read by ray parity. A `bevel` passes
its input through.

**A later node paints.** A cell wears the material of the last node **in the document** that
covers it and carries one. Document order rather than build order, because build order breaks
ties by name, and a canopy written after the hull should win whatever the two are called.

`build.write(document, "ship.glb")` on such a document writes `ship.voxels.json` beside the
mesh, and the mesh is the same cells as cubes with only their exposed faces, grouped by
material, so `bake` and every render take it unchanged:

```json
{
  "name": "ship", "cell": 1.0, "size": [16, 7, 5], "origin": [-8.0, -3.5, -2.5],
  "palette": [ { "name": "hull", "colour": "#808080" }, { "name": "glass", "glow": 2.0 } ],
  "nodes": ["hull", "canopy", "ship"],
  "cells": { "x": [], "y": [], "z": [], "palette": [], "node": [] },
  "count": 312
}
```

`cells` is five flat arrays of one entry per cell: its grid index on each axis, its slot in
`palette`, and the index in `nodes` of the node that decided what it wears. A palette entry is
the material's resolved table with its keys passed through untouched, since `glow` means
something to a game and nothing here; a cell nothing painted wears an entry whose name is
empty. The readback is one line: `a voxel model 16 by 7 by 5, 312 cells in 3 materials`.

## Rebuilding

A parameter change forces a rebuild of every node that references it, transitively; a rig
change forces only a re-render. The compiler computes that from the graph, and **the search
needs it** — rebuilding geometry costs more than re-rendering it, so a mixed search over
shape and light orders its sampling to rebuild as rarely as it can (§PW32).

**The ordering is where a name sits in the product.** A cartesian product varies its last
axis fastest, so putting the rebuilding parameters first holds one shape still while every
rig value is swept over it. That is the whole mechanism, and the search reports the rebuilds
it actually paid for against one per sample, so the saving is counted rather than claimed.

**A parameter is the shape's if the document declares it**, which is how one search space
carries two costs without either side being told which is which. A search naming a
parameter the document does not have is refused (`geom.unknown-name`) — a budget spent
turning a knob attached to nothing would otherwise be reported as a finding.

Every parameter a search may touch needs a declared range for the same reason a rig parameter
does: a wall thickness that goes negative does not produce a poor render, it produces an
invalid mesh. **A build that refuses is a failed sample**, scored zero and named in the
answer, because a search that died on one invalid combination would report nothing about the
valid ones it had already paid for.

## Conventions

Axes, units, origin, colour and angles are fixed in
[tool-surface.md](tool-surface.md#6-conventions-fixed-once) and are not restated per format.
