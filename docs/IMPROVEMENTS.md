# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

### §PW495 The declared finish as a Godot material

Found in Spinhold on 2026-10-17, for the plastic city of PW498
(`docs/specs/geometry.md`). When the finish PW494 shipped (`docs/specs/geometry.md`) is
accepted on a sitting, the game must draw the same thing. A built model reaches Godot as
a `.glb`, and the importer keeps what glTF and its own mapping keep: a coat, a rim, a
subsurface tint or a sheen may come in at other numbers or not at all, and the game's
city is drawn on a MultiMesh in its own shader, which takes no material from a mesh.
Then the accepted look is re-made in game code by eye, which is what the project's rule
forbids.

What polyweave should do: write the declared material beside the build as a Godot
material (a `.tres` StandardMaterial3D, or a generated `.gdshader` where a feature the
standard one lacks is asked for), with the same numbers the bake used and a provenance
record, so the game loads what was judged. A capture of the game against the bake of the
same model at one rig says whether the two agree.

## Block H — Proof on a real game

### §PW36 Cottony adopts it without a fork

Cottony is the first consumer and the test of whether the configuration boundary in
Block A actually holds. Its pipeline uses everything this backlog proposes: a
script-built mesh, a fetched mesh re-dressed in drawn cloth, a cushion inflated from a
drawing, a fourteen-parameter rig, a paid service with a lock file, and four engine
captures. If all of that can move onto the plugin with a configuration file and no fork,
the boundary is real. If any of it needs a change inside the plugin that only Cottony
would ever want, that is the defect, and it is much cheaper to find here than via a
second adopter. The migration is also what keeps this from being a rewrite for its own
sake: each piece moves only once the plugin's version passes the same check the existing
one does, and the pieces that are better left alone stay where they are. What this line
delivers is the adoption plus a written list of everything that had to be configured,
which is the plugin's real interface, discovered rather than designed.

### §PW57 One floor of five is a target now, and one more is a floor

A threshold inside a gate can only answer after the render is spent. The same number in
an acceptance spec is what `search` moves towards, so the bar stops being a verdict and
becomes the target. That was the reason for this line, and the vivid floor is now that:
`docs/design/accept/board_drawn.accept.toml` and `board_mesh.accept.toml` in Cottony,
read by `saturation_hsv_p99`, with `check_vivid.py` reduced to running them. It needed a
measure: at a whole screen's tail HSL saturation reads 1.0 on every picture, so the
claim in `docs/specs/acceptance-spec.md` that it needed nothing new was wrong.

Reading the other four corrected the count. Only one more is a floor on a picture.
`check_palette.py` checks that `pieces.gd` mirrors `palette.py`. `check_plush.py` and
`check_markings.py` draw a synthetic body through Cottony's own 2D code and assert
ratios between two materials drawn in one run. They are unit tests of drawing code, no
asset is under them, and no search turns their parameters. They stay where they are.

What is left is `check_pieces.py`, which holds the committed sheet
`docs/design/screenshot-pieces3d.png` to three rules: ink on the faced kinds, no pale
ring of marks round a rim (rope or thread), and the kinds' radial silhouettes kept
apart. None of the three is a measure in `docs/specs/measurements.md`. The ring rule is
a property of a set of marks, which the script argues at length, and porting it is
either a measure that counts marks forming a ring on a subject, or a person deciding it
stays a test.

### §PW82 The rig has to actually go

This is the task PW53's objection was about. Setting it aside said that one asset moving
leaves bake_model.py standing for the rest, so the rig the plugin exists to remove is
still the thing that runs — and that stays true of two families, or five. It stops being
true only when the file is gone.

So the sequence needs an end that is checkable rather than assumed. After PW76 through
PW81 there should be no `tools/art/bake_model.py`, nothing importing it, and every
sprite under docs/design/art/ produced by the plugin. Until then Cottony has two routes
to the same picture, and the older one keeps working, which is exactly how a replaced
rig survives its replacement.

It is filed separately rather than folded into the last family because the failure it
guards against is not any one port going wrong. It is six ports going right and the file
remaining, with a handful of constants nobody moved and no reason left to look at them.

