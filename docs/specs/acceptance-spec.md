# The acceptance spec

Binds **PW12, PW13, PW15**. One file per asset, stating what makes a render of it correct.

Today that knowledge lives in commit messages and in somebody's memory, so no later change
can be checked against it and no search can aim at it. This file is what turns a judgement
into a gate.

`<asset>.accept.toml`, beside the asset or under a directory the project config names.

## Shape

```toml
asset    = "mascot"
artefact = "docs/renders/mascot.png"   # optional: the file `verify` holds to this
rung     = "final"       # the lowest preview rung a verdict may be taken at

[[predicate]]
id      = "face-reads-cream"
measure = "delta_e"
region  = [120, 80, 180, 140]
target  = "#E8D5C4"
max     = 2.0

[[predicate]]
id      = "silhouette-holds"
measure = "silhouette_iou"
against = "docs/design/art/ui/mascot.png"
min     = 0.97

[[predicate]]
id     = "has-a-saturated-tail"
measure = "saturation_p99"
region  = "subject"
min     = 0.85
weight  = 0.5

[search.key]
min = 120.0
max = 900.0

[search.exposure]
min  = -1.5
max  = 1.5
step = 0.1
```

## Rules

**`measure` is a name from [measurements.md](measurements.md).** An unknown name is refused
(`spec.unknown-measure`). The vocabulary is closed on purpose: a spec that accepts any string
is a spec that silently checks nothing, which is §PW19's lesson applied one layer up.

**Every predicate has an `id`.** The search reports a score per predicate and the trace
(§PW15) addresses them by name, so an anonymous predicate cannot be discussed.

**`min` and `max` are the only comparisons.** A predicate states a bound, not an expression.
Anything needing more than a bound is a measure that does not exist yet, and the honest
response is to add the measure rather than to widen this grammar. A predicate with neither
bound is refused: nothing could fail it.

**`target`, `against`, `display` and `delta` are arguments to the measure**, not
comparisons — the colour `delta_e` is measured to, the reference a silhouette is compared
with, the size `luma_bands` counts at. Every other key is refused where it is written, so a
misspelled field is never a claim that reads as checked while it is not.

**A measure whose answer is not a number cannot be bounded.** `region_colour` is a colour and
`saturation` is a set; a bound on either is refused and told to name a statistic instead.

**Bounds produce a margin, not only a verdict.** Each predicate yields pass/fail *and* a
value in `[0, 1]` for how comfortably it passed, normalised against the bound. A pure boolean
gives a search a cliff and nothing to climb; the margin is what makes PW13's parameter search
converge on something rather than wander. The overall score is the weighted mean of the
margins, with `weight` defaulting to 1.

The margin is **continuous on both sides of the bound**, so a failing predicate still reports
how close it came: against a `min` it is `value / min` below the bound and 1 at or above it,
and against a `max` it is `max / value` above the bound and 1 at or below it. A predicate
carrying both takes the worse of the two.

**A bound can say where its number came from** (§PW106). A bare number is still a bound. A
table beside it says which of three it is:

```toml
max = { value = 0.37, origin = "margin", measured = 0.3438 }       # put over a value by hand
max = { value = 0.41, origin = "person", date = "2026-09-24", why = "same star at size" }
min = { value = 0.30, origin = "measured", measured = 0.3207 }     # read off an artefact
```

It takes `value`, `origin`, `measured`, `date` and `why`, and an origin other than those
three is refused (`spec.bad-origin`), because a bound that cannot say where it came from is
the guess this exists to expose. What changes is the failure: each predicate's result names
the bound that decided it (`bound`: the side broken, or the nearer one on a pass, with its
origin), and a miss says what it means — on a `margin` that the number may be what is
wrong, on a `person` bound that the look moved, on a `measured` one that the render
drifted. The check lists the misses on a margin as `guessed`, which is what an agent needs
to choose between searching again and asking. The dim star's 0.37 would have said so.

