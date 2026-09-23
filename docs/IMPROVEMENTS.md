# Improvements

## Block A — What a tool call costs the turn

### §PW51 A measurement without the tolerance it was taken against is a number, and the file cannot be read back for it

A record says which mesh, which seed, which sample count and which view transform made
an artefact, and nothing about the numbers the verdict beside it was taken against. Two
records can therefore carry the same measurement and mean different things, because the
alpha floor that decided what counted as the subject sat in a file that has since been
edited. Reading the config back does not recover it: the record is the artefact's, and
the file is the project's as it is now.

`Config.tolerances()` resolves all six together for exactly this reason, and
`Tolerances.as_dict()` exists to be written down. What is missing is the field and the
decision about where it goes.

The decision is whether they belong in the cache key. They should not, on the argument
that they do not change the artefact: a render made at one alpha floor is byte-identical
to the same render at another, because the floor is read after the pixels exist. That
argument has a hole worth checking first — a search that accepts on a predicate measured
at one floor and is re-run at another reuses a hit whose verdict no longer holds, which
is a stale acceptance rather than a stale picture. Whether that is the key's problem or
the spec's is the thing to settle.

Measure how often a project actually changes a tolerance, because a field nobody varies
is a field nobody needs.

### §PW52 How little of a frame a subject may fill is a number nothing has measured, and the nearest one means something else

The line that made flatness a tolerance expected the transparency check beside it to be
`max(alpha) == 0`, with the same equality problem. Measured on 2026-09-22, it is not:
the check is `not mask.any()` over `alpha > round(alpha_floor * 255)`, so it already
asks whether anything clears the floor. The equality was gone before the line was
written.

The gap it pointed at is real all the same, and different. A 64x64 render whose only two
opaque pixels sit in one corner passes both checks today: coverage 0.000488, above the
floor because those pixels are fully opaque, and not flat because the two differ. It is
empty for every purpose and nothing says so.

What is missing is a floor on how much of a frame a subject must fill to be worth
judging, and the reason it was not folded into that fix is that no number for it has
been measured. `[tolerance] subject_coverage` is 0.12 and looks like the answer. It is
not: it means the least of the frame a photograph's subject may fill before the cut is
worth spending on, and a correctly framed render of a thin asset — Cottony's
booster_wand, a rope — is well under 12% by area while being exactly right. Borrowing it
here would refuse real work.

So the number has to come from measuring real renders of the thinnest assets rather than
from picking one. Until then a two-pixel render passes, which is a smaller failure than
refusing a wand.

### §PW61 Two readers of one dep grammar, and only one of them was written against it

roadkeep accepts three spellings for a dep: an id, a `Block X` label, and a range.
`site/scripts/roadmap.mjs` was written against the first and never told about the other
two. `waitingOn` splits each dep on whitespace and keeps the leading token, which is
right for `PW5` and for `PW5 ✅` — the mark is what says the wait is over — and wrong the
moment the first token is not an id.

When §PW54 was filed carrying `deps: Block G`, the generated module came out holding
`deps: ["Block"]`, and a `PW53-PW58` range came through whole. Both are dangling ids on
a page whose entire job is to say what a line is waiting on.

**The gate caught it and described it as something else.** `every dependency names a
line that exists` failed with `Block is depended on and is not in the roadmap`, which
reads as a typo in the backlog rather than as a parser meeting grammar it does not
implement. Somebody reading that fixes the roadmap, and that is what happened here: both
lines were rewritten to plain ids and the defect stayed.

More cases in `waitingOn` is the wrong repair. The generator already shells out to
roadkeep, and `deps <id>` returns the expansion with its kind, so the answer can be
asked for rather than re-derived — the same argument that stopped a tolerance holding
one default in the config and another in the function using it.

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

### §PW60 A format every piece of which is built, with nothing composing them

`docs/specs/geometry.md` says what a build returns — a mesh and a per-node report — and
the report half exists. `review.report(document, built)` takes the built meshes from its
caller, and every test in the suite supplies that mapping by hand.

Everything either side of the gap is there. Each `op` is a function: `solid.prism`,
`solid.plate`, `solid.inflate`, `solver.carve`, `solver.bevel`, `custom.build`. `expand`
resolves every expression and instances every repeat. `order` returns the nodes in an
order where each input is built before what needs it, which is a walker's scaffolding
with no walker on it. `custom.build(node, instance, built, root=…)` already takes a
`built` mapping of id to mesh, so the convention a builder would fill is written down
and used by one node type.

