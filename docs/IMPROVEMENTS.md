# Improvements

## Block A — What a tool call costs the turn

### §PW6 Every output carries what produced it

A path-traced bake is not byte-reproducible. Two runs of one unchanged scene in Cottony
differed in 29,696 pixels, none of them by more than 1/255. That is normal for the
technique and fatal for attribution: when a render changes, nothing says whether the
scene moved, a library moved, or the sampler simply landed somewhere else. The answer is
a sidecar written beside every artefact recording what produced it. The versions of the
renderer and its bindings, the seed, the sample count, the hashes of every input, the
parameter values, and the elapsed time. It costs nothing to write and it is the only
thing that makes a difference explicable weeks later. It also makes the cache in Block C
correct rather than hopeful, because the cache key is exactly this record. And it is
what allows a regression to be bisected at all: a render that got worse is compared
against the record of the last one that was right, and the fields that changed between
them are the suspect list.

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

## Block B — Seeing the result cheaply

### §PW7 The preview ladder

A material is read on a sphere, and a sphere renders in three seconds where a character
takes two minutes. That ratio is the whole argument. Judging a surface on the final mesh
pays forty times over for an answer the cheap shape already gives, and the only reason
it keeps happening is that nothing makes the cheap path the default. The ladder has
rungs: the same rig and the same material on a primitive; the real mesh decimated, at a
quarter resolution and a low sample count; the full render. A caller asks a question and
the tool answers from the lowest rung that can carry it. A material question stops at
the sphere, a silhouette question needs the real mesh but not the samples, a final
judgement needs everything. Two constraints keep it honest. The rungs must share the rig
exactly, or the cheap answer describes a different scene and is worse than no answer.
And the tool must say which rung it answered from, so a verdict taken at the sphere is
never mistaken for one taken at the top.

### §PW8 The picture comes back with the numbers

Judging a render is one question with two halves: does it look right, and by how much is
it off. Today that is a render call, then a file read to see the image, then a separate
measurement run. Three calls, two of which exist only because the first returned a path
instead of an answer. A render call should return the image itself alongside its
measurements, so the verdict is formed in a single turn. This matters most in a sweep,
where the number of turns is the cost: eight samples at three calls each is twenty-four
round trips for what should be eight. Two details decide whether it works. The image has
to come back at a size worth looking at rather than a thumbnail, which argues for the
preview rung being the default resolution and the full render being asked for by name.
And the measurements have to be the ones a verdict actually needs, which the other lines
in this block define, rather than whatever happened to be cheap to compute.

### §PW9 A look is a distribution

Cottony's board was asserted to be washed out against the concept art. Measured, the
mean saturation was 0.31 against the art's 0.32 and the luma spread matched, so the
claim looked wrong. It was not wrong. At the 99th percentile the board read 0.68 against
the art's 0.88. The averages agreed because most of the board is cream tray, and what
was actually missing was any deeply saturated pixel at all. The lesson generalises well
past that screen: a mean over an image is dominated by whatever covers the most area,
which is almost never the thing being judged, so a comparison reporting only means will
cheerfully agree with a picture that is plainly wrong. Every comparison this plugin
makes should report a distribution rather than a number: percentiles of saturation, of
luma and of hue spread, for the whole frame and for the subject's own silhouette
separately. The masking is half the value, because a prop measured against only its own
pixels is not diluted by whatever background it happens to be sitting on.

### §PW10 Judged in the place it will be seen

An asset that reads correctly on its own can be the one wrong thing in the frame it
lands in. Cottony's first modelled prop looked right in isolation and then sat on a
sheet beside five drawn siblings that each had a soft specular window and a shadow
beneath them; it had a pin-point highlight and floated. Nothing in a solo render shows
that. So a judgement needs its context: the asset composited into the screen or the
sheet it will appear on, at the size it will actually be drawn, beside whatever it will
be drawn beside, with the comparison run against that composite rather than against the
asset's own file. Two forms are worth building. A contact sheet, which places the new
asset among its siblings so that the odd one out is visible at a glance. And an in-place
composite, which puts it into a real capture of the screen it belongs to. Both are
cheap, both catch a class of error that no metric on a lone render can reach, and
neither exists today in any form.

### §PW11 Change is perceptual, not byte-wise

