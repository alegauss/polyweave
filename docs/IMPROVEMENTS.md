# Improvements

## Block A — What a tool call costs the turn

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

A deferred dep no longer dangles: `generatedPaused` now holds those ids.

### §PW62 A per-rung tolerance whose only caller asks for it without the rung

`render.bake` resolves its tolerances with `config.tolerances()` and names no rung — two
lines after computing `chosen["rung"]`, and a few before handing that same rung to
`measure.measure`. One call tells the measurer which rung it is on and does not tell the
bar.

`Config.tolerances(rung)` is explicit about what naming none means: it takes the
strictest of the table, "the safe way to be wrong". The defaults are `sphere = 0.025`,
`preview = 0.020`, `final = 0.013`, so every render is checked against 0.013 — final's
floor, measured at five hundred samples — including the sphere rung, which runs at four.

For this tolerance the strictest is the wrong direction. `render_noise` is the bar below
which a picture counts as **flat**: the spread across the visible pixels is measured and
anything under the floor is refused as blank (PW42). A lower floor refuses less. So a
sphere render whose spread falls between 0.013 and 0.025 — sampler noise at four samples
— reads as a picture with content, and the assertion passes on exactly the rung its own
evidence came from: an unlit sphere through Cycles at four samples, black to any
observer.

PW44 built the per-rung table, and the one caller that needs it does not ask for it.

The fix is the argument. The test is a flat render at each rung, and it should fail at
sphere before it is made to pass. Worth checking at the same time whether any other
caller knows its rung and omits it.

### §PW63 Three names the renderer takes, meaning something the caller did not ask for

PW36's audit found that `light` and `form` name nothing the renderer has, and the guard
it added refuses an axis no parameter takes. Three more constants are worse than
missing: they share a name with a plugin parameter that means something else, so the
guard passes them.

Cottony's `Model` against the plugin's `Rig`, on the same three words:

- `fill` is how much of the frame the model fills, 0.92. The plugin's `fill` is a fill
  light in watts, default 120.
- `key` is the key's width as a fraction of the framed reach, 0.55. The plugin's `key` is
  the key's power in watts, default 400.
- `ambient` is a multiplier on the rig's ambient, 1.0. The plugin's `ambient` is the world
  value itself, 0.25.

A port that copies `fill = 0.92` across asks for a 0.92-watt fill light and gets a
nearly black picture, and nothing refuses it, because `fill` is a parameter the renderer
really takes. A search handed Cottony's fill range sweeps 0.85 to 0.95 watts and reports
a best among near-identical dark renders.

`search.unknown-parameter` cannot catch this and should not be stretched to. The names
are right and the meanings are not, which no near-match sees.

What would catch it is a declared range or a unit per parameter: 0.92 W is outside
anything a watt-valued knob would declare, and that is checkable without knowing where
the number came from. Whether the range belongs on `Rig` or in the spec is the open
choice.

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
is the key's share of it, and neither is a parameter the renderer has. An axis with no
knob is refused before a render is spent, but the conversion stays a person's:
`exposure` is in stops, and a wrong one is a different picture rather than an error.

So each model's constants become an acceptance spec, the spec is what `search` aims at,
and the ledger `docs/specs/adoption.md` defines takes the before side for that asset
before it moves. A comparison with one side recorded is refused, and rightly.

Set aside: it needs a person three times over, and §PW63 traps a hand conversion.

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
