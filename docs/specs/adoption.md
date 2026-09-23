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

**Three more are worse than missing, because the name is taken** (§PW63). Cottony's `fill`
is how much of the frame a model fills, 0.92, and this one is a fill light in watts,
default 120. Its `key` is the key's width as a share of the framed reach, 0.55, against the
key's power in watts, 400. Its `ambient` is a multiplier on the rig's ambient, 1.0, against
the world value itself, 0.25. A port that copies any of them across is accepted and renders
the wrong picture, and the guard above cannot see it: the name is right and the meaning is
not, which no near-match finds.

A declared **range** was the obvious answer and does not work. The rig is legitimately
driven with every light at zero — that is how a test proves the lights are what light the
subject — so no bound separates 0.92 W from a wattage somebody meant. What is left is to
say the unit: `rig.UNITS` holds it as data rather than as a comment, and every axis a
search accepts comes back as `fill (W)` rather than `fill`. That does not refuse the
mistake; it puts it where the person making it is looking, which is the moment the axis is
declared rather than the render it would have produced.

**The fluff had no home at all.** `FLUFF_SHELLS`, `FLUFF_DEPTH`, `FLUFF_EDGE`, `FLUFF_FIBRE`,
`FLUFF_FIBRE_WEIGHT`, `FLUFF_VARY`, `FLUFF_RISE`, `FLUFF_LEAN` are shell texturing — the same
surface drawn twenty times a little further out. That is a **technique**, not a number, and
no table here held one. Same for `scrub` and its three constants, which are a pass over the
rendered pixels. Both were filed rather than guessed at, and both have since landed: the
scrub as a measured pass (§PW49), and the fluff as a two-number intent on a material with
the eight constants derived from it (§PW50, `geometry.md`). **Adopting the fuzz is therefore
not a translation of eight values but a re-fit of two**, and the fit is worth doing against
a render rather than by reading the old constants across — this vocabulary derives them from
a different starting point and will not land on Cottony's eight exactly.

### What is left of PW36

The port itself. It edits a repository this one does not own, and **§PW35 requires a baseline
recorded before anything moves** — a before side taken after the port is refused, and rightly.
So the audit lands here and the adoption waits on a person starting the ledger.

## Bringing an existing ledger in

Binds **PW55**. A project adopting this plugin has usually bought things already, and its
own client wrote them down somewhere. Cottony's is `tools/art/3d/meshy.lock.json`: five
purchases, 130 credits, each entry holding the task id, the exact request, what it cost and
the sha256 of what went in and what came out.

`purchase.adopt` replays such entries, and **costs nothing** — every claim in a file like
that is about a file already on disk, so nothing is asked of the service and no credit is
spent. The mapping from the foreign field names is the caller's, because the service's
format is not this plugin's to hard-code and a project's own paths are the thing that must
never be compiled in. For Meshy it is this:

| The lock file holds | The ledger calls it |
|---|---|
| `mesh` | `artefact` |
| `mesh_sha256` | `sha256` |
| `task_id` | `task_id` |
| `credits_measured` | `credits` — what the balance said, not what was quoted |
| `consumed_credits` | `expected_credits` |
| `request.texture_prompt` or `request.prompt` | `prompt` |
| `image` | `reference` |
| `finished_at` (epoch ms) | `at` |

**An entry is adopted only where the file is there and still hashes to what it claims.** The
ledger is written last precisely so it can never name an asset that is not there, and
importing past that rule hands the project back the failure it started with: a receipt for a
mesh nobody has. A claim that no longer holds is reported as `missing` or `changed` instead.

That report is the first time the question is asked mechanically. A lock file records a hash
and nothing ever compares it. Asked of Cottony's five, all five still hash to what they were
bought as, and none was charged differently from what the service declared.

**An adopted credit does not count against the ceiling.** Those meshes were bought before
this project had one here, and charging them to the budget a person set for today would
refuse the next call over money already gone. They stay in the ledger, because `held` is the
question about assets and every one of them is an asset — so `held` reports the full
`credits` and `against_ceiling` separately.

A live fetch stays a person's call and is not what this covers.

## How a consumer depends on this

Binds **PW70**. Cottony reaches the plugin as an ordinary Python dependency, in the file
its CI already installs from, **pinned to a commit**:

```
polyweave @ git+https://github.com/alegauss/polyweave.git@<sha>
```

Pinned for the reason that project pins its linter, in its own words: an unpinned
dependency is a build that breaks on somebody else's release, and the point is that the
answer is the same in CI as on a desk. Moving it is a deliberate edit. A git URL rather
than a release because there is no release yet; when there is one, the line changes and
nothing else does.

