# Fetching from a paid service

Binds **PW16**, and is where the rest of Block D's contract will go.

## The shape is checked before the credits are

A generative service reinterprets silhouettes. Cottony sent a wide low cap on a short stem
and got back a tall dome on a long stem: thirty credits spent to learn that the shape was
not respected, discovered only once the money was gone.

The check is cheap and **nothing about it has to happen after payment**. Render the front
silhouette — azimuth zero, level, which §6 fixes as the front of a thing — and compare it
against the drawing that asked for it by intersection over union, against
`[tolerance] silhouette_iou`.

**Two doors, in order of preference.** Where the service offers any preview at all, however
low its resolution or however watermarked, take it and run the check there, because that is
the one place the answer arrives before the spend. Where it does not, the check still runs
on arrival, and its result is recorded against the prompt so the next attempt is informed
rather than a re-roll.

**A fetch that fails the check is a failure with a picture attached.** "It came back wrong"
is not actionable; the path of the render and the path of the drawing are. The refusal also
carries how the shape differs — the centroid offset and the largest edge of the bounding
box — because *which way* it is wrong is what a clearer prompt is written from.

Both masks are normalised to one size before comparing, so a 1024-pixel render and a
thumbnail drawing still compare. The render goes through the project's own rig rather than
a camera of its own: a silhouette taken through a different camera is a silhouette of
something else.

## A paid artefact is captured, not referenced

The service deletes a task's assets seventy-two hours after it completes. One Cottony run
recorded the settings it had proved and did not commit the mesh or its ledger entry, and the
mesh is now gone — thirty credits spent for a receipt.

That is a design problem, not a discipline one, so **the order is fixed**:

1. the bytes land on disk and are asserted against the length and digest the response
   declared;
2. they are hashed and the provenance record is written beside them, carrying the task id,
   the prompt or reference, and the credits consumed;
3. **only then** is the ledger entry appended.

The ledger is last so that it can never claim an asset that is not there. The reverse — a
file nothing recorded — is what `verify` finds. Between the two there is no window in which
a session can believe an asset is safe because a ledger mentions it, and a capture that
fails partway leaves no entry at all.

**Everything downstream keys off the local file and its hash**, never the remote id, because
the remote id is the identifier that stops existing.

The ledger is `[paths] purchases`, inside the tree and committed with it: a paid mesh and its
record are one artefact. `held()` answers the question that matters — is every artefact the
project paid for still present and still what it was — and names what each missing one cost.

## The ceiling is approved once, not each call

An agent may not decide that a mesh is worth money, and that rule is right. But enforcing it
by stopping at each fetch and asking means a session with five meshes to fetch stops five
times. What the rule actually constrains is **the ceiling**, not the individual call.

So a person sets `[budget] credits` with an `expires`, and the plugin spends against it
**without asking** and refuses the call that would pass it (`fetch.over-budget`). An absent,
expired or exhausted budget permits nothing at all (`fetch.budget-closed`) — the absence of
a ceiling is never read as permission. What is given up is the per-call veto; what is bought
is one approval made with the whole plan in view.

**The balance is read immediately before and after a spend**, and the difference between
those two readings is what the call really cost. That number, not the caller's expectation,
is what goes in the ledger and counts against the ceiling, and an entry where the two
disagree is flagged. It is also what makes a claim that some call is free checkable rather
than asserted: two equal readings either side of it, written down.

## The schema is learned once and kept

A request the server refuses never enqueues a task, so **a rejection is free information**.
Send an empty payload to learn the required fields; then send a value no enumeration could
hold, to make the server print what that field does accept.

**An unknown field is dropped in silence**, so a field that passes validation proves
nothing at all. Only an invalid value proves a field is read. Every probe therefore carries
a deliberately made-up field as its control, and a field is recorded as `proved` only where
an invalid value came back refused *with the permitted set*. A required field that is free
text can never be proved this way, and the schema says so rather than pretending.

**Every payload the probe sends must be one the server is certain to refuse**, or the
probing is not free. The first pass is guaranteed a refusal by having no valid value for
anything. After that, a field already proved to be enumerated is held at an impossible
value as an anchor — and where no anchor exists the probing stops rather than risk a
request the server might accept and charge for.

The result is `[service] schema`, TOML because a person reads and corrects it, and the
client validates against it **before sending**. A typo in a field name becomes a local
refusal instead of a silent no-op, and re-learning after the service changes is one call
rather than an afternoon.

The balance is read either side of the run and the difference recorded in the schema, which
is the only proof that the probing really was free.

## A mesh is put in the project's frame on arrival

A generated mesh faces wherever the service left it, at whatever scale, with its origin
wherever the generator happened to put it. Cottony's hammer came back standing upright
where the drawing leans it, and the fix was two angles found by re-rendering until it
looked right — a parameter search spent on something that is not a judgement at all.

Orientation, scale and origin are **mechanical**. The **principal axes** of the vertex
cloud give a candidate frame, the **bounding box** gives the scale, and the **base of the
silhouette** gives the origin, which is §6's own convention: a prop whose origin is its
middle is a prop that floats.

