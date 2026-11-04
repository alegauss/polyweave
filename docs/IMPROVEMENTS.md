# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

### §PW659 The aspect ratio a 4.0 buy asked for

Met in the Shio repository, `marketplace/quilhara/` (Shio SH1254), buying ten
photographs on Ideogram 4.0 through `picture.buy`.

```
python -m polyweave picture.buy --root . --out assets/source/home-coast.png \
  --transparent false --aspect_ratio 16x9 --prompt "..."
python -m polyweave picture.buy --root . --out assets/source/about-map.png \
  --transparent false --aspect_ratio 3x2 --prompt "..."
```

The answers were `credits: 0.06` and no warning. The files are 2496x1664 (3:2) for the
16x9 request and 1792x2240 (4:5) for the 3x2 one; the record says `details.aspect_ratio:
"3x2"` beside `details.resolution: "1792x2240"`, two fields that contradict each other
with nothing saying so. The same 16x9 request sent straight to the 3.0 endpoint earlier
in the session came back 1312x736, so either 4.0 spells the parameter differently (or
takes `resolution` instead), or it treats the ratio as a hint and the prompt overrides
it.

What polyweave should do: send the ratio in whatever form 4.0 honours (schema.read for
the service would settle which), and compare the returned resolution with the ratio
asked. A mismatch is a named finding on the answer (`picture.aspect-differs`, asked and
got), not a silent record, because the caller has already paid and a crop is a decision
about the picture.

Workaround in the project: the bought pictures are centre-cropped to the asked ratio
with Pillow in the same one-off re-encode that PW658 covers.

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

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

### §PW203 A level declaration compiled by the game's own step

Landed 2026-11-03: `level.validate` holds every file `[levels] files` matches to the
project's own JSON Schema, `[levels] schema`, in the part of JSON Schema a level needs,
and checks an `x-entity` string against the world's ids (`docs/specs/engine.md`).

What is left is the compile half. `level.compile` runs the project's declared compile
command, which turns a source a person or an agent edits into the engine's own resource,
and writes a provenance sidecar naming the source, the schema and the command's hash.
The compiled file is still what the game loads, so nothing at runtime depends on
polyweave, and a hand-tuned level stays a source file a person owns.

Neither consumer has that step yet, which is why it waited. Spinhold's game reads its
`*.waves.toml` as it is, so there the source is the resource and compiling is nothing
but the record. Cottony's JSON is written by `tools/make_levels.py` from a curve, not
from a source per level: PW206 is where Cottony's levels become declarations, and the
compile command is shaped by what that step needs (the curve's constants, the level
number) rather than guessed ahead of it. Build it with PW206, or with a second game
whose levels are compiled.

### §PW204 Difficulty bounds and a search over a level's parameters

Once a probe reports measures and a level compiles from a declaration, a level's
difficulty works like any other asset property. A `*.accept.toml` for a level bounds the
probe's measures at a percentile: win rate at the median between 0.45 and 0.70, moves
left at the tenth percentile no lower than one, and, where a game scores a level in
stars, the share of deals reaching its top score. PW201 is why the last one is there:
the owner felt Cottony's level 20 hard because three stars were out of reach, while the
bot still won 65% of deals and never counted stars. `accept.check` reads the probe's
record and passes or fails.

A level set needs one more kind of bound, because a game's difficulty is a curve. A set
spec names its levels in order and states the shape: difficulty never falls by more than
a declared step between neighbours, rises across each region, and dips after a boss.
Each is checked against the measures and reported as the pair that broke it.

`search.sweep` then searches a level's declared parameters (Cottony's target and moves,
a wave's count and interval) for values that pass. Every candidate is compiled and
probed locally at no cost. What the search returns is a proposal. Which candidate ships,
and whether a level that passes also feels right, are decided on the verdict page with
the bot's numbers beside it, because the bot is a proxy a person holds to account.

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

Found in Spinhold on 2026-10-16 (RK198): Resogun's phase 1
(`.polyweave/references/resogun_p1`) has enemies of the violet of the city behind them.

Landed: `motion` against the scene's scroll, `reference.sample`, and through PW641 a
kind's `warp`, which keeps only tracks born at a flash just before them. The lull counts
no track and the phase 282 (`docs/specs/fetching.md`).

Left is the count stretch by stretch against `art/reference/resogun/phase1-sheet.md`.
Measured 2026-11-03 at warp tolerance 0.05, the twelve stretches read 53, 10, 5, 7, 7,
19, 5, 22, 22, 11, 7, 26 against about 9, 8, 5, 3, 21, 38, 15, 22, 10, 20, 15, 12. Two
errors remain.

- Kills over-count: a death burst is white like a warp-in and its debris is born at it.
  Ignoring a flash near a track that just ended cut the opening from 53 to 35 but the
  chain run from 19 to 10, since the noise tracks the gate drops end everywhere. A burst
  has to be told by its own look: size, colour spread, how fast it fades.
- Chains are rings, not pods, and are under-counted. A kind told by its silhouette, the
  island's mask against its sample's foreground, would make a chain a kind of its own.

Done when each stretch's count is within the sheet's own uncertainty, which the owner's
sheet decides.

### §PW608 A level schema's reader and field metadata for the engine

