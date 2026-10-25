# Operations by task

`describe` is the authority on every operation, its parameters, ranges and units.

| Task | Operations |
|---|---|
| Adopt | `project.new`, `project.init` (`init`), `project.check`, `project.adoption`, `project.inventory`, `kit.list`, `kit.install`, `kit.update`, `kit.prove` |
| Know the machine | `capabilities`, `engine.find`, `offscreen.routes`, `search.worth_parallel` |
| Start on an asset | `asset.brief`, `loop.pending` |
| Make a shape | `geometry.build`, `geometry.build_all`, `geometry.kit` (a folder built, rendered, specced, checked and sat in one call), `geometry.describe`, `geometry.variants`, `geometry.fit`, `geometry.compare` |
| Render | `render.plan`, `render.bake` |
| Measure | `measure.take`, `measure.same`, `measure.available`, `measure.digest`, `measure.contrast`, `measure.pressure`, `measure.level`, `measure.flashes` |
| Judge against the bar | `accept.check`, `accept.verify`, `accept.check_screen`, `reference.concept`, `cost.read`, `sound.measure`, `sound.speech`, `sound.declared` (what is missing) |
| Search for numbers | `search.sweep`, `port.run` (a whole family), `trace.read` |
| See it where it is seen | `compose.place`, `compose.sheet`, `store.capsules`, `picture.vector`, `picture.copies` |
| Size a bound from noise | `calibrate.run`, then `calibrate.apply` |
| Carry a person's verdict (an accept needs the page's `code`) | `verdict.sheet`, `verdict.sitting`, `verdict.judge`, `verdict.promote`, `verdict.target` (a bar the look must reach, always needs `code`), `sound.sitting`, `verdict.answer`, `verdict.move`, `verdict.place`; `review` shows one, `verdict.answers` resumes |
| The decision screen | `review.state`, `review.words`, `review.canon`, `review.compare`, `review.answer` |
| Asked changes | `revision.ask`, `revision.open`, `revision.turn`, `revision.check`, `revision.settings`, `revision.outside`, `revision.close` |
| Keep the ledger | `loop.start`, `loop.spent`, `loop.judged`, `loop.finish`, `loop.compare` |
| Read the ledger | `loop.runs`, `loop.assets`, `loop.changes`, `loop.bounds`, `loop.report` |
| Provenance | `provenance.read`, `provenance.verify`, `provenance.dependents`, `provenance.outdated`, `provenance.unrecorded`, `provenance.credits`, `provenance.generated`, `provenance.borrow` |
| The game side | `engine.check`, `engine.states`, `game.test`, `game.boot`, `game.pack`, `tables.check`, `capture.run`, `capture.again`, `capture.movie`, `capture.declared`, `engine.run`, `engine.run_declared`, `engine.sweep`, `engine.cost`, `engine.perf`, `engine.preset_search`, `godot.install` |
| Drive a game | `game.open`, `game.query`, `game.input`, `game.step`, `game.wait`, `game.call`, `game.set`, `game.shot`, `game.text_fit`, `game.close`, `game.batch`, `game.keep`, `game.record_flow`, `game.crash_read`, `game.rekey`, `game.replay`, `game.compare_runs`, `game.release_check`, `game.export_smoke` |
| Scale against the engine | `units.check`, `units.engine_scale`, `units.read_number` |
| World | `world.read`, `world.validate`, `voice.design`, `voice.choose`, `voice.lines`, `words.check`, `words.unlisted`, `words.glyphs`, `words.sheet` |
| Music | `music.validate`, `music.to_midi`, `music.from_midi` (a MIDI as a score), `music.from_audio` (a recording as a score), `music.render`, `music.track`, `sound.synth`, `sound.loop`, `sound.stems` (a recorded track), `sound.buy`, `sound.speak` (paid) |
| Visual effects | `vfx.build`, `vfx.preview`, `panel.build`, `panel.capture`, `picture.sew`, `icons.build` |
| A teaser | `video.cut` |
| A project's look | `style.read`, `style.drift` (before a person looks), `style.train` |
| Buy a drawing | `picture.buy`, `picture.gate`, `picture.letters`, `picture.describe`, `picture.vary`, `picture.against_parent`, `picture.fit`, `picture.collect` |
| Before buying a mesh | `reference.pick`, `reference.prepare`, `reference.register`, `reference.frames`, `reference.objects`, `reference.sample`, `reference.regions`, `reference.minimap`, `reference.events`, `reference.compare`, `reference.transcription`, `reference.transcribed`, `shape.check`, `shape.silhouette`, `shape.turntable` |
| Paid meshes | `mesh.buy`, `purchase.remaining`, `purchase.quote`, `purchase.allow`, `purchase.held`, `schema.validate`, `schema.read`, `schema.proved` |
| The purchase ledger | `purchase.spent`, `purchase.ledger`, `purchase.find`, `purchase.adopt`, `purchase.reconcile` |
| After buying | `normalise.ingest`, `mesh.budget` (to a triangle count and a texture edge), `texture.worth_scrubbing` |
| Bake a clip | `motion.bake`, `clip.camera`, `clip.timeline`, `clip.shots` |
| Motion | `clip.new`, `clip.read`, `clip.set_key`, `clip.retime`, `clip.write`, `clip.compiled` |
| A skeleton | `skeleton.plan`, `skeleton.shared`, `skeleton.joints_in`, `skeleton.plays`, `sprites.matched` |

A long operation (`asynchronous` in `describe`) takes `--job` and answers with a
handle; `job poll|result|cancel <handle>` follows it.
