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

**A verdict says which bound it was about** (§PW108). `loop.judged` takes the `check` the
person looked at and the predicate ids they `named` when they overruled it. The verdict
then keeps each predicate's value, whether it passed and the side of its bound. A name the
check does not carry is refused (`loop.unknown-predicate`). A caller passing neither
records what it always did. `loop.bounds(root, asset=)` counts over the ledger. A bound is
too tight when its predicate failed and a person accepted the result anyway. It is too
loose when its predicate passed and a person rejected the result and named it. Overruled
twice in one direction, and more often that way than the other, it is reported as the
wrong number, with the values that overruled it. That is the evidence a calibration (§PW107)
or a person needs. A rejection that names nothing counts as `unattributed` on its asset,
not against every predicate that happened to pass. This is counting over a file, not a
model of taste: nothing is called and no judgement is delegated.

**What waits on a person is a read, not a memory** (§PW110). `loop.pending(root)` reads
the ledger, the specs under `[paths] specs` and the render records under `[paths]
renders`, and nothing else. It gives one row per asset: its spec, whether a before and an
after side are recorded, its newest candidate, when a person last judged it, and whether
it is `waiting`. A render is a candidate for an asset when its file is named after it
(`<asset>.png`). The asset waits when its newest candidate is newer than the last verdict
on it. The waiting assets come first, and `says` counts them. Grouped into families, they
go to `verdict.sitting(families, out=)`, which writes every sheet as `<out>/<family>.png`
so a person looks once. The answers come back as one `judge` call per family. The list
decides nothing and reorders nothing.

## A baseline cannot be written afterwards

The baseline is what the existing pipeline costs today, recorded **before anything is
ported**, so that it cannot be reconstructed favourably once the answer is known.

That is enforced rather than asked for: starting the *before* side for an asset the plugin
has already made is refused (`loop.baseline-too-late`). Each run also carries the commit it
was taken at, so its place in the order is checkable by somebody who was not there, and the
ledger is append-only and committed with the tree.

A comparison with only one side recorded is refused too. A claim measured on one side is not
measured.

## A run is recorded, not reported

Binds **PW115**. `loop.spent` adds whatever its caller says. Recording the stars charged
32 renders for 28, because four final bakes were cache hits the caller counted as renders.
It was caught only by reading the log, in a ledger that is append-only once committed. A
bake already knows which it was. Inside `with loop.recording(run):` every `render.bake`
counts itself into the run: a fresh render adds to `renders`, a hit to `cache_hits`, and
both add their seconds to `render_seconds`. The parallel search counts its workers' bakes
the same way, since no run is open in a worker. A comparison shows `cache_hits` beside
`renders`. A hit is not free and not a render, and a loop that is fast because it repeats
itself should be visible as that. `spent` stays for what the plugin cannot see.

## The claim is about the second change, not the first bake

Binds **PW114**. The stars' first comparison said the work was not reduced: 8.6 s the new
way against a 3.3 s re-bake of constants already found. A first port will say that for
nearly every family, because the old rig's cost was never the first bake. It was the
afternoon that found the constants, and that afternoon comes back whenever something they
were tuned against moves.

So a run can name a `change` (`loop.start(asset, way, change="palette hue")`): one
perturbation of an asset already made both ways. It can be a hue, a sample count, a
renderer version or a geometry parameter. Each way then has to get back to an accepted
look. The old way is a person retuning, and `spent(person_minutes=)` records their time as
it happens. A change on an asset with no first port is refused (`loop.not-ported`), and
the baseline rule holds per change: a before started after that change's after is
`loop.baseline-too-late`. `compare(asset, change=)` compares that change's runs alone and
says which `event` it was about, with the asset's other `changes` beside it. The verdict's
wording is unchanged. Person-minutes are among the costs it watches for having moved.

## The comparison is allowed to say it got worse

The verdict is one sentence, and the order it checks in is the order that matters:

1. **more overruling than before** — "faster or not, it is approving work that gets
   rejected";
2. **no faster** — "the work was not reduced by this measure";
3. **faster, but renders, calls or credits went up** — "the cost may have moved rather than
   gone", which is the specific failure this line exists to catch;
4. **faster with nothing else higher** — the only case that is unambiguously a win.

**A side can say what it did not measure** (§PW116). Every before side of Cottony's ledger
said in its brief that the hand search was never timed, and `compare`, which does not read
briefs, summed it as complete and called the stars not reduced. `loop.start(...,
unmeasured=["seconds"])` names the costs a run never measured: `seconds`, `renders`,
`calls`, `credits` or `person_minutes`. Anything else is `loop.unknown-measure`. A
comparison lists them per side under `unmeasured`, and they take verdicts out of reach
rather than deciding them. With seconds unmeasured the verdict is **inconclusive**:
neither faster nor slower can be said. A cost left unmeasured is never said to have gone
up, and a faster verdict names it. The overruling verdict still stands, because it needs
only the verdict counts.

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
search accepts comes back as `fill (W at the sphere rung's size)` rather than `fill`, the
watts being scaled by the square of the subject's size since §PW84. That does not refuse the
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

