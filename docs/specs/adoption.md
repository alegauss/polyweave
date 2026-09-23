# Adoption

Binds **PW35**, and is where the rest of Block H's contract will go.

## What one asset cost, each way

Every line in this backlog is a claim that something will be faster or more certain, and
**not one of them is measured**. The risk is specific: the work gets rearranged rather than
reduced, and the plugin becomes a different way to spend the same afternoon.

So the loop is instrumented against a real asset made both ways. Five numbers, from brief to
accepted render:

| What | Why it is here |
|---|---|
| wall-clock seconds | the number the claim is actually about |
| renders spent | a faster loop that renders ten times as much is not faster |
| tool calls | a turn is what an agent pays |
| credits | some of this is real money |
| results a person rejected after the tool passed them | the honest measure of assertiveness |

**A tool that approves renders a person then rejects has made things worse however fast it
was**, and nothing else recorded here would show it. So every result carries **both**
verdicts — the tool's and a person's — and the gap between them is counted. The tool's own
verdict alone is worth nothing at this level.

## A baseline cannot be written afterwards

The baseline is what the existing pipeline costs today, recorded **before anything is
ported**, so that it cannot be reconstructed favourably once the answer is known.

That is enforced rather than asked for: starting the *before* side for an asset the plugin
has already made is refused (`loop.baseline-too-late`). Each run also carries the commit it
was taken at, so its place in the order is checkable by somebody who was not there, and the
ledger is append-only and committed with the tree.

A comparison with only one side recorded is refused too. A claim measured on one side is not
measured.

## The comparison is allowed to say it got worse

The verdict is one sentence, and the order it checks in is the order that matters:

1. **more overruling than before** — "faster or not, it is approving work that gets
   rejected";
2. **no faster** — "the work was not reduced by this measure";
3. **faster, but renders, calls or credits went up** — "the cost may have moved rather than
   gone", which is the specific failure this line exists to catch;
4. **faster with nothing else higher** — the only case that is unambiguously a win.

Nothing here can report a success that the numbers do not support, which is the whole
reason the line sits late in the file and is deliberately not optional: the alternative is a
backlog whose central claim cannot be falsified.

## What Cottony had to configure

Binds **PW36**. The non-goal says Cottony is the first consumer and not the specification,
so anything it needs that a second project would not is configuration. That is a claim, and
the way to test it is to write Cottony's config out of the constants it actually has and see
what is left over.

`tests/fixtures/cottony.toml` is that file — every value read off a named constant in
`D:\Git\viglet\cottony`, with the file it came from in the comment. `tests/test_adoption.py`
is the gate on it, so a key renamed inside the plugin turns red here rather than in the
consumer. The audit sorted into three piles.

### One: a key already existed

| Cottony has | Where | The key |
|---|---|---|
| `ART` | `tools/art/bake_model.py` | `[paths] renders` |
| `MODELS_DIR` | `tools/art/bake_model.py` | `[paths] meshes` |
| `SAMPLES = 320` | `tools/art/bake_model.py` | `[render] samples`, per rung |
| `SEED = 7` | `tools/art/bake_model.py` | `[render] seed` |
| `meshy.lock.json` | `tools/art/3d/` | `[paths] purchases` |
| `MESHY_API_KEY` | `tools/art/meshy.py` | `[service] key_env` |
| `const CELL := 112` | `scripts/board.gd` | `[units] source` |
| viewport 1080×1920 | `project.godot` | `[capture] resolution` |
| two translations | `project.godot` | `[capture] declared`, `locale` |
| `FABRIC_ROUGHNESS` | `tools/art/cloth.py` | `bake(material=…)` |

**No key had to be added.** That is the boundary holding, and it is the one result here that
was hoped for rather than found.

### Two: per-asset, so never configuration