If a family turns out not to port — the friends and the mascot are the candidates — then
this is where that is recorded honestly: what still runs by hand, and why the rig shrank
instead of disappearing. An outcome worth having, stated, beats the same outcome
unstated.

### §PW546 The dialogue proof ends on the game's signal

On 2026-10-18 the gate went red at 98ea6d5 on
`test_kit_dialogue.py::test_a_broken_dialogue_box_fails_the_proof_by_name`, in its
`_shown += 100000.0` case (a box that types every character at once). The proof came
back `no-signal`: it printed no KIT line before the engine run's timeout, so the test
found no "characters typed in" to read. The file passed four runs out of four alone, and
the change under test touched no dialogue code.

So under the full gate's twelve workers this proof, with that mutation, runs past the
time it is given, where alone it finishes. Like PW525, the proof is racing the clock.

Measure first: run the file under `-n 12` beside the render and kit tests ten times and
count `no-signal`, and read the dialogue proof for a wait counted in wall-clock time or
in frames that the mutation can stretch. Then make the proof end on the game's own
signal. Each typed-in check waits for the box's own `finished` or a frame count it sets,
not a time, and a proof that cannot finish says which step it was on. Done when the file
holds ten runs of ten under the gate's load.

### §PW547 Pick one of several on the review page

Found in Spinhold (RK168, 2026-10-19). `voice.design` laid three previews of the studio
voice at art/review/rk168-studio-voice, and `voice.choose` takes one of them. On the
review page each preview is a card of its own with Aceitar and Refazer, and the batch
accept takes every card, so the owner accepted all three. Nothing in the sitting said
the cards were alternatives, and nothing stopped three accepts where one was meant. The
agent had to ask in chat which one, and the verdicts now record three accepted voices of
which the game uses one.

The same shape comes back wherever polyweave lays out candidates for one slot: voice
previews, takes of a spoken line (`sound.speak`), picture variants (`picture.vary`), and
search results a person picks from.

What polyweave should do: a sitting may declare its members as alternatives for one slot
(`pick = "one"` on the family, or a `choose` kind of sitting). The review page then
draws them as one card with a select (radio buttons) and a single answer, refuses an
accept of more than one, and the batch accept skips such a card. The answer records the
chosen member; the others are passed over, not refused. `voice.design` and `sound.speak`
lay their sittings this way, and `verdict.answers` says which member was chosen, so
`voice.choose` can take it from the answer with no question in chat.

Done when Spinhold's next voice or take sitting shows one select, the owner picks one,
and the chosen id reaches `voice.choose` from the answer alone.

### §PW548 Measures for a transparent picture's edge

Found in Spinhold (RK150, 2026-10-19). The game's 4K transparent logo
(art/brand/spinhold-logo-4k.png, drawn by picture.vector) needed an acceptance spec
whose bounds say its alpha edge is clean: no grey or dark halo round the letters, no
wide half-transparent fringe left by a resize or a matte. RK150's design named
`fringe_width` and `edge_width`; `measure.available` lists neither, and nothing among
alpha_coverage, edge, luma or saturation reads the edge's alpha ramp. The spec
(art/accept/spinhold-logo-4k.accept.toml) went out without the predicate, with a comment
naming this line.

What polyweave should do: measures over the boundary of a picture with an alpha
channel, on the pixels whose alpha is between the floor and opaque:
- `fringe_width`: the median width, in pixels, of that ramp across the silhouette's
  edge, so a resize-softened or feathered edge reads wider than a crisp one;
- `fringe_luma` and `fringe_delta_e`: the brightness and colour of the partly
  transparent pixels against the opaque ones next to them, so a dark or white matte
  halo (premultiplied wrongly, or keyed off a background) is caught.
They take `region` like the rest, are listed by `measure.available`, and accept.check
reads them as any predicate.

Done when Spinhold's logo spec holds `fringe_width` and `fringe_delta_e`, and a copy
resized with a dark matte fails them where the drawn one passes.

