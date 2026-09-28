# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

### §PW267 The resolution a capture holds, measured on the picture

Found in Starship (2026-09-27, RK85). The key art was captured with `environment =
{"resolution": "3840x2160"}` on a 3840x2160 display. The window cannot be taller than
the desktop's work area, so the OS shrank it, and the picture on disk is 3840x2119. The
stage script printed `environment: ... resolution=3840x2160`, the size it had asked the
window for, and `capture.run` compared that line with what it asked. It answered `holds:
true` and recorded a picture of the wrong size.

The resolution a capture holds should be measured on the artefact itself: its pixel size
against the one asked. The script's own line is a claim. Where they differ, the answer
should say so (`the picture is 3840x2119, asked 3840x2160`) with the likely cause (a
window larger than the desktop's work area) and the routes that could render it (an
offscreen viewport of that size). This is PW245's other half: there the script applied a
size and the window override won, here the OS did.

Done when that capture answers `holds: false` naming the measured size.

### §PW273 A movie at the size asked

Found building `vfx.preview` (PW259, 2026-09-27). `capture.movie` passes `--resolution`
before `--`, as `_sized` does for a still (PW245), and a script that sets `root.size`
reports the size asked. But Godot's Movie Maker records at the project's window size
whatever either says: Godot 4.7.1 printed `recording movie in 1152×648` for a run asked
at 320x240, the frames came out 1152x648, and `_measured` read that off the first frame,
so the run was refused as `environment-resolution` although the script's `environment:`
line said 320x240. The movie test passes only because its project's viewport is already
the size it asks.

