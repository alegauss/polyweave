# Operations by task

`describe` is the authority: every operation, its parameters, ranges, choices and units.
This page only groups them by what you are trying to do.

| Task | Operations |
|---|---|
| Know the machine | `capabilities` (verb), `engine.find`, `offscreen.routes` |
| Start on an asset | `asset.brief`, `loop.pending` |
| Make a shape | `geometry.build`, `geometry.build_all`, `geometry.describe`, `geometry.variants` |
| Render | `render.plan` (free), `render.bake` (costs a render) |
| Measure | `measure.take`, `measure.same`, `measure.available` |
| Judge against the bar | `accept.check`, `accept.verify`, `accept.check_screen` |
| Search for numbers | `search.sweep`, `port.run` (a whole family), `trace.read` |
| Size a bound from noise | `calibrate.run`, then `calibrate.apply` |
| Carry a person's verdict | `verdict.sheet`, `verdict.sitting`, `verdict.judge` |
| Keep the ledger | `loop.start`, `loop.spent`, `loop.judged`, `loop.finish`, `loop.compare` |
| Provenance | `provenance.read`, `provenance.verify`, `provenance.dependents`, `provenance.outdated` |
| The game side | `capture.run`, `engine.run`, `godot.install`, `units.check` |
| Paid meshes | `purchase.remaining`, `purchase.allow`, `purchase.held`, `schema.validate` |
| Motion | `clip.new`, `clip.set_key`, `clip.retime`, `clip.write`, `skeleton.plan` |

A long operation (`asynchronous` in `describe`) takes `--job` on the command line and
answers with a handle; `job poll|result|cancel <handle>` follows it.
