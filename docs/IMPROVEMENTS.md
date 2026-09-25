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

## Block J — A bar a person sets once

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

### §PW178 Buying a picture asynchronously

`picture.buy` sends the synchronous endpoints, so one call holds a connection open until
the picture is drawn, and ten of them fill the account's default of ten in flight.
Ideogram also takes the same request asynchronously: the answer is a generation id at
once, and `GET /v1/generations/{generation_id}` returns the picture when it is ready.

**Build the asynchronous variant as a job**, the way a long bake already is:
`picture.buy` gains the job kind, the request is sent to the async route, the generation
id is the entry's `task_id` (which is what the synchronous answer never carried), and
the poll is the job's own stage. Capture still happens the moment the poll returns a
link, because the link expires.

What to check before building: the exact async route and the poll's answer shape, which
the public reference names but did not spell out when PW163 shipped. A poll that is
never answered must end on the job's timeout rather than hold a slot for ever.

### §PW179 A paid picture that never arrived

`picture.buy` asks `purchase.allow`, the service draws and charges, and only then is the
picture downloaded. If that download fails, the refusal says the picture was paid for
and gives the link, but nothing is ledgered, because the ledger is written last so that
it never names an asset that is not there. The spend is therefore invisible to `spent`
and `remaining`, and the next call is judged against a ceiling that is too high.

The same window exists for a mesh, but there the balance is read either side, so the
next reading shows the money gone. A picture service reports no balance (PW164), so for
pictures nothing ever shows it.

**The two rules conflict, and neither may give way silently.** One way through is a
second, separate list of charges with no asset: `purchase.capture` is never called, but
the charge is written to a `pending` list that `spent` counts and `held` reports as
lost, until a retry of the link lands the asset and moves the entry into the ledger.
This keeps the ledger's rule (every entry has its file) and the ceiling's rule (every
charge is counted). PW164 shipped `purchase.reconcile`, which already names such a
charge after the fact: a usage row nothing matches lands in `unmatched_rows`. What is
missing is counting it before the next spend, not finding it.

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

### §PW181 Reframing an approved picture

PW170 built two of the three variations its design named: a remix and an edit inside a
mask. The third, reframe (the same picture in another aspect ratio, with the new area
drawn in), was left out because the service's public reference, read when PW170 shipped,
documented no reframe endpoint for 3.0 or 4.0.

A reframe is the variation a game needs most often: one approved character as a square
icon, a tall card and a wide banner. It has the clearest rule of the three. **Everything
the parent held must still be there, unscaled**, and only the added border is new. So
`picture.against_parent` needs no mask from a person. The parent's own frame, placed
where the reframe put it, is the region that must not have changed. Finding where it
landed is an alignment problem: search the offset that minimises the pooled delta E, and
refuse where the best offset still differs.

Build it as a third `change` of `picture.vary` once the endpoint is confirmed, priced by
a `reframe` row of `prices`, and learn its fields by the schema probe before trusting
any of them.

## Block O — A person sees and answers

### §PW175 The refused beside the kept

The agent refuses drift before a person looks (PW167), which is right — and makes the
agent the one filter nobody checks. A picture wrongly refused is never seen, so a bar
set too tight costs good work silently, and the person has no way to find out.

**The page shows the refused beside the kept.** Each family has two lanes: the
candidates offered, and the ones the agent set aside, each with the measure that refused
it, the value, and the floor — palette ΔE 14 against 6, warmer. The refused lane is
collapsed by default and never absent.

**A person may overrule a refusal.** Promoting a refused picture is a verdict like any
other, through `judge`, and it records that the bar was wrong for this one — the
evidence a tolerance is loosened from, where today the only evidence is a person
noticing.

**Every picture carries its numbers.** Beside each candidate: the drift report, the
silhouette IoU where there is one, what it cost, and what is left of that service's
ceiling. A decision is made with the same facts the agent used, never with fewer.

**What was not checked is shown as unchecked.** A measure a family cannot compute — no
spread in a one-picture canon, no OCR engine — appears as a gap by name, so a clean
report is never mistaken for a complete one.

### §PW176 Comparing in one place

Two versions of an asset side by side hide exactly what the drift measures find: a
palette a few ΔE warmer, a line a pixel thicker, a silhouette that grew. Eyes compare a
difference well only when the two are in the same place.

**Pictures, four ways:**

- side by side, at the size the game shows them and at full size;
- a slider across one picture, the old on one side and the new on the other;
- onion skin, one over the other at an opacity the person sets;
- a difference map, computed by `measure.same` against the noise floor, so what lights up is
  what is above noise and not every resampled pixel.

**Meshes, turned.** A glTF is shown as a turntable at the project's own rig angles,
never at a camera of the viewer's choosing — a mesh seen through a different camera is a
mesh seen differently. The reference drawing's silhouette can be laid over the front
view, which is the picture the shape check already scored, now visible.

**The comparison is chosen by what is compared**: a variation against its parent (PW170)
opens as a slider with the mask outlined, a refused picture against the canon as a
difference map. The person can switch.

The viewer loads its 3D library from the plugin's own static files, never from a
network, so the page works offline like everything else here.

### §PW177 The canon on one board

The canon (PW166) is a folder of files and a table in the config. What a family is meant
to look like is therefore never seen whole, and a canon that has quietly become two
styles — the early pictures and the late ones — is found only by somebody opening every
file.

**The page has a board per family**: every canon picture, the palette as swatches, the
prompt skeleton as text, and the spread the drift floor is measured from (PW167), so a
person sees what the canon looks like and how tolerant it made the agent.

**A picture joins the canon by a click, and only by one.** "Add to canon" is a `judge`
with its own choice, recorded with the person's sentence; the canon's record names that
verdict. There is no other route in, so the rule that only a person grows the canon is a
property of the page and not a promise.

**Removing is the same.** A picture taken out of the canon is a verdict too, and the
board shows what its removal did to the floor before the person confirms — a canon
picture that was the outlier widening every tolerance is visible as exactly that.

**Two canons, one page.** A project with several families shows them side by side, so
the icons and the characters of one game can be seen to belong to it, which is the
question Cottony and Spinhole will each ask of their own.