### §PW549 Place an accepted take where the game loads it

Found in Spinhold (RK168, 2026-10-19). `sound.speak` wrote three takes of the studio tag
under art/review/rk168-studio-tag, `sound.sitting` laid them, and the owner accepted
take_3 on the review page. The game loads the tag from
game/audio/voice/SPLASH_STUDIO.mp3. No operation carries an accepted take there:
`verdict.move` moves a whole sitting's folder, `verdict.promote` is for a gate's refused
picture, `provenance.borrow` brings in another project's file. The agent copied the mp3
and its .prov.json by hand. The copied record still names
art/review/rk168-studio-tag/take_3.mp3 as its artefact, so `provenance.verify` checks
the review copy twice and the game's file not at all.

What polyweave should do: an operation (or `verdict.answers` with a `place` step) that
takes an accepted member of a sitting and a destination under the project, or the cue
the member was spoken or rendered for, copies it there, and writes a record for the new
path that names the take it came from, the verdict that accepted it, and the purchase it
was bought in. Re-running it after a new verdict replaces the file and its record.

Done when Spinhold's SPLASH_STUDIO.mp3 is placed from the accepted take with a record
naming its own path, and `provenance.verify` lists it.

### §PW553 Game arguments for game.open and clip.shots

Found in Spinhold (RK241-RK243, 2026-10-19), framing the cutscenes of the Waist, the
Stern and the Quilt with `clip.shots`. Each cutscene plays only once its world begins,
and the game opens a run straight in a world with its own flag (`--world=quilt`, which
run.cmd passes). `game.open` takes a scene, a locale, a resolution and a seed, but no
arguments for the game, so the flag could not be given. The agent reached each world by
hand, three times over: game.open, game.step 5, game.call Campaign._settle(["quilt"]),
game.call RouteScreen.hide, game.call Campaign._begin(1), then clip.shots and
game.close. That is three private methods of the game, called from outside, to stand in
for one flag.

What polyweave should do: `game.open` takes `args`, the game's own command-line
arguments after `--`, as `engine.run` does for a script, recorded in the session's log.
`clip.shots` could take the same, so one call opens the game where the clip plays,
frames it and closes it.

Done when Spinhold frames a world's cutscene with one `clip.shots` (or `game.open` with
`args: ["--world=quilt"]`) and no game.call.

### §PW554 Declared timelines of a scene's properties

Found in Spinhold (RK155, 2026-10-19). The title's logo reveal (the halo coming up out
of the dark, the orbit spinning in, a light wiping the letters on from the edge, a hit
as it settles) was to have "its timing and curves declared (polyweave clip)", as the
cutscenes are with `clip.camera`. polyweave's clips are skeletal motion (`clip.new` keys
joints for `motion.bake`), and `clip.camera` builds only camera shots. Nothing declares
a keyed timeline of a scene's own properties (a Control's modulate, scale or a shader
parameter) and builds it into the game, so the reveal's curves were written as constants
and smoothsteps in game/ui/title_logo.gd, with a comment naming this line.

What polyweave should do: a `clip.timeline` (or a kind of clip) that declares tracks of
keyed values on named properties, `node:property` or `node:shader_parameter/name`, each
with its easing, plus marks for a cue (a sound at a time), and builds it into a Godot
`Animation` a game plays or seeks by time, recorded like the camera clip. `clip.shots`,
or a capture of it, frames it to judge.

Done when Spinhold's reveal is a declared timeline built by polyweave, and the constants
in title_logo.gd are gone.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

### §PW449 Driven from a second MCP client

The server is MCP and nothing in the protocol ties it to Claude Code, but everything
that teaches an agent to use it arrives with the Claude Code plugin: the skill, and the
hook that guards derived files. Another client, such as Cursor or Codex, gets the tools
list and nothing else. Whether an agent there gets a call right the first time, which is
the project's one test of a feature, has never been tried.

MCP directories in 2026 compare Blender, Godot and Unity servers side by side, and they
are where a developer looks for one. Being listed there is free reach, but only honest
once the surface has been driven from a client without the skill.