**A margin is measured from the noise, not chosen by eye** (§PW107). A tail moves more than
a median under the same harmless change, so one margin rule is too loose on one predicate
and too tight on the next. `calibrate.calibrate(spec, accepted)` reads the accepted
render's own record back as the bake that made it, and renders it again under the changes
that should not change the look: two more seeds, the sample count of the rung below, and
the size one eighth smaller and larger (the scale, for a declared rectangle). A
predicate's `spread` is the range of its value across the accepted picture and those.
The proposed bound is the accepted value plus three spreads (`multiple`, stated in the
answer), written as `origin = "measured"` with `measured` and `spread` beside it. It
proposes and writes nothing; `calibrate.apply(spec_path, proposal)` is the separate
call. It rewrites each bound's line in place, so comments survive. It refuses a bound
that moved after the proposal was measured (`spec.stale-proposal`) and one not written
on a single line (`spec.unwritable-bound`), and it leaves a `person` bound alone. `bake`
takes `seed`, `samples` and `size` so the variants can be made, and a search may not turn
any of the three (`search.noise-axis`), because that would pick whichever sample the
noise happened to favour.

**A person's verdict is one sheet and one call** (§PW109). `verdict.sheet(members, out=)`
puts a whole family on one PNG. A member is `name`, `spec`, `new`, and optionally `old`,
`capture` with a crop `box`, and `shown`, the size the game draws it. Each member gets a
row: old, new and the capture at the size shown, with every failed predicate in words
under it, including where its bound came from. The answer carries the same words and the
three choices, so an agent can ask the question without opening the picture.
`verdict.judge(members, choice, why, run=, named=)` carries the reply. `accept` means the
look is right. `look` means the renders go back and the bounds stay, with `named`
blaming the bounds that let it through. `number` means a bound that failed is wrong, and
each failed bound is rewritten to the measured value (rounded outward) as
`origin = "person"`, with the date and the sentence. It is the one writer allowed to
replace a person's bound. Each member's verdict goes into the open loop run with its
check. With no run open, the answer says it was not recorded. The codes are
`loop.unknown-choice`, `loop.no-reason` and `loop.no-failed-bound`, the last for `number`
said of a family that all passes. A sheet and a command, never an editor, and the verdict
stays the person's.

**The sheet is put in front of the person on one local page** (§PW172). `verdict.sitting`
writes `<out>/sitting.json` beside its sheets, with each family's members, sheet and failed
predicates, and lists it in `[paths] work`/`sittings.json`. `python -m polyweave review`
serves one page from static files shipped with the plugin, on the standard library's server,
**bound to 127.0.0.1 and nothing else**, and prints its address. The page is a reader: it
shows `loop.pending`, every listed sitting's sheets and failed predicates, and nothing it
does not read from disk, so it keeps no state and cannot disagree with the files. A file
is served only from inside the project, and only as a picture or a record.

**It has one write**, `POST /api/judge`, which calls `verdict.judge` with the members taken
from the sitting's own manifest rather than from the page, and the person's choice and
sentence. A sitting or family the project never laid out is `loop.unknown-sitting`. The
post must carry `X-Polyweave: 1`, a header a browser will not send across origins without a
preflight this server never answers, so another site open in the same browser cannot post
a verdict.

**Every answer is an event on disk** (§PW173). The page's call appends one line to
`[paths] work`/`answers.jsonl`: when, which sitting and family, the choice, the sentence, and
each member's verdict with the predicates its check read. **`verdict.answers(since, run=)`
is the read**: the answers after `since`, and `latest` to pass next time. Given the agent's
open run, it carries each member's verdict into it as `judge` would have, so a session that
offered five families resumes from what was said without the person repeating it in chat.
Nothing is marked or moved, because a file two sessions both edit is one they race on. The
same file is what a background wait watches instead of polling. The page reads again every
five seconds unless an answer is being written, and shows each family's answers with any
newer candidate for its members, so the person sees their sentence acted on.

