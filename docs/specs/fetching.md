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

**A change a person asked for spends only what they weighed** (§PW308). The ceiling is
approved once for a plan, and a session opened from one click on one picture is not that
plan. Every operation that draws on a balance is marked `spends` in `describe`: `mesh.buy`,
`picture.buy`, `picture.describe`, `picture.vary`, `sound.buy` and `sound.speak`. A window reads that mark
and keeps no list of its own. `purchase.quote(operation, arguments)` prices one call the way
the operation prices itself, by its service's `prices` row for the model it would buy, and
spends nothing. It answers the price, what the ceiling leaves before and after, whether it
is affordable, and `cheaper`, a free operation where one may do (`picture.fit` beside a
picture). A revision's settings put every paid tool under `permissions.ask`, so a saved
allow never lets one run. The window holds the question until its quote is beside it, and a
yes allows that one call. The session's environment carries `POLYWEAVE_REVISION`, so what
it buys enters the ledger tied to the revision, and the revision's closing event says what
the change spent, per service.

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

**A price may be by the character** (§PW320). Speech is billed per character sent, at a
rate the model sets, so one figure per call would overstate a twelve-character tag and
understate a paragraph. A row may name its unit instead of being a number,
`"eleven_v3" = { per = "character", rate = 0.00003 }`, `per` one of `character` and the
rate above zero, or the file is refused when it is read. The call counts what it would
send (`sound.buy` its `prompt`) before anything is sent, and the price is the count
times the rate. `purchase.quote` counts the `text` or `prompt` among the arguments and
answers `per`, `rate` and `count` beside the price; a row by the unit with nothing to
count is `fetch.uncounted`, never priced at zero. A refusal over the ceiling quotes the
count and the rate as well as the sum. Where the service answers `/v1/user/subscription`,
its `character_count` is read before and after the call, and the spend is the difference
times the rate, a measurement (`measured: true`, the quote kept as `expected_credits`). A
reading that fails leaves the quote standing, and the entry says it was quoted.

**A plan that lacks a feature is said so** (§PW410). A 403 from the speech service is
`fetch.plan-lacks`, not `fetch.service-error`: the account's plan does not include what
was asked (voice design is paid plans only), the service's own message is the refusal's
`message`, and nothing is ledgered, since a refused call is not charged.

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
3. its silhouette matches the declared one by IoU against `[tolerance] silhouette_iou`,
   **both framed alike first** (§PW194): each is trimmed to its alpha, fitted with its
   aspect kept into one 256-pixel square and cut hard at half alpha, because where a
   service puts its subject and how large is not the shape;
4. where the project declares a style, it does not drift from its family's canon
   (`style.drift`).

**A failure is a record, not a re-roll.** Each candidate's answer is written beside it as
`<name>.gate.json` with the prompt it was bought with, the IoU, the centroid offset, the
box difference and which measure drifted which way, so the next prompt is corrected from
it. **No taste enters the choice**: of those that pass, the highest IoU is `chosen`. Where a
person wants to choose, that is a verdict sheet. How many pictures an attempt may buy is
bounded by the ceiling, never by the agent deciding one more is worth it.

### The letters are read back

Lettering is what the picture service does best and the one defect no palette or silhouette
measure sees: a letter missing, an accent dropped (§PW169). `picture.letters` holds a
picture to the text it was asked to carry. That is the `text` elements of the structured
prompt on its record, or `texts` where the caller gives them. `picture.gate` runs it on every
candidate.

**The reader is a binary on the machine**, `[paths] tesseract`, found and reported by
`capabilities` under `ocr` the way Blender and Godot are. Its language is the project's
`[capture] locale` (`pt_BR` reads as `por`), so a game in Portuguese is read in Portuguese.
**The comparison folds case and whitespace and never folds accents**, because a dropped
accent is the defect. A refusal gives the text asked for and the text read side by side.

**An absent engine is a stated gap, not a pass.** Without one, the report is
`checked: false` and `passed: null`, and `picture.gate` names the unchecked text under
`lettering_unchecked` rather than letting it through silently.

### A variation is measured against its parent

Refinement is where consistency is lost (§PW170). `picture.vary` sends an approved picture to
the service's remix call (`/v1/ideogram-v3/remix`, with `strength` as `image_weight`) or its
edit call (`/v1/ideogram-v3/inpaint`, with a mask, black where it may change). Each is priced
by the `remix` or `edit` row of `prices`. Both take a text prompt only, so a family's style
is not carried into the request, and is measured afterwards.

**A variation has a parent.** Its record carries the parent's path and digest, the change,
the strength, the region and the mask, with the parent as its input, so
`provenance.dependents` of a replaced parent names every variation made from it.