The run is the line: set the server up in Claude Desktop, the client the owner has
(2026-10-15), ask it for one asset end to end, and file what it got wrong as friction.
Two findings are expected and are the reason to do it before any listing. Whatever the
skill alone teaches has to move into tool descriptions or `describe`. And every promise
that relies on the skill or a hook, rather than the server, is named; PW443 is the first
of those.

Evidence that it landed: a second client builds, checks and offers one asset for a
verdict, and each gap it met is a filed line.

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

### §PW450 Buying a picture from Scenario

Block N holds pictures to a canon: a family's approved members, its palette and its
style block. The services behind it today are FLUX and Ideogram, which take the style as
words, and PW180 sends one canon picture as a style reference on Ideogram 3.0. Scenario
takes a different route: a model trained on a team's own art, which reviews in 2026 name
as the strongest answer to style consistency for game art.

A canon is exactly the training set such a model wants, already chosen by a person's
verdicts. This line is an adapter behind the existing `picture.buy` surface: the same
ceiling, quote, ledger and provenance, and a record naming the trained model and which
canon members trained it, so a model trained before a member joined reads as outdated.

Training spends money, so it is a purchase like any other, quoted and bounded by the
ceiling, and never started on the agent's own judgement. The pictures it returns are
held to the canon and the gate like any service's; being trained on the style earns no
pass.

Evidence that it landed: one family's canon trains a Scenario model within the ceiling,
a picture bought from it passes or fails the family's gate, and its record names the
model and the members.

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

## Block Q — Words held to the world

## Block R — Levels measured before a person plays them

### §PW201 Whether a bot's win rate says how hard a level feels

The block rests on one premise: that a cheap simulated player, run headlessly over many
seeds, ranks a game's levels by difficulty the way a person playing them would. If it
does, a level's difficulty becomes a number a search can aim at. If it does not, every
later line tunes against noise.

The spike ran in Cottony on 2026-09-28. A throwaway bot, gitignored at Cottony's
.polyweave/spike/bot.gd, played the 20 shipped levels over 200 seeds each, first taking
the hint's swap and then greedily. Both won 95 to 100% of deals on every level. Their
moves left fell from 25 and 30 at level 1 to 12 and 18 at level 20, in the same order.
The owner, playing, felt no difference.

So the bot and the person agree that nothing here is hard. That cannot answer the
premise, since a set with no spread tests no ranking. It also suggests that moves left
is not what a player feels, and a chance of losing is. Cottony filed RK150 to give its
curve a loss within reach.

Once RK150 lands, rerun the bot. The owner then plays eight levels spread across its
ranking, and says whether the order matches what they felt and where it does not. An
agent does not judge the proxy it built.

If yes, the findings go into the designs below: which bot, how many seeds, and which
percentile carries the feel. If no, the open lines are retired with the spike as the
reason.

### §PW202 A level probe the game runs and polyweave reads

A match-3 bot and a shooter's threat count have nothing in common except their shape. A
script inside the game takes a level and some seeds, plays or analyses it, and returns
numbers. polyweave cannot own that script, since it would be one genre compiled in. It
can own the handshake, the way the capture environment already does.

`[levels] probe` in `polyweave.toml` names the script and the measures it reports, each
with a unit and a direction. `level.probe` runs it through the existing engine runner.
The level file and the seeds are passed after `--`, the same as capture settings. The
script prints one `level: name=value ...` line per seed. polyweave checks that every
declared measure came back and that nothing undeclared did, and a line missing a measure
is a refusal rather than a zero.

Across the seeds, polyweave aggregates each measure at the percentiles the project asks
for, because a level's feel lives in its bad runs as much as its median, the same lesson
that measures a look at a percentile. The result is written beside the level with its
seeds, the probe's hash and the engine version. A later run is compared against that
record, so a change in the rules that moves a level's difficulty is reported, not
rediscovered by a player.

### §PW203 A level declaration compiled by the game's own step