What is missing is the twenty lines between them: walk `order`, dispatch on `op`,
collect into `built`, hand it to `report`. Nothing under `src/` imports
`polyweave.geometry` at all, so the format is a library no operation calls.

The cost is that the spec's own worked example cannot be produced by any call in the
package, and §PW54 — porting Cottony's `tray_model.py` and `star_model.py` to
declarations — meets this on its first line.

The open question is where the dispatch table lives. `outline.GENERATORS` is the
precedent. `review._says` already enumerates the same op names in an if/elif chain, so
whatever is chosen should be the one list both read, or the two will drift.

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
is the key's share of it, and neither is a parameter the renderer has. An axis the
renderer has no knob for is now refused before a render is spent, but the conversion
itself stays a person's — `exposure` is in stops, and a wrong one is a different picture
rather than an error.

So each model's constants become an acceptance spec, the spec is what `search` aims at,
and the ledger `docs/specs/adoption.md` defines takes the before side for that asset
before it moves. A comparison with one side recorded is refused, and rightly.

### §PW54 A shape that exists only inside a bake cannot be read, diffed or searched

`tools/art/solid.py` is 283 lines of bmesh primitives working in image coordinates
turned on their side, imported by `tray_model.py`, `star_model.py` and any `builder` a
`Model` carries. It exists for a good reason, stated in its own docstring: the second
modelled asset needed the same four operations as the first, and a second copy of a
bevel that took three attempts to get right is a copy that will drift.

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

A fuzzy surface is declarable now: a depth and a coarseness on its material, with the
shells derived (`docs/specs/geometry.md`). What this still meets is §PW60 — a
declaration has no builder, so a ported model is a document nothing can build.

### §PW55 One spend, two ledgers, and neither knows the other

`tools/art/meshy.py` is 540 lines and nearly all of it is now duplicated. It builds its
own payload, carries its own procedure for probing a metered API for free, writes its
own `meshy.lock.json` — task id, exact request, model asked for, cost, and the sha256 of
the sprite that went in and the mesh that came out — and handles the 72-hour expiry
itself, a rule RK88 paid 30 credits to learn and recorded without committing the mesh.

Block D built each of those generically. `purchase.py` holds the budget, the ledger and
what is held; `schema.py` learns the service's own field set rather than restating it;
`reference.py` prepares the drawing; `shape.py` checks the returned silhouette against
it; `normalise.py` orients and scales; `provenance.py` writes the sidecar and the cache
key.

**The port is provable without spending a credit**, which matters because nothing here
spends money on an agent's own judgement. Five meshes are already in `tools/art/3d/`
with their lock entries — `booster_hammer`, `booster_wand`, `scenery_mushroom`,
`friend_plush`, `mascot`. Each entry replays into the plugin's ledger, and the sha256 it
already records either matches the file on disk or does not. A lock entry whose mesh has
moved is exactly the question that file was written to answer, and it has never been
asked mechanically.

A live fetch stays a person's call, and is not what closes this line.

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

### §PW58 The motion block has never run against something a game ships

Block F shipped a skeleton fitted to a mesh, a clip authored once as text, and a sprite
sheet whose atlas is matched to the animation. Every figure it was tested against was
built in code, with its limbs where the plan puts its bones. That is right for the
arithmetic, and it is not proof.

Cottony's entire motion surface is `squash`: the same mesh pressed to 93% of its height,
spread sideways by the square root of that, and re-rendered — because a scaled sprite
squashes its own highlight and its own shadow with it. Two frames, and the game crosses
between them.

So this line splits, and the split is the point. The sheet half is direct:
`sprites.bake`, `sprites.sheet` and `sprites.matched` do what `make_assets.py` composes
by hand, and the settle frames are a real pair to do it with.

The skeleton half gets the treatment RK97 established — look for the half that needs
nothing new before proposing anything. `mascot.glb` and `friend_plush.glb` are bodies
already in the repository and `skeleton.plan` names a joint set to fit them with, so the
fit and its check are runnable today against a mesh a service returned. If the game has
no motion worth authoring beyond the settle, that is a finding worth recording once so
nobody checks twice, and it closes this line as honestly as a clip would.

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
Cottony's own work. The palette and the fonts are the same. What counts is what §PW53 to
§PW58 name, and the gate may report a fraction below one for as long as it says what is
left and why.
