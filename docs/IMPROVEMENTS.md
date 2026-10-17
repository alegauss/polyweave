# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

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

### §PW372 A camera clip the game plays

Met in starship (RK190): a cinema opening before the first phase, with four camera shots
of the city, each a position, a target and a slow drift over about 1.2 s, cut by a
flash, then a glide back to the run's camera. The project's rule is that timing and
curves are declared and built through polyweave, not set by eye.

`clip.new`/`clip.set_key`/`clip.write` author a clip of joints and their properties, and
`motion.bake` bakes one onto a skeleton. Nothing declares a camera move (a shot list
with position, look-at, field of view, hold, drift, ease and cut), and nothing writes
one the game can play, so the shots live in the project's own
`game/ui/opening_shots.json`, read by `game/ui/opening.gd`, with no record and no spec.

What polyweave should do: a camera clip, a clip whose channels are a camera's position,
target and FOV (absolute or relative to a named anchor, here the ship's start on the
ring), with cuts and holds. Plus an export the engine plays, and a capture per shot so a
person accepts the framing on the review page.

Landed: `clip.camera` builds a `*.camera.toml` into a Camera3D scene the game seeks by
time, recorded as kind `camera` (docs/specs/motion.md, "A camera clip"). Not an
Animation track: an anchor placed at run time, on a ring that is not Cartesian, cannot
be baked, so a place stays in its anchor's frame and the game maps it with `place`.
Left: each shot captured onto a sitting, and Starship's opening moved onto it.

### §PW486 Accepting a look a bound refused

Found in Cottony, RK149 (2026-10-16). A sitting opened with `verdict.sitting` for one
member, the mascot, whose new render failed one bound (`median-tone`, 0.762 against a
min of 0.780). The review page offered two buttons, Refazer and Ajustar o limite, and no
Aceitar. The owner liked the look and asked where the accept was: the page never says
that, when a bound fails, moving the bound *is* the acceptance.

The choices are honest - `accept` means the look is right and the spec agrees, which a
failed member cannot be - but the label `number` carries reads as a tweak to a spec, not
as the approval of a picture. A person who came to approve sees no approve button.

What polyweave should do: when a member failed a bound, label the `number` choice as an
acceptance that moves the bound (pt-BR: Aceitar e ajustar o limite; en: Accept and move
the bound), and say under it which bound moves and to what measured value. Keep `accept`
hidden for that member, as now. Optionally, show a line under the buttons explaining why
Accept is absent ("this member failed median-tone; accepting it moves that bound").

### §PW487 A sweep that keeps what its runs printed

Found in Cottony, RK150 (2026-10-16), sweeping the goal count of level 20 with the
careless spike bot:

    python -m polyweave engine.sweep --script .polyweave/spike/bot.gd --grid @.polyweave/spike/grid.json --pattern "level:" --args=--seeds=200 --args=--bot=careless --args=--levels=20-20 --lanes 4

Two answers misled on the way.

1. Every run came back `no-signal` at about 4 seconds. The cause was the default frame
   budget of 6000 ending a run that prints its line once at the end; the `why` does name
   the budget as a possibility, but a run that the budget killed and a run that never
   printed read the same. `--frames 2000000` fixed it. A run cut off by the budget should
   say so as its own verdict (`budget`), with the frame it reached.

2. With a hit, `lines` held `["level:"]`, the matched text only, not the line the script
   printed. Every number the run measured (wins, spare moves) was on that line and
   dropped. The workaround was a pattern of `level: .*` so the match is the line.

What polyweave should do: keep the whole printed line of each hit in `lines` (or add
`line` beside the match), and give a budget-ended run its own verdict. With both, a
parameter sweep reads its measurements straight off the answer.

### §PW488 A capture that knows what it read

Found in Cottony, RK155 (2026-10-16). After re-baking
`docs/design/art/ui/booster_tray.png`, the three screen captures that draw it were
re-taken:

    python tools/capture_screens.py tools/capture/board.gd tools/capture/strike.gd tools/capture/card.gd

Each came back OK, and two carried this warning:

    SAME SETTINGS, DIFFERENT PICTURE: screenshot-card.png: the same declared settings produced
    different bytes ... so something this picture depends on is not declared