Found in spinhold while planning its stage editor (RK264, RK269, RK281). The keys of a
level file, their bounds, units and what each means live in three places in that game:
the reader's list of accepted keys and its refusals, the editor's table of bounds and
steps, and the doc comments a person reads. Each new key is added three times, and they
already disagree on what a person may type.

§PW203 makes the schema a project's declaration (`[levels] schema`) and checks a level
against it. That covers the checking. What the engine still lacks is the rest of what a
declared schema knows:

- **a typed reader**: `tables.check --write` already writes a typed script from a
  declared table; the same for a nested level document (tables of arrays of tables, inline
  tables, enumerations, cross-references to other entries), refusing a key by name as
  the schema does;
- **field metadata for tools**: per field its type, bounds, step, unit, default, the
  values an enumeration allows and a one-line help, exported as a resource or JSON a
  game's own editor or debug panel builds its inspector from;
- **help in every locale**: the help text routed through the string table, so
  `words.check` holds it like any other line.

A level editor is the game's, not polyweave's (non-goal "A graphical editor"); this
gives that editor its fields from the one declaration. Proven on two genres' schemas, as
§PW205 asks of the level contract.

### §PW609 A draft level from an accepted transcription

Found in spinhold (RK198, RK258, and the library of pieces RK274 plans). A reference
video is read with `reference.frames`, `reference.events` and `reference.objects`, laid
out with `reference.transcription`, and a person answers it row by row. What comes next
is by hand: an agent reads the accepted rows (what arrives, how many, from where, in
what formation, at what second) and retypes them into the game's level file. Two stages
have been carried over this way, each a long session of retyping and a source of slips
the transcription had already settled.

polyweave should take that step: `reference.draft` (or a mode of `level.compile`) turns
an accepted transcription into a draft level in the project's own declared schema
(§PW203). The mapping is the project's, declared once beside the schema: which column of
a row becomes which field, how a row's time becomes the level's clock, how a named
formation or kind maps to the project's names, what a row with no mapping becomes. No
genre is compiled in: a shooter maps rows to spawn groups, a rhythm game to notes, a
platformer to placed objects.

The draft is written with its provenance naming the transcription, its verdicts and the
mapping, marked as a draft so a person still tunes it; rows a person corrected carry
their corrected value, and a row nobody answered is refused, not guessed.

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

### §PW678 Borrowed files keep their origin and derivation

**Where it happened.** viglet dumont (`D:\Git\viglet\dumont\2026.3\wordpress`, project
root with `polyweave.toml`), 2026-11-03: replacing the demo video's music bed. The
track, *Monday Market Open*, was generated by the owner in Google Gemini (Lyria) and
downloaded as an MP3. The chain was: ffmpeg to WAV, `python -m polyweave sound.loop
--track demo/narration/candidate/monday-market-open.wav --out
.../monday-market-open.loop.wav` (63 bars at 120 BPM, seam passed), ffmpeg to MP3, then

    python -m polyweave provenance.borrow --path <scratchpad>\monday-market-open.loop.mp3
        --out demo/narration/music.mp3
        --licence "Google Gemini generative AI terms; commercial use not confirmed"
        --credit "Music: Monday Market Open, generated with Google Gemini (Lyria)"

**What came back.** A `music.mp3.prov.json` whose only origin is the borrowed file's
path, a session scratchpad folder that is gone tomorrow (`inputs[0].role: borrowed`).
There is no field for the service that made the original (Gemini), the original file, or
the step that derived the loop from it. `sound.loop` itself wrote no `.prov.json` beside
its loop (only `music.track` wrote one), so even polyweave's own step left nothing to
chain to.

**Workaround.** The facts went into the project's prose credits by hand
(`demo/seed/CREDITS.md`), where nothing checks them against the file.

**What polyweave should do.**
- `sound.loop` (and every operation that writes an artefact from an input) writes a record
  naming its input by hash and its parameters, like the generators do.
- `provenance.borrow` takes the origin of a file made outside any project: `--source`
  (the service or person), `--original` (a path or URL, hashed when it is a file), and keeps
  the chain when the borrowed file has its own record (the loop's), so the shipped file says
  "Gemini track -> sound.loop 63 bars -> mp3".
- `provenance.credits` then prints the credit from that record.

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

### §PW677 The preset sheet that is written and never named

Found on 2026-11-03 while building `render.in_game` (PW495), which uses the same call.

`engine.preset_search` writes a sheet of every preset that loses quality and answers it
as `sheet`, so a person judges them (`src/polyweave/layers/engine/presets.py`). It reads
the sheet's path as `verdict.sheet(...).get("out")`, and `verdict.sheet` answers
`{"sheet": ..., "members": ..., "choices": ...}`, with no `out`. The sheet is written,
but the answer's `sheet` is always null, so an agent following the answer never hands it
to the person and the says line still tells them to judge it.

What to build: read `["sheet"]`, as a path relative to the project the way the rest of
the answer spells its pictures, and add a test where one preset loses quality and the
answer's `sheet` is a file on disk. A test of this exists only behind `$GODOT`, which is
why the gate never saw it: the shape of `verdict.sheet`'s answer can be checked without
an engine by stubbing the capture.

## Block W — A core that grows by layers

## Block X — The site on the shared design system
