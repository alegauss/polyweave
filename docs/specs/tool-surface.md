# The tool surface

Binds **PW1–PW6**. The contract every call in this plugin obeys.

One measure governs everything below: **a caller gets a call right on the first attempt, and
answers a failure, without opening an implementation file.** Where a rule here does not serve
that, the rule is wrong.

## 1. Calls that take longer than a moment return a handle

Anything expected to exceed roughly two seconds is asynchronous. A bake, a fetch, a capture
and a search all are; a measurement and a config read are not.

```
start  → { job: "j_7f3a", stage: "queued" }
poll   → { job, stage, progress?, started_at, elapsed_s }
result → { job, status: "done" | "failed", … }   # blocks only if asked to wait
cancel → { job, status: "cancelled" }
list   → [ … ]                                   # every job this project knows about
sweep  → { reaped, removed, orphans }            # collect what was abandoned
```

- `stage` is a short vocabulary per operation kind (`queued`, `building`, `rendering`,
  `downloading`, `done`, `failed`, `cancelled`), so a caller branches on a word rather than
  parsing a message.
- **State lives in a file**, `.polyweave/jobs/<job>.json`, so a handle survives the session
  that made it. A session that ends mid-render can be told what happened by the next one.
- **A dead worker is a failure, not a hang.** A job carries the OS process id and a
  heartbeat its worker keeps moving; a `poll` that finds no live process, or a live one
  whose heartbeat stopped, and no result, returns `failed` with the code `job.worker-gone`.
  Both are needed: a pid that no longer exists is conclusive, and a pid that does exist may
  be a stranger who inherited the number.
- `cancel` is not advisory. A search that has found its answer stops paying for the renders
  it no longer needs, which is what makes PW13 affordable. It ends the worker's whole
  process tree, because a worker killed on its own leaves the renderer it started running.
- **An abandoned job is collectable, not a leak.** `sweep` fails every job whose worker is
  gone, kills the descendants that outlived it, and deletes the records of jobs that
  finished long enough ago to be nobody's business.
- **A sweep cannot walk a tree, so the worker leaves a trail instead.** `cancel` walks the
  tree from a living worker; by the time a sweep finds a job abandoned there is no living
  worker to walk from, and on Windows nothing at all connects a dead parent to its
  children. So a worker writes each process it spawns into `.polyweave/jobs/<job>.kids`
  **before** it waits on it — killed a millisecond later, it has still left the trail —
  and a sweep ends those pids directly, reporting how many as `orphans`. Each pid is
  recorded with the process's own start time and is ended **only while that still
  matches**: killing a stranger who inherited the number is a worse failure than leaking a
  renderer, and a sweep that might do it is one nobody will run. A pid the OS will not
  date is left alone rather than guessed at.
- Concurrency is the caller's: four handles is four parallel samples, bounded by
  `[render] max_parallel` in the project config. A `start` beyond that bound is refused with
  `job.at-capacity` rather than queued, because a queue nobody can see is a wait by another
  name.

## 2. Every operation asserts its own output

A success returned over a result nobody checked is the failure mode this plugin exists
partly to remove (§PW2). Before returning, each operation checks what must be true of what
it produced:

| Produces | Asserted |
|---|---|
| A mesh | at least one face; finite bounds; no NaN in any vertex |
| A boolean result | face count is not zero where both operands had faces |
| A render | not a single uniform colour; not fully transparent; dimensions as requested |
| A texture | not fully transparent; not a single uniform colour |
| A field | the file's own bit depth, and distinct values per channel, are what was asked |
| A download | byte length matches the declared length; sha256 recorded |
| A capture | the named artefact exists on disk and is a readable image |

A failed assertion is an **error**, never a warning, and its code names the assertion
(`post.mesh-empty`, `post.render-uniform`). Where an assertion is expensive — a manifold
check on a dense mesh — it is opt-in through the config and off by default, but the cheap
ones above always run.

A check **returns what it measured** — the face count and bounds, the dimensions and alpha
coverage, the byte length and sha256 — because those are the same numbers §PW6 writes
beside the artefact, and measuring them twice is how the two come to disagree.

Where an assertion can be legitimately false, it names the door rather than being dropped:
a picture that really is one flat colour passes on `allow_uniform`, which `bake` exposes so
that a render of one deliberately is possible to ask for.

**Flat is a tolerance, not an equality.** A real render is never exactly anything. An unlit
sphere through Cycles at four samples came back with two distinct colours — `(0,0,0)` across
the subject and `(1,1,1)` on the antialiased edge — so a picture that is black to any
observer passed the assertion that exists to catch it, on one least significant bit (§PW42).
What is measured is the spread across the visible pixels, against `[tolerance] render_noise`.
That floor is deliberately tight: 1/255 is 0.0039 and the floor is 0.0040, so it catches the
render measured above and calls a two-step spread a picture. It can afford to be tight
because `allow_uniform` is the door for a render that really is one colour.

**A speck is not a render, and the bar for it is extent rather than area** (§PW52). A 64×64
render whose only two opaque pixels sit in one corner passes both checks above: coverage
clears the alpha floor because those pixels are fully opaque, and it is not flat because the
two differ. It is empty for every purpose and nothing said so.

