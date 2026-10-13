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

### §PW414 Speech checks and quotes that mislead

Where: spinhold RK218, the pilot's Portuguese and English takes from `voice.lines`.

Three frictions, each met voicing thirteen short lines:

1. `sound.speech`'s `said` fails takes that say the line. "Lá" heard as "la" is a miss
   (no accent folding), and an interjection's spelling ("uhuu" heard as "woohoo", "vamo"
   as "vamos") is a miss. Fold diacritics before comparing, and let a line's
   interjections, or a project list of them, count as said whatever the spelling.
   Worse, the recogniser is not told the take's language: a Portuguese take is
   transcribed as English ("Isso, isso aí! Capataz" heard as "this this is the
   kapatais"), so every Portuguese line reads as failed. The record carries the line's
   locale; pass it to the recogniser.
2. `voice.lines --keys A B C` is refused by the CLI as unrecognised arguments; only a
   JSON list (`--keys '["A","B"]'`) works, and neither `describe` nor the refusal says so.
3. Before a speaker has a voice id, the quote prices nothing (`characters: 0`), so the
   cost of a set is unknown until a voice is bought and chosen. Price the unvoiced rows
   too, marked as such.

### §PW415 A page per sitting

Where: spinhold, approving the pilot's voice and lines on `python -m polyweave review`.
The page drew every card of every open sitting on one page: 198 items in four sittings,
the pilot's four pending takes lost among 166 old line cards. The owner could not find
what waited on them, and asked for a page per sitting.

Built: the page opens on an index of sittings, newest first, each a row with its title,
its folder, "N to answer", how much is answered and when it was laid out; finished ones
fold under "older sittings". A row opens that sitting alone, `?sitting=<manifest>` in
the browser, so a link to one sitting is a link to it and the back button returns to the
index. `?member=` still opens the sitting that judges a file, and a smoke run's answer
the sitting holding its family. The window draws the same screen. `listed()` and
`sittingOf()` in @pw/core, tested in desk.test.ts; the index words in both catalogs.

### §PW416 Where voice.lines lays its sitting

Where: spinhold RK218, `voice.lines --speaker pilot --spend true`.

The takes' sitting landed at `<project>/voices/lines/`, a folder at the project's root
beside `game/` and `art/`, where Godot imported its PNG sheets as game assets. The
project keeps sittings under `art/review/` (which carries a `.gdignore`), and
`voice.design` takes `out` for that; `voice.lines` has no `out`, and its default
resolves against the root rather than the work area.

The workaround: the folder was moved to `art/review/pilot_lines/` by hand and the paths
rewritten in its `sitting.json`, `.polyweave/sittings.json` and
`.polyweave/answers.jsonl`; missing the last left 23 answers pointing at a sitting that
no longer existed, and the index showed it unanswered.

What polyweave should do: give `voice.lines` an `out`, default it to a project setting
for sittings (or the work area, never the root), and offer a way to move a sitting that
carries its answers with it.

### §PW420 A voxel build renders whole

Found in spinhold, RK192 (the Hod, a new voxel enemy). Its declaration
(art/voxels/carrier.toml, `hollow = 1`) builds cleanly: `polyweave build ... --preview`
draws a whole, solid model in its four views (assets/voxels/carrier.voxels.png). Its
acceptance spec renders the build to hold `silhouette_aspect`:

    python -m polyweave render.bake --out art/renders/carrier.png
        --model assets/voxels/carrier.glb --rung preview

The render shows the model shattered: scattered cubes with holes through it, faces
missing, nothing like the build's own preview. The Gleaner's build
(assets/voxels/keeper.glb) renders the same way, so it is the render of a voxel build's
glb, not one model. The silhouette predicate still passed (the bounding outline holds),
but the picture a person is shown on the review page would be this broken one, and a
luma or coverage bound measured from it would be wrong.

Expected: a voxel build's render at any rung looks like the build's own preview, every
skin face drawn and lit (the glb's faces culled from the wrong side, or a hollowed
model's inner cells exported without their faces, are the likely causes).

Workaround: none. The spec holds the owner's premise alone, and the look waits for a
person on the build's own preview.

### §PW421 A built ribbon frees whole

Found in spinhold, RK195 (a check suite that leaks nothing). The path ribbon scene
`vfx.build` writes (`kind = "path_ribbon"`, src/polyweave/vfx.py `_FOLLOWS`) carries an
inline script whose members are initialised where they are declared:

    var strip := ImmediateMesh.new()
    var drawn := MeshInstance3D.new()

and `drawn` enters the tree only in `_ready`, by `add_child(drawn)`. A ribbon instanced
and freed without ever entering the tree (a check reading its nodes, a preview, a pool
that builds ahead) never runs `_ready`, so `drawn` is never its child and outlives it:
an orphan MeshInstance3D and a leaked render instance per ribbon. spinhold's
check_trails built its seven trails that way and left seven of them at exit.

Workaround: spinhold's check adds each built effect to the tree before freeing it.

What polyweave should do: make `drawn` (and `strip`) in `_ready`, or free `drawn` in
`_notification(NOTIFICATION_PREDELETE)` when it has no parent, so a built effect frees
whole however it is used. A test can instance a built path ribbon, free it, and count
orphan nodes.

### §PW422 A score's reference, recorded

Found in spinhold, RK207 (the Quilt's music). The design asked that the Quilt's cue be
written against Cottony's calm loop (another project's docs/design/audio/music_calm.ogg)
and that "the cue's provenance names Cottony's loop as its reference". The score
(art/audio/quilt.music.toml) can say so only in a comment: `[music]` has no key for a
reference, and `music.render` takes `source`, `out`, `root` and `formats`, so the record
beside game/audio/music/quilt.wav names the score alone. A person comparing the cue to
what it answers, or a later session, cannot find the reference from the record.

Workaround: the score's header comment names the loop; nothing records it.

What polyweave should do: let a score declare `reference = "<path>"` (a file under the
project, brought in with `provenance.borrow` when it is another project's) and have
`music.render` record it as an input with the role `reference`, as a fitted model's
record names its mesh. `verdict.sitting` and the review page could then play the
reference beside the cue, so a person judges the one against the other.

### §PW423 A cue's kit in its record

Found in spinhold, RK207. The phase music scores play a chip kit, `[kit.chip] effects =
"art/audio/drums.sfx.toml"`, which music.render synthesises and places on every drum
note. RK207 added a kick (`bd`) to that kit. The records beside game/audio/music/
phase_*.wav name the score (`role: score`), the engine and the patches, but not the
kit's .sfx.toml, so editing the kit changes what a re-render sounds like while every
record still reads current. A hat retuned in the kit would change three cues silently.

Then, checking that, `python -m polyweave provenance.outdated` stopped with a traceback:

    File "src/polyweave/provenance.py", line 1124, in _same_entity
      return still_drawn(source, drawn["id"], drawn["sha256"], ...)
    KeyError: 'sha256'

(polyweave's working tree had uncommitted changes to provenance.py at the time, so this
may be work in progress.)

What polyweave should do: record each kit's .sfx.toml as an input of the render (`role:
kit`), so `provenance.outdated` names every cue a kit edit leaves behind; and have
`outdated` refuse a record missing a field with a code naming the record, never a
traceback.

### §PW424 A preview laid where sittings go

Where: spinhold, RK222 (one review sitting for the day's pieces), 2026-10-12.

The call: `vfx.preview --source art/vfx/bomb.vfx.toml --out art/review/rk222-bomb-vfx`,
so the bomb's motion would sit in art/review/ beside the day's other sittings.

What came back: `vfx.unshipped`, "art/vfx/bomb.vfx.toml sits where the game's export
leaves it out (art holds a .gdignore), so a scene built beside it would not ship",
remedy "pass out, a folder the game ships or set [paths] vfx in polyweave.toml". But
`out` was passed, and the only folders that satisfy it are shipped ones such as
game/vfx/, where the effect scenes already live (vfx.build wrote them there for RK219).
Passing that would lay a review sitting, its sheets and its sitting.json inside the
shipped game.

Expected: a preview is a sitting for a person, so its `out` is where the sitting goes
and may be under art/review/ like every other sitting. The scenes it films are either
the built ones (game/vfx/, found from the declaration's records) or built into the work
area (.polyweave/), never into `out`. The refusal should name which of those two it
needs.

Workaround: no preview. The bomb's family in spinhold's rk222-day sitting is in-game
stills from dev/shot.gd --hold=bomb at several frames, which show its life only as far
as those frames do.

What polyweave should do: split where the sitting is laid from where a scene is built,
take the built scenes from their provenance when they exist, and accept any `out` for
the sitting.

### §PW425 The replaced sound as a sitting's old

Where: spinhold, RK71 (the phase music in layers), 2026-10-12.

`music.render --source art/audio/phase_1.music.toml --out game/audio/music/phase_1`
rewrote game/audio/music/phase_1.wav in place, as it should. The person then has to hear
the new mix beside the one it replaces, so `sound.sitting` was given an `old` for each
track. But the old file no longer exists on disk: it lives only in git, and in this
project as a Git LFS pointer, so `git show HEAD:<path>` gives 132 bytes of pointer.

Workaround: for each track, by hand, `git show HEAD:game/audio/music/phase_N.wav | git
lfs smudge > .polyweave/shots/rk71/phase_N.old.wav`, then those paths as `old`. Three
commands per render, and nothing records where the old file came from.

What polyweave should do: let `old` name a committed version (`HEAD:<path>`, or "the
version this render replaced"), resolved through git and LFS into the work area,
recorded in the sitting; or have music.render and sound.synth keep the file they
overwrite in the work area and offer it as the sitting's `old` by default.

### §PW426 A score derived from another

Where: spinhold, RK71 (the phase music in layers), 2026-10-12.

The game's three phase scores (art/audio/phase_1..3.music.toml) are one piece in three
keys: the Waist's is the Bow's a tone up, the Stern's a tone down, with their own tempo,
title and a drum line or two of their own. Adding a lead and a high layer meant writing
the same new patterns three times, transposed by hand note by note (`e5` to `f#5` to
`d5`, `c6` to `d6` to `bb5`), and copying every patch, kit and track block into each
file.

Workaround: a throwaway script (the session's scratchpad, derive_scores.py) that read
the Bow's score and rewrote the other two by regex, with the transposed patterns typed
in. A wrong hand transposition is a wrong note no validator catches.

What polyweave should do: let a score derive from another (`extends =
"phase_1.music.toml"` with `transpose = 2`, `bpm`, `title` and the patterns or tracks it
overrides), compiled as a whole score so `music.validate` and the render see the result;
or a `transpose` modifier in the mini-notation per pattern. Either way one edit to the
Bow's lead reaches all three.

### §PW427 Particles drawn as a mesh

Where: spinhold's Stuffing effect, game/world/stuffing.gd, whose tufts are a squashed
sphere built in GDScript and thrown as particles. PW408 gave vfx.build a twinkle, a star
and a heart, each a picture on a quad that faces the camera, and a tuft is none of
those: it reads as soft only where it has depth and catches the light from one side.

Every particle vfx.build writes draws a QuadMesh (or a RibbonTrailMesh for a ribbon),
and `shape` only chooses the texture on it. A declaration has no way to say "throw small
round puffs", so the game builds the mesh itself and the effect's look is split between
a declaration and a script.

What polyweave should do: let a particle's draw pass be a mesh as well as a quad. A
`mesh` key naming one of a few primitives the engine already ships (a sphere, a capsule,
a box), with a `squash` of three scales, writes a SphereMesh (or the others) as
`draw_pass_1`, shaded rather than unshaded so its light reads, with `colour_over_life`
still on the vertex colour. A mesh of the project's own (a .glb or a .tres under the
project) is the same key with a path, refused where nothing is there, as a picture shape
is. The measures stay as they are.

Open choice: whether a meshed particle keeps the billboard (it should not: a puff turns
as it flies) and whether `angle` then means a turn about the view axis or all three.

### §PW429 A teaser cut from captures

Where: spinhold, RK223 (the store page's 30-second teaser), 2026-10-12.

`capture.movie` writes every frame between two marks a script prints, into a folder. A
store teaser is several such stretches from different runs, cut together at stated
lengths, with the game's music under them, encoded at 1920 by 1080 in a format Steam
takes (H.264 MP4), and opening on play within three seconds. Nothing in polyweave takes
the sequences that far: there is no operation to declare a cut list (which sequence,
from which frame, for how long, with what transition), lay audio under it, encode it,
measure it (length, the first frame with play) and record it. The project would have to
drive ffmpeg itself, which the owner's rule puts in polyweave.

What polyweave should do: a declared edit (`*.cut.toml`: clips from capture.movie
sequences or kept runs, their in and out frames, the sound beneath) built into a video
with its record, held to an acceptance spec (duration, resolution, time to first
motion), and laid in a sitting for a person. Spinhold's RK223 waits on it.

### §PW435 A free tier's licence in a take's record

Where: spinhold RK218, the pilot's voice on an ElevenLabs account on the free tier.
PW410 made a 403 from the speech service `fetch.plan-lacks`, in the service's words, and
printed a refusal's detail in its text. What it left: ElevenLabs' free tier allows takes
for non-commercial use only, and nothing in a take's record says which tier made it.

A game that ships commercially with a free-tier take is in breach, and the record is the
one place that could have said so. `provenance.credits` lists who made each shipped
file; it cannot warn about a licence the record never held.

What polyweave should do: read `/v1/user/subscription` (free; `sound_buy._used` already
reads it for `character_count`) and keep its `tier` in each take's record, under the
engine beside the model, for `sound.buy`, `sound.speak`, `voice.design` and
`voice.lines`. `provenance.credits` then names any shipped sound whose tier is `free` as
not licensed for commercial use, with the file and the tier, and a project can make that
a gate. A reading that fails records no tier, never a guess, as `_used` does.

The proof: a take bought on a stubbed free subscription carries `tier = "free"`, and
credits over a project shipping it says so; a paid tier says nothing.

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

### §PW430 A declaration's vocabulary over MCP

Where: PW409 gave `describe vfx.build` a `declares` answer, the keys a *.vfx.toml may
hold with each one's type, default, choices and sentence. It is reached through `python
-m polyweave describe vfx.build` and through `describe.describe()` in Python.

The MCP server (src/polyweave/server.py) lists every operation as a tool whose
description is the summary and whose inputSchema is the parameter set. It has no tool
for `describe`, `capabilities` or `explain`, so an agent that drives polyweave through
the MCP tools sees `source: the *.vfx.toml` and nothing of what that file may hold. It
falls back to the shell, or to reading vfx.py, which is what PW409 was filed against.

What polyweave should do: put the declaration where the MCP caller looks. Either a
`describe` tool beside the operations, answering `describe(name)` as the CLI does
(declares included), or the vocabulary carried in the inputSchema itself, as the
description of the parameter that names the file. The first keeps tools/list short and
serves every later `declares` an operation grows; the second needs no extra call but
costs every listing the vocabulary's tokens, which PW129 bounds. The proof: over MCP, an
agent learns that `shape` takes `heart` without a shell or a source read.

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

### §PW192 Cottony's audio made through polyweave

The block is proven when its first consumer uses it. Cottony's music and effects are
declared in its `polyweave.toml`, made by `music.render` and `sound.synth`, and held to
`*.accept.toml` bounds, and its own audio scripts are removed. Anything Cottony needs
that a second game would not becomes configuration.

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
the first twenty make.

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

### §PW428 A drawn pad in the remap kit

Every game that rebinds a pad wants the screen Spinhold designed as RK148: the pad in
use drawn large in its layout, a line from each button, trigger, stick direction and
menu button to the action it holds or "free". A real press lights it on the picture;
choosing a button and pressing fire binds through the kit's own swap rule. With the
players kit, a tab per seated player. The owner chose (2026-10-12) to build it in the
kit.

What to build: a `pad_screen.gd` and scene in the remap kit, opened from its controls
tab row beside the remap screen. Its picture per layout is declared art: an SVG per
layout drawn to PNG by picture.vector, each button at a declared spot (a table the
screen reads, so drawing and screen cannot drift), with an acceptance spec (hue_spread,
alpha_coverage, silhouette_aspect) and the pictures laid in a sitting for a person. The
pads are detailed: shell, shading, wells, lit rims in the layout's colours, no maker's
marks. A first Xbox drawing in that frame (1000 x 667) is at spinhold's
.polyweave/pad/pad_xbox.svg (work area, uncommitted). Spinhold's game/ui/pad_screen.gd
(commit ab85f69) is the logic to extract: the slots, the leaders, lighting a press,
choosing and binding.

The proof: a rebind on the picture takes and swaps, a press lights its spot, each layout
draws, and the spots table matches each SVG's buttons.

### §PW431 Every button named, in every family

Where: spinhold, RK216 (moving the game onto the prompts, remap and players kits),
2026-10-12, read against prompts 0.3.0.

1. No "generic" family. `family_of` reads any pad that is not PlayStation or Switch as
   xbox, so an unknown pad is labelled A/B/X/Y although its buttons may say anything.
   Spinhold names such a pad's face buttons by direction (SOUTH, EAST, WEST, NORTH through
   the string table's PAD_SOUTH...) and its menu buttons SELECT/START.
2. Nothing names a raw code. `named(action, player, family)` takes an action; a screen
   that shows a pad's every button (Spinhold's pad screen, PW428) needs the name of
   `button:3` or `axis:2:-1` in a family, bound or not. Spinhold has `named(code, layout)`
   and `describe(codes, layout)` (a binding's codes joined, for the Controls tab row).
3. The clicks are spoken LS/RS where Spinhold says L3/R3 and has GUIDE; `said` translates
   any name with no guard, where Spinhold leaves a one-letter glyph (A, B) untranslated.

What polyweave should do: a generic family whose glyphs are the compass names, a
`named_code(code, family)` and `describe(codes, family)`, and the clicks' names a family
declares. Spinhold's game/core/bindings.gd (named, said, table_key, GLYPHS) is the
reference; check_button_prompts and check_every_line_from_the_table hold its behaviour.

### §PW432 A remap menu a game can ship

Where: spinhold, RK216, read against remap 0.3.0 (core/remap_menu.gd).

1. The remap menu binds on press. Spinhold's Controls tab listens until the input is
   released (`AXIS_RELEASE`, options.gd 185-253), so a stick pushed past the threshold
   binds the direction it ended on rather than the first one it crossed, and holding the
   cancel button cancels instead of binding it. The kit has `AXIS_PRESS` and no release.
2. Its words are hard-coded English ("Press a key", "Reset"...), so a game in pt-BR shows
   English on its Controls tab; Spinhold's go through the string table (tr) and its
   words.check.
3. It has no player-facing label or order per action: the list is ProjectSettings' order
   and the raw action names. Spinhold declares `Bindings.LABELS` (action -> table key) and
   shows actions in that order.

What polyweave should do: a capture that listens through release with a hold to cancel,
every string a key the game's table translates (with English defaults), and a declared
label and order per action in the game's declaration (res://polyweave_remap.gd).
check_rebind in Spinhold's dev/check.gd holds the behaviour to match.

### §PW433 A game's own pad options in the remap kit

Where: spinhold, RK216, read against remap 0.3.0 (core/bindings.gd).

1. The remap kit keeps its own file (user://polyweave_bindings.cfg) with a fixed [pad]
   section of deadzone and invert_vertical. Spinhold's controls live in its one settings
   store (user://settings.cfg, section controls) beside every other options tab, validated
   and reset per section, and include a pad option the kit has no slot for: `twin_stick`
   (fire with the right stick's direction). FROM adopts the bindings once but drops
   twin_stick, and afterwards the game's Options screen and the kit write two files.
2. The deadzone differs: the kit defaults to 0.5 and clamps 0.05 to 0.95, Spinhold to
   0.25 within 0.05 to 0.6, so an adopted value can land outside the game's range.
3. `invert_vertical` is an instance field, where the ship reads it every frame; a game
   needs the kit's store reachable without holding an instance.

What polyweave should do: let a game declare extra pad options (name, type, default,
range) the kit keeps and adopts, declare the deadzone's default and range, offer a
static `shared()` store, or let the game hand the kit its own settings section to keep
the bindings in.

### §PW434 A help line the prompts kit keeps filled

Where: spinhold, RK216, read against prompts 0.3.0 (core/prompts.gd).

A help line names buttons ("{fire_right} take  {bomb} back"), and it must be filled
again whenever the player's device changes, a binding changes, or the language changes.
Spinhold's Prompts autoload does it with `watch(label, key, player)` (a label filled
from a table key and kept filled) and `follow(redraw)` (a callable run on every change),
and it refills on NOTIFICATION_TRANSLATION_CHANGED. Thirteen screens use them (codex,
status, shop, route, options, title, menus, ship select, records, pad screen, draft).

The prompts kit only signals `family_changed` and `player_changed`; each screen would
have to connect, keep its own key and refill by hand, and a language change refills
nothing.

What polyweave should do: `watch(label, key, player)` and `follow(callable)` on the
prompts service, refilled on a family change, a rebind and a translation change, so a
screen states once what it shows.
