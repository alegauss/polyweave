# Operations by task

`describe` is the authority on every operation, its parameters, ranges and units. This
page groups them by task.

| Task | Operations |
|---|---|
| Adopt | `project.init` (`init`), `project.check`, `project.inventory`, `kit.list`, `kit.install`, `kit.update`, `kit.prove` |
| Know the machine | `capabilities` (verb), `engine.find`, `offscreen.routes`, `search.worth_parallel` |
| Start on an asset | `asset.brief`, `loop.pending` |
| Make a shape | `geometry.build`, `geometry.build_all`, `geometry.describe`, `geometry.variants`, `geometry.fit`, `geometry.compare` (voxel models) |
| Render | `render.plan` (free), `render.bake` |
| Measure | `measure.take`, `measure.same`, `measure.available`, `measure.digest`, `measure.contrast`, `measure.pressure`, `measure.flashes` |
| Judge against the bar | `accept.check`, `accept.verify`, `accept.check_screen`, `cost.read`, `sound.measure` (seam, level), `sound.speech`, `sound.declared` (declared audio, what is missing) |
| Search for numbers | `search.sweep`, `port.run` (a whole family), `trace.read` |
| See it where it is seen | `compose.place`, `compose.sheet`, `store.capsules`, `picture.vector` |
| Size a bound from noise | `calibrate.run`, then `calibrate.apply` |
| Carry a person's verdict | `verdict.sheet`, `verdict.sitting`, `verdict.judge`, `verdict.promote`, `sound.sitting`; `review` shows a sitting, `verdict.answers` resumes from it |
| Asked changes | `revision.ask`, `revision.open`, `revision.turn`, `revision.check`, `revision.settings`, `revision.close` |
| Keep the ledger | `loop.start`, `loop.spent`, `loop.judged`, `loop.finish`, `loop.compare` |
| Read the ledger | `loop.runs`, `loop.assets`, `loop.changes`, `loop.bounds` |
| Provenance | `provenance.read`, `provenance.verify`, `provenance.dependents`, `provenance.outdated`, `provenance.unrecorded`, `provenance.credits`, `provenance.generated`, `provenance.borrow` |
| The game side | `engine.check`, `capture.run`, `capture.movie`, `capture.declared`, `engine.run`, `engine.sweep`, `engine.cost`, `godot.install` |
| Drive a game | `game.open`, `game.query`, `game.input`, `game.step`, `game.wait`, `game.call`, `game.set`, `game.shot`, `game.text_fit`, `game.close`, `game.batch`, `game.keep`, `game.record_flow`, `game.crash_read`, `game.rekey`, `game.replay`, `game.release_check` |
| Scale against the engine | `units.check`, `units.engine_scale`, `units.read_number` |
| World | `world.read`, `world.validate`, `voice.design`, `voice.choose`, `voice.lines`, `words.check`, `words.unlisted`, `words.glyphs`, `words.sheet` |
| Music | `music.validate`, `music.to_midi`, `music.render`, `sound.synth` (effects from a seed), `sound.buy`, `sound.speak` (paid) |
| Visual effects | `vfx.build`, `vfx.preview`, `panel.build` (a menu panel), `panel.capture`, `icons.build` |
| A project's look | `style.read`, `style.drift` (before a person looks; only `verdict.judge` grows a canon) |
| Buy a drawing | `picture.buy`, `picture.gate`, `picture.letters`, `picture.describe`, `picture.vary`, `picture.against_parent`, `picture.fit`, `picture.collect` |
| Before buying a mesh | `reference.pick`, `reference.prepare`, `reference.frames`, `shape.check`, `shape.silhouette`, `shape.turntable` |
| Paid meshes | `mesh.buy`, `purchase.remaining`, `purchase.quote`, `purchase.allow`, `purchase.held`, `schema.validate`, `schema.read`, `schema.proved` |
| The purchase ledger | `purchase.spent`, `purchase.ledger`, `purchase.find`, `purchase.adopt`, `purchase.reconcile` |
| After buying | `normalise.ingest`, `texture.worth_scrubbing` |
| Bake a clip | `motion.bake` (from files) |
| Motion | `clip.new`, `clip.read`, `clip.set_key`, `clip.retime`, `clip.write`, `clip.compiled` |
| A skeleton | `skeleton.plan`, `skeleton.shared`, `skeleton.joints_in`, `skeleton.plays`, `sprites.matched` |

A long operation (`asynchronous` in `describe`) takes `--job` on the command line and
answers with a handle; `job poll|result|cancel <handle>` follows it.