## A family is stated, not scripted

Binds **PW120**. Cottony's three port scripts, about a hundred lines each, are one skeleton:
build or ingest the models, search the rig against their specs, bake the accepted ones
where the game reads them, and record the run. `port.port(family_file, run=)` runs that
skeleton from a TOML file that states only what differs. It gives the `family`, its `rig`
(`searched` over `[search.<axis>]` ranges, or `given` as a `[given]` table), a `budget`,
and one `[[member]]` per asset. A member has its `spec`, a `model` or a `declaration` built
first, what its render `fixes`, where the search renders it (`out`) and where it is
`bake`d. The axes belong to the family, so every member's spec is searched over them
together, through `search.family`. Nothing is baked unless every member passes. The bakes
run at the final rung and are checked there. With a run open, every render counts itself
into it, finals included. Anything else in the file is `search.bad-family`. The verdict on
the look is still a person's, given with `verdict.judge`. The scripts that exist stay until
their family is re-expressed. The next one need not be written.

## A second adopter, unlike the first

Binds **PW117**. "No key had to be added" was the boundary holding for one project, and the
features since were shaped by that project's numbers. So `tests/fixtures/website.toml` is a
project chosen to differ: a web page with pictures, no Godot, no locale to pin, two rungs
instead of three, a smaller ladder, and a scale kept in a TypeScript module.
`tests/test_second_adopter.py` is its gate. It set `[paths] renders` and `specs`, `[render]
rungs`, sizes, samples and seed, `[units] source`, and an empty `[capture] declared`.
Again, no key had to be added. Two things inside the plugin did change, and both were
Cottony's shape compiled in:

- **Every project was assumed to enable all three rungs.** A project with no sphere was
  refused any material question (`render.rung-disabled`), though its preview carries
  everything the sphere does. `plan`, and the search's own rung choice, now take the
  cheapest enabled rung at or above the one the question needs, and `why` says which rung
  was skipped. A question nothing enabled can carry is still refused.
- **A scale could only be read from a GDScript constant, a JSON key or an ini line.**
  TypeScript's `export const PIXELS_PER_METRE: number = 48` already read. A typed
  C-family constant, such as `public const int CELL = 112` or `static readonly float`, did
  not, and it now does.

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

**A runner calls `polyweave.readable()` before it prints anything** (PW73). Nothing in the
plugin prints its own prose: a refusal's message and remedy, and every line a run reports,
are returned for the caller to print. So the encoding of the stream they land on belongs to
the consumer's process, and left at the locale's on a Windows desk an em dash goes out as
one correct cp1252 byte and reaches a UTF-8 reader as a lozenge. Nothing is lost writing
it, which is what makes it hard to notice: the process that wrote the line saw nothing
wrong. The call is the consumer's rather than an import side effect, because a library must
not reconfigure a process it does not own. It returns the streams it changed, is empty when
they were already UTF-8, and is safe to call twice. All three of Cottony's runners make it.

**A consumer's agent is told the plugin exists** (§PW132). Six of Cottony's tools
imported it and none of its agent documents named it, so each session rediscovered it
from a script's imports. The repository is now a Claude Code plugin and its own
marketplace. `.claude-plugin/plugin.json` declares the `polyweave` MCP server inline,
since the root `.mcp.json` also launches this repository's roadkeep and would break in
someone else's project. `skills/polyweave/` is a skill for a session *driving* the tool:
the four-call loop (brief, build, search, check) and its rules, with two reference pages
opened on demand. `hooks/hooks.json` runs `python -m polyweave notice` at SessionStart.
That prints one line saying which installed copy answered, how many declarations and
specs the project holds, and that `asset.brief` answers where one stands.
`tests/test_plugin.py` holds the notice to 240 characters and the skill to 3,400. It
requires every operation the skill names to exist, and keeps plugin and project skill
names apart, because a plugin skill drives the tool and a project skill changes it.

**A derived file is not edited by hand** (§PW133). A built mesh or voxel file follows its
declaration, and the build stamp hashes only inputs, so a hand edit went unnoticed and
kept being reported `cached`. The plugin's `hooks/guard.py` holds the rule where it is
broken, as roadkeep's guard does for its files. On `PreToolUse` it denies a Write or Edit
to a file a build stamp lists as an output, or that carries a provenance record. The
denial names the declaration to change and the `geometry.build` to run; the stamp now
records its `source` for that. A shell command naming such a file gets `ask`, because
nobody parses what a command writes. On `SessionStart` it marks the time. On `Stop`, any
recorded artefact changed since then that no longer matches its record blocks the stop
and is named, and a stop already continuing because of it is let through. It uses the
standard library only, and any failure inside allows the edit.

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
