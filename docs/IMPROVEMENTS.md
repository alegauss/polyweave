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

### §PW53 The rig is the thing being replaced, so it cannot be the thing still running

§PW36 moves one asset and stops there, which is the right size for a first port and the
wrong size for a claim. `tools/art/bake_model.py` is 1023 lines, and its `MODELS` table
holds twelve entries carrying up to fourteen rig parameters each — `fill`, `light`,
`turn`, `ambient`, `key`, `form`, `roughness`, `shadow`, `gloss`, `square`, `scrub`,
`roll`, `plate`, `dust` — every one of them found by hand at about two minutes a sample.
That table is the cost this plugin was written to remove.

One asset ported proves a picture can be made. Eleven left behind prove nobody chose the
plugin over the rig, and the rig is what still runs on a build.

The work is a translation rather than a move, which is why it is one line per asset.
§PW36's audit already found the sharp edge: `light` is a whole-rig multiplier and `form`
is the key's share of it, and neither is a parameter the renderer has. An axis with no
knob is refused before a render is spent, but the conversion stays a person's:
`exposure` is in stops, and a wrong one is a different picture rather than an error.

So each model's constants become an acceptance spec, the spec is what `search` aims at,
and the ledger `docs/specs/adoption.md` defines takes the before side for that asset
before it moves. A comparison with one side recorded is refused, and rightly.

Set aside: it needs a person three times over. The trap a hand conversion walks into is
in `docs/specs/adoption.md`.

### §PW56 Twelve runners, twelve ways to start Godot, and no check on what applied

`tools/capture_screens.py` drives four scripts under `tools/capture/`;
`tools/measure_frames.py` drives one. The other seven under `tools/perf/` have none —
started by hand, from a command line written in a docstring. Both drivers open a real
window, because `--headless` draws nothing; both distrust Godot's exit code; both bound
the run by a wall clock; and both fail a run whose line never came. That procedure is
written twice, and a third time in `run_tests.py`.

Block E is that, generalised and then taken further. `offscreen.py` probes which
offscreen route actually works on this machine instead of assuming one; `engine.py` and
`capture.py` run a script and compare the settings that were asked for against the ones
that applied; `units.py` checks a declared `pixels_per_unit` against the engine's own
number, which here is `const CELL := 112` in `scripts/board.gd`.

That comparison is the part Cottony has no equivalent of at all. `docs/specs/engine.md`
is about the settings a picture was taken under, and today a capture that ran at the
wrong resolution, the wrong locale or the wrong renderer prints its line, writes its
file and passes. The site publishes it.

**Replacing Blender, Godot or the generative service** is a non-goal, and this line
stays inside it: Godot still runs the scene. What changes is who starts it, and what is
checked once it has.

Godot 4.7.1 is installed and the probe answers the machine: `window-offscreen` and
`window-minimised` work, `virtual-display` cannot on Windows, and `headless` drew
nothing. The route exists, so what is left is Cottony's tree.

### §PW57 Five floors in five files, and not one of them is a target

`check_vivid.py`, `check_palette.py`, `check_markings.py`, `check_plush.py` and
`check_pieces.py` are about a thousand lines of measurement, each holding its own floor.
The best of them makes the argument this plugin adopted: `check_vivid.py` exists because
"washed out" was asserted, measured, and found true only at the tail — mean saturation
0.31 against the concept art's 0.32, and the 99th percentile 0.68 against 0.88. A look
is a distribution, and the interesting part is usually not its middle.

`measure.py` closed that vocabulary and `accept.py` turns a bar into a file. The
difference is not tidiness and it is not line count. **A threshold inside a gate can
only answer after the render is spent.** The same number in an acceptance spec is what
`search` moves towards, so the bar stops being a verdict and becomes the target, which
is the whole loop this plugin is.

A second cost is being paid quietly. Five floors in five files are five numbers that
move independently, and `check_vivid.py` already records what that costs: for as long as
only one of the two boards was read, the mesh board sat at 0.776 with nothing saying so.

The end state is one spec per asset, the gates reduced to running them, and the
percentile argument surviving as a measurement name rather than as a paragraph in a
script.

### §PW59 Adopted is an opinion until something fails when it is not

Today the number is zero. A search for `polyweave` across `D:\Git\viglet\cottony`
returns nothing, against 8,839 lines under `tools/`. Every line in this block moves that
number and none of them defends it.