Both consumers already treat levels as data. Cottony has 20 JSON files written by
`make_levels.py` from a difficulty curve. Starship has 15 `.tres` waves under three
phases, and its own comment says a harder wave is a different file, never a multiplier
in code. What neither has is a layer that checks a level before the engine sees it, ties
it to the world, and records how it was made.

A `*.level.toml` is the source a person or an agent edits. Its schema is the project's,
declared in `[levels] schema` as a JSON Schema, because the plugin must not know what a
wave or a goal is. `level.validate` checks it against that schema. Where the project
declares a world (`docs/specs/world.md`), every field the schema marks as an entity
reference must name one of its ids, so a wave that spawns an enemy the world never
declared fails with the line and a remedy.

`level.compile` runs the project's declared compile command, which turns the source into
the engine's own resource: Starship's `.tres` or Cottony's JSON. It then writes a
provenance sidecar naming the source, the schema and the command's hash. The compiled
file is still what the game loads, so nothing at runtime depends on polyweave. A
hand-tuned level, like the files `make_levels.py` refuses to overwrite, stays a source
file a person owns.

### §PW204 Difficulty bounds and a search over a level's parameters

Once a probe reports measures and a level compiles from a declaration, a level's
difficulty works like any other asset property. The acceptance spec already states
bounds on measures. A `*.accept.toml` for a level bounds the probe's measures at a
percentile: win rate at the median between 0.45 and 0.70, and moves left at the tenth
percentile no lower than one. `accept.check` reads the probe's record and passes or
fails.

A level set needs one more kind of bound, because a game's difficulty is a curve and not
a single level. A set spec names its levels in order and states the shape: difficulty
never falls by more than a declared step between neighbours, rises across each region,
and dips after a boss. Each is checked against the measures and reported as the pair of
levels that broke it.

`search.sweep` then searches a level's declared parameters (Cottony's target and moves,
a wave's count and interval) for values that pass. Every candidate is compiled and
probed, and all of them run locally at no cost. What the search returns is a proposal.
Which candidate ships, and whether a level that passes also feels right, are decided on
the verdict page with the bot's numbers shown next to it, because the bot is a proxy
that PW201 tested once and a person holds to account afterwards.

### §PW205 A second genre: Starship's waves measured without a bot

A bot that plays a shooter well is a project of its own, so Starship cannot prove the
level contract by playing. It can prove it by analysis, and that is the useful test: a
probe that reads a wave without running it has to fit the same handshake as one that
plays a board over 200 seeds.

Starship's probe loads a compiled wave `.tres` headlessly. From each group's count, delay and interval it lays the spawns on a timeline and reports four measures:
- the peak and median enemies alive at once, per second of the wave;
- a threat total weighted per enemy kind, with the weights in the project's config;
- the share of the `time_limit` that the last spawn leaves for clearing;
- how many humans a keeper wave puts at risk at once.

Seeds are irrelevant here and pass as one, which the contract must allow without special
cases.

`check_phase_waves` already asserts that the enemy total rises each phase. A set spec
over these measures states that rule and the ones it misses, such as no spike of more
than a declared factor between neighbouring waves. The line is done when both genres
pass through `level.probe` and `level.compile` with no change to polyweave between them,
and the set spec follows once §PW204 lands. A change needed for the second genre is the
evidence that the first one leaked in, which is what the non-goal "One genre's level
format built in" forbids.

### §PW206 Cottony's levels made through polyweave

Cottony is where the level loop pays for itself first. Its 20 shipped levels are JSON
files generated from curve constants that `make_levels.py` reads out of `level_set.gd`
with a regular expression. Any level without a file falls back to that same curve at
runtime, so level 900 is only as good as a curve nobody has measured.

Adoption is done when:
- Each of the 20 levels is a `*.level.toml` under a schema Cottony declares, and `level.compile` writes the JSON the game already loads.
- The match-3 probe from PW201 is Cottony's declared `[levels] probe`, and every level carries a probe record.
- A set spec holds the 20 levels to the curve a person agreed on the verdict page, and `accept.check` passes on all of them.
- `make_levels.py` is deleted, and the runtime fallback curve is fitted from the accepted levels rather than typed.

