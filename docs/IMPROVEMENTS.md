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

### §PW76 The stars are the asset that moves first

PW36 and PW53 were both set aside waiting for the same thing: which asset moves first,
and what its before-side baseline is. The four progress stars are the answer.

They are the smallest port that is still a real one. `star_model.builder` makes the
geometry from code, so no mesh enters Git, nothing is fetched and nothing is paid for.
What is hand-found is the rig alone, and it is three numbers: `light=1.85`,
`ambient=0.42`, `key=0.14`, with a `plate` that sets the resolution.

What makes them worth being first rather than merely easy is that they are four sprites
off one geometry, in two hues at two sizes. An exposure fitted to one picture would pass
on one and fail on the other three, so a port that holds is evidence the search
generalises across a family rather than having been fitted.

The bake file already says why the rig is shaped this way — a star's whole read is which
facet catches the light, which is why the ambient is dropped and the key narrowed. That
sentence is the bar, and stating it as something measurable is the work.

The baseline is recorded: the re-bake is pixel-identical, and the specs are
`docs/design/accept/star_*.accept.toml`. `tools/art/search_stars.py` fits the 96 px gold
and exits 1 until one rig passes all three. At key 15, ambient 6, the gold holds at both
sizes and the dim's p99 reads 0.397 against 0.37, yet at display size matches the
shipped sprite (`.polyweave/stars/compare.png`). A person decides which is wrong.

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

### §PW85 A covers bake reports a size it did not draw

Found porting the stars (§PW76). A final-rung bake with `covers = [96/112, 96/112]` at
112 px a unit wrote a 96 by 96 picture and answered `"size": 1024`, which is the rung's
square and not anything that was drawn.

`bake` computes `frame` from the declaration and renders at it, then builds its answer
from `chosen["size"]`, the plan's number from before the declaration was read. The
provenance record is right, because it is taken off the file. The answer is the half a
caller reads, and an agent comparing the answer against a spec's `display` or its own
`units.check` is told a size nothing has.

The fix: answer with `list(frame)`, which is the size that was rendered in every case,
and keep the rung's square as `rung_size` if anything reads it. Nothing in `src/` does
today; the tests that assert `size` do so on square rungs, where the two agree. Also
check the cache-hit path in `_from_cache`, which reports the same number for the same
reason.

### §PW87 A silhouette is scored inside the render's own outline

Found writing the mushroom's spec (§PW77). The same render against the same drawing read
0.916 with no region and 0.856 with `region = "frame"`.

`measure` resolves a missing region to `subject` wherever the image has alpha, and
`_silhouette_iou` intersects both masks with it. The render's mask is the subject, so
the reference is cut down to wherever the render already is. What comes back is the
share of the render the drawing covers, and a render missing half the drawn shape scores
close to one. Every silhouette predicate written without a region reads that way,
Cottony's four star specs included, and it is the default a person writes first.

The silhouette measures compare two shapes, and the region that means that is the whole
frame. So `silhouette_iou`, `silhouette_centroid_offset` and `silhouette_bbox_delta`
take `frame` when no region is named, and a region that is named still bounds both masks
alike, which is what a rectangle is for.

A test states the case: a reference twice the render's area, with the render inside it,
reads about 0.5 with no region named and not 1.0.

### §PW90 Ingest keeps the shape and drops the paint

Found starting on the boosters (§PW80). The hammer and the wand are fetched meshes whose
whole colour is a texture the service painted. `ingest` is the one call that puts an
arriving mesh in the project's frame, and it reads the file with `read_mesh`, which
keeps vertices and faces and nothing else. `write_mesh` then writes what it was given.
So the normalised hammer comes out the right way round, the right size, and white.

Nothing flags it. The record says the mesh was oriented against its drawing at some
silhouette IoU, which is true, and the render that follows is the first place anyone
sees the texture is gone.

`write_mesh` already carries UVs and material groups; the gap is on the reading side.
`read_mesh` should return the UV per vertex where the file has a layer, the reverse of
`_write_uv`, and the materials by reference. A texture is an image, so the written file
has to carry the image the material points at, which the glTF exporter already packs
when the material is on the object it exports.

The narrow version is the one to build: carry the arriving object's materials across to
the one `write_mesh` exports, rather than rebuilding them from a table, and keep the UVs
through the reorientation, which moves points and never re-indexes them.

Test: a textured quad ingested against nothing comes back with its UV layer and a
material whose base colour is fed by an image.

### §PW91 Orient cannot find a lean

Found starting on the boosters (§PW80). The service returned Cottony's hammer standing
upright where its drawing leans it, and `bake_model.py` carries `roll=-22.0`, found by
re-rendering. Leaning it widened its box, so its `fill` had to rise to 0.72 to keep the
drawing's size. Both numbers answer one question, how does the drawing hold this object,
and the drawing is on disk.

`orient` answers the other half of that question already. It projects the mesh's front
silhouette onto a grid for each of twenty-four ways round, scores each against the
drawing's outline, and keeps the best, with no render spent. But the twenty-four are the
mesh's own axes mapped onto the interface's, so every candidate is a multiple of ninety
degrees, and a lean of twenty-two is not among them.

The same projection answers the lean. After the best way round is chosen, turn it about
the view axis across a range, one degree at a time, scoring the same IoU, and keep the
best angle. It costs one rasterisation per degree and no renders. The size then follows
from the drawing too: the leaned silhouette's box against the drawing's, which is what
`fill` was standing in for.

The lean is reported in the record beside the IoU, so the number that used to be found
by hand is now a result a person can read and overrule.

Test: a box leaned by a known angle is found at that angle within a degree.
