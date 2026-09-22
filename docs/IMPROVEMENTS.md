# Improvements

## Block A — What a tool call costs the turn

### §PW37 Ending a renderer whose parent is gone

A worker is killed, or simply dies, and the Blender it started keeps rendering. `cancel`
does not have this problem: it walks the tree from a living worker, which both `taskkill
/T` and a POSIX process group can do. `sweep` does have it, because by the time a job is
found abandoned the worker is already gone. On POSIX the process group outlives its
leader, so an orphan is reachable by group id. On Windows nothing connects a dead parent
to its children, and the render runs until somebody opens Task Manager.

The answer is to stop needing the tree. A worker that spawns a renderer records its pid
in the job record before it waits on it, and a sweep ends those pids directly. Two
things make that honest rather than hopeful. The pid is written before the wait, so a
worker killed a millisecond later has still left the trail. And the record needs the
child's start time beside its pid, or the reuse problem the heartbeat solves for the
worker comes straight back for its children — killing a stranger's process is a worse
failure than leaking a renderer, and a sweep that might do it is one nobody will run.

The measure is whether a sweep after a killed worker leaves no renderer behind, on both
platforms. That test needs a real child process rather than a mocked one, because the
whole question is what the operating system does with it once the parent is gone.

### §PW38 The assertion that needs to know what an image is for

Two of the three silent failures the post-conditions were drawn from are asserted now:
the boolean that returned nothing, and the download that stopped early. The third is
not. A height field blurred through an eight-bit buffer comes back as a staircase — the
gradient is still there, the image is not uniform, it is not transparent, it is the size
that was asked for, and every cheap assertion passes it.

What separates it from the checks already here is that it needs to know what the image
is for. A colour texture with forty distinct levels is fine; a displacement map with
forty is broken, and nothing in the file says which it is. So this cannot be folded into
`texture`. It is a kind of its own, declared by the operation that produced it, carrying
the precision it was meant to keep.

The cheap form is a count of distinct values per channel over the subject region,
against a floor the caller states. The honest form also asks what the file's own bit
depth is, because a sixteen-bit PNG holding only 256 levels is a different bug from an
eight-bit one: the first is a buffer in the middle of the pipeline, the second is the
renderer writing too little, and the remedies point at different code.

`luma_bands` in the measurement vocabulary asks a related question at display size. This
one is about precision in the file, and collapsing the two would lose both answers.

### §PW39 One rule with two reaches, not two rules

Two argument checks now exist and they disagree about what a bad argument is. The worker
reads the target's signature in the child process and refuses a keyword the function
does not take. The describe surface reads the operation's registration and refuses an
unknown keyword, a missing required one, a value outside the declared range, and a value
outside the declared choices.

So an operation run as a job is held to a weaker contract than the same one called
directly. A size of 8192 against a range of 16 to 4096 is refused at once by one door
and, through the other, spawns an interpreter, imports the target and comes back a
failed job — the expensive way to learn what the surface already knew.

The parent should validate through the registry before it spawns anything, and the
worker should keep its own check for the targets that are not registered operations: a
project's own generator named as a file path is a legitimate target and has no
registration. That leaves one rule with two reaches rather than two rules.

The obstacle is that the parent does not import the target — deliberately, because a
target may need an environment the parent does not have. So the registry has to be
consultable by name without importing the implementation, which means registration has
to happen somewhere the parent already loads, or the validation has to travel into the
child as data rather than as a lookup.

### §PW40 A number with two homes has no home

`[tolerance] alpha_floor` is 0.02 in the config defaults, and `check("render", path)`
falls back to 0.0 in its own signature. Both are defaults for one number, and they
disagree. An operation that resolves the setting and passes it measures the subject the
project asked for; one that forgets measures every pixel in the frame, including the
background, and neither reports that a choice was made.

The same shape waits for `render_noise`, `silhouette_iou` and `delta_e` as soon as Block
B has a comparison to apply them to. The library functions are deliberately pure — they
take numbers and do not read files, which is what makes them testable and what lets them
run inside Blender — so the resolution belongs at the operation, not inside them.