What the axes cannot settle is which of them is up and which way is forward. A frame from
the axes alone is determined only up to **twenty-four signed permutations**, and that last
step is settled against the reference drawing — each candidate's front outline against the
drawing's, by intersection over union, the same measure a shape check is held to.

**The outline is rasterised rather than rendered.** Deciding which of twenty-four ways
round a mesh goes is not worth twenty-four pictures, and the outline is arithmetic: project
the vertices along §6's azimuth zero, splat each face over a coarse grid at a fixed
low-discrepancy set of barycentric samples, and close the result. Fixed rather than random,
because an orientation that turns on a seed is not an answer. Both the candidate and the
drawing are fitted to their own bounding box, so what is compared is proportion and outline
and never how either one was framed.

**Where every orientation scores the same, that is reported and not guessed**
(`mesh.ambiguous-forward`). A symmetric mesh, or a drawing that does not distinguish its
front, leaves the question open, and answering it is the judgement this does not make. The
same holds for a mesh too flat or too sparse to have axes at all.

The transform is applied **once, on ingest**, and recorded as one 4×4, so the stored mesh
sits in the project's convention and nothing downstream carries a correction angle.
Anything that genuinely is a judgement — a deliberate lean, a pose — stays a parameter, but
it now starts from a known frame rather than an arbitrary one.

## What the service painted in, and taking it out

A generative service returns a mesh whose texture has **shading painted into it** — a dark
line where a seam was drawn, a smudge where the model thought a shadow belonged. Under the
plugin's own lighting those marks are wrong twice over: they are shadows that do not move
when the light does, and they are darker than anything the rig produces (§PW49).

**The threshold is measured.** On Cottony's real hammer, a 4096-square sheet, the typical
texel sits 0.0000 from its own surroundings, ordinary detail reaches 0.062 at the 99th
percentile, and painted marks reach 0.372. A purely adaptive bar was tried in two spellings
and both broke — a whole-sheet sigma flagged 7.8% because a UV sheet is mostly flat unused
space, and a high percentile flagged nothing on a texture whose marks *were* its own tail.
So the bar is a measured floor of 0.10 that the texture may raise and never lower.

**It runs only where it shows, and only when asked.** Rendering the hammer both ways puts
the scrub 0.0085 apart at the preview rung against a measured noise floor of 0.0315, and
0.0452 apart at the final rung against 0.0187 — invisible on the cheap rung and 2.5× the
floor on the dear one. And it stays opt-in, as Cottony's own pass was per model, because a
dark line somebody drew deliberately and a shadow the service painted look identical to
anything measuring darkness: removing the first is a judgement about what somebody wanted.
The flag is in the cache key, so a scrubbed render is never served for an unscrubbed one.

It lives in the render path rather than beside the normalise, for a plain reason: a
normalised mesh is rebuilt from vertices and faces and has no texture on it by the time it
is written, and the render is where the service's own image is still attached.

## The reference is prepared, not uploaded

Whatever stands in front of or behind the subject in a reference photograph ends up in the
mesh. Cottony sent a picture of a plush toy and got back the logo the toy had been sitting
on, fused into the model as geometry, and no camera move removes it.

A photograph is an input like any other, and every check that would have caught this is a
routine image operation: **cut the subject out**, **flatten the background** so nothing in
it reads as shape, **check the subject fills enough of the frame**, and **say where the
silhouette touches an edge** — what runs off the frame is what the service invents.

**The cut grows in from the frame's own edge.** The background is the pixels within
`[tolerance] background_delta_e` of the ground colour that are *reachable* from the border,
so a pocket of background colour enclosed by the subject stays subject and a patterned
floor stops the fill rather than eating into the toy. The ground colour is the **mode** of
the border and never its average: a subject that runs into the frame makes the border two
colours, and their mean is a third colour that matches neither, which is how a cut ends up
removing nothing at all. Of what is left, **only the largest island is the subject** — and
that is the step that drops the logo, which the fill cannot reach but which is still a
second thing in the picture.

Two refusals, both before the spend: a background that cannot be told from the subject
(`fetch.background-fused`) and a subject too small to be read from
(`fetch.subject-small`). Touching an edge is a **warning** and not a refusal, because a
tight crop is sometimes what was wanted.

The background is made transparent **and** flattened to one colour behind it, because a
service that ignores alpha still has to see something uniform there.

**The prepared image is the one on file**, written under `[paths] references` with its
digest, so the input that actually produced the mesh is recorded rather than whichever
original a person happened to have open. It is written at a bounded size and the cut is
computed on exactly those pixels, so what was measured is what was sent.

**A drawing beats a photograph** and `pick` says so, rather than letting a photograph win
by being the argument that was passed. A drawing is recognised mechanically — a real alpha
channel with a transparent border — and it is passed through untouched, because a picture
with no background does not need one cut away.

## Still to come in this block

The service client itself, and the lock that stops two sessions spending at once.
`provenance.md` already pins the fields a `fetch` record carries.