**The mask comes from the request.** An edit names a `region` by the words of one of the
parent's described elements (`picture.describe`), and that element's box becomes the mask,
written beside the variation as `<name>.mask.png`. A region matching no element, or more than
one, is refused (`fetch.no-region`). A `mask` file may be given instead.

**Outside the mask, nothing should have changed.** `picture.against_parent` compares the
unmasked region with the parent pixel for pixel, pooled, against `[tolerance] delta_e`, and
the silhouette there against `[tolerance] silhouette_iou`. Where a style is declared, it also
holds the variation to its family's canon. What the variation should show stays the
person's verdict.

**A reframe keeps the whole parent** (§PW181). `picture.vary(change="reframe",
resolution=)` sends the parent to `/v1/ideogram-v3/reframe` with the new frame and no
prompt, priced by the `reframe` row, and the new area is drawn in. `against_parent` needs no
mask for it. It searches where the parent landed, at its own size and fitted to the new
frame, at every offset on small copies, then refines the best placement at full size. The
placement's pooled ΔE must sit within `[tolerance] delta_e`, or the reframe redrew what it
was asked to keep. The answer names the `placed` scale and offset. What the drawn-in border
should look like stays the person's.

**A 4.0 request goes to the asynchronous route** (§PW178): `/v1/ideogram-v4/async/generate`,
or `.../async/generate-transparent`. 3.0 has none, its `async/generate` answering 404, so
it goes to `/v1/ideogram-v3/generate` or `.../generate-transparent`, which answer the
picture in the body, and its `task_id` is the answer's `created` and seed (§PW437, probed
with an empty request, which draws nothing). The answer is a `generation_id` at once, so no
connection is held while the picture is drawn. `GET /v1/generations/{id}` is asked every two
seconds until its `status` is `completed` or `failed`, for at most five minutes, so a poll
never answered ends rather than holding one of the account's ten slots. The id is the
entry's `task_id`. `picture.buy` is a `fetch` job, so `--job` runs it in the background,
reporting the poll as `building` and the download as `downloading`. Where the completed
answer reports `usage_cost_usd_micros` and the ceiling is in USD, that is the charge: a
measurement, `measured: true`, with the quote kept as `expected_credits`. A failed
generation ledgers nothing. An answer that already carries its pictures, as a synchronous
one does, is taken as it is, and is identified by its `created` time and seed.

**A picture charged for and never delivered is owed** (§PW179). By the time its link is
read, the service has charged, so a failed download meets two rules: the ledger never names
an asset that is not there, and the ceiling never misses a charge. The charge goes to
`<ledger>.owed.json` beside the ledger, committed with it, holding the task id, the service,
the charge, the link and everything capture needs. `purchase.spent` and `remaining` count
it, and `purchase.held` lists it under `owed`. `picture.collect(task_id)` reads the link
again. Once the picture lands it is ledgered like any other and the charge leaves the owed
list, so it is counted once. A retry that fails again replaces its own entry. A link that
has expired leaves the charge owed for good, because the money went either way.

## A mesh is bought through the plugin

`mesh.buy` is the plugin's own Meshy client (§PW183), so a consumer keeps its prompts and
nothing else. It buys one untextured mesh from a `prompt` (`/openapi/v2/text-to-3d`, preview
mode) or from `picture_path` (`/openapi/v1/image-to-3d`, the picture sent as a data URI,
`should_texture` off), at `model` and `polycount`, against that service's own ceiling:

1. the price is the `prices` row for `model`, and a model with no row is refused;
2. `purchase.allow` is asked, and the account's balance is read;
3. the task is sent and polled every five seconds, for at most fifteen minutes, reporting as
   a `fetch` job's `building` stage;
4. the `.glb` is taken delivery of, the balance is read again, and the difference between
   the readings is the cost on the ledger, `measured: true`.

**A picture must have passed the gate.** `picture.gate` writes `<name>.gate.json` beside each
candidate. `mesh.buy` refuses a picture with none, one the gate refused, or one whose bytes
changed since (`fetch.picture-ungated`). So a mesh bought from a picture always had its
silhouette settled on the picture first. A 402 from the service is `fetch.over-budget` on
the account itself, a 429 `fetch.rate-limited`, and a failed or cancelled task ledgers
nothing.

