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
sweep  → { reaped, removed }                     # collect what was abandoned
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
| A download | byte length matches the declared length; sha256 recorded |
| A capture | the named artefact exists on disk and is a readable image |

A failed assertion is an **error**, never a warning, and its code names the assertion
(`post.mesh-empty`, `post.render-uniform`). Where an assertion is expensive — a manifold
check on a dense mesh — it is opt-in through the config and off by default, but the cheap
ones above always run.

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
  `post.`, `config.`, `job.`, `geom.`, `spec.`). It is part of the contract and does not
  change once published.
- `remedy` is the call that closes it with arguments filled in wherever they are derivable.
  Where the choice is a judgement the tool cannot make, it names both doors and what
  separates them. Where only a person can supply the content, it says so and marks the blank.
- `message` never contains a traceback. `detail` may.
- An **unknown field in any input is refused**, never dropped. §PW19 is the lesson: a silent
  drop makes a typo indistinguishable from a working call.

## 4. The surface describes itself

- `describe(operation)` returns the parameter set — name, type, range, default, one sentence —
  read from the implementation, so the documentation and the code cannot drift apart.
- `capabilities()` returns what this installation can actually do on this machine: which
  renderer and version, whether an engine is reachable, which offscreen route works (PW23),
  whether a service key is present, and the remaining budget. A caller plans against this
  rather than discovering a missing binary three calls later.

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
  not the centre of the bounding box.
- **Colour** is sRGB in every authored document and every reported hex value. Linear values
  appear only inside a renderer and are never part of an interface.
- **Angles** are degrees in authored documents, radians nowhere a caller can see.