Two runs of one unchanged path-traced scene differ. Cottony measured 29,696 differing
pixels across a render nobody had touched, none of them by more than 1/255. So the
natural question, did this change anything, cannot be asked of the bytes, and a gate
comparing files will fire on every single run. What is needed instead is a comparison
with a tolerance: a perceptual distance between two renders and a stated threshold below
which they are the same picture. That makes three things possible that are impossible
now. A change that should move nothing can be proved to have moved nothing, which is the
only real proof that an opt-in default is genuinely opt-in. A visual regression can be
caught without a person looking at it. And a cache can return a hit without anyone
having to wonder whether the hit was subtly wrong. The threshold is configuration and it
is per comparison, because the bar for sampler noise is not the bar for a silhouette
that has to land within three pixels.

## Block C — The asset compiler

### §PW12 The acceptance spec

Nothing in Cottony's repository states what makes a render correct. The knowledge
exists. The face should read the drawing's own colour, the silhouette should match the
drawn outline, the lobes should separate, the surface should read as cloth at the size
the screen draws it. But it lives in commit messages and in a person's memory, so no
later change can be checked against it and no search can aim at it. The spec is a file
per asset stating the predicates directly: this region reads this colour within this
tolerance, the silhouette's intersection over union against this reference is above this
figure, the 99th percentile of saturation is at least this. Each predicate is one of the
measurements Block B provides, so the vocabulary is closed and every claim is
machine-checkable. This is the line that turns judgement into a gate, and everything
else in this block depends on it existing first. Written for one asset it documents
intent; written for all of them it is a regression suite nobody had to invent
separately.

### §PW13 Search the parameters, do not guess them

Fourteen tuned constants in Cottony's rig were each found the same way: render, look,
change a number, render again. At two minutes a sample that is the single largest cost
in making an asset, and it is a search a machine should be running. Given the spec from
the line above and a cheap render from Block B, the loop is mechanical: propose values,
render at the lowest rung that can evaluate the predicates, score, continue. The space
is small and mostly continuous, so a coarse grid followed by local refinement is very
likely enough before anything cleverer is warranted, and the interesting engineering is
in the evaluation budget rather than in the optimiser. Two things keep it honest. It
searches only the parameters it is told it may search, with ranges taken from
configuration, so it cannot wander to a value that is wrong for reasons the spec does
not capture. And it reports the winner with its score against every individual
predicate, so a spec that was satisfied by an ugly render is visible as exactly that
rather than as a success.

### §PW14 Renders are content-addressed

A search revisits neighbourhoods, and a caller re-runs the same render across sessions.
Without a cache every one of those is paid again at the full price of a path trace. The
key is the provenance record from Block A: the input mesh hash, the parameter values,
the renderer version and the seed. Everything that can change the output is in the key
and nothing that cannot is, which is precisely what makes a hit safe to return rather
than merely likely to be right. The store lives under the project so it can be inspected
and deleted by hand, with a size ceiling and least-recently-used eviction, and it is
excluded from version control. Two refinements matter more than they look. A hit should
be reported as a hit rather than passed off as a fresh render, because a caller timing a
sweep needs to know what it actually measured. And the cache must key the preview rungs
too, since those are the renders a search asks for thousands of times and the full ones
are asked for once.

### §PW15 The search shows its work

A search that returns only its winner is a search nobody can overrule. The failure it
hides is specific and likely: a spec that is satisfiable by a render a person would
reject, where every predicate passes and the picture is still wrong. If the only output
is a set of numbers, that outcome is indistinguishable from success. So the search
returns a trace. The samples it evaluated, each one's score against each predicate, and
a contact sheet of the best handful side by side. A person looks at the sheet, sees that
the top-scoring render is not the one they would have chosen, and now knows the spec is
wrong rather than the renderer. That is the loop this entire block exists for: the spec
is the thing being debugged, and the search is the fastest way yet found to discover
that it is incomplete. The trace is also what makes a result reproducible, since it
records the seed and the search's own configuration beside the samples it scored.

## Block D — Fetching from a paid service without surprise

### §PW16 Validate the shape before paying for it

A generative service reinterprets silhouettes. Cottony sent a wide low cap on a short
stem and got back a tall dome on a long stem, which is thirty credits spent to learn
that the shape was not respected, discovered only once the money was gone. The check
that would have caught it is cheap: render the returned mesh's front silhouette and
compare it against the drawing that asked for it, by intersection over union, against a
threshold. Nothing about that has to happen after payment. Two doors are worth having.
Where the service offers any preview at all, low resolution or watermarked, take it and
run the check there first. Where it does not, the check still runs on arrival and its
result is recorded against the prompt, so the next attempt is informed rather than a
re-roll. Either way the silhouette test becomes part of the fetch instead of something a
person remembers to do afterwards, and a fetch that fails it is reported as a failure
with a picture attached, never accepted in silence.