What is missing is that a pure function currently gets to invent a fallback. It should
not: a tolerance has one home, and a function that needs one should require it rather
than default it. Making the parameter required moves the mistake from a silent wrong
answer to a refusal at the call, which is the trade this whole block is built on.

The cost is that every call site resolves the config first. A resolved tolerances
object, passed once into an operation, would carry all four together and would also give
the provenance record the values actually in force rather than whatever the file holds
when it is read back.

### §PW41 The half of the question verify cannot ask

`verify` walks the records and checks their artefacts. It cannot walk the artefacts and
check their records, because it has no idea which files in a project are supposed to
have one. A mesh that was paid for, downloaded, committed, and never recorded is
invisible to it: there is no sidecar to start from, so nothing is reported and the
project looks sound.

That is the more expensive half of the same failure. A recorded artefact that went
missing costs a re-render. An unrecorded one that was paid for costs the credits again,
and nothing says which of the meshes in the tree those are.

What is missing is a statement of which files are supposed to carry a record. The config
already names the directories that hold produced artefacts — `[paths] meshes` and
`[paths] renders` — and the extensions are knowable from what the plugin writes. So the
check is: every file under those directories with a produced extension has a sidecar,
and anything that does not is named.

The trap is that a project puts hand-made files in those directories too, and calling
each of them a defect makes the report useless within a week. So it has to be ignorable
per path, from the project's config rather than a flag someone remembers to pass. A
report nobody can quieten is a report nobody reads, and this one has to stay worth
reading for the one week in a year when a mesh goes missing.

### §PW42 An assertion about a render needs a tolerance

The check that refuses a render carrying no image asks whether every visible pixel is
the same colour, exactly. A real render is never exactly anything. An unlit scene
rendered through Cycles at four samples came back with two distinct colours — (0,0,0)
across the subject and (1,1,1) on the antialiased edge — so a picture that is black to
any observer passed the assertion that exists to catch it, on one least significant bit.

The fix is a tolerance rather than equality: the range across the visible pixels,
compared against a floor the project already declares a sibling of. `[tolerance]
render_noise` is 0.004, which is one part in 250 and almost exactly the 1/255 seen here,
so the number is already written down and the check is not reading it.

The trap is the other direction. Raise the tolerance far enough and a render that is
nearly flat by design — a matte card, a silhouette study — starts being refused, and the
door out of that is `allow_uniform`, which already exists. So the tolerance wants to be
tight, measured against a real render rather than chosen, and the test that proves it
should be an actual unlit render rather than a constructed array.

Worth doing at the same time: the same equality appears in the transparency check, where
`max(alpha) == 0` has the same problem in reverse — a render whose only non-zero alpha
is one stray edge pixel is empty for every purpose and passes.

## Block B — Seeing the result cheaply

### §PW43 An installation that cannot measure colour should say so

The render path asks Blender for the view transform that puts back what was put in, so a
measured colour and an authored one are the same number. On the bpy module installed
here that request is accepted and does not take effect: the wheel ships without the
colour configuration the transforms are defined in, and the scene keeps the one it had.

It was measured. An emission of linear 0.2158605 — sRGB 0.5, which should land on 128 —
came back at 161 under the default transform and 172 after asking for the standard one.
Neither is 128, and the second is further away than the first, so the request did
something without doing the right thing.

Every predicate in an acceptance spec compares a measured colour against a target. On an
installation like this one, `delta_e` against a hex value is measuring the tone curve as
much as the material, and a search would tune the lighting to compensate for a transform
rather than to match the colour. The failure is silent and the result looks plausible.

The record already carries the transform in force, so a difference is attributable after
the fact. What is missing is the check before it: a known colour rendered and compared
against what it should be, once, as part of what `capabilities` reports — so an
installation that cannot measure colour says so rather than answering confidently. One
small render settles it for every measurement built on top.

### §PW44 The noise floor is measurable, and configuring it is a guess

`[tolerance] render_noise` is one number for a project, and the noise it describes is
not one number. Two seeds of one unchanged scene were measured on a 48-pixel sphere at
four samples and came back 0.046 apart; at sixty-four samples the same pair sat at
0.014. The configured default is 0.004, which is calibrated for a full-size final render
and calls every preview a change.