The picture changed because a sprite it draws changed, which is the reason it was
re-taken. The capture's provenance records the script's hash and the declared settings
(locale, resolution, seed) but not the assets the scene loaded, so a legitimate change
and a real non-determinism (RK164's strike flash) read the same. The warning is right
only half the time, and the half it is wrong is the common one.

What polyweave should do: record in a capture's provenance the hashes of the project
files the run read (Godot can list loaded resources, or the capture can hash what
`res://` paths it opened), and say "a dependency changed: <path>" when one did, keeping
SAME SETTINGS, DIFFERENT PICTURE for the case where nothing it read moved.

### §PW489 A shader that failed to compile fails the run

Found in polyweave on 2026-10-16, building PW473. A uniform named `lift` was redeclared
as a local in the panel shader, and Godot printed

    SHADER ERROR: Redefinition of 'lift'.
    ERROR: Shader compilation failed.

on every film. `panel.capture` still answered with every still, each one the plain white
`ColorRect` the material failed to draw on, and nothing in the answer said the shader
never compiled. Only a pixel assertion in a test noticed.

`engine.ERRORS` (`src/polyweave/engine.py`) reads `SCRIPT ERROR`, `Parse Error`,
`Compile Error` and `String formatting error`, and not `SHADER ERROR`, so
`capture.movie` takes a run whose shader failed as a clean one. Every caller that films
a shader is exposed: `panel.capture`, `vfx.preview`, and any `capture.movie` of a scene
with a `.gdshader` in it.

Add `SHADER ERROR` (and the `Shader compilation failed` line that follows it) to
`ERRORS`, so the run's verdict is `script-error` with the shader's path and line, which
the engine prints as `at: (null) (res://ui/card.gdshader:142)`. `panel.capture` already
refuses a film whose `ok` is false as `compose.unfilmed`, so the refusal then names the
shader's error rather than handing back white stills. A test: a panel whose shader is
broken on purpose is refused, not filmed.

### §PW490 A panel filmed at the sizes it will be drawn

Found in polyweave on 2026-10-16, shipping PW474. The panel shader sews its seam by arc
length at the Control's own size, which is the whole point of the shader route: a button
grown to fit a longer translation keeps its stitch pitch, its pill ends and its
material's grain size. PW474's criterion asked for a filmed panel grown wider to prove
that, and it could not be written: `panel.capture` sizes the `ColorRect` from the
state's declared `size` times `scale`, so every still is the panel at the size a
nine-patch would also draw it at. What the shader does differently is never filmed.

A `sizes` argument on `panel.capture`, a list of `[width, height]` in the panel's
pixels, filming each state once per size as `<name>.<state>.<w>x<h>.capture.png`,
recorded with the size in its params. Left out, the declared size alone, as now. The
screen grows to fit the largest at `scale`, or the call is refused naming the size that
does not fit.

With it, a test films the sewn panel at its size and at twice its width and holds the
stitch count to the declared pitch at both, and a spec can hold a translated button's
look at the width it will really be drawn.

### §PW491 A section sign mis-encoded in a citation

Found in polyweave on 2026-10-16, shipping PW480. Four committed files carry the section
sign read twice through cp1252 and written back as UTF-8: the bytes `C3 82 C2 A7` (`Â§`)
where `C2 A7` (`§`) was meant, each in a docstring citing a line, such as
`src/polyweave/reference_objects.py`'s first line `(Â§PW379)`. The others are
`tests/test_camera.py`, `tests/test_contrast.py` and `tests/test_reference_objects.py`.

Nothing reads them wrong at run time, but a citation that has to be searched for
(`section find "§PW379"`, a grep for `§PW379` when a design is repointed) misses them,
and a reader sees garbage where the reason should be. The cause is a PowerShell
round-trip: `Get-Content` without `-Encoding UTF8` reads a UTF-8 file as cp1252, and
`Set-Content -Encoding utf8` writes the result back, also adding a byte-order mark. This
run did it once to a test file and caught it.

Repair the four (`Â§` to `§`), and add a test over the package and the tests: no source
file holds the bytes `C3 82 C2 A7`, nor starts with a UTF-8 byte-order mark, naming the
file and line. The gate then catches the next round-trip in the commit that makes it.

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

### §PW370 Starship onto the input kits

The prompt, remap and co-op kits (the prompts, remap and players kits, in
docs/specs/kit.md) are extracted from Starship's game/core/bindings.gd, controls.gd and
coop.gd. Starship then adopts them, which is the decision that every project adapts to
polyweave rather than the other way round: its actions and options become the kit's
declaration, its own input code is removed, its Controls tab becomes the kit's screen
under Starship's Theme, and the checks in dev/check.gd that cover the same ground give
way to the kits' acceptance specs.

Whatever Starship needs that the kits lack is filed here as friction and fixed in the
kit, never patched in the game, so the extraction ends with one copy of the code and not
two. Measured on 2026-10-10 against Starship's bindings.gd, prompts.gd and coop.gd: the
prompts in words per player (PW394, docs/specs/kit.md), prompts per player's device
(PW395, docs/specs/kit.md), a join the game answers (PW396, docs/specs/kit.md) and
bindings taken from the game's older file (PW397, docs/specs/kit.md). The game's own
side, Controls.MAP into project.godot and its input code gone, is Spinhold's RK216.

Done when Starship carries no input code the kits provide, its gate passes on the kits'
proof, and provenance.read names each kit with its version.

### §PW371 Cottony onto the settings and save kits

Cottony's scripts/settings.gd, and scripts/save_file.gd with tests/save_test.gd, are a
second instance of what the options and saves kits provide, written without either kit
in mind. Moving Cottony onto them proves the kits against a game they were not extracted
from, which is the non-goal on one project's palette, rig or paths compiled in, checked
in practice rather than asserted.

Players' existing save files must load through the kit's declared migration, so no one
loses progress on the update that swaps the code; that is part of the proof, not a
follow-up.

What Cottony needs that the kits lack is filed as friction and fixed in the kits:
measured on 2026-10-10, the kits read only their own files, so its user://cottony.cfg
needs a door into them (PW398, docs/specs/kit.md: `adopted()` and `ADOPTED`). The game's
own side is Cottony's RK151. Done when Cottony carries neither file, its own save test
is replaced by the kit's acceptance, a save written by the current release loads after
the swap, and its gate passes.
