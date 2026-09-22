# Shipped Ledger

## Block A — What a tool call costs the turn

- ✅ **PW1** **an operation that takes minutes holds the turn, and nothing reports progress until it ends** — Long work returns a handle at once; poll names the stage it reached, result the artefact or the typed failure, cancel the whole process tree (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW2** **a tool reports success on an empty result, so the failure is found a render later** — Every operation asserts its own output before returning, and an empty boolean, a blank render or a short download is an error naming what failed (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW3** **a tool's parameters are learned by reading the source that implements them** — One call returns an operation's parameters with type, range, default and a sentence, read from the signature; another says what this machine can do (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW4** **a failure arrives as a stack trace, so the fix is guessed from the frame that raised it** — Every code is declared with what it means and what produces it, explain answers any of them, and a code the table lacks cannot be raised (design recorded in `docs/specs/tool-surface.md`).
- ✅ **PW5** **paths, palette and rig defaults are written into the tool, so a second project cannot run it** — Every path, tolerance, binary and budget is read from polyweave.toml on each call, over a default the plugin ships for all of it (design recorded in `docs/specs/project-config.md`).
- ✅ **PW6** **the renderer's version is not recorded, so a render that moved cannot be told from a change** — Every artefact carries a record of the engine, seed, samples, inputs and params that made it, and the same record is the cache key (design recorded in `docs/specs/provenance.md`).

## Block B — Seeing the result cheaply

- ✅ **PW7** **judging a material costs a two-minute render when the verdict needs three seconds** — A question is answered from the lowest rung that carries it, on one shared rig, and the answer names the rung it came from (design recorded in `docs/specs/rungs.md`).
- ✅ **PW8** **a render is judged by opening the file it wrote, so every verdict costs a second call** — A render returns the picture and its measurements in one answer, each measurement naming the region and the rung it was taken at (design recorded in `docs/specs/measurements.md`).
- ✅ **PW9** **a mean over an image agrees while the look is plainly wrong** — Saturation, luma and hue spread come back as distributions over the frame or the subject, so a picture that is wrong at the 99th percentile says so (design recorded in `docs/specs/measurements.md`).
- ✅ **PW10** **an asset is judged alone and then lands beside five siblings it does not match** — An asset is composited onto a sheet with its siblings or into the screen it belongs to, and the measurement runs on that rather than the lone file (design recorded in `docs/specs/context.md`).
- ✅ **PW11** **a bake is not byte-reproducible, so a file diff cannot say whether anything changed** — Two renders are compared with a tolerance rather than byte-wise, and a path tracer's own noise sits fifty times below a real change (design recorded in `docs/specs/measurements.md`).

## Block C — The asset compiler

- ✅ **PW12** **what counts as a correct render lives in somebody's head, so it is approved by opinion** — A file per asset states what makes a render of it correct, and every predicate returns a verdict and a margin a search can climb (design recorded in `docs/specs/acceptance-spec.md`).
- ✅ **PW13** **a rig number is found by rendering, looking, and changing it by hand, one sample at a time** — A rig number is found by searching the range the spec permits, on a stated budget of renders, reported against every predicate it was scored on (design recorded in `docs/specs/acceptance-spec.md`).
- ✅ **PW14** **a search re-renders states it has already rendered** — An identical render is returned from the store instead of paid for again, keyed on everything that can change it, and a hit says it was one (design recorded in `docs/specs/provenance.md`).
- ✅ **PW15** **a search reports the winning numbers and not what it rejected** — A search writes down every sample it scored and lays the best handful side by side, so a spec satisfied by a wrong render is visible as that (design recorded in `docs/specs/acceptance-spec.md`).

## Block D — Fetching from a paid service without surprise

- ✅ **PW16** **a generated mesh's silhouette is checked after its credits are spent** — A returned shape is compared against the drawing that asked for it, on a preview where there is one, and a mismatch is a refusal with the picture (design recorded in `docs/specs/fetching.md`).
- ✅ **PW17** **a paid asset is deleted by the service seventy-two hours after it is made** — A bought artefact lands on disk, is hashed and recorded, and only then ledgered, so nothing ever claims an asset the service has since deleted (design recorded in `docs/specs/fetching.md`).
- ✅ **PW18** **every fetch needs a human decision, so work stops between approvals** — A ceiling set once is spent against without asking, refused when it would be passed, and what each call really cost is the balance either side of it (design recorded in `docs/specs/fetching.md`).
- ✅ **PW19** **an unknown field is dropped in silence, so a payload that validates proves nothing** — The service's shape is probed for free, kept as a file, and payloads are refused locally, so a typo is a refusal rather than a field dropped in silence (design recorded in `docs/specs/fetching.md`).
- ✅ **PW20** **a fetched mesh arrives at an arbitrary orientation, scale and origin** — A fetched mesh is oriented, scaled and stood on its origin on arrival, against the drawing that asked for it, and the correction is kept as one matrix (design recorded in `docs/specs/fetching.md`).

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