A movie should come out at the size asked. Movie Maker takes its size from
`display/window/size/viewport_width` and `viewport_height`, which can be overridden on
the command line only through a project override file; so either the run writes an
`override.cfg` of its own beside a copy of the settings (never the game's own files), or
the frames are refused before the run with a remedy naming the project setting, rather
than after it with a verdict that looks like the script's fault. `vfx.preview` asks no
size for now and scales its stills.

Done when `capture.movie` asked at 320x240 of a project whose window is 1152x648 keeps
320x240 frames, or says before running why it cannot.

## Block F — Motion

### §PW272 Contrast of a target against its surround

Found in Starship (2026-09-27, RK142). The owner could not tell the ship's shots from
the hostile ones against a lit city. The fix had to be proven by how well each shot
stands out from what lies right behind it, and polyweave cannot measure that.
`measure.take` gives statistics of one region, so the project called it twice per shot,
once for the shot and once for a box beside it. It worked out a luminance ratio by hand
in a script, over positions the game printed.

A `measure.contrast` should take a picture and a list of targets, each a point or a box.
It should give each target's contrast against the ring around it: the WCAG-style
luminance ratio, and the colour distance in ΔE. It should report the minimum and the
median, so a spec can bound the worst shot (`contrast_min >= 3`). It should also take
the target list from a driver's printed line, so the capture that placed the shots can
name them.

Done when Starship's shots spec holds `contrast_min` on its recorded combat frame
without a project script.

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

### §PW258 A change's frame cost, before and after

Found in Starship's RK131 (2026-09-27), adding a sky shader, haze and searchlights
behind the city. The design says the change must hold the frame rate, so its cost had to
be known. The project's `dev/perf.gd` times one heavy wave per preset, and the table it
had recorded (`Graphics.MEASURED`, 2.03 ms at High) was a day stale: other work had
since raised the same wave to 4.23 ms. So the only honest number was a comparison, and
it was made by hand: `git stash --include-untracked`, re-import, run perf, `git stash
pop`, re-import, run perf again, then four more runs for the table.

polyweave should answer "what does this change cost a frame": run a project's timing
script on the working tree and on a named revision (in a worktree, never stashing the
user's files), on the same machine and settings, several times each, and report both,
the difference with its spread, and the machine and driver it was taken on. It should
record the result beside the script's own record, so a stale table like MEASURED is
named as stale. PW56 is about how those scripts are started; this is what they are for.

Done when RK131's 0.7 ms is one call against HEAD, and the answer says how sure it is.

## Block I — Voxel models from a declaration

### §PW274 Every op takes a point on its face the same way

Found writing PW262's test (2026-09-28). On a grid of 1.0 with cell centres at x.5, a
cube one cell wide on x with its faces at -0.5 and 0.5 takes both columns, since a
primitive's inside test takes a point on its face. A plate with the same box, `rect`
from -0.5 wide 1, takes only the column at -0.5: its ring is tested with a polygon test
that takes the left edge and not the right. So one box declared as two ops fills
different cells, and whether a region straddles depends on which op drew it.

Either the ops should agree on a point lying on a face, in or out, or a voxel build
should never sample a centre that falls on one. The first is the smaller change: one
rule, stated in the geometry spec, applied by the primitive, prism, plate and cells
tests alike, likely a half-open interval on every axis so a face shared by two touching
shapes gives its cell to exactly one of them. PW262's finding then reads the same for
every op.

Done when a cube and a plate over the same box, with faces on cell centres, fill the
same cells, and a test holds each op to the rule.

## Block J — A bar a person sets once

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

### §PW269 compose.place records what it composed

Found in Starship (2026-09-27, RK74). Eight store capsules were composed with
`compose.place`, the wordmark placed on a crop of the key art. Every file it wrote
landed with no `.prov.json` beside it. So `provenance_unrecorded` lists them. Nothing
says which key art and which logo they came from, so a changed key art cannot find the
capsules it left stale (`provenance_dependents`).

`compose.place` should write a record like any other producing operation. Its inputs
would be the asset and the scene it was placed into, with their hashes. Its params would
be `at`, `width` and `anchor`.

Done when the Starship capsules, composed again, each carry a record naming
art/brand/key-art.png and the wordmark.

## Block M — What a game needs beyond the look

### §PW259 Visual effects as declarations

Found in Starship's RK136 (2026-09-27): cosmetic trails, the ribbon of light and the
particles a ship leaves behind it, one look per crew family (sparks, a heat shimmer,
rings, a sunlit band, little lights) and one for the Holders. Starship's rule is that
every visible part is declared and built through polyweave and a person accepts its
look. polyweave declares geometry, voxels, pictures, sounds and music, but a visual
effect has no declaration: its `effects` are sfxr sounds. So the trails are written as
game data (a Resource per trail: colours, width, life, particle counts and shapes) and
tuned by looking at captures, which is the tuning by eye the project's rules forbid.

polyweave should take a declaration of a particle or ribbon effect (emission, life,
colour over life as a gradient, size over life, shape, blend, a budget of particles) and
build it into what the engine plays, which `vfx.build` now does
([vfx.md](specs/vfx.md)), render it over a few frames on a neutral background as a look
a person can judge, and hold it to an acceptance spec (how long it lives, how far it
reaches, its brightness, its particle count against a budget).

Done when Starship's seven trails are seven declarations built and accepted through
polyweave, and the game reads what was built instead of its own data.

### §PW268 A store's capsules from one key art

Found in Starship (2026-09-27, RK74). A Steam page asks for one key art in about ten
shapes:

- header, small, main and vertical capsules;
- library capsule, header, hero and logo;
- page background, community icon.

Each has its own size and aspect, and most carry the game's logo. polyweave has
`compose.place`, which puts a picture into another, and `picture.fit`, which fits a
sprite to a family's grid. Neither crops a key art to a size around its subject, and
nothing knows a store's list of sizes or checks that a logo still reads at the small
capsule's 462 by 174. So the project wrote a crop script of its own in the work area.

A `store.capsules` operation should take a key art, a logo with alpha, and a store
(`steam`, with its sizes declared as data, not code). It should write each capsule:

- cover-cropped around a focus point the caller gives;
- the logo placed by a rule per shape, and left off where the store forbids text (the
  library hero);
- each with its provenance.

It should refuse a key art smaller than the largest size rather than upscale it quietly.
It should also measure the logo's legibility at each size (its smallest stroke in
pixels) and fail a capsule where the name would not read.

Done when Starship's capsule set is written by one call from art/brand/key-art.png and
the wordmark.

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

### §PW266 Canon candidates on the page, gated or not

Found in Starship (2026-09-27, RK93). The project's canons were to be grown on the
review page. The page offered only the six Mote drawings, because a picture reaches a
canon there only through a gate run's lane (`review.answer` with `gate` and `canon`).
The studies the project adopted for its brand and holders families (RK91) were never
gated: they are key art and a wordmark, with no outline to hold a silhouette to. So two
of the three families could not be started from the page at all. The owner's picks were
carried with `verdict.judge` members carrying `canon`, a shape learned from
`style.admit`'s source.

The page should list, for each declared `[style.<family>]`, the pictures a project
points at as candidates, such as a `candidates` glob under the family. Each should have
the same admit-with-a-sentence control the gate lanes have. The board should say that a
family with fewer than two pictures judges nothing yet.

Done when Starship's brand family can be started from the page with its two studies.

## Block O — A person sees and answers

### §PW265 Promoting a refused picture from any surface

Found in Starship (2026-09-27, RK97). The owner promoted a refused Mote drawing in
conversation ("use the original mote-3"). `mesh.buy` accepts a promotion only as a
verdict recorded against a gate run's lane, and the one write that records it is
`review.answer`, which only the review page's HTTP handler calls. No operation on the
CLI or the MCP surface takes a gate id, a picture and a person's words. The agent had to
call the Python function directly and learn the body's keys from the source.

A `verdict.promote --gate <id> --picture <path> --why <words>` (or `verdict.judge`
taking a gate lane) should make the same write. Its refusals should list the gate runs
and pictures it knows, as `_overruled` already does internally.

Done when the Mote's promotion can be recorded with one CLI call and `mesh.buy` then
accepts the picture.

## Block P — Music and sound a game can ship

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

### §PW270 Nodes addressed by what they are

Found keeping Cottony's flows (PW217). Cottony builds its screens in code and names few
of its nodes, so the paths an agent queries are Godot's generated names:
`/root/Main/@Node2D@14/@Node2D@35` is the board, `@Node2D@1133/@Node2D@1126/@Label@1129`
the result card's heading. A kept flow expects and clicks at those paths. They hold
while the game builds its tree in the same order, and any change that adds a node before
them renumbers every one after, so a flow breaks on an edit that changed nothing it
proves.

Let a node be addressed by what it is rather than where the counter left it: by class
and a property that picks it out, such as `{"class": "Label", "text": "NÍVEL
CONCLUÍDO"}` or `{"class": "Board"}` (a script's class_name), answered as the path it
resolves to now. `game.keep` writes that selector into the flow in place of a generated
path wherever it finds one unique, and `game.replay` resolves it again each run, so the
flow survives a reordering. A path with no generated name in it is kept as it is.

Done when Cottony's two flows are kept again with selectors, still replay to the same
frames, and a test that inserts a node ahead of the board replays unchanged.

### §PW271 Long flows in few calls

Found keeping Cottony's flows (PW217). An agent driving through the command line pays a
fresh Python process per call, about 0.3 s, and a match-3 level is a loop of query the
board, tap two cells, wait until it settles: thirty-three moves took two hundred calls
to keep and thousands to find. The explorer wrote its own loop script to cope, and its
third flow, losing a level later than the first, never finished: a fresh save unlocks
only level 1, so reaching a later one meant winning the ones before it, and after two
hours and ten sessions it had not.

Two gaps, each worth closing:
- a game's own setup should be reachable from a flow: `game.call` can already run a
  method the game exposes, and a flow that starts at level 5 with `call start_level 5`
  proves the level without replaying four wins, which is a game-side change the finding
  should name when no such method exists;
- the session tools should take a short script of commands in one call, answering each,
  so a loop of query, input and wait costs one process and not three hundred.

Done when the lose-a-later-level flow is kept for Cottony in under a hundred calls, and
replays to the same frame every time.

## Block T — Adopting polyweave in a project