### §PW17 A paid artefact is captured, not referenced

The service deletes a task's assets seventy-two hours after it completes. One Cottony
run recorded the settings it had proved and did not commit the mesh or its lock entry,
and the mesh is now simply gone: thirty credits spent for a receipt. This is not a
discipline problem, it is a design one. The download and the record have to be a single
transaction, so there is no window in which a session can believe the asset is safe
because a lock file mentions it. The fetch should complete only once the file is on
disk, hashed, and its entry written naming that hash, the prompt or reference that
produced it, the task id, the credits consumed and the date. Everything downstream keys
off the local file and never the remote id. A verification pass then answers the
question that matters, which is whether every artefact the records claim to hold is
actually present and still hashes to what was written down. Today nothing can answer
that at all.

### §PW18 A budget approved once, spent against a ledger

An agent may not decide that a mesh is worth money, and that rule is correct. But it is
enforced today by stopping at each fetch and asking, so a session with five meshes to
fetch stops five times and the work between them stalls. The rule the constraint
actually expresses is about the ceiling, not about the individual call. So a person sets
a budget in the project's configuration, in credits, with an expiry. The plugin spends
against it without asking, refuses the call that would exceed it, and records every
spend in a ledger with the balance read immediately before and after. The delta between
those two readings is the proof of what a call really cost, which is also what makes the
free-probe technique verifiable rather than merely asserted. What is given up is the
per-call veto. What is bought is an approval made once with the whole plan in view
instead of five interruptions. The default ceiling is small, and the ledger is the
artefact a person reviews afterwards.

### §PW19 The schema is learned once and kept

A request the server refuses never enqueues a task, so a rejection is free information:
send an empty payload to learn the required fields, then one field at a time with a
value no enumeration could hold, to make the server print that field's permitted set. It
works, and it is how Cottony's client was written. The trap that makes it honest is that
an unknown field is dropped in silence, so a field passing validation proves nothing at
all. Only an invalid value proves a field is read, and every probe therefore carries a
deliberately made-up field as its control. None of that knowledge is kept anywhere
today. It should be: the probe runs, its results become a schema file in the project,
and the client validates payloads locally before sending. Then a typo in a field name is
a local refusal rather than a silent no-op, and re-learning the schema after the service
changes is one command instead of an afternoon. The balance is read either side of the
probe run and the delta printed, which is the only proof that the probing really was
free.

### §PW20 Normalise on ingest

A generated mesh faces wherever the service left it, at whatever scale, with its origin
wherever the generator happened to put it. Cottony's hammer came back standing upright
where the drawing leans it, and the fix was two angles found by re-rendering until it
looked right, which is a parameter search spent on something that is not a judgement at
all. Orientation, scale and origin are mechanical. The principal axes of the mesh give a
candidate frame, the bounding box gives the scale, and the base of the silhouette gives
the origin. Where the asset has a reference drawing, matching the front view against it
resolves the remaining ambiguity about which way is forward. The normalisation is
applied once on ingest and recorded, so the stored mesh sits in the project's own
convention and nothing downstream carries a correction angle. Anything that genuinely is
a judgement, such as a deliberate lean or a pose, stays a parameter, but it now starts
from a known frame rather than an arbitrary one.

### §PW21 The reference is prepared, not uploaded

Whatever stands in front of or behind the subject in a reference photograph ends up in
the mesh. Cottony sent a picture of a plush toy and got back the logo the toy had been
sitting on, fused into the model as geometry, and no camera move removes it. The
photograph is an input like any other and it should be processed before it is spent on:
cut the subject out, flatten the background to something uniform, check that the subject
fills enough of the frame, and warn where the silhouette touches an edge. Each of those
is a routine image operation and each one prevents a specific failure that currently
costs a whole fetch. The prepared image is what gets stored in the records, so the input
that actually produced the mesh is the one on file rather than whichever original a
person happened to have open. And where the project has already drawn the thing, the
drawing is the better reference, so the tool should say so rather than let a photograph
win by default.

## Block E — One world with the engine

### §PW22 The runner returns a result, not a log