That matters because the failure mode is not a port that never happens; it is a port
that comes back. A helper reintroduced under deadline, a floor copied into a sixth check
script, a thirteenth GDScript runner written because twelve were there to copy from —
each is one commit, each looks reasonable in review, and nothing fails.

So this block closes with a gate in Cottony rather than a claim in this repository. It
names the surfaces the plugin owns — the rig, the geometry, the fetch, the engine run,
the measurement, the sheet — and fails when one of them is re-implemented beside a call
that already exists.

**The denominator has to be stated or the number is a slogan.**
`tools/art/make_assets.py` is 2,406 lines of drawn 2D generation and is not in it: this
plugin is geometry, surface and motion in three dimensions, and a flat PNG generator is
Cottony's own work. The palette and the fonts are the same. What counts is what the rest
of this block names, and the gate may report a fraction below one for as long as it says
what is left and why. Two of those are already answered in `docs/specs/adoption.md`: the
fetch ledger replays, and the motion Cottony has is two frames and no clip.

### §PW77 A bar that was measured and then left in a comment

The map's props are the family with the best-recorded target in the project and no way
to act on it. `scenery_mushroom` carries this, verbatim: tuned against the drawn sprite
on its cap and stem medians, 223,118,87 and 215,197,173 against 225,127,83 and
214,198,174. Somebody measured the thing the render had to match, wrote it down, and the
only reader is a person.

That makes them the right second family. The work is not finding a bar — it is moving
one that already exists into something a search can aim at, which is a smaller step than
inventing the bar and the port at once.

Four of the five are built from the outlines make_assets.py draws them with, so they
carry the stars' property of costing nothing to re-render. The fifth, the mushroom, is
fetched, and it is here rather than with the boosters because it shares the other four's
settings exactly: one exposure, one gloss, one shadow, differing only in how much of the
canvas each drawing spans. A port that holds across a built prop and a fetched one at
the same numbers is worth more than one that only holds across four siblings.

What it must not lose is the reason the numbers exist: each prop lands on a sheet beside
drawn siblings, and reading as the odd one out is the failure.

### §PW78 Framing that answers to a number the game already holds

The board tray and the booster tray are the two assets whose framing is not a matter of
taste. `board.gd` addresses a cell at `CELL := 112`, so the render has to put its wells
on that grid or the game draws pieces a few pixels off their homes. The bake answers
with `plate`: a world rectangle given outright, which replaces the fitting that `fill`
and `size` do and sets one unit to one pixel.

That is a different kind of hand-tuning from the stars' exposure, and it is why these
two come after the families where the only loose thing was light. An exposure that is
slightly wrong makes a picture somebody may accept. A plate that is slightly wrong makes
a board that does not line up, and the failure is structural rather than a matter of
looking right.

Both are built rather than fetched — the booster tray is a cushion inflated from the
lobed card drawn beside it, the board tray a grid that could not come from a service. So
the geometry is already a declaration and what has to move is the framing contract.

The thing to keep is that the number comes from the game, not from the render. A port
that lets the picture choose its own rectangle has lost the point.

### §PW79 The simplest rig with the hardest bar

The brand marks are the one family where the rig is nearly nothing and the criterion is
nearly everything. Two blends produce three sprites — the Cottony logo is baked twice,
large for the title and small for the board's corner, because a sprite for each beats
one scaled for both — and the whole of the hand-tuning is `light`, at 1.0 and 1.18.

They are deliberately not first. A family with one constant looks like the easy port,
and it is, right up to the point of saying what a correct render is. A wordmark is type:
it either reads or it does not, and the failure is not a median drifting but a letter
losing its edge. Every other family in this list can be stated as a colour and a
contrast against something drawn; this one cannot, and taking it early would mean
inventing an acceptance vocabulary under the pressure of the first port.

By the time the stars, the props and the trays have moved, three bars exist that were
written to be read rather than admired, and the question here is narrower: what does a
search aim at when the subject is a shape that must stay legible.

The marks also leave markings off — a rope round the silhouette of a word is not a thing
this style has.

### §PW80 What a fetched object arrives wearing

The boosters are the first family whose hand-tuning is not about light at all. The
hammer and the wand came back from the service, and each needed three separate
corrections that no exposure search would have found.

The service painted edges it saw: a dashed dark line round the hammer's head, a dark rim
on the wand's star, both of which rule 2 forbids on candy and neither of which a prompt
saying so prevented. `scrub` takes them back out of the texture before rendering. The
hammer also returned standing upright where the drawing leans it, so it carries a roll
of -22 degrees, and leaning it widens its box, so its fill had to go up to 0.72 to keep
the drawing's size. Each of those three is a consequence of the one before it.