The fourteen-parameter rig — `fill`, `light`, `turn`, `ambient`, `key`, `form`, `roughness`,
`shadow`, `gloss`, `square`, `scrub`, `roll`, `plate` — is declared **per model** in Cottony,
and a project-wide key for any of it would be the wrong shape. These belong in an acceptance
spec, one per asset, which is what §PW12 and §PW13 are for. Not a gap, and worth saying so:
the reflex on seeing a constant is to add a key for it, and thirteen of these would have been
thirteen keys nobody could use.

### Three: nothing had a home

**The names do not survive, and nothing said so.** Cottony calls the whole-rig scale `light`
and the key's share of it `form`. Neither is a parameter the renderer has. Worse, the
acceptance spec's own worked example in this repository used `[search.light]` and
`[search.form]` — so the documented example could not run. The spec loaded, `ranges` returned
the axis, and the search died on its first sample with a bare `TypeError`, after the setup
was paid for. A spec's search axes and the renderer's parameters were two lists and nothing
reconciled them.

That is the one thing this adoption changed **inside** the plugin: an axis the renderer has
no knob for is now refused before a render is spent (`search.unknown-parameter`), with the
near match named. The translation itself stays a person's — `light` is a multiplier and
`exposure` is in stops, and a wrong conversion is a different picture, not an error.

**The fluff has no home at all.** `FLUFF_SHELLS`, `FLUFF_DEPTH`, `FLUFF_EDGE`, `FLUFF_FIBRE`,
`FLUFF_FIBRE_WEIGHT`, `FLUFF_VARY`, `FLUFF_RISE`, `FLUFF_LEAN` are shell texturing — the same
surface drawn twenty times a little further out. That is a **technique**, not a number, and
no table here holds one. Same for `scrub` and its three constants, which are a pass over the
rendered pixels. Both are filed rather than guessed at.

### What is left of PW36

The port itself. It edits a repository this one does not own, and **§PW35 requires a baseline
recorded before anything moves** — a before side taken after the port is refused, and rightly.
So the audit lands here and the adoption waits on a person starting the ledger.

## Testing against artefacts somebody actually made

Binds **PW48**. Every other input the suite has is built in code: a box of stated
proportions, a photograph of a rectangle on a plain ground, a figure whose limbs are where
the plan puts its bones. That is right for the arithmetic — a test states the numbers its
assertion depends on, which a committed PNG never does — so the builders stay. What they
never show is an artefact anybody made, and those are where every symptom in this backlog
was measured.

`tests/fixtures/cottony/` holds copies, not a path into another checkout, because a test
needing a sibling repository on the same disk is one nobody else runs. **One per failure
worth reproducing, not one per asset Cottony has**: the 30 MB mascot buys nothing the 8 MB
hammer does not, and it is not there. A capture from a running game was considered and left
out on the same rule — §PW25 is about the settings a picture was taken under and not about
its pixels.

**What a real artefact is for is the numbers a built one cannot give.** The hammer's mesh
and the drawing it was made from agree at a silhouette IoU of **0.4343** across 24
orientations. The synthetic tests clear 0.8 on a box against its own outline, so a threshold
picked from those would have called this real, correct match a failure to orient. That is
the whole argument for the fixtures in one number.

**Size is what LFS answers.** `*.glb` is routed to it and `*.png` deliberately is not: Git
keeps every version of a file whole, so an 8 MB mesh replaced three times is 24 MB in every
clone from then on and the only fix afterwards rewrites history, while a drawing is 11 KB
and reading one out of a pointer is a step nobody should have to take to run the tests. The
hammer is 132 bytes in the repository and 8 MB on disk. A checkout where `git lfs install`
has not been run **skips** rather than failing: a pointer file is a thing that happened to
the checkout, not a thing that is wrong with the plugin.

**The GDScript belongs in files either way.** The offscreen tests ran a scene script that
lived as a Python string literal full of escaped tabs, where nothing highlighted it and
nothing linted it. It is `tests/fixtures/gdscript/capture.gd` now, read by the test.

## Still to come in this block

Nothing, once the port PW36 is deferred on has somebody to record its baseline.