Godot's exit code cannot be trusted. It exits zero after a script error and non-zero
after a clean quit, so the only honest verdict is the line the script printed, the
absence of an error pattern in the output, and the existence of the file it claims to
have written. Cottony's capture driver encodes exactly that: a regular expression for
the success line, another for the three spellings of a script error, a frame budget and
a wall-clock timeout. Every project that drives the engine writes that same thing again
from scratch. It belongs in the plugin: run a scene script and return a structured
result naming the artefacts produced, the errors matched with their line numbers, the
frames elapsed and whether the run was bounded out. The bounds are part of the contract.
A capture settles in a few dozen frames, so a script still running after several
thousand is hung and the tool should say so rather than sit there until a timeout. The
same runner serves tests and measurement runs, which are the same problem with a
different success line.

### §PW23 Offscreen, but really drawn

Godot's headless mode runs on a dummy renderer that draws nothing, so any capture
needing real pixels needs a real window, which means it cannot run where there is no
screen, which means it never runs in a gate. That pushes every visual check onto a
developer's desk and out of automation entirely, and it is the single reason Block B's
comparisons cannot be enforced. There are routes worth trying: a virtual display, an
offscreen swap chain, or rendering into a viewport texture and reading it back inside
the engine rather than grabbing a window. Which of them works on which platform and
driver is the actual research here, and the answer has to hold on the machine this is
developed on before it is worth anything to anyone else. What the plugin should expose
is one call that produces pixels without the caller having to know which route was
taken, plus a diagnostic saying which routes are available on this machine. The payoff
is large: once a screen can be captured with nobody present, every visual comparison
becomes a gate.

### §PW24 Units are a contract, not a coincidence

Cottony's board tray renders at one unit per pixel because somebody set the render
rectangle to exactly the world rectangle the board covers, so that its wells land on a
cell size the game holds separately as its own constant. The two numbers agree because a
person made them agree. Nothing fails if either one moves; the sprite simply lands a few
pixels off the grid and someone notices later, on a screen, by eye. That coupling should
be declared instead. The asset states the world rectangle it covers and the pixels per
unit it is baked at, the engine side states the same, and a check compares them and
refuses a mismatch at bake time. Where the engine can render the asset itself the
problem disappears entirely, which is the stronger version of this line and the reason
it sits in this block rather than in the renderer's. Either way the goal is the same: a
scale disagreement becomes a refusal with two numbers in it, rather than a misalignment
discovered visually three commits later.

### §PW25 A capture declares its environment

The same capture script on two machines gives two different pictures, because the game
picks its language from the machine's locale and nothing in the script says which
language the picture is being taken in. Cottony found this the expensive way and now
checks, with a regular expression, that every capture script both names a locale
constant and actually passes it to the translation server, because naming it and not
setting it passes a naive check and still produces the wrong image. Locale is one of a
family. Resolution, display scale, theme, time of day, random seed, and whatever else
the running game reads from outside itself are each a way for a committed screenshot to
depend on whose desk it was taken at. The runner should take that environment as an
explicit argument, set it, and record it beside the image, and it should refuse a
capture that leaves a declared-relevant setting to chance. What makes this affordable is
that the list of settings that matter is per project and short.

## Block F — Motion

### §PW26 Rig and retarget on ingest

A generated mesh arrives as a static surface with no skeleton, so it cannot be posed at
all, and rigging one by hand is the step that keeps character animation out of reach
entirely. For the shapes this pipeline actually produces, which are stuffed toys, props
and rounded characters rather than anatomically demanding figures, automatic rigging is
tractable: a skeleton fitted to the mesh's own volume, weights solved from proximity,
and a small library of skeletons for the body plans that recur. The retarget half
matters as much as the rig: a clip authored against one skeleton should play on another,
so motion is made once and reused across a cast. Two guards belong here. The rig must be
inspectable, and a render of the mesh in a test pose is the cheapest possible check that
the weights are not tearing it. And it must be re-runnable, because a mesh refetched at
better quality should not cost its animation. Nothing else in this block is reachable
while every mesh is a rigid surface.

### §PW27 Clips, not frame pairs

Motion in Cottony is a second static render of the same mesh squashed to 93 per cent of
its height, which the game crossfades to. That is a real technique and it is the right
answer for one beat, since it keeps the face and the thread at the size they were where
a scaled sprite would not. But it has no way to express anything longer. A walk, a
reaction, an idle, a hit: none of them are two frames. What is missing is a clip as a
first-class object, with a name, a duration, channels over time, and a way to be
rendered at a rung exactly as a still is rendered. Once a clip exists, everything Block
B does to a still applies to it: a preview at low resolution, a contact sheet of its key
poses, a measurement of whether the silhouette stays inside its budget across the whole
clip rather than only at rest. The squash then stays as what it honestly is, a clip of
two poses, rather than being the only thing the pipeline can say.