The shuffle ball is here because it is the counter-example: it is built rather than
fetched, after the service returned a ring instead of a ball. Having both in one task is
the point — what a fetched object needs and what a built one does not is the comparison
this family exists to make.

The risk being carried is that a correction found for one object is a correction fitted
to one object. A port worth having states what the correction is for, not the number it
landed on.

### §PW81 The five that are looked at, and go last

The friends and the mascot carry more hand-found numbers than the other seventeen
sprites together, and they are also the ones a player looks at. Both facts point the
same way: last.

Nothing here is only an exposure. The mesh is dressed in cloth drawn in Python and
projected from the camera, because the service's own texture did not read as cotton. The
face is composited on afterwards, because a sculpted face comes back as dents that shade
and never read as eyes. The mascot needs its sculpted face taken back out first at 0.9,
where 1.0 flattens the cheek's own light; it arrives in 34,391 pieces, so a dust
threshold of 0.01 keeps the head and the lower body while dropping the tongue inside its
open mouth. Its face centre was solved rather than chosen: measured at 0.444 of the
height, then moved up by 0.09 so the mesh's cavity becomes the inside of the mouth we
draw.

The lean frames are the same mesh squashed to 0.93 and re-rendered rather than scaled,
so the light stays where the light is while the body moves under it.

Every earlier family in this list is a rehearsal for this one. If the search cannot hold
here, the honest outcome is that these five stay hand-tuned and the rig shrinks around
them rather than disappearing.

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

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

### §PW180 Canon pictures as style references

PW166 declared a style as a palette and a skeleton, and a canon a person grows. Its
design also named `references`: which canon pictures go to the service as style
references, and one character reference per recurring character. That part did not land,
because no model this client sends to takes a reference picture together with a
structured prompt.

3.0 takes `style_reference_images` and `character_reference_images`, as uploaded files,
but only with a text prompt, and a text prompt has nowhere to carry the skeleton or the
palette. The 4.0 generate reference, read when PW166 shipped, lists no reference field.

**Build it where a model takes both.** Add `references` to `[style.<family>]`, naming
canon pictures by file name. Send them as repeated file fields: `_send` currently maps
one field to one file, so it needs a list. Record each reference's digest on the
picture's record, so a regeneration sends the same pictures. Until a model takes both, a
family with references should refuse a structured call rather than drop them.

Check first whether 4.0 has gained a reference field, and learn it by the schema probe,
since a reference the service ignores is dropped without an error.

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

### §PW184 Whether agent-composed music is good enough to ship

The block rests on one premise: that an agent writing music as data, rendered headlessly
through existing open-source engines, sounds good enough for a casual game. Nothing has
tested it, and every later line spends effort on it.

The spike runs outside the package, in a throwaway directory. The agent composes three
loops of one to two minutes (chiptune, synthwave and a small orchestral cue) as
multi-track scores with drums, each written in two candidate notations for the patterns,
such as ABC and Strudel's mini-notation, so the one the agent gets wrong least and a
person finds easiest to change is chosen. A script renders each through Surge XT and
sfizz or FluidSynth, driven from DawDreamer or Pedalboard, with one fixed mix and master
chain. Ten retro sound effects come from a seeded sfxr-style synthesiser. Each file is
measured with `sound.measure` for seam, loudness and peak.

The verdict is a person's: they listen beside a track from a paid generator such as Suno
and say whether the result is good enough for Cottony. An agent does not judge its own
sound, for the reason the non-goal on looks gives.

If the answer is yes, the findings (which engine, which instrument libraries, which
licences) are written into the designs below and the block proceeds. If it is no, every
open line in this block is retired with the spike's outcome as the reason, and paid
generation becomes the path instead.

### §PW185 Declaring what a game needs to hear

A game's audio is a list the consumer owns: music per level or state, and a sound per
event. Today that list lives in Cottony's scripts, so polyweave cannot say which files
are missing or out of bounds.

A `[sound.<family>]` table, shaped like `[style.<family>]`, names each cue with its kind
(music loop, stinger, effect), its target duration and loudness, and where the file
lands under a new `paths.audio` default. Acceptance bounds stay in `*.accept.toml`,
which already reads `sound.*` measures; the declaration only says what exists and where.
Nothing about Cottony is compiled in, per the non-goal on one project's paths.

