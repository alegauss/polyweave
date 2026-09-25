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

A project buying from more than one service gives each its own ceiling, `[budget.<name>]`
with an `amount` and a `unit`, and the ceilings never pool: a spend is judged only against
the ceiling of the service it draws on, which the call names. The contract is in
[project-config.md](project-config.md#more-than-one-paid-service).

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

The result is `[service] schema`, one file per named service, TOML because a person reads and corrects it, and the
client validates against it **before sending**. A typo in a field name becomes a local
refusal instead of a silent no-op, and re-learning after the service changes is one call
rather than an afternoon.

The balance is read either side of the run and the difference recorded in the schema, which
is the only proof that the probing really was free.

## A picture is bought by the plugin itself

`picture.buy` is the first call the plugin sends to a paid service on its own, rather than
capturing what a consumer's client fetched (§PW163). It buys one picture from Ideogram,
by default through the transparent endpoint, whose PNG carries a real alpha channel and so
reads as a drawing to `reference.pick`. It goes through the same doors a mesh does, in the
same order:

1. the payload is checked against `[service.<name>] schema` where one is learned. The models
   spell the prompt differently (`text_prompt` on 4.0, `prompt` on 3.0), so a schema learned
   from one refuses the other's payload before it is sent;
2. `purchase.allow` is asked for the picture's price, against that service's own ceiling.
   The price comes from the project's table, never the caller (below);
3. the request is sent. A 422 is `fetch.prompt-refused`, a 429 `fetch.rate-limited`, and
   anything else `fetch.service-error`. None of them ledgers anything. The client holds no
   more than ten calls open at once in one process, the account's default;
4. the picture is captured at once, because the service's links expire. The entry is
   `bought = "image"`, and the record carries the model, the speed and the resolution the
   answer reported, which may not be the ones asked for.

### A price that says it was quoted

**This is a deliberate exception to reading the balance.** Ideogram publishes no balance
endpoint, so what a picture cost cannot be read off two balances the way a mesh's is
(§PW164). The price is declared instead, in `[service.<name>] prices`, keyed `<model>` for
the speed the service defaults to and `<model>:<speed>` for another. The service bills per
picture returned, so an answer carrying three is charged three prices.

**A quoted price says it was quoted.** Every ledger entry carries `measured`: true where the
cost is the difference between two balance readings, false where it came from the table.
`purchase.remaining` and `purchase.held` report `quoted`, how much of what was spent is a
declared price rather than a reading, so a total never passes off a figure as evidence.

**The ceiling counts quoted spend in full**, because under-counting is the direction that
lets a session pass a ceiling a person set. A model and speed with no row are refused
(`fetch.unpriced`) rather than priced at zero, and a row that is not a number above zero is
refused when the file is read.

**A quote is not trusted forever.** `purchase.reconcile` takes the service's own usage export,
its columns mapped by the caller onto `at`, `cost` and `count` as `adopt` maps a foreign
ledger, and matches each row to the quoted entry nearest it in time, within five minutes,
with the same count of outputs (`outputs` on the entry). The billed amount becomes the
entry's `credits`, the quote stays as `expected_credits`, the entry becomes `measured`, and a
difference sets `surprised`. A row nothing matches is reported under `unmatched_rows`,
because a charge with no entry is money the ceiling never saw. A stale price table is
found on the first reconcile rather than on the invoice.

### A picture its record can make again

Ideogram 4.0 rewrites a text prompt before it draws, and its answer returns the prompt it
drew from, so a record holding only what was sent describes a picture nobody asked for
(§PW165). Three rules follow.

**`json_prompt` is the prompt that is drawn as written.** `picture.buy` takes either a text
`prompt` or a structured `json_prompt` (a high-level description, a background, ordered
elements, and a style), never both, and the structured one only on 4.0. It is sent as a
JSON field and kept on the record.

**The record holds everything a second call needs**: the prompt sent (on the ledger entry),
and on the record's `details` the structured prompt, the prompt the answer says it drew
from (`returned_prompt`), the seed the answer reports, the model, the speed, the aspect ratio
and the resolution. **A seed is asked for only where the learned schema proved the field**
(`fetch.seed-unproved` otherwise), because a dropped seed records a picture as repeatable
when it is not. A call without one still records the seed the answer reports.

**An approved picture can be turned back into a prompt.** `picture.describe` sends a picture
to the service's describe call and writes the structured prompt it returns beside it, as
`<name>.prompt.json`, with a record naming the picture as its input, so the next variation
starts from the approved picture's own terms. It is priced by the `describe` row of `prices`
and ledgered as `bought = "description"`.

### The silhouette is settled on the picture

A picture costs cents and a mesh thirty credits, so the outline is refused on the picture
(§PW168). `picture.gate` takes the pictures bought for one asset and the declared
silhouette. That is a picture of the outline, typically `shape.silhouette` of the mesh
`geometry.build` makes from the asset's declaration. A candidate passes only if every step
does:

1. it is a drawing: a real alpha channel and a clear border (`reference.is_drawing`);
2. its subject fills at least `[tolerance] subject_coverage` of the frame and touches no
   edge of it, because what runs off the frame is what the mesh service invents;
3. its silhouette matches the declared one by IoU against `[tolerance] silhouette_iou`;
4. where the project declares a style, it does not drift from its family's canon
   (`style.drift`).

**A failure is a record, not a re-roll.** Each candidate's answer is written beside it as
`<name>.gate.json` with the prompt it was bought with, the IoU, the centroid offset, the
box difference and which measure drifted which way, so the next prompt is corrected from
it. **No taste enters the choice**: of those that pass, the highest IoU is `chosen`. Where a
person wants to choose, that is a verdict sheet. How many pictures an attempt may buy is
bounded by the ceiling, never by the agent deciding one more is worth it.

The synchronous endpoints carry no task id, so the entry's `task_id` is the service name,
the answer's `created` time and the seed. The asynchronous variants and their poll are not
built yet.

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
Anything that genuinely is a judgement — a pose — stays a parameter, but it now starts from
a known frame rather than an arbitrary one. A lean the drawing already shows is not one of
those, and is read off it (below).

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

It lives in the render path rather than beside the normalise. When it was written a
normalised mesh was rebuilt from vertices and faces and had no texture left to scrub. Since
§PW90 the arrived object is moved in place and keeps its image, but the scrub stays where it
is: it is a judgement per render, keyed with the render, and a stored mesh that had been
scrubbed once would take the choice away from every render after it.

**The lean comes from the drawing too** (§PW91). The twenty-four ways round are quarter
turns of the mesh's own axes, so a drawing that tilts its subject, as Cottony's hammer is
tilted 22 degrees, is matched by turning the four best of them about the view axis a degree
at a time, with no render spent, and the angle is recorded beside the IoU.

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