The obvious repair is a floor on how much of the frame the subject fills, and it does not
work. A rope or a wand framed exactly right covers about 1.6% of the frame by area — the
same order as the speck — so every area floor high enough to catch the speck refuses the
correctly framed thin asset. `[tolerance] subject_coverage` looks like the key for it and is
not: it means the least of the frame a *photograph's* subject may fill before cutting it out
is worth spending on.

What separates them is how far the subject reaches. `[tolerance] subject_extent` is the
fraction of the frame the subject's bounding box spans along its longer axis, and the two
cases are 1.000 against 0.016. The default of 0.05 comes from rendering the two real meshes
the suite has through the project rig: the booster hammer spans 0.578 and the plush body
0.539, at 0.166 and 0.168 coverage. An order of magnitude of margin on each side, which is
what a number nobody can re-measure on their own assets needs. `post.render-speck` is the
refusal, and lowering the tolerance is the door for an asset that really is that small in
frame.

**A field is its own kind because only the caller knows which one an image is.** A height
field blurred through an eight-bit buffer comes back as a staircase, and every check above
passes it: the gradient is there, it is not uniform, it is not transparent, it is the size
that was asked for. What separates it from a texture is what the image is *for* — a colour
texture with forty distinct levels is fine and a displacement map with forty is broken, and
nothing in the file says which. So the caller declares it by checking a `field` and stating
the precision it meant to keep, and two failures are kept apart because their remedies
point at different code: `post.field-shallow` is the renderer writing too few bits, and
`post.field-quantised` is enough bits holding too few distinct values, which is a buffer
in the middle of the pipeline. The depth is read off the file rather than off the loaded
array, since every image is held here as RGBA bytes and measuring that would measure the
conversion. `luma_bands` in [measurements.md](measurements.md) asks a related question at
display size; this one is about precision in the file, and collapsing the two would lose
both answers.

## 3. Errors are typed, and name the door

```json
{
  "code": "render.no-material",
  "message": "the model 'mascot' carries no material, so the rig has nothing to light",
  "remedy": "set `material` on the model, or pass `glaze: {roughness: 0.22}` to apply the default",
  "detail": "…traceback, for a human…"
}
```

- `code` is a stable kebab-case string, namespaced by area (`render.`, `mesh.`, `fetch.`,
  `post.`, `config.`, `job.`, `geom.`, `spec.`, `op.`, `prov.`, `compose.`, `search.`). It
  is part of the contract and does not change once published.
- `remedy` is the call that closes it with arguments filled in wherever they are derivable.
  Where the choice is a judgement the tool cannot make, it names both doors and what
  separates them. Where only a person can supply the content, it says so and marks the blank.
- `message` never contains a traceback. `detail` may.
- An **unknown field in any input is refused**, never dropped. §PW19 is the lesson: a silent
  drop makes a typo indistinguishable from a working call.
- **A code is declared before it can be raised.** The whole set lives in one table with what
  each means and what produces it, and constructing an error under a code that table does not
  carry is refused. So `explain(code)` can answer every code that exists, and a code
  assembled at runtime — which nothing could enumerate — cannot be built at all.
- `explain(code)` is the read a caller makes when **planning** for a failure, and `remedy` is
  the same answer with the arguments filled in, which is the one to act on. `codes()` lists
  the set, and `capabilities()` carries it, so what can go wrong is knowable before it does.
- An operation putting a boundary around work it did not write turns whatever came out into
  a typed failure, traceback in `detail`. A failure that is already typed passes through
  untouched, because wrapping it would bury the better answer.

## 4. The surface describes itself

- `describe(operation)` returns the parameter set — name, type, range, default, one sentence —
  read from the implementation, so the documentation and the code cannot drift apart. It
  cannot drift because the sentence is **part of the parameter**, carried in its annotation:
  an operation whose parameter has none is refused where it is registered, and deleting a
  parameter deletes its description with it.
- **A declared range is enforced, or it is a comment.** The same declaration that `describe`
  reports is what refuses an out-of-range argument (`op.out-of-range`), so the two cannot
  disagree about what is allowed.
- **One rule with two reaches, not two rules.** The declaration is checked in the caller's
  process before a job spawns, not only in the worker after it has. Otherwise the same
  operation is held to a weaker contract as a job than as a direct call: an elevation of 400
  against a range of −89 to 89 was refused at once through one door and, through the other,
  spawned an interpreter, imported the target and came back a failed job — the expensive way
  to learn what the surface already knew. The registry is consulted **by target**, and the
  plugin's own operation modules are imported to fill it, since registration is a side effect
  of an import and a caller that never imported the module would otherwise be told a real
  operation is not one. A target with no registration — a project's own generator named as a
  file path — is left to the worker's own signature check, which is the only contract it has.