**A mark says where** (§PW174). On the page a person may drag boxes over any member's own
picture, in that picture's pixels. The API also takes a loose `outline` of points. With the
answer they become a mask the picture's size, black where marked, in `[paths]
work`/`marks/`, and the answer's `marks` names the member, the picture, **its digest**, the
mask, the shapes and, for a render, the camera it was drawn from. A mark on a member the
family does not have is refused before the verdict is recorded. `picture.vary` bounds an
edit by an explicit `mask` first, then **the newest mark a person drew on that very
picture**, matched by digest so a mark never applies to another picture or an earlier
version, and only then by a described element's box. The record's `mask_from` says which
(`given`, `person` or `described`), and `picture.against_parent` then checks the region the
person drew.

**The refused are shown beside the kept** (§PW175), because a filter nobody sees into is a
filter nobody audits. Every `picture.gate` run appends its answer to `[paths]
work`/`gates.jsonl`. Each candidate carries its failures, its silhouette IoU, every drifted
measure's value, canon, floor and direction, what was left unchecked by name (no OCR
engine, a canon too small to have a floor), and what it cost from which service. The page
lays each run out in two lanes: the kept, and the refused, collapsed and never absent, with
what is left of each service's ceiling read at the time of looking. **A person may promote
a refused picture.** That is the same one write, `verdict.judge`, with the picture taken
from the gate's own log. A member with no acceptance spec carries the gate's refusal as the
tool's verdict, so the answer records the tool refusing what the person accepted, which is
the evidence a tolerance is loosened from. `number` is refused for such a member, since it
has no bound to move.

**Two versions are compared in one place** (§PW176), because a few ΔE of drift or a
silhouette a pixel wider is what side by side hides. Four ways, switchable: side by side;
a slider across one picture, old on one side and new on the other; onion skin at an
opacity the person sets; and a difference map. `GET /api/compare?old=&new=` makes the map
from the pooled per-patch ΔE `measure.same` uses, lit only where a patch is past the
tolerance `same` resolves, so a resampled pixel never lights up. The map is written under
`[paths] work`/`compare/`. A new picture of another size is scaled to the old one's, and
the floor is then the strictest rung's. **The comparison is chosen by what is compared**:
a variation against its parent opens as a slider with its mask laid over, a gate candidate
with no parent against its family's first canon picture as a difference map, and a sitting
member with an `old` as a slider.

**A mesh is turned at the rig's own camera, never a viewer's**, because a mesh seen through
another camera is a mesh seen differently. `shape.turntable(mesh, out=, against=)` bakes
`frames` pictures (eight by default) through the project's own `render.bake`, at the rig's
elevation and distance with its azimuth stepped round the up axis from the rig's own. It
also bakes the front view, the one `shape.check` scores. It writes them and a
`turntable.json` into `out`, listed once in `[paths] work`/`turntables.json`. The page
compares the two newest turntables of one mesh frame by frame, in the same four ways, and
lays `against`, the drawing that asked for the shape, over the front view.

**Each family's canon is seen whole, on one board** (§PW177). `GET /api/canon` returns, per
declared family, every canon picture with the verdict that admitted it, the palette, the
skeleton, and each drift measure's floor. It also returns every floor as it would be
without each picture, so a canon picture that is the outlier widening every tolerance
shows as exactly that. The page loads the boards when asked, since measuring a canon is
heavier than the rest of the page. **The canon changes only by a person's click.** "Add to
canon" on a gate's candidate is the same verdict, `judge` accepting the look with the
member carrying `canon`, and the canon's entry names it. "Take out of the canon" requires
a sentence (`loop.no-reason` otherwise). It moves the picture into `withdrawn/` beside the
canon, with the entry and the removing verdict in `withdrawn/canon.json`, so nothing
drifts against it any more and the removal can still be argued with. A picture not in the
canon is `style.not-in-canon`. Neither door is an operation an agent can call.

**A pass also says how comfortably** (§PW104). The margin is 1 anywhere inside a bound, so
Cottony's stars passed with a facet at 0.4695 under a ceiling of 0.47 and the search called
that nothing left to gain. Each predicate now also carries its `headroom`: the distance to
the nearer bound as a share of the band where there are two, or of the bound itself where
there is one, below zero outside and absent where nothing bounds it. A check reports the
smallest as `headroom` and names its predicate as `tightest`. The verdict is untouched —
passed is still passed. A search whose evaluator measures headroom ranks passing samples by
it and keeps going while a pass still raises it, stopping when one does not; one that does
not measure it stops at the first pass, as before.

**A family is searched as one** (§PW105). `search.family(members)` takes each member as its
own spec and the evaluator that renders it with what it fixes, and hands every sample to all
of them. The sample passes only where every member passes, scores the worst member's score
and has the least headroom any member left, so the search climbs towards what the whole
family accepts; a predicate is named `<member>:<id>`. Fitting on one and checking the rest
stays possible as the held-out test it is. Where nothing passes on every member, the answer
carries a `conflict`: the two predicates on different members that each held somewhere and
never together, with the sample nearest each side, and any predicate no sample ever held.
That is the question a person has to answer, asked by the tool.

**A spec can name the file it holds to its bar, and then binds after the search exits**
(§PW111). `artefact = "sprites/star.png"`, relative to the project, is optional.
`accept.verify(root)`, and `python -m polyweave verify` on the command line, walks every
spec under `[paths] specs` and checks each artefact as it sits on disk, with no render.
Where the artefact has a record, the check uses the rung the record names. Each spec
comes back as `passed`, `failed` (with the failed predicates in words), `missing`,
`refused`, or `unanchored` when it names no file. An unanchored spec is reported, never
given a path guessed from its name, which would be one project's layout compiled in. The
answer's `passed`, and the command's exit status, fail on anything failed, missing or
refused, so a CI job can stand on it. An unanchored spec does not fail.

**The same bar holds on screen** (§PW112). Once the game loads a mesh, its material is what
the player sees and the bake is a reference. `screen = { capture = "captures/title.png",
region = "star" }` names a capture and a rectangle its script printed (see
[engine.md](engine.md)). `accept.check_screen(spec)` checks the predicates on that crop
exactly as on a bake. `verify` gives such a spec a second answer, under `screen`, and the
spec takes the worse of the two. Where the bake passes and the screen fails, `disagree`
says the engine draws it differently from the bake, which is the finding this is for. A
region the capture never printed is `spec.no-screen`, and the refusal names the regions it
did print. The bar stays one file, so moving it moves both checks.

**`rung` is a floor.** It raises the rung a verdict on this asset may be taken at and never
lowers one the predicates themselves require, and a verdict offered from lower down is
refused (`spec.rung-too-low`) rather than quietly accepted.

**`[search.<param>]` is the whole permission.** A parameter not named there is not searched,
whatever the optimiser would like. This is what stops a search reaching a value that is wrong
for reasons the spec does not capture — it can tune the exposure and it cannot decide the
asset should be twice as large. Ranges come from the spec; where a project wants defaults for
a parameter it always searches, they live in `polyweave.toml`. A spec with predicates and no
ranges is not searchable, and a search over it is refused rather than run over nothing.

**`<param>` is a parameter the renderer actually takes**, and one it does not is refused
before a sample is spent (`search.unknown-parameter`, with the near match named). §PW36 found
this the hard way: the example above used to read `[search.light]` and `[search.form]`, which
are Cottony's names for its own rig, and neither is a parameter here. The spec loaded, the
range came back, and the search died on its first sample with a bare `TypeError` — after the
setup had been paid for. A project's names for its knobs do not survive adoption, and the
place to say so is before the renders.

## How the search spends

**The budget is a number of renders, not a wall-clock.** It is the thing being managed, so it
has to be legible and it has to be obeyed exactly: the search evaluates no sample twice and
stops the moment it is spent.

A **coarse grid, then the window closes around the best** — the space is small and mostly
continuous, so this converges without anything cleverer. The grid is as fine as the remaining
budget affords and never coarser than the ends of the range. Each pass halves the window
rather than measuring a neighbourhood from the best value, because a best value sitting dead
centre of its range is the common case and its neighbourhood would be the range it started
as.

**A search that has its answer stops paying.** Once the spec passes with nothing left to
gain, the renders after it buy nothing, and the answer says which of those things ended it.

**A pass is what runs at once, not a sample and not the budget.** The evaluator comes in two
forms: one takes a sample and one takes a whole pass and returns a list in the same order.
The second is what lets four samples be four job handles rather than four waits (§PW45). It
is the pass rather than the whole budget because the stopping above is per pass, and handing
over everything at once would pay for the samples the answer made unnecessary.

**Whether that is worth it is measured, not assumed.** Blender's Python module is a singleton
and cannot render two scenes at once in one interpreter, so a parallel sample pays an
interpreter start — 0.85s, measured. Serial costs `lanes × one`; parallel costs `one + start`.
They cross at `start / (lanes − 1)`, about 0.28s per render at four lanes. Against the ladder
on Blender 5.2.1, four at a time: a sphere renders in 0.24s, so 0.95s serial against 1.09s
parallel, a loss; a final renders in 11.44s, so 45.78s against 12.30s, a win of 3.7×. **So the
dear rung is what parallelism is for, which is what the cheap rung is for not needing it.**

The winner is reported with its score **against every individual predicate**, so a spec that
was satisfied by an ugly render is visible as exactly that rather than as a success, along
with the whole trace of what was tried.

## The trace

A search that returns only its winner is one nobody can overrule, so it writes down what it
rejected: `<name>.json` holding every sample with its score against every predicate, and
`<name>.png` laying the best handful side by side, best first.

The sheet is what closes the loop. A person looks at it, sees that the top-scoring render is
not the one they would have chosen, and now knows **the spec is wrong rather than the
renderer**. The spec is the thing being debugged, and the search is the fastest way yet found
to discover that it is incomplete.

The sheet is assembled **from the cache**, which already holds every sample's picture under
its key, so no sample has to be rendered twice or kept anywhere else. Where the cache holds
none of them there is nothing to lay out, and the trace says so rather than writing a sheet
of the last render repeated.

The seed and the search's own configuration — the budget, the ranges, the rung, why it
stopped — sit beside the samples, because a result nobody can reproduce is one nobody can
check.

## Any picture, not only a bake

Nothing in this format is 3D (§PW113). A predicate is a measure over a region of pixels,
and `accept.check`, `verify` and `check_screen` take a PNG from anywhere. A drawn 2D
sprite, a board screenshot or a sheet some other generator made can be held to a spec in
this same file, with `artefact` naming it. Where its maker has parameters, a search can
turn them through `search.search` with its own evaluator. The renderer stays 3D; the bar
does not have to. Cottony's `check_vivid.py`, a board held at its 99th-percentile
saturation, is a spec with one predicate. It needs nothing new.

**Sound is held to the same file** (§PW113), which the owner decided. A spec whose
`artefact` is a `.wav` (or an `.ogg`, `.flac`, `.mp3` or `.opus` where ffmpeg is on
PATH) bounds its sound measures, and `accept.check`, `verify` and a search read it as
they read a picture:

```toml
asset    = "music_calm"
artefact = "audio/music_calm.wav"