**Rodin is the third mesh service** (§PW446), for a part that needs clean topology: a
service whose `base` is on `hyper3d` or `deemos` (Hyper3D's v2 API) is spoken to as
Rodin. `model` is its `tier` (`Gen-2` and the like, each with its own `prices` row) and
`polycount` its `quality_override`; the mesh is asked as quads (`mesh_mode = "Quad"`),
`.glb`. The task is posted as a form to `/api/v2/rodin`, words as `prompt` and gated
pictures, views included, each as an `images` file; its jobs are asked after at
`/api/v2/status` by the `subscription_key` it answers until all are `Done` (one
`Failed` ledgers nothing), and `/api/v2/download` lists its files by the task's `uuid`,
of which the `.glb` is taken. Rodin publishes no balance to read, so the ledger records
the project's quoted price with `measured: false`, as a service with no balance does.

**A mesh can be bought from several views** (§PW428). `views` names up to three more
pictures of the same thing beside `picture_path`, a side and a top say, each gated as
the front is; Meshy is sent them in one `/openapi/v1/multi-image-to-3d` task, the front
first as its primary view, so depth the front cannot show, a stick standing off the
face or a trigger behind a shoulder, is drawn rather than guessed. The record keeps the
`views` it was bought from. Views without a front, more than three, or views to Tripo
are `fetch.bad-choice`.

**Tripo is the second mesh service** (§PW445), behind the same call, ceiling, gate and
ledger. A service whose `base` is on `tripo3d` (`https://openapi.tripo3d.com/v3`, its v3
API; v2 is being retired) is spoken to as Tripo: `model` is its `model_version`, such as
`v2.5-20250123` or `P1-20260311`, each with its own `prices` row; `polycount` is its
`face_limit`; texture is off. Words go to `/generation/text-to-model`. A picture is
gated first as for Meshy, and once the spend is allowed it is sent up to `/files` as a
form and named in `/generation/image-to-model` by the `file_token` it answers, since
Tripo takes no picture inline. The task is read at `/tasks/<id>` until `data.status` is
`success`, and `data.output.model_url` is the mesh; `failed`, `cancelled`, `banned` and
`expired` ledger nothing and say Tripo's `error_message`. The balance read either side
is `/account/balance`'s `data.balance`, a decimal. Tripo's free plan is for
non-commercial use, and its API answers no plan, so a Tripo record keeps none; the tier
`provenance.credits` warns on (see provenance.md) is recorded only where a service says it.

## A picture is put on the project's grid on arrival

A picture service returns an image at a size, margin and position it chose, and an icon or
a flat sprite needs the project's (§PW171). That fix is mechanical, so `picture.fit` makes it
once, from the family's `[style]` `cell`, `margin`, `anchor` and `filter`:

- the fringe's colour is replaced by the subject's own, grown outward from its opaque
  pixels, so a halo of the generator's background never reaches the engine. The halo's
  ΔE is measured before and after, and alpha is kept, so the edge stays soft;
- the subject is trimmed to its alpha, then scaled to fit the cell inside the margin.
  `smooth` resamples, and `pixel` is never smoothed: its alpha is all or nothing and its
  colours are taken from the family's palette;
- it is placed at the anchor: `centre` for an icon, `base` (on the bottom margin) for what
  stands on the ground, the convention a mesh's origin already follows.

**The fitted file is what the engine loads**, with a `picture` record naming the original as
its input and carrying the whole transform: trim box, scale, size, offset, cell, margin,
anchor, filter and halo. The original stays on file, so a changed cell is one refit, never a
second purchase. An empty `cell` leaves the size alone and only trims, defringes and pads.

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
low-discrepancy set of barycentric samples, and close the result. A face gets samples in
proportion to its area, taken evenly across the whole set rather than from its head: the
set runs outwards from one corner, so a small face sampled from the head was drawn as a dot
at that corner, and a service's mesh of thousands of small faces as a speckle. Fixed rather than random,
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

## A reference video, read as frames

Rebuilding a known level from a gameplay video meant ffmpeg by hand and hundreds of frame
reads, with no record of the source (§PW328). `reference.frames(video)` samples it into
the work area, `references/<video stem>/` unless `out` says otherwise, and the video
itself is never copied in:

- frames at `rate` a second across the whole video, and denser inside `ranges`, each
  `[start, end, rate]` in seconds; each frame is `t<milliseconds>.png`, named by its
  time, the first sample of a time kept where two stretches overlap;
- `changed` (a share of 0 to 1) keeps a frame only where it differs from the last one
  kept by that mean, so a still stretch costs one frame;
- contact sheets of sixteen frames, four by four with the time burnt into each tile,
  `sheet_001.png` on, so sixteen moments of play are one read; `crop`, `[left, top,
  right, bottom]` in the video's pixels, adds `crop_001.png` on of that strip alone.

`frames.json` lists the frames, sheets and crops with the rate and ranges, and its record
(`capture`, by ffmpeg) has the video as an input with its SHA-256, so what was read is
traced to the file it came from. What happened in the frames, what spawned where on what
path, stays the agent's and the person's reading.

**Another game's footage stays internal** (§PW384). The frames land under `[paths] work`,
and an `out` outside it is refused, so no commit or export reaches them by default. Their
record carries `internal: true`, and everything made from them is internal through its
inputs: `provenance.verify` names any of it git tracks under `leaked`, and a store page is
never cut from it (provenance.md). Nor does a capture run on it (§PW407): `capture.run`
refuses a scene script, or a path among its arguments (a `--name=value` read by its
value), that is internal, with `capture.internal-input`, and `project.check` reports
what git tracks of it as `adopt.internal-tracked`.

**A reference registered once** (§PW407). Named by path each call, a video replaced or
re-encoded between two calls was read as the same one. `reference.register(video, name)`
keeps it in the work area's `references/registered.json`: its path, SHA-256, size and
modification time, and the width, height, frame rate and duration ffprobe reads. A
`[reference.<name>]` declared at another size than the video is refused then, as
`capture.wrong-size`. `reference.frames` takes the name in place of a path, and checks a
path that is registered as well; `frames.json` keeps the name under `reference`. A
registered video whose size or time moved is hashed again, and one whose digest moved is
refused as `fetch.reference-changed`, with the call that registers it again; so is
`reference.events`' reading of the soundtrack the frames came from.

## What moves in those frames, counted

Counting twenty small enemies by eye on every sheet put miscounts in front of the owner
(§PW379). `reference.objects(frames, kinds)` reads the frames `reference.frames` wrote
and finds the objects of each kind the call declares: a `colour` (`#rrggbb`), a
`tolerance` (a share of the widest colour distance, 0.12 unless said) and a `size` range
in the video's own pixels. No game's kinds are built in; they are kept in the record. An
`area` leaves the HUD out. Each frame is read at most 480 pixels wide, its islands of a
kind's colour found four-connected, and positions given back in the video's pixels.

Colour and size alone make two enemies of one colour one kind, and lose a kind whose
colour flares (§PW404). A kind may name `samples`, a few crops of it taken from the
frames as pictures under the project, and a `match` (0.2 unless said). Its islands are
then found at twice its tolerance, and each is kept only where its crop, resized to a
sample's size, differs from the nearest sample by at most `match`, as a share of the
widest colour distance averaged over the pixels. An island two sampled kinds both keep
goes to the one it looks most like. A kind with no samples is found by its colour alone,
as before. The samples and the match are kept with the kinds in objects.json, and each
sample is an input of its record with its digest, so a count can be traced to what it
was matched against.

Detections become tracks, joined to the nearest of their kind in the next frame within
`speed` (a share of the frame's width a second): each track has its first and last
second, its path, and how it ended: `left` where its last sight was at the frame's edge,
`gone` where it vanished inside it, `alive` where the last frame still holds it. Tracks of
one kind born within `together` seconds and `apart` of the frame's width of one another
are a group, with when it was born, its count, how its members ended, and a formation:
`line` where their birth places lie along one axis, `ring` where they sit round a centre
at one radius, else `cluster` (`single` and `pair` below three). `objects.json` lands
beside the frames with its record (`capture`, the frames as its input), and
`objects_001.png` on are the frames with each track's id drawn where it was seen, so the
counts are checked against the picture rather than taken on trust.

## A reference's fixed places, and its minimap read

A radar a few dozen pixels high is guessed from a contact sheet, not read (§PW380). A
project declares a video's fixed places once, as `[reference.<name>]` in polyweave.toml
(project-config.md): the source frame's `size`, `regions` as rectangles in its pixels,
which region is the `minimap`, its `map` shape, the `player`'s blip colour and each other
blip's. Frames of another size than `size` are refused (`capture.wrong-size`).

`reference.regions(frames)` lays each region out on sheets of its own,
`region_<name>_001.png` on, each tile enlarged `scale` times with nearest neighbour so a
dot stays a dot, its time on it; a strip four times wider than tall is stacked one to a
row. `reference.minimap(frames)` reads the minimap per frame: each blip of a declared
colour within `blip_size` pixels, placed as shares across and down the region. On a
`strip` map, whose left and right ends meet as a cylinder's do, a place is also an angle
from 0 to 360, and each blip's angle from the player's, -180 to 180, says whether it is to
the player's `left` or `right`; on a `rect` map the offset is the shares across and down.
`minimap.json` lands beside the frames with how many of each blip stood on each side frame
by frame, recorded with the frames as its input and the declaration as its params.

## A timeline to split a reference at

A video has no markers, so where a wave begins was found by watching frames (§PW381).
`reference.events(frames)` lays the game's own signals on one timeline, in seconds from
the start:

- `numbers_in`, regions of the reference holding a number (a score, a counter), read
  per frame by the OCR engine at `[paths] tesseract`, enlarged three times; each change
  is an event with its `from` and `to`, and each frame where no number was read is
  listed under `unread`, never guessed. Without an engine every region is said unread.
- flashes: frames where the `play` region's mean brightness, or the share of its pixels
  that moved by more than 0.12 since the frame before, stands above the video's own
  median by six times its median absolute deviation; the frame after one, which changes
  as much going dark again, is the same flash and not a second.
- onsets: the soundtrack's strong onsets, taken through ffmpeg as mono at 11,025 Hz and
  found as the peaks of its spectral change above the level `sound.measure` holds a
  seam to, each timed at the end of the window it first shows in, less half a hop.
- sections (§PW405): where the music changes section, from the same soundtrack read in
  half-second windows, each its log energy in 24 log-spaced bands from 60 Hz with one
  more for silence, so every silence is alike. A checkerboard kernel two seconds a side
  over their cosine self-similarity is the novelty, 1 where one sound turns into a
  wholly unlike one; its peaks above six median absolute deviations, a quarter of its
  strongest and 0.05, two seconds apart, are the sections.

`events.json` holds them with what could not be read and whether the sound was, recorded
with the frames as its input. `events.png` is the timeline under its frames: at most 30
thumbnails at a fixed step, ten to a strip, each with its second, and under each a row a
kind with a tick where each event falls in that thumbnail's stretch and a number's new
value beside it, so what a tick was is read without opening the frames. Which event
begins a wave stays the agent's reading.

## A rebuilt level laid against its reference

Where a rebuild plays differently was found by looking at the game and the video apart
and remembering both (§PW382). `reference.compare(reference, capture, kinds)` takes both
as `reference.frames` folders, the game's capture sampled from `capture.movie` the same
way, and counts the objects of `kinds` in every frame of each (`capture_kinds` where the
game's colours differ). It aligns them by `offset`, the seconds the game runs ahead, or
by `anchor = "first"`, the first second an object shows on each side. Each reference
second is paired with the game's nearest aligned frame; one aligned outside the game's
footage by more than half its step is listed as `unmatched`, never compared with its
edge frame. A second whose counts differ by more than `bound` is a gap, with both frames
and both counts. `compare.json`, recorded with both sides as inputs, holds the counts,
gaps and unmatched seconds; `compare_001.png` on pair the reference frame with the
game's, and `compare_counts.png` charts both counts over the reference's time. A gap is
a bug or a choice by the owner's word, not by this.

A gap alone reads as "the game shows three where the video shows five", which a fault in
the game and a wave declared differently both explain (§PW406). Given the rebuilt
level's declared `wave` (its events, as `measure.pressure` reads them, or `wave_file`,
the file the game wrote them to) and `wave_at`, the reference's second its zero falls
on, the declared `alive_slow` curve is drawn on the chart in steps a second on its own
axis, `compare.json` holds it under `declared`, and each gap carries `declared`, what the
wave had alive at that second. A wave's file is an input of the record; an inline wave
is kept with its params. A call without a wave is as before.

## A transcription a person checks row by row

What the agent read from a video was checked as free prose, citing no frames, with the
corrections kept in a conversation (§PW383). A transcription is a file the agent writes,
JSON or TOML: the `frames` folder it read, the `columns` it reads, and `rows`, each with
an `id`, the seconds `from` and `to`, a value for every column, and the `frames` (file
names in frames.json) or `tracks` (ids in `reference.objects`' objects.json) that support
it. `reference.transcription(sheet)` refuses a row citing nothing that exists
(`capture.bad-transcription`), records the sheet against the frames, and lays out a
sitting of kind `transcription` (`[paths] work`/review/<sheet> unless `out` says): one
card a row, up to six of its cited frames side by side, its span and values as its words.

On the review page, or through `verdict.answer`, the person answers each row: right, or
wrong or unsure with the right value in their words. `verdict.judge` keeps each answer
beside the sheet, `<sheet>.answers.jsonl`, with when, and that is the only door into it.
`reference.transcribed(sheet)` reads each row's latest answer back: which are unanswered,
what was corrected and in whose words, and `accepted` only where every row is answered
and none is wrong. The agent never accepts its own reading.

## Still to come in this block

The service client itself, and the lock that stops two sessions spending at once.
`provenance.md` already pins the fields a `fetch` record carries.
