# Operations by task

`describe` is the authority: every operation, its parameters, ranges, choices and units.
This page only groups them by what you are trying to do.

| Task | Operations |
|---|---|
| Know the machine | `capabilities` (verb), `engine.find`, `offscreen.routes`, `search.worth_parallel` |
| Start on an asset | `asset.brief`, `loop.pending` |
| Make a shape | `geometry.build`, `geometry.build_all`, `geometry.describe`, `geometry.variants` |
| Render | `render.plan` (free), `render.bake` (costs a render) |
| Measure | `measure.take`, `measure.same`, `measure.available`, `measure.digest` (did the outline move, or only the look) |
| Judge against the bar | `accept.check`, `accept.verify`, `accept.check_screen`, `cost.read` (what it costs to draw), `sound.measure` (a loop's seam, level) |
| Search for numbers | `search.sweep`, `port.run` (a whole family), `trace.read` |
| See it where it is seen | `compose.place`, `compose.sheet` |
| Size a bound from noise | `calibrate.run`, then `calibrate.apply` |
| Carry a person's verdict | `verdict.sheet`, `verdict.sitting`, `verdict.judge` |
| Keep the ledger | `loop.start`, `loop.spent`, `loop.judged`, `loop.finish`, `loop.compare` |
| Read the ledger | `loop.runs`, `loop.assets`, `loop.changes`, `loop.bounds` |
| Provenance | `provenance.read`, `provenance.verify`, `provenance.dependents`, `provenance.outdated`, `provenance.unrecorded` |
| The game side | `capture.run`, `capture.declared`, `engine.run`, `godot.install` |
| Scale against the engine | `units.check`, `units.engine_scale`, `units.read_number` |
| Buy a drawing | `picture.buy` (one picture, against its service's own ceiling) |
| Before buying a mesh | `reference.pick`, `reference.prepare`, `shape.check`, `shape.silhouette` |
| Paid meshes | `purchase.remaining`, `purchase.allow`, `purchase.held`, `schema.validate`, `schema.read`, `schema.proved` |
| The purchase ledger | `purchase.spent`, `purchase.ledger`, `purchase.find`, `purchase.adopt`, `purchase.reconcile` (a quoted price against the bill) |
| After buying | `normalise.ingest`, `texture.worth_scrubbing` |
| Bake a clip | `motion.bake` (the animation and the sheet, from files) |
| Motion | `clip.new`, `clip.read`, `clip.set_key`, `clip.retime`, `clip.write`, `clip.compiled` |
| A skeleton | `skeleton.plan`, `skeleton.shared`, `skeleton.joints_in`, `skeleton.plays`, `sprites.matched` |

A long operation (`asynchronous` in `describe`) takes `--job` on the command line and
answers with a handle; `job poll|result|cancel <handle>` follows it.