**What forced the question was one lookup.** Three of Cottony's runners each carried their
own copy of "find Godot, bound the run, distrust the exit code". Two of them moving here
left the third — `run_tests.py`, the one both CI workflows run — as the only one that did
not read the project's config, so a person who set the project up by writing
`polyweave.toml` got two runners working and one saying there was no Godot. Porting two
lines needed the import, and the import needed this decision.

**A binary is not stated in a committed config.** `engine.find` reads `[paths] godot`,
then `$GODOT`, then `PATH`, and a declared path that is not there is **refused rather than
fallen back from** — so one desk's path committed to a shared file breaks every other
desk, including a CI that downloads its own engine and exports `$GODOT`. The refusal names
all three places, which is what makes leaving it out safe.

## Three model routes, stated rather than programmed

Binds **PW54**. `tools/art/solid.py` is 283 lines of bmesh primitives that three scripts
import, and a shape that exists only inside a bake cannot be read, diffed or searched.
`tests/fixtures/cottony/star.toml`, `tray.toml` and `panel.toml` are those three routes as
declarations, with that project's own numbers as parameters a search can reach.

They are here because the vocabulary being able to express a real model is a claim only a
real model tests, and it turned out to be four ops short. Reading the scripts against the
format found every one of them: a star could not be asked for with a point count (§PW64);
a rim between two rounded rectangles had no op (§PW65); a crowned star reached 82 units
past its own silhouette (§PW66); a model in two materials came back carrying neither
(§PW67); and a drawn panel had nowhere to say where its picture goes (§PW68). Each was
small, and none was visible until a real shape was written down.

What each route exercises is different, which is why all three are kept:

| Route | What it proves |
|---|---|
| `star.toml` | One `crowned` node over a concave outline, at 51.2 deep with a 66.56 crown |
| `tray.toml` | Four parts in two materials, 2,599 faces, joined and carved |
| `panel.toml` | A drawing given volume by its own alpha, wearing itself, at 672 by 244 |

The conventions are restated rather than carried across. `tray_model.py` works in image
coordinates turned on their side and flips y into Blender's z on every ring; an outline
here is a closed ring in XY and a solid extrudes it along Z, so the flip happens once, in
the reading.

## What the motion block met when it reached a real game

Binds **PW58**. Block F shipped a skeleton fitted to a mesh, a clip authored as text and a
sprite sheet matched to the animation, and every figure it was tested against was built in
code with its limbs where the plan puts its bones. Run against a game, two things came back.

**There is no clip to author.** Cottony's entire motion surface is the settle: the same mesh
pressed to 93% of its height, spread sideways by the reciprocal square root of that, and
**re-rendered rather than scaled** — because a scaled sprite squashes its own highlight and
its own shadow with it. Two frames per friend, and `hud.gd` crossfades between them, loading
each through `Art.sprite` as its own file. There is no `AtlasTexture`, no `SpriteFrames` and
no atlas anywhere in the project.

`tools/art/make_assets.py` does compose sheets, and they are not these: they are contact
sheets of every screen, a design deliverable for a person to look at, and the file is the
2,406 lines of drawn 2D generation that §PW59 puts outside the denominator on purpose. The
settle frames come from `bake_model.py` instead, as 3D renders. So the sheet half of this
line had nothing in Cottony to replace — which is worth recording once, so that nobody looks
twice, and it closes the question as honestly as a clip would have.

**The two frames carry a number.** Measured off the shipped PNGs, the leaning silhouette is
186 px tall against the standing one's 200 — 0.930, which is the `squash` constant recovered
from pixels rather than read back out of the file that declares it. It is also 346 px wide
against 332, and the two share a bottom row exactly: the toy settles onto the same ground
line, which is what makes the crossfade read as one toy rather than two. A pair built in a
test would have had all three properties by construction and would have proved none of them.

So what the plugin adds here is not motion Cottony lacks. It is that the pair becomes **one
sheet and an index a machine can read**, cut to a single cell that is the union of both
silhouettes — a frame trimmed to its own outline is a sprite that jitters on its own axis —
and that the sheet and the animation carry the same clip digest, so neither can drift from
the other unnoticed.

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

The port PW36 is deferred on, once somebody records its baseline — and then the six
surfaces that one port leaves standing.

**Cottony runs on none of this today.** A search for `polyweave` across the checkout returns
nothing, against 8,839 lines under `tools/`. §PW53 to §PW58 name the surfaces one at a time:
the fourteen-parameter rig on the eleven models PW36 does not move, `solid.py`'s geometry as
a program, `meshy.py`'s second ledger, the twelve GDScript runners that each start Godot
their own way, the five look gates each holding their own floor, and a motion block that has
never run against something a game ships.

§PW59 is the one that makes *adopted* fail rather than be claimed, and it is where the
denominator is stated: `make_assets.py`'s 2,406 lines of drawn 2D generation are not in it,
because this plugin is geometry, surface and motion in three dimensions.