### §PW186 Music as an editable source an agent writes and polyweave checks

An agent composes well only when its output is structured and a validator answers it,
which is the loop piano's score format proved. But a piece is also something a person
reopens and changes, so the file that is edited and the model that is checked are two
layers.

The source is a `*.music.toml` in the consumer's repository, beside its `*.accept.toml`,
laid out like a tracker: tracks naming an instrument and a layer, short named patterns
written in a compact text notation with one line per bar or phrase, and an arrangement
that chains patterns into sections, with tempo, meter, key and the loop span. Changing a
riff is one line, the arrangement follows, and a diff reads as music. An agent asked to
darken the bridge edits one pattern rather than rewriting the piece.

The note model, absolute ticks per note in the shape of piano's JSON, is derived from
that source and never edited. `music.validate` compiles the source into it and reports
errors against the source's own line, with remedies in the house style; `music.to_midi`
writes a standard MIDI file from it, so any DAW can open the result. Piano's JSON can be
read as input, but polyweave does not depend on piano's runtime. Which notation fills
the patterns is what the spike settles.

### §PW187 Rendering a score without a DAW open

`music.render` turns a validated score into WAV and OGG headlessly, orchestrating
engines that already exist rather than writing a synthesiser, as the non-goal on
replacing tools requires. Which engines (Surge XT, sfizz, FluidSynth, through DawDreamer
or Pedalboard) is what the spike settles.

What decides how professional the result sounds is the instruments and the mix more than
the notes, so the render applies one fixed, declared chain: per-track levels, bus
compression, and a limiter to the declared loudness. A loop's reverb tail is wrapped
into its start, so the seam `sound.measure` checks is clean. Instrument libraries are
configuration and are never bundled.

### §PW188 One theme at several intensities

Game music changes with play: calm, tense, combat. A score can declare layers that share
one length and grid, and `music.render` writes one stem per layer, so the game fades
layers in and out and they never drift.

Each stem is measured like any other file, and the acceptance spec can bound their
summed loudness. The Godot side stays the consumer's; polyweave only guarantees that the
stems line up.

### §PW189 Retro effects from a seed

Cottony synthesises its effects with its own `tools/audio/make_sfx.py`, which a second
project would have to copy. `sound.synth` ports it the way `sound.measure` ported the
seam measures from `loop_music.py`: an sfxr-style generator (oscillator, envelope, pitch
slide, noise, filter) driven by a TOML table of parameters and a seed, so a person tunes
an effect by editing a number, writing mono 16-bit WAV.

The same seed gives the same bytes, so a verdict on an effect holds across runs.

### §PW190 Realistic effects bought under a budget

Footsteps, glass or rain are not what a synthesiser does well. `sound.buy` fetches from
a paid effects service such as ElevenLabs, following the pattern `mesh.buy` and
`picture.buy` set: config names the service and its prices, `purchase.allow` checks the
ceiling, and `purchase.capture` writes, hashes and ledgers the file.

No budget means no spend, and the decision to spend stays with a person.

### §PW191 Where a rendered sound's instruments came from

A render uses sample libraries and presets whose licences differ: CC0, CC-BY needing
credit, or terms that forbid redistribution. `music.render` and `sound.synth` write a
provenance sidecar naming the score, the engine and each instrument with its licence,
through `provenance` rather than the purchase ledger, since nothing was bought.

A render that uses a library whose licence is undeclared is refused, and `provenance`
can list the credits a game owes.

### §PW192 Cottony's audio made through polyweave

The block is proven when its first consumer uses it. Cottony's music and effects are
declared in its `polyweave.toml`, made by `music.render` and `sound.synth`, and held to
`*.accept.toml` bounds, and its own audio scripts are removed. Anything Cottony needs
that a second game would not becomes configuration.

## Block Q — Words held to the world

### §PW200 Starship held to its own world

Starship is the consumer with a world to hold to. Its bible names the Spinhold, the
Holders, the Lattice and its three Foremen, and the crew, and none of those names reach
the screen yet. The draft is still open under RK88 with four questions unanswered, which
is why this line waits on it: formalising a world whose answers may still change costs a
second pass over every entity.

Adoption is done when four things are true:
- `world.md` stays the prose, and a `starship.world.toml` beside it declares every name in its glossary, with the three factions tied to `[style.brand]`, `[style.holders]` and `[style.lattice]`.
- RK73's rename moves every player-facing string into the translation table, `words.unlisted` counts zero, and `words.check` passes.
- The crew lines RK89 adds pass through `words.sheet`, and the ones a person approves form the lines canon.
- The next Lattice enemy or Foreman picture is bought with `entity=`, and its sidecar names the entity.