[[predicate]]
id      = "seam"
measure = "seam_flux"
max     = 1.0
```

A sound measure asks nothing of the ladder and reports no rung. `of` names the sound
where the subject is something else, and a sound bound checked on a picture is
refused (`spec.not-sound`). The measures are in measurements.md.

## What it costs to draw

A spec bounds what an asset costs the game as it bounds how it looks (§PW143), so a search
that finds a better look at twice the triangles answers with the predicate it broke:

```toml
[[predicate]]
id      = "budget"
measure = "triangles"
of      = "art/block.voxels.json"
max     = 1200
```

A cost is read off the file the game draws and never off pixels, so it asks nothing of
the ladder and reports no rung. `of` names the file. Where it is left out the cost is read
off the mesh the picture's own record names as its input. A `.glb` answers `triangles`,
`materials`, `draw_calls` (one per primitive) and `texture_bytes` (every embedded image
as uncompressed RGBA8, without mipmaps). A `.voxels.json` answers `cells`,
`cells_drawn` (the skin), `triangles` (twelve per drawn cube), `materials` and
`draw_calls`, and a `.png` answers `texture_bytes`. A cost a file cannot answer is
refused (`spec.no-cost-source`) with the ones it can. `cost.read` gives all of a file's
costs, which is where a first bar is measured.

## What this file deliberately cannot say

Anything no measure can compute. "Reads as cloth rather than paper" is a real criterion and
not a predicate, and pretending otherwise by inventing a proxy for it is how a spec ends up
satisfied by a render a person rejects.

That case is expected, not designed away. It is exactly what PW15's contact sheet is for: the
search returns its best handful side by side, a person sees that the winner is not the one
they would have chosen, and now knows the **spec** is incomplete rather than the renderer.
The spec is the thing being debugged, and the search is the fastest way to find out it is
wrong.