### §PW28 Curves are data

An animation inside a binary mesh file is a binary track. A timing change to it is
invisible in a diff, unreachable by an edit, and only makeable by re-exporting from a
tool nobody has scripted. That puts the most iterated part of animation, which is the
timing, behind the highest-friction door in the whole pipeline. The clip's authored form
should be text: named channels, keyframes with their interpolation, stated in a file
that a person and an agent can both read and change, with the binary being an export
rather than the source. Two things follow. A review can see that an ease changed, which
is the difference between an animation that can be collaborated on and one that can only
be replaced wholesale. And an agent can adjust a curve directly instead of describing a
change to a tool and hoping, which is the whole reason this line is in the backlog. The
exporter to the engine's own format is then a compile step with a cache, exactly like
the renders in Block C.

### §PW29 One clip, two outputs

The same motion is needed in two shapes. A 2D screen needs frames, as a sprite sheet the
interface crossfades or plays. A 3D scene needs a clip the engine plays on a skeleton.
Cottony has the first and will want the second, and authoring them separately means
keeping two things in step by hand, which is the failure this line exists to prevent.
One authored clip should produce both: the engine's own animation resource for the 3D
path, and a baked sprite sheet with its atlas metadata for the 2D one, rendered through
the same rig so that the two genuinely match rather than merely resemble each other. The
sheet's frame rate, its frame count and its trim are configuration rather than decisions
taken inside code. The value is not only the saved second authoring pass. It is that a
change to the timing lands in both outputs, so a screen playing the sprite version and a
scene playing the clip cannot drift apart without someone noticing.

## Block G — Geometry as a declaration

### §PW30 A shape is a declaration, and data beats a new language

Cottony's tray, star, ball and props are four modules of imperative geometry code. The
tray's docstring is excellent and the shape it describes is still not readable without
running the module, because the shape exists only as the result of executing statements.
That has three costs. Writing one means writing and debugging a program, so the unit of
work is a file rather than an edit. Reviewing one means rendering it. And nothing else
can read it, so no tool can reason about the shape, vary it or check it. The shape
should be data: a document naming parameters, then a tree of operations over them. Data
rather than a new language, because a language needs a grammar, a parser, error messages
and an editor story before it renders its first triangle, and a document in a format
everything already reads needs none of that. The one thing plain data cannot do is
arithmetic, and the tray is a loop over a cell size, so the format needs named
parameters, expressions over them, and a repeat construct. That is three features, not a
language.

### §PW31 The vocabulary comes from the scripts that exist

A format that covers cubes and spheres would leave every real asset in code, which is
the failure mode to design against. The vocabulary should be read off what the existing
scripts actually do, and they are unusually clear about it: a rounded plate, a crowned
plate, a prism, an annulus, a radial array of points about a centre, a boolean carve, a
bevel, a material with a colour and a roughness, and an outline extruded from a
two-dimensional shape function. That last one is the interesting case and the most
valuable, because it is how a star's silhouette becomes a mesh that is not merely
similar to the drawn sprite but is the drawn sprite extruded. So the format needs to
reference a 2D outline the project already has, whether that is a drawn image or a
generator, and treat extrusion as a first-class operation rather than an escape into
code. The list above is small enough to implement and was arrived at by building real
objects, which is a better provenance than a survey of what a modelling package offers.

### §PW32 Geometry parameters join the search

The rig's parameters live in a dataclass and the geometry's live inside Python modules,
so the search in Block C can reach the lighting and never the shape it is lighting. That
split is arbitrary. A bevel radius, a wall thickness, a crown height and a pitch are all
numbers somebody tuned by rendering and looking, exactly like the exposure was. Once
geometry is a declaration with named parameters at its head, those numbers are
addressable, and the search can be handed a mixed space of shape and rig. Two things
have to hold for that to be safe. Rebuilding geometry is more expensive than
re-rendering it, so the search has to know which parameters force a rebuild and order
its sampling accordingly, or it will pay the rebuild cost on every sample. And a
geometry parameter needs a declared range like any other, because a wall thickness that
goes negative does not produce a bad render but an invalid mesh, which is Block A's
post-condition check earning its place.

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