The measure is the census Block H uses: which of Starship's text and character assets
are declared, checked and judged through polyweave, and which still sit in scripts. A
string left in GDScript is a line this adoption has not reached, and the count says so.

## Block R — Levels measured before a person plays them

### §PW201 Whether a bot's win rate says how hard a level feels

The block rests on one premise: that a cheap simulated player, run headlessly over many
seeds, ranks a game's levels by difficulty the way a person playing them would. If it
does, a level's difficulty becomes a number a search can aim at. If it does not, every
later line tunes against noise.

The spike runs in Cottony, where it is cheapest. The match rules already run headlessly,
and `match3_test.gd` has a `find_move` that agrees with a brute-force rescan. A
throwaway GDScript bot plays each of the 20 shipped levels over 200 seeds, first
greedily and then with a one-move lookahead. It reports each level's win rate and the
moves left at a win, at the median and the tenth percentile. It spends nothing, and it
lives outside the package.

The verdict is a person's. They play a sample of eight levels, spread across the bot's
ranking, and say whether the order matches what they felt and where it does not. An
agent does not judge the proxy it built, for the reason the non-goal on looks gives.

If yes, the findings go into the designs below: which bot, how many seeds, and which
percentile carries the feel. If no, the open lines are retired with the spike as the
reason, and levels stay hand-tuned.

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
the first twenty make.

## Block S — Playing the game, not only rendering it

### §PW211 Whether GodotTestDriver can carry an agent through a game

polyweave runs the engine one shot at a time: a script, a frame budget, a line in the
log. Nothing holds a game open while an agent decides what to press next, so a flow
through menus, a level and a win is tested by no one.

GodotTestDriver is the first candidate because it already has the parts a driver needs.
Drivers target nodes through a producer lambda, input goes through
`Input.ParseInputEvent`, and waits can count frames. The spike measures its three costs.
It is C# and needs the Godot .NET build, while Cottony and Starship are GDScript on the
standard 4.7 build. It runs only inside the game, with no socket. Its waits in seconds
use the wall clock, not game time.

The spike runs in Cottony, outside the package, and spends nothing. It adds the .NET
build and GodotTestDriver, and a C# harness goes from the title screen to a won first
level. It reads GDScript properties with `Get` and calls GDScript methods with `Call`.
It advances by frame counts only, with the tree paused between steps. The sequence runs
ten times and the final states are compared.

The findings are what adding .NET took and whether it changed the export, whether
driving GDScript nodes works, and whether ten runs out of ten agree. If not, the
fallback is gdUnit4's SceneRunner, which is GDScript, tried against the same flow. The
later lines take whichever passes.

### §PW212 A driver inside the game, stepped by the agent

An agent's turn takes seconds and the game runs at sixty frames a second. A game left
running between two calls has moved on by the time the second arrives, and no sequence
of calls can be replayed. So the driver holds the tree paused and advances only when
told to, by a count of frames at the fixed rate the engine runner already sets. The seed
of every random source is set at start. The same calls then give the same game.

The driver is an addon and autoload that the project installs. It is loaded only under a
`polyweave_driver` feature tag, listens on loopback with a token printed at start, and
dispatches to whatever PW211 chose, so its commands stay the same if the library
changes. The commands are `query`, which returns a node's properties by path, group or
class, and `input`, which sends an action, a key, or a click on a node's centre. The
others are `step`, which advances by a number of frames, `wait`, which waits for a
signal, a node or a value within a frame budget, `call`, which runs a method the game
exposes for setup, and `shot`.

Waits count frames and never seconds, which removes the wall-clock waits PW211 found.
The contract goes in `docs/specs/driving.md` before code, as the capture environment's
did, because the addon, the tools and the recorded test all read it.

### §PW213 Game session tools an agent calls

`game.open` launches the project through the existing engine runner with the driver's
feature tag and a display where a `shot` is wanted, since `--headless` renders nothing.
It waits for the token line and returns a session id. `game.query`, `game.input`,
`game.step`, `game.wait`, `game.call` and `game.shot` each forward one command of the
PW212 contract, and `game.close` ends the process and says why it ended.