The separation is not in doubt — a changed material measured 0.75 against both, fifty
times the floor — so the metric works. What is missing is that the floor depends on the
rung a render was taken at, and nothing says so. A caller stating its own tolerance gets
the right answer and one relying on the default does not, which is the defect
configuration removes.

Two ways out. The narrow one is a tolerance per rung: `[tolerance] render_noise` becomes
a table keyed like `[render] samples`, read for the rung the renders already record. The
wider one is to stop configuring the floor and measure it — render the scene twice at
that rung and use the distance between them as the bar. It costs one render and it is
right on any machine at any sample count, which a configured number never is.

The second is better and the first is cheaper, and a measured floor also wants somewhere
to be cached — which is the cache in Block C, so the decision is worth taking after it
lands.

## Block C — The asset compiler

### §PW45 Four samples were meant to be four handles

The job system was built so that four parameter samples are four handles rather than
four waits, and that was named at the time as what makes a search affordable at all. The
search does not use it. It calls its evaluator once per sample and waits for each render
before proposing the next, so a budget of twenty-four samples is twenty-four renders end
to end where the machine could be running four at a time.

The seam is already in place: the evaluator is a function the search is handed, and
everything about rendering is on the far side of it. What is missing is a batched form —
a pass proposes a grid, hands the whole grid over, and gets back a list — and an
evaluator that starts one job per sample, bounded by `[render] max_parallel`, and
collects them.

There is a reason it was not built with the search. The render path drives Blender
through the bpy module in process, and bpy is a singleton that cannot render two scenes
at once in one interpreter. Parallel samples therefore need the worker, so each sample
pays an interpreter start it currently avoids. At four spheres that trade is probably a
loss; at four final characters it is plainly a win, and the crossing point is
measurable.

So the work is a batched evaluator, a job-backed implementation of it, and the
measurement that says which rungs it should be the default for.

## Block D — Fetching from a paid service without surprise

### §PW46 Record what a normalisation derived

Normalising a fetched mesh writes a second file beside the paid one, and nothing records
where it came from. The ledger holds the bytes that arrived and their digest, which
stays true, but the file the rest of the project actually loads is the normalised one —
and to `held()` and `verify` that is a file nothing recorded, the exact shape of the
problem PW17 exists to prevent, arriving from the other direction.

The normalisation already computes everything the record needs: the source path, the
rotation, the scale, the offset and the correction as one 4x4. What is missing is the
write. A derived artefact should carry a provenance record of its own, naming its parent
by hash rather than by path, so the chain from the credits spent to the mesh in the
scene is one a person can follow without guessing which file came first.

That also settles what happens when one mesh is normalised twice against different
drawings. Two records naming one parent is a fact; two files with no records is a
question nobody can answer later.

The open choice is whether the derived record has the same shape as a render's, or a
smaller one carrying only a parent and a transform. The first keeps one vocabulary and
one reader; the second does not pretend a normalisation has an engine, a seed or a
sampler. Prefer the first with the irrelevant fields absent rather than empty, unless
reading the two side by side says otherwise.

## Block E — One world with the engine

### §PW47 Bake at the size the declaration gives

A sprite covering a 4 x 2 world rectangle at 64 pixels per unit has to be 256 x 128
pixels. The renderer produces square pictures at whichever size the rung names, so such
a declaration can only be refused, never met. PW24 put the contract in place and its
refusal names the size it wants; nothing yet renders at it.

Two things stand in the way. The first is the render: `render_to` sets one resolution on
both axes, and the framing centres the subject in a square frame rather than mapping a
stated world rectangle onto the pixels.

The second is the cache key, and that is the part needing care. The key carries the
rung, the seed, the samples, the inputs and the rig; the size rides along only because
the rung implies it. Once a bake can be asked for a size the rung does not imply, the
key has to carry it, or a square render comes back for a rectangular request — a wrong
answer rather than a slow one. The subset is pinned in `docs/specs/provenance.md` and
every cached entry was keyed without it, so the open question is whether the field is
added always or only where a size was asked.

