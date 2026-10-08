# Operations by task

`describe` is the authority on every operation, its parameters, ranges and units. This
page groups them by task.

| Task | Operations |
|---|---|
| Adopt | `project.init` (`init`), `project.check`, `project.inventory` |
| Know the machine | `capabilities` (verb), `engine.find`, `offscreen.routes`, `search.worth_parallel` |
| Start on an asset | `asset.brief`, `loop.pending` |
| Make a shape | `geometry.build`, `geometry.build_all`, `geometry.describe`, `geometry.variants`, `geometry.fit` (to a reference), `geometry.compare` (voxel models) |
| Render | `render.plan` (free), `render.bake` (a render) |
| Measure | `measure.take`, `measure.same`, `measure.available`, `measure.digest` (did the outline move, or only the look), `measure.contrast` |
| Judge against the bar | `accept.check`, `accept.verify`, `accept.check_screen`, `cost.read` (draw cost), `sound.measure` (seam, level), `sound.speech` (a voiced line), `sound.declared` (declared audio, and what is missing) |
| Search for numbers | `search.sweep`, `port.run` (a whole family), `trace.read` |
| See it where it is seen | `compose.place`, `compose.sheet`, `store.capsules`, `picture.vector` (SVG layers) |
| Size a bound from noise | `calibrate.run`, then `calibrate.apply` |
| Carry a person's verdict | `verdict.sheet`, `verdict.sitting`, `verdict.judge`, `verdict.promote`, `sound.sitting`; `review` shows a sitting, `verdict.answers` resumes from it |
| Asked changes | `revision.ask`, `revision.open`, `revision.turn`, `revision.check`, `revision.settings`, `revision.close` |
| Keep the ledger | `loop.start`, `loop.spent`, `loop.judged`, `loop.finish`, `loop.compare` |
| Read the ledger | `loop.runs`, `loop.assets`, `loop.changes`, `loop.bounds` |
| Provenance | `provenance.read`, `provenance.verify`, `provenance.dependents`, `provenance.outdated`, `provenance.unrecorded`, `provenance.credits`, `provenance.generated` |
| The game side | `capture.run`, `capture.movie`, `capture.declared`, `engine.run`, `engine.sweep`, `engine.cost`, `godot.install` |
| Drive a game | `game.open`, `game.query`, `game.input`, `game.step`, `game.wait`, `game.call`, `game.set`, `game.shot`, `game.close`, `game.batch`, `game.keep`, `game.rekey`, `game.replay`, `game.release_check` |
| Scale against the engine | `units.check`, `units.engine_scale`, `units.read_number` |
| World | `world.read`, `world.validate`, `voice.design`, `voice.choose`, `voice.lines`, `words.check`, `words.unlisted`, `words.sheet` |
| Music | `music.validate`, `music.to_midi`, `music.render`, `sound.synth` (effects from a seed), `sound.buy`, `sound.speak` (paid) |
| Visual effects | `vfx.build` (particles, ribbon), `vfx.preview`, `panel.build` (a menu panel), `panel.capture` |
| A project's look | `style.read`, `style.drift` (before a person looks; only `verdict.judge` grows a canon) |
| Buy a drawing | `picture.buy`, `picture.gate` (before the mesh is bought), `picture.letters`, `picture.describe`, `picture.vary`, `picture.against_parent`, `picture.fit` (onto the family's grid), `picture.collect` |
| Before buying a mesh | `reference.pick`, `reference.prepare`, `shape.check`, `shape.silhouette`, `shape.turntable` |
| Paid meshes | `mesh.buy` (words, or a gated picture), `purchase.remaining`, `purchase.quote`, `purchase.allow`, `purchase.held`, `schema.validate`, `schema.read`, `schema.proved` |
| The purchase ledger | `purchase.spent`, `purchase.ledger`, `purchase.find`, `purchase.adopt`, `purchase.reconcile` |
| After buying | `normalise.ingest`, `texture.worth_scrubbing` |
| Bake a clip | `motion.bake` (animation and sheet, from files) |
| Motion | `clip.new`, `clip.read`, `clip.set_key`, `clip.retime`, `clip.write`, `clip.compiled` |
| A skeleton | `skeleton.plan`, `skeleton.shared`, `skeleton.joints_in`, `skeleton.plays`, `sprites.matched` |

A long operation (`asynchronous` in `describe`) takes `--job` on the command line and
answers with a handle; `job poll|result|cancel <handle>` follows it.
