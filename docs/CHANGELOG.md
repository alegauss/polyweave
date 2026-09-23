# Shipped Ledger

## Block A — What a tool call costs the turn

- ✅ **PW1** **an operation that takes minutes holds the turn, and nothing reports progress until it ends** — Long work returns a handle at once; poll names the stage it reached, result the artefact or the typed failure, cancel the whole process tree (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW2** **a tool reports success on an empty result, so the failure is found a render later** — Every operation asserts its own output before returning, and an empty boolean, a blank render or a short download is an error naming what failed (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW3** **a tool's parameters are learned by reading the source that implements them** — One call returns an operation's parameters with type, range, default and a sentence, read from the signature; another says what this machine can do (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW4** **a failure arrives as a stack trace, so the fix is guessed from the frame that raised it** — Every code is declared with what it means and what produces it, explain answers any of them, and a code the table lacks cannot be raised (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW5** **paths, palette and rig defaults are written into the tool, so a second project cannot run it** — Every path, tolerance, binary and budget is read from polyweave.toml on each call, over a default the plugin ships for all of it (design recorded in `docs/specs/project-config.md`).
- ✅ **PW6** **the renderer's version is not recorded, so a render that moved cannot be told from a change** — Every artefact carries a record of the engine, seed, samples, inputs and params that made it, and the same record is the cache key (design recorded in `docs/specs/provenance.md`).
- ✅ **PW37** **a renderer outlives the worker that started it, and a sweep on Windows cannot find it to end it** — A worker writes every process it spawns down before waiting on it, and a sweep ends those pids directly, while the recorded start time still matches (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW38** **a height field survives an eight-bit round trip as a staircase, and every assertion says it is fine** — A field is its own checked kind, holding the file's own bit depth and its distinct values per channel, with a shallow write and a flat buffer apart (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW39** **a job checks only that an argument exists while a direct call checks its range, so one call has two contracts** — A registered operation is validated in the caller before a job spawns, and an unregistered target is left to the worker's signature check (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW40** **a tolerance has one default in the project config and a different one in the function that uses it** — A tolerance is resolved once by the operation holding a root, and the pure functions below default nothing, so a second value has nowhere to live (design recorded in `docs/specs/project-config.md`).
- ✅ **PW41** **an artefact that was produced without a record is invisible, because verify starts from the records** — Verify now walks the produced directories as well as the records, so a file with no sidecar is named, and a project says which it made by hand (design recorded in `docs/specs/provenance.md`).
- ✅ **PW42** **a render that is black to any observer passes the check for a blank render, on one bit of edge noise** — Flat is now the spread across the visible pixels against the noise floor, so the unlit render that used to pass on one bit of edge noise is refused (design recorded in `docs/specs/tool-surface.md`).

## Block B — Seeing the result cheaply

- ✅ **PW7** **judging a material costs a two-minute render when the verdict needs three seconds** — A question is answered from the lowest rung that carries it, on one shared rig, and the answer names the rung it came from (design recorded in `docs/specs/rungs.md`).
- ✅ **PW8** **a render is judged by opening the file it wrote, so every verdict costs a second call** — A render returns the picture and its measurements in one answer, each measurement naming the region and the rung it was taken at (design recorded in `docs/specs/measurements.md`).
- ✅ **PW9** **a mean over an image agrees while the look is plainly wrong** — Saturation, luma and hue spread come back as distributions over the frame or the subject, so a picture that is wrong at the 99th percentile says so (design recorded in `docs/specs/measurements.md`).
- ✅ **PW10** **an asset is judged alone and then lands beside five siblings it does not match** — An asset is composited onto a sheet with its siblings or into the screen it belongs to, and the measurement runs on that rather than the lone file (design recorded in `docs/specs/context.md`).
- ✅ **PW11** **a bake is not byte-reproducible, so a file diff cannot say whether anything changed** — Two renders are compared with a tolerance rather than byte-wise, and a path tracer's own noise sits fifty times below a real change (design recorded in `docs/specs/measurements.md`).
- ✅ **PW43** **a colour measured off a render is not the colour that was authored, and nothing says so** — Capabilities renders one known colour and reports what came back, so an installation that cannot measure colour says so before a spec is built on it (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW44** **one configured noise floor calls every preview-sized render a change, because the floor moves with the rung** — The floor is keyed by rung and read for the one a render records, and a twin render measures it outright, right at any sample count anywhere (design recorded in `docs/specs/project-config.md`).

## Block C — The asset compiler

- ✅ **PW12** **what counts as a correct render lives in somebody's head, so it is approved by opinion** — A file per asset states what makes a render of it correct, and every predicate returns a verdict and a margin a search can climb (design recorded in `docs/specs/acceptance-spec.md`).
- ✅ **PW13** **a rig number is found by rendering, looking, and changing it by hand, one sample at a time** — A rig number is found by searching the range the spec permits, on a stated budget of renders, reported against every predicate it was scored on (design recorded in `docs/specs/acceptance-spec.md`).
- ✅ **PW14** **a search re-renders states it has already rendered** — An identical render is returned from the store instead of paid for again, keyed on everything that can change it, and a hit says it was one (design recorded in `docs/specs/provenance.md`).
- ✅ **PW15** **a search reports the winning numbers and not what it rejected** — A search writes down every sample it scored and lays the best handful side by side, so a spec satisfied by a wrong render is visible as that (design recorded in `docs/specs/acceptance-spec.md`).
- ✅ **PW45** **a search renders its samples one after another, so a budget of twenty-four costs twenty-four waits** — A pass can be handed over whole and rendered through job handles, and the crossing is measured: a loss on the sphere rung, 3.7x on the final one (design recorded in `docs/specs/acceptance-spec.md`).

## Block D — Fetching from a paid service without surprise

- ✅ **PW16** **a generated mesh's silhouette is checked after its credits are spent** — A returned shape is compared against the drawing that asked for it, on a preview where there is one, and a mismatch is a refusal with the picture (design recorded in `docs/specs/fetching.md`).
- ✅ **PW17** **a paid asset is deleted by the service seventy-two hours after it is made** — A bought artefact lands on disk, is hashed and recorded, and only then ledgered, so nothing ever claims an asset the service has since deleted (design recorded in `docs/specs/fetching.md`).
- ✅ **PW18** **every fetch needs a human decision, so work stops between approvals** — A ceiling set once is spent against without asking, refused when it would be passed, and what each call really cost is the balance either side of it (design recorded in `docs/specs/fetching.md`).
- ✅ **PW19** **an unknown field is dropped in silence, so a payload that validates proves nothing** — The service's shape is probed for free, kept as a file, and payloads are refused locally, so a typo is a refusal rather than a field dropped in silence (design recorded in `docs/specs/fetching.md`).
- ✅ **PW20** **a fetched mesh arrives at an arbitrary orientation, scale and origin** — A fetched mesh is oriented, scaled and stood on its origin on arrival, against the drawing that asked for it, and the correction is kept as one matrix (design recorded in `docs/specs/fetching.md`).
- ✅ **PW21** **a reference photograph brings whatever stood behind the subject back as geometry** — A reference photograph is cut, flattened and checked before a fetch carries it, and the prepared picture is what the record names (design recorded in `docs/specs/fetching.md`).
- ✅ **PW46** **a normalised mesh sits beside the paid one with nothing recording what it derives from** — A normalised mesh carries a record naming its parent by hash and holding the transform, so the chain from credits spent to mesh in scene is followable (design recorded in `docs/specs/provenance.md`).

## Block E — One world with the engine

- ✅ **PW22** **the engine's exit code is not the verdict, so each project writes its own output parser** — One runner drives a scene script and returns a verdict read off the printed line, the errors and the file, with both bounds set and the log kept (design recorded in `docs/specs/engine.md`).
- ✅ **PW23** **a real renderer needs a window, so a capture cannot run where there is no screen** — One call captures real pixels by whichever route draws on this machine, each route proved by a picture it drew and read back rather than assumed (design recorded in `docs/specs/engine.md`).
- ✅ **PW24** **the baked sprite and the running game agree on scale only because a constant was tuned** — An asset declares the rectangle it covers and the scale it is baked at, checked against the engine's own number before a render, both numbers in a refusal (design recorded in `docs/specs/engine.md`).
- ✅ **PW25** **a capture takes its picture in whatever language and settings the runner happens to have** — A capture is passed the settings it must be taken under, prints back what it applied, and is refused where the two differ; the answer is recorded beside it (design recorded in `docs/specs/engine.md`).

## Block F — Motion

- ✅ **PW26** **a fetched mesh has no skeleton, so it cannot be posed at all** — The fitted skeleton and its weights are written into the mesh file as a glTF skin, proved by turning a joint in the re-imported file and watching it follow (design recorded in `docs/specs/motion.md`).
- ✅ **PW27** **motion is expressed as a second static render, so nothing longer than two frames exists** — A clip has a name, a duration and channels over time, each frame renders as a still, and one measurement runs across all of them rather than at rest (design recorded in `docs/specs/motion.md`).
- ✅ **PW28** **an animation lives in a binary track, so a curve cannot be reviewed or edited as text** — A clip is authored as TOML with one key per line, so a timing change is one line in a diff, and the glTF export is a compile step keyed on that text (design recorded in `docs/specs/motion.md`).
- ✅ **PW29** **a 2D screen needs frames and a 3D scene needs a clip, so the motion is authored twice** — One clip produces the engine's animation and a trimmed sprite sheet with its atlas, both carrying the digest that says they are the same motion (design recorded in `docs/specs/motion.md`).

## Block G — Geometry as a declaration

- ✅ **PW30** **a shape is a Python script, so stating one means writing and debugging a program** — A shape is a TOML document of named parameters, expressions over them and a repeat, resolved into a flat graph that says what a change rebuilds (design recorded in `docs/specs/geometry.md`).
- ✅ **PW31** **a format covering only primitives would leave every real asset in code** — Carve, bevel and inflate complete the vocabulary, with the boolean asserted non-empty because that is what protects a build rather than the solver chosen (design recorded in `docs/specs/geometry.md`).
- ✅ **PW32** **a shape's own numbers are unreachable from the search that tunes everything else** — A shape's parameters and a rig's search as one space, ordered so the shape is rebuilt once per shape rather than once per sample (design recorded in `docs/specs/geometry.md`).
- ✅ **PW33** **a shape cannot be reviewed without building it, so a wrong construction is found in the render** — A shape reads back in words before it is built, beside what is odd about it, and a built one reports a face count per node (design recorded in `docs/specs/geometry.md`).
- ✅ **PW34** **a declaration that cannot express a shape leaves no way back to code** — One node may be a project function, handed resolved arguments and its inputs as meshes, with its source hashed so a change to the code costs a rebuild (design recorded in `docs/specs/geometry.md`).

## Block H — Proof on a real game

- ✅ **PW35** **the plugin's value is asserted and never measured against what it replaced** — One asset's cost is recorded each way, with a baseline that cannot be written after the port and a verdict allowed to say the plugin made things worse (design recorded in `docs/specs/adoption.md`).
- ✅ **PW36 (the configuration audit)** **a real project cannot adopt the plugin without carrying its own paths and palette into it** — Cottony's whole config is a fixture no key had to be added for, and the one thing that did not survive it, a spec axis the renderer has no knob for, is refused before a render.