Each answer carries the frame the game is on and any error the engine printed since the
last call, read with the same error pattern the runner uses. A script error in the
middle of a flow is then reported by the step that caused it, not found later in a log.
A session the agent forgot is closed after `[driving] idle` seconds, so no Godot process
outlives the conversation.

A `game.query` answer is structured and costs few tokens, and a `game.shot` answer is an
image and costs many. So a shot returns a path and the image's dimensions, and the agent
chooses to read it, as `capture_run` already does. A shot answers questions about where
things are and what is on the screen. Whether the screen looks right is still a person's
verdict and goes to the verdict page, under the non-goal on an agent judging its own
look.

### §PW214 A driven flow kept as a test that replays without an agent

Playwright's recorder turns a session somebody clicked through into a script that runs
without them. This is the same step for a game, and it is what turns exploring into
testing.

`game.keep` writes the session's commands so far to a flow file under the project's
tests. Each input and step becomes a line, and each `query` or `wait` the agent chose to
keep becomes an expectation: a node, a property and the value it held. The agent names
what the flow proves and removes the steps it took by mistake. Nothing is kept
automatically, because a session includes wrong turns.

`game.replay` runs a flow in one launch through the engine runner. The driver reads the
file inside the game instead of over a socket, so a flow runs as fast as the engine and
a continuous-integration job needs no agent. The verdict follows the runner's rules:
every expectation held, no error was printed, and the frame budget was not hit. A
failure names the first expectation that broke, the frame it broke on, and a shot of
that frame.

The flow format is declared in `docs/specs/driving.md` beside the commands, so a flow is
a declaration like a geometry or a capture, and it is recorded with its engine version
and driver hash. A later run on a different engine reports that difference.

### §PW215 A release export checked for the driver

The driver is loaded only under a feature tag, and the addon is excluded from export
presets. Either can fail without anything noticing: a preset added later without the
exclusion, an autoload that loads without checking the tag, or a `call` target left in
game code with no guard. The loopback binding and the token limit who can reach the
driver while it runs. They do nothing about a driver that ships.

`game.release_check` takes an exported pack, or runs the project's release preset in the
scratch folder, and lists the files in the pack. It fails if any driver file is present
or if the project's autoloads name the driver without the feature check. If PW211 chose
GodotTestDriver, it also fails when the GodotTestDriver or GoDotTest assemblies are
present, because a library meant for tests only has no place in a player's build.

The check is a gate, not advice: `require` closes with one code per finding, in the same
way the engine runner's gate does, so a project can put it in its own release script. It
reads a pack and spends nothing, and it never edits a preset. The finding names the
preset and the line to change, and the person who owns the release makes that change.

### §PW216 Starship driven frame by frame

A match-3 board changes only when the player moves, so a driver that pauses between
calls can hardly fail on it. A shooter is the harder case. Enemies spawn on a timer,
bullets move under physics, and a frame counted twice or a timer driven by the wall
clock is enough to make two runs of one flow differ.

The proof is a Starship flow kept by `game.keep`. It starts the first phase, holds fire
and a direction for a set number of frames, and expects the score, the player's health
and the number of live enemies at three frames along the way. Replayed ten times, it has
to give the same values ten times.

When it does not, the finding names the frame where the runs diverged and the node whose
value differed. The fix belongs in the game or in the driver's contract, and the finding
says which. A timer on `Time.get_ticks_msec` is the game's to change. A `SceneTreeTimer`
that keeps running while the tree is paused is the driver's to handle. What the flow
checks is the game's own rules, not whether the phase is fun or fair, since those remain
a person's verdict and Block R's measure.

### §PW217 Cottony's flows kept and replayed

Cottony's tests check the match rules headlessly and its screens by capture. Neither
presses a button. A menu whose signal was disconnected by a scene edit, a level-select
button that opens the wrong level, and a win screen that never appears would all pass
every current check.

The proof is that an agent, given only the session tools and no reading of Cottony's
scenes, drives three flows and keeps them. The first goes from the title to a won first
level. The second opens a later level from level select and loses it. The third goes
through settings and back with a changed value that persists. The flows sit in Cottony's
tests, `game.replay` runs them in its release script, and `game.release_check` passes on
its export.

The count is part of the evidence. It is how many calls each flow took to find and how
many tokens a session spent, recorded in the ledger entry, so the cost of exploring is a
measured number that later work can reduce. A flow that needed the agent to read the
source counts as a failure of the tools, under the block on reaching things without
reading the source, and it is filed as its own line.

## Block T — Adopting polyweave in a project