- `capabilities()` returns what this installation can actually do on this machine: which
  renderer and version, whether an engine is reachable, which offscreen route works (PW23),
  whether a service key is present, and the remaining budget. A caller plans against this
  rather than discovering a missing binary three calls later. A version is **asked of the
  binary**, never inferred from a path existing, and a key is reported present or absent and
  never echoed. What no line has established yet is named as pending, with the line that
  will establish it, because "nobody has said" and "there is none" are different answers.
- **Usable and trustworthy are different questions.** A renderer that runs can still hand
  back a colour that is not the one that was authored: the request for the view transform
  that puts back what was put in can be accepted and not take effect, and then every
  `delta_e` in every acceptance spec measures the tone curve as much as the material, and a
  search tunes the lighting to compensate for a transform (§PW43). So `capabilities` renders
  **one known colour** — a flat emission of linear 0.2158605, which is sRGB 128 — and reports
  what came back, alongside the transform in force. An installation that cannot measure
  colour says so, before a spec is written against it, rather than answering confidently.
  The check belongs to the probing read, because it costs a render.
- **What is not yet an operation is still named** (§PW124). `capabilities()` carries
  `unregistered`, every module whose surface is not yet registered with what it is for,
  and `measures`, the vocabulary's names and statistic suffixes. `polyweave.census`
  classifies every public function in the package: a registered operation, an `entry`
  read a caller starts from (`capabilities`, `describe`, `explain`), or, by its module,
  `internal` (a helper an operation calls) or `pending`. `tests/test_census.py` refuses
  one left unclassified and one listed that no longer needs to be. It pins the pending
  count so that count can only fall, and it checks that every operation, code, area and
  measure `capabilities` names can be followed up with a single read. Registered so far:
  `render.bake`, and `accept.check`, `accept.verify` and `accept.check_screen`, which take
  paths because a call's arguments are JSON (§PW147), and `search.sweep`, asynchronous, and
  `search.worth_parallel` (§PW148), and `calibrate.run` and `calibrate.apply`, which takes
  no `person` flag, so an agent calling by name can never overrule a person's bound
  (§PW149), and `verdict.sheet`, `verdict.sitting` and `verdict.judge`, whose choice is
  declared so `validate` refuses a fourth (§PW150), and the ledger's ten `loop.*` calls,
  with the open run passed back and forth as JSON (§PW151), and `port.run` and
  `trace.read` (§PW152), and `provenance.read`, `.verify`, `.unrecorded`, `.dependents` and
  `.outdated` (§PW153), and `render.plan`, `units.check`, `units.engine_scale` and
  `units.read_number` (§PW154), and `measure.take`, which names the four arguments a
  measure takes, `measure.same` and `measure.available` (§PW155), and `geometry.build`,
  `geometry.build_all`, `geometry.describe` and `geometry.variants`, which take a
  declaration's path and its param values as one table (§PW156), and the purchase
  ledger's seven reads and the service schema's three (§PW157), and `engine.find`,
  `engine.run`, `capture.run`, `capture.declared`, `offscreen.routes` and `godot.install`,
  none carrying the hooks its tests stand in with (§PW158), and `shape.check`,
  `shape.silhouette`, `reference.pick`, `reference.prepare`, `normalise.ingest`,
  `compose.place`, `compose.sheet` and `texture.worth_scrubbing` (§PW159). A declared
  `choices` is read off the module's own constant, never retyped beside it. Last, the
  clip's own document (`clip.new`, `.read`, `.write`, `.set_key`, `.retime`,
  `.compiled`), the skeleton's plan and rigged-file reads, and `sprites.matched`. With
  those, nothing is pending. What stays internal says why. Baking a clip still needs a
  mesh and a fitted rig in memory, and a path-based `motion.bake` is §PW160. A module's leftover helpers may be
  listed as internal one function at a time. `describe()` loads
  the registry before answering, so a fresh process no longer lists only what it happened
  to have imported.

## 5. Configuration is resolved per call

Explicit argument, then `polyweave.toml`, then the plugin default — in that order, evaluated
on every call rather than cached at startup, so correcting a config file does not need a
session restart. See [project-config.md](project-config.md).

**Nothing is written outside the project tree.** Working state goes in `.polyweave/`, which
belongs in `.gitignore`. A cache in a home directory is state a repository cannot review and
a colleague cannot reproduce.

## 6. Conventions, fixed once

Stated here so that no other spec has to repeat them and no ingest has to guess (§PW20).

- **Axes: Y up, −Z forward, right-handed.** This is the engine's convention, and the engine is
  what draws the result. Blender's Z-up and glTF's +Z-forward are converted on the boundary,
  in one place.
- **One unit is one metre** unless the asset declares `pixels_per_unit`, which is what an
  asset baked to a pixel grid uses (§PW24).
- **Origin** is the centre of the footprint, on the ground plane — the base of the silhouette,
  not the centre of the bounding box. An asset that flies rather than stands says so on
  ingest (`origin="centre"`), and says which extent its size is stated on
  (`size_on="length"` or `"longest"`), both recorded beside the scale (§PW92).
- **Colour** is sRGB in every authored document and every reported hex value. Linear values
  appear only inside a renderer and are never part of an interface.
- **Angles** are degrees in authored documents, radians nowhere a caller can see.