There is an orthographic question underneath. A world rectangle mapped onto pixels is an
orthographic projection; the rig is a perspective camera with a margin. A baked sprite
wants the former, which may mean a rung of its own rather than a parameter.

## Block F — Motion

## Block G — Geometry as a declaration

### §PW33 A declaration is reviewable before it is built

Two wrong constructions of Cottony's tray seats were built before the right one, and
both looked entirely reasonable while being written. Raised bars between the cells gave
a woven basket where the separators read as rungs laid on top of the tray. Cutting those
bars into segments so their bevels would stop fighting turned them into a ladder of
lozenges. Neither was visible until rendered, and rendering is the expensive place to
find a construction error. A declaration can be read before it is built, which is the
point of it being data. Three checks are worth having, in increasing cost: a structural
read that says what the tree does in words, a wireframe or clay preview at the cheapest
rung, and the post-condition that the built mesh is manifold with a plausible face
count. The first two are what a person or an agent looks at before committing to a full
bake. None of them replace judgement, but all three catch the class of error where the
code did exactly what it said and what it said was wrong.

### §PW34 An escape hatch that is a node, not a mode

Any format will eventually meet a shape it cannot state, and the framework that forces
the shape into the format anyway produces worse geometry than the script it replaced. So
the escape hatch is part of the design rather than an admission of failure. A
declaration should be able to name a project-supplied function as one node in its tree,
receiving the declared parameters and returning geometry the rest of the tree composes
with. That keeps three properties that matter. The parameters stay declared, so the
search can still reach them. The provenance record still hashes the code, so a change to
it still invalidates a cache. And the rest of the shape stays data, so only the
genuinely awkward part is code. The rule to hold to is that the hatch is a node and
never a mode: a declaration does not become a script because one operation in it is
custom. Where the same custom node appears in three projects, that is the signal it
should have been vocabulary, and the backlog should record it as such.

## Block H — Proof on a real game

### §PW35 Measure the loop, not the features

Every line in this backlog is a claim that something will be faster or more certain, and
not one of them is measured. The risk is specific: the work gets rearranged rather than
reduced, and the plugin becomes a different way to spend the same afternoon. So the loop
itself is instrumented against a real asset made both ways, recording wall-clock time
from brief to accepted render, the number of renders spent, the number of tool calls,
the credits spent, and how many results were rejected by a person after the tool had
reported them as passing. That last number is the honest measure of assertiveness: a
tool that approves renders a person then rejects has made things worse however fast it
was. The baseline is what the existing pipeline costs today, recorded before anything is
ported so that it cannot be reconstructed favourably afterwards. This line sits late in
the file and is deliberately not optional, because the alternative is a backlog whose
central claim cannot be falsified.

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

### §PW48 Test against what Cottony actually has

Every input the suite has is built in code: a box of stated proportions, a photograph of
a rectangle on a plain ground, a figure whose limbs are where the plan puts its bones.
That is right for the arithmetic — the test states the numbers its assertion depends on,
which a committed PNG never does — so the builders stay.

What it never sees is an artefact anybody made. No mesh from the service, no photograph
of a real object on a real table, no capture from a running game — and those are where
every symptom here was measured.

Cottony has them. `booster_hammer.drawn.png` is the drawing the hammer leans in and
`booster_hammer.glb` is what came back standing upright, which is the case PW20 was
written about. Copies, not a path into another checkout: a test needing a sibling
repository on the same disk is one nobody else runs.

Size is what LFS answers. Drawings are 10–21 KB and stay plain blobs; meshes are 1.7–30
MB and become pointers, by the reasoning Cottony's own `.gitattributes` gives: git keeps
every version whole, and the only fix afterwards rewrites history.

The GDScript in the engine tests belongs in files either way: real code living as Python
string literals full of escaped tabs, where nothing highlights it and nothing lints it.

Which assets earn a place is open. One per failure worth reproducing, not one per asset
Cottony has: the 30 MB mascot buys nothing the 8 MB hammer does not.