The census from Block H counts which of Cottony's levels are made this way. The fallback
curve is the part to watch: it is still a formula for levels nobody declared, and the
probe can at least sample it. Probing levels 21 to 200 from the curve and reporting
where they leave the set spec's bounds says whether the endless tail keeps the promise
the first twenty make. Cottony's RK150 (2026-10-16) set that bar by hand: the careless
spike bot, swept with engine.sweep, put level 20 at 64 to 66% wins, against the owner's
60%.

### §PW327 Playtest traces measured beside the declared curve

Found in starship while planning its Block V (RK176, RK177): the owner finds the waves
unbalanced and wants balance measured, not felt.

§PW205 measures what a wave declares. It cannot measure what happened when a person
played it, and it still reads `.tres`: starship's waves are now authored in
`game/waves/phase_<n>.waves.toml` (RK122), and Block V adds formations, rails, `follow`
and `sway` (RK172 to RK174), so a probe must read the compiled spawn timeline, not the
file format.

What starship needs from polyweave:

- **A trace contract.** The game writes one event per line, each stamped with phase, wave and second: `spawn` (kind, weight), `kill` (kind, time alive), `hit` and `life_lost`. polyweave reads one trace or many and gives, per second, damage taken, kills and enemies alive, averaged across runs.
- **The declared curve beside it.** From the spawn timeline and the per-kind weights (§PW205), the pressure entering and alive in the two bounding cases (every enemy killed on landing; nothing killed until the time limit), and the longest gap with nothing to shoot.
- **A spec over both.** Bounds such as "alive pressure never above N", "never more than 2.5 s with nothing to shoot" (starship's multiplier window) and "each phase's peak above the one before", checked by `accept.check` and failing with the rule named. A person sets the bounds; the feel stays a verdict.

Until it lands, starship keeps the pass in `dev/` as the thinnest workaround, named
against this line.

### §PW480 Objects told from a scene of their own colour

Found in Spinhold on 2026-10-16 (RK198), re-reading Resogun's phase 1 from the owner's
capture (`reference.register` as `resogun_p1`, 170 frames from `reference.frames`).

The enemies are violet and blue-violet, and so is the city behind them: a violet ring,
navy towers, pink-lit edges. `reference.objects` was called three times on
`.polyweave/references/resogun_p1`, area `[0, 180, 1920, 1080]`:

- pod `#604ba0` tol 0.12, samples (two 76 px crops), match 0.25, and chain `#282670`
  tol 0.10, one sample: 9595 tracks, the city counted everywhere.
- pod alone, tol 0.06, match 0.12: 0 tracks.
- pod alone, tol 0.10, match 0.20: 987 tracks; `objects_004.png` shows most of them on
  buildings and the ring, while the stack of pods at 0:28.5 is partly missed.

No step between those settles it: hue and an average colour distance to a sample cannot
tell a lit studded sphere from a lit window of the same hue. Colours were also taken by
a throwaway PIL snippet, since nothing picks a kind's colour or sample from a point.

What polyweave should do: separate objects from a busy scene by more than colour, using
what the footage gives: motion against the scrolling background (frame differencing
after aligning the scene), shape (a sample's silhouette, not its mean colour), and the
white warp-in each enemy makes a second before it is live. And `reference.sample(frames,
at, box, name)` to cut a kind's sample and read its colour from a frame. Until then
Spinhold's RK198 cites frames, not tracks, and its comparison with `phase_poc` waits on
this line.

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

## Block U — A window on everything a project governs

### §PW311 The window proved on Starship

Every block here that reached a person was finished only when a real owner used it.
PW287 through PW295 were each found by Starship's owner on a review page that passed
every test. The window is the same kind of surface, so it is proved the same way.

On Starship, the owner does the following in their own language:
- opens the project in the window;
- finds one generated picture and one sound through the inventory, without typing a path;
- marks where the picture is wrong;
- asks for a change in their own words;
- answers the session's questions;
- judges the result in the sitting it ends on.

One of the two revisions should need a paid call, so the price stop (PW308) is exercised
on a real balance under a small ceiling. One should reach a dependent, so the scope
question (PW309) is seen.

The evidence is the two closed revision records, the screenshots of each step taken
before handing the window over, and every friction filed as its own line in this block.
It is not a test run. A change of plan that the owner asks for mid-way ("undo, try the
other palette") is part of what is being proved, because a revision a person refines
several times is the case this block exists for.

## Block V — Parts every game repeats, installed already proved

### §PW368 Declared states and transitions

Menus, characters and the flow of a game are each a state machine written by hand, and
the failure is structural: a state no transition reaches, or one with no way out that
was not meant to be final, found only by a person who walks into it.

A kit could let the project declare its states and transitions, generate the skeleton
the code fills in, and check in the gate that every state is reachable from the start
and has an exit unless it is declared final. The check is the valuable half, since it
needs no run.

It is the most opinionated kit in this block: games structure their state very
differently, and a skeleton that suits one may fight the next. So it stays an idea until
Starship and Cottony both show code it would replace, at which point the shape it should
take is read off that code rather than invented here.

### §PW550 Kit records that name where the file landed

Found in Spinhold (2026-10-19), running `provenance.verify` after RK216 moved the game
onto the prompts and remap kits. It reports 128 records as missing: every icon and pad
picture the kits brought, under addons/polyweave/prompts/icons and
addons/polyweave/remap/{icons,pads}. Each copied .prov.json still names the artefact
where polyweave built it, either `src/polyweave/layers/kits/prompts/core/icons/...` or a
bare `core/icons/...`, paths that exist in polyweave's checkout and not in the game. The
files are present in the game; only their records point elsewhere. So the verify a
project runs before release is drowned in 128 false findings, and a real missing
artefact would hide among them.

What polyweave should do: `kit.install` and `kit.update` rewrite each copied record so
its artefact is the path it lands at in the project, keep the kit-side path as the
source it was copied from, and record the kit version. The two spellings (with and
without `src/polyweave/layers/kits/`) should become one. Spinhold's existing records are
fixed by the next `kit.update`.

Done when `provenance.verify` in Spinhold lists the kit's icons and pads as ok and
reports nothing missing.

### §PW551 Help lines filled with icons from the same marks

Found in Spinhold (RK147, 2026-10-19). Every help line in the game's string table holds
`{action}` marks and `{move}` (PAUSE_HELP reads "{pause}  resume  {bomb}  quit to title
..."), and `fill(text, player, in_family)` turns them into words for the player's own
pad. To draw the same lines with the kit's icons, which the owner accepted on
2026-10-19, there is only `bbcode(text, size)`, and it does not meet them:

- it reads `[action=x]`, a different mark from the `{x}` the table and `fill` use, so
  every row would be written twice or converted by the game;
- it takes no `player` and no `in_family`, so the second player's line and a screen
  that names a family both draw the first player's pad;
- where an action has no icon (a key with no keycap, an unbound action) it writes the
  action's id, not the word `fill` would;
- `{move}` is not handled at all.

Spinhold's help label bridges it in a few lines, naming this line.

What polyweave should do: `fill_bbcode(text, player := 0, in_family := "", size := 32)`
reading the same `{action}` and `{move}` marks as `fill`: an icon where the family has
one, the word `fill` would give where it has none, `{move}` as the stick's or the four
keys' icons. `watch` gains a form that keeps a RichTextLabel filled with it, so a screen
states once what it shows.

Done when Spinhold's help labels call the kit and the game's bridge is deleted.

### §PW552 Let a freed lambda follower go

Found in Spinhold (RK239, 2026-10-19). A help label called
`PolyweavePrompts.shared().follow(func() -> void: show_line(...))` from a node that was
later freed. On the next `refresh()` (the remap kit's `load_kept` calls `rebound()`),
the kit filtered followers with `redraw.is_valid()`, kept the lambda because a GDScript
lambda's callable still reads as valid after its instance is freed, and called it:
"Attempt to call function '<anonymous lambda>' on a null instance", once per freed
screen. The doc comment promises "one whose object is freed is let go".

Spinhold's workaround: follow a bound method (`_refill`) instead of a lambda, with a
comment naming this line.

What polyweave should do: `follow` and `refresh` let a follower go when
`redraw.get_object()` is null or freed (`is_instance_valid`), not only when `is_valid()`
fails, so a lambda made in a node is dropped with the node; the kit's proof frees a node
that followed with a lambda and refreshes, and expects no error.

Done when a freed node's lambda follower is dropped silently.

### §PW555 Ready button maps in the remap kit

Found in Spinhold (RK149, 2026-10-19). Its owner wants ready button maps a player picks
in one press on the controller screen, instead of rebinding eleven actions one by one.
The game's input is the remap kit's (PW345), so the maps belong there, not in the game.

What the kit should do:
- A game declares its maps beside its actions, in the remap declaration
  (res://polyweave_remap.gd): `const MAPS := {"face": {"fire_left": ["button:2"], ...}}`,
  each a complete binding of the pad half. The keys are left alone, as `rebind` keeps the
  halves apart. "default" is the project's own InputMap.
- The remap screen and the drawn pad screen (PW428) gain a Map row: left and right step
  through the maps, the drawn pad shows the one in focus before it is applied, and
  applying it starts a "keep this?" countdown that puts the old map back if nothing
  confirms it.
- What the player rebound by hand is kept aside as "custom", so trying a map and leaving
  it never loses it, and "custom" is offered among the maps once it exists.
- The store keeps the chosen map's name and the custom map.
- The kit's proof checks that each declared map binds every action with no button
  shared, and that the countdown undoes an unconfirmed map.

Done when Spinhold declares Default, Face buttons and Left-handed maps and its
controller screen offers them with the countdown, and RK149 needs no code of its own for
them.

### §PW556 Button names chosen per pad

Found in Spinhold (RK149, 2026-10-19). The prompts kit reads a pad's family from the
name the system gives it (`family_of`). A pad whose name hides its maker (an 8BitDo in
one of its modes, a clone, a pad behind Steam Input) reads as generic, or as the wrong
family, and the player has no way to say which buttons they are holding. Every prompt,
the remap screen and the drawn pad then name the wrong buttons.

What the kit should do: a choice of button names per pad, Automatic (as `family_of`
reads it today), Xbox, PlayStation, Switch or Generic, kept in the remap store by the
pad's name so a second pad keeps its own. A forced choice wins over `family_of`
everywhere the kit names a button: `fill`, `named`, `icon_path`, the watched labels, the
remap screen and the drawn pad, all refilled at once on the change. The remap screen
offers it as a row for the pad in use. The kit's proof forces each family on a pad named
as another and expects every prompt renamed.

Done when Spinhold's controller screen offers Button names and a forced choice renames
every prompt at once, with no code of the game's own.

### §PW557 Menu actions per player

Found in Spinhold (RK242, 2026-10-19). The owner asked that every menu confirm on A and
go back on B, which the game does through `ui_accept` and `ui_cancel`. The crew draft is
one player's own screen: in co-op the second player's draft opens for them alone. The
players kit copies a player's actions as `p2_<name>` (`action(name, player)`), but only
the remap store's actions, never the `ui_` ones, and the project's `ui_accept` answers
every pad. So nothing says "A on player two's pad": the first player's A would take the
second player's card.

Spinhold's workaround: the draft reads `ui_accept` and `ui_cancel` from `_input` and
keeps the press only where `player_of_event` is the draft's player, with a comment
naming this line.

What polyweave should do: the players kit gives each seated player their own copy of the
menu actions a game names (`const MENU := ["ui_accept", "ui_cancel"]` in its
declaration, those two by default), pinned to their pad as it pins the others, so
`action("ui_accept", 1)` is `p2_ui_accept` and answers player two's A alone; the first
player's copy narrows to FIRST_PAD once two play, as `_narrow_first` does.

Done when Spinhold's draft reads `PolyweavePlayers.action("ui_accept", player)` and the
`_input` filter is gone.

## Block W — A core that grows by layers
