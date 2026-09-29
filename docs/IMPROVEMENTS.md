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

### §PW297 The driven game's scene changes as it does for a player

Met in starship (RK143), putting the new Lancer in front of a camera. `game.open
display=true` loads the project's main scene, the Splash, and the game leaves it with
`get_tree().change_scene_to_file(next)`. Five thousand frames later `game.query` still
found `/root/Splash`, its `Camera` still `current = true`, and `/root/Main/Camera` not
current. Every `game.shot` showed the splash's intro close-up of the ship while `Main`
was playing under it. Nothing in the answer said so: the shot came back with a path and
a size, as it always does.

The cause is in `godot/addons/polyweave_driver/driver.gd`, `_initialize`: the scene is
instantiated and `root.add_child(main)`, and `current_scene` is never set. Godot's
`change_scene_to_file` frees the current scene, and there is none, so the first scene
never leaves. A game whose scenes hand over to each other (splash, title, ship select,
play) runs two at once under the driver, which it never does for a player.

The workaround was `game.set /root/Main/Camera current true` before the shot. It lives
nowhere, since the session was thrown away.

What polyweave should do: set `current_scene = main` after adding it, so the game's own
scene changes behave as they do without the driver. A check drives a two-scene fixture
where the first changes to the second and asserts the first is gone.

### §PW298 A spec that measures the model the game draws

Met in starship (RK143). `art/accept/gunship.accept.toml` holds the gunship to
`silhouette_aspect >= 0.6`, and its artefact `art/renders/gunship.png` is a render of
`assets/models/gunship.glb`, the Meshy mesh. The game has drawn the voxel build of
`art/voxels/gunship.toml` since RK40, so the spec measured a model no player sees.
`asset.brief --asset gunship` names both the declaration and the artefact, reports
`matches_record: true`, and says nothing about the render's input not being the
declaration's output.

When the voxel gunship was made again, its preview render (`render.bake` of
`assets/voxels/gunship.glb`) passed the aspect at 1.09, but failed `brightness-holds`
and `stays-untextured`. Those two bounds were set by margin from the grey Meshy render,
and a coloured voxel model can never meet them. So the spec cannot be moved onto the
model the game draws without a person redoing those bounds. Its render was left where it
was.

What polyweave should do: `asset.brief` (and `accept.verify`) should say when an asset
has a geometry declaration whose built output is not the input its spec's artefact was
rendered from, naming both paths. A spec should also be able to name the declaration's
build as its subject, so `render.bake` renders that build at the rung. Then a spec
written for a mesh the project replaced reads as stale, and doesn't pass as current.

### §PW312 A parameter named like a function still counts as read

Met in starship (RK144), building `art/voxels/mine_layer.toml`. It declares `[params]
floor = -0.38`, and nearly every node places itself with it in an expression, such as
`at = ["0", "floor + 0.35", "0"]`. `geometry.build` and `geometry.describe` both answer
`warnings: ["the parameter floor is declared and no node reads it"]`. The model builds
with `floor` applied: the discs stand where the expressions put them. So the warning is
false, and it has stood on that declaration since RK42 without anyone trusting it.

The warning comes from `warn` in `src/polyweave/geometry/review.py`, which collects
`uses(node)` over the nodes. My guess is that `floor` is also a function name the
expression language knows, so `uses` counts it as a call rather than as a parameter. The
other params of the same file (`wide`, `long`, `lights`) are not reported.

Nothing was worked round; the warning was ignored. A warning that is sometimes false
teaches the reader to ignore all of them, and that is the cost.

What polyweave should do: a name that is declared in `[params]` is a parameter wherever
an expression names it, even when a function shares the name. Better, a param that
shadows a built-in function is refused, or named at declaration, so `floor(x)` and
`floor` cannot mean two things in one file. A check declares a param named after a
function, reads it in an expression, and asserts that no unused warning comes back.

### §PW315 A vector logo rendered whole and in layers

Met in starship (RK150): the title should show the logo the owner accepted for the Steam
page. That logo is a vector, `art/brand/spinhold-wordmark-clear.svg`, whose groups hold
a blurred magenta halo, a dashed cyan ring through the O, and the letters with their
drop and bevel, drawn with blur filters and masks. The store's `library_logo.png` came
from a work-area rasterisation that no record covers.

The game needs that logo at 4K width, transparent, with a `.prov.json` naming the SVG,
so store and game cannot drift. It also needs it in layers (ring, halo, letters) on one
canvas, so the ring can turn and the glow pulse while the letters hold still. `describe`
lists no operation that rasterises a vector or picks groups out of one. Nothing was
built: RK150 waits on this line.

What polyweave should do: render a vector picture to PNG at a stated width, filters and
masks included, recording the SVG as input. Given group selectors, write one PNG per
layer on the same canvas and origin, so the layers stack back into the whole, and let a
spec hold each layer's alpha edge. The SVG's groups carry no ids, so selecting by order
or paint, or naming layers in a declaration, is part of the answer.

### §PW316 A UI panel built from a declaration

Met in starship (RK151): the menus need a kit of panels, bevelled holo-glass frames with
corner brackets, scan lines and an accent tick in the logo's palette, each with a focus,
pressed and disabled state. The design asks for them "generated and checked through
polyweave (nine-patch textures or a shader with a declared spec)". `describe` has
nothing for it: `vfx.build` declares particles and ribbons, `geometry` builds meshes and
voxels, and no operation makes a nine-patch, a UI shader or a stylebox from a
declaration.

The workaround is a hand-written canvas shader in the project,
game/ui/kit/holo_panel.gdshader, with its look held only by the owner's verdict on
screenshots. Its numbers (edge width, bracket length, scan-line pitch, glow) are chosen
in code, which is what "never tuned by eye" meant to prevent.

What polyweave should do: declare a UI panel (a frame's parts, palette, states, and the
nine-patch margins) and build it to either nine-patch PNGs with a `.prov.json` or a
Godot canvas shader with its uniforms. Then capture it in each state and hold a spec to
it: text contrast over the fill (measure.contrast), edge crispness at the smallest scale
the game draws, and the palette's distance from the declared colours. The project's
shader is then replaced by the built one.

### §PW319 Text legibility measured glyph by glyph

Met in starship (RK154): the title now stands over the living voxel city, and the design
asks that "a gradient keeps the text above the declared contrast". The screenshot was
taken with dev/shot.gd. `measure.contrast --targets '[{"box":[360,405,925,635]}]'` then
answered `ratio: 2.549`. That ratio is the box against the ring around it: a whole score
table against the city beside it. It is not each glyph against the pixels behind it,
which is what decides whether a line reads, so no bound on it can say the text is
legible.

The workaround was a radial veil behind the text column (game/ui/title.tscn, `Veil`),
with its strength chosen by looking at the shot.

What polyweave should do: a measure of text legibility over a picture. Given the text's
boxes (or a capture where the game draws its labels once with and once without the
backdrop), it separates glyph pixels from background. It reports the contrast ratio of
each line's glyphs against the local background behind them, the worst line named, so a
spec can hold `text_contrast_min >= 4.5`. `capture.run` could emit the label boxes it
drew, the way `measure.contrast` already reads a `target:` log.

## Block I — Voxel models from a declaration

### §PW317 A voxel build's --set that is dropped

Found in starship (RK169), searching for the cell size that gives the splash V three
times its cells. `python -m polyweave build art/voxels/viglet_v.toml --out <scratch>
--root . --set voxels.cell=0.03 --no-mesh --json` came back `"status": "built"` with the
same 2590 cells and the findings of the 0.05 cell: the `--set` was dropped without a
word. Four sizes were "tried" this way before the counts gave it away.

Expected: `--set voxels.cell=<n>` overrides the declaration's `[voxels] cell` for that
build (the way `--set` answers a declared parameter), or a refusal naming the keys
`--set` does take, with `allowed` and `did_you_mean`. A build answer should also echo
what each `--set` changed, so a silent drop cannot pass as a result.

Workaround: `sed` copied the declaration to the scratchpad with the cell edited, once
per size, and built the copy. A sweep over the cell (count, findings per size) is the
operation this really wanted; `search.sweep` over a voxel declaration's `cell` would do
it.

### §PW318 A cell ceiling per declaration

Found in starship (RK169). `[voxels] budget = 6000` in polyweave.toml is the ceiling the
owner set for the game's actors, which crowd the screen and break into debris. The
Viglet Games splash V is the one model on its screen, and the owner asked for three
times its cells (8732 at cell 0.033). Every build of it now carries `budget: 8732 cells,
over the 6000 this project can afford`, a finding that stands for good though the owner
allowed it, and that reads the same as a real overrun on an actor.

`post/voxels.py` reads the budget only from the project's `[voxels]` table
(`ACCEPTS_VOXELS`); a declaration cannot state a ceiling of its own.

Expected: a declaration may state `[voxels] budget = <n>` (or a named class the project
declares, `[voxels.budget] actor = 6000, hero = 12000`), and the check holds it to that,
with the provenance saying where the bound came from. Raising the project's ceiling
instead would loosen it for every actor, which is not what the owner said.

Workaround: none; the V's declaration says in a comment that it stands over the budget
by the owner's word, and the finding stays.

### §PW326 A part fitted to a region of a picture

Found in starship (RK170): the splash's voxel V gives way to the studio's real badge PNG
under a flash, so the voxel V must stand exactly where the badge's V does. The badge's
silhouette is a disc, so `geometry.fit --source art/voxels/viglet_v.toml --reference
game/ui/brand/viglet_games_badge.png` can only fit the disc: the V inside it, which is
what moved, is invisible to an alpha silhouette. The voxel V was 1.49 units tall against
the badge's 1.22, and the jump showed on screen.

Expected: a fit reference can be a region of a picture, named by colour or palette entry
(the badge's dark body and cream edge), scored against the cells of the declaration's
materials that stand for it (`body`, `edge`), with the frame held by the whole picture's
bounds, so a part is fitted in place and at scale, not only in proportion. Also
`atan`/`atan2` and `degrees` in the expression grammar, so a part can be declared by two
end points instead of a length and a tilt.

Workaround: a throwaway script in the scratchpad (`measure_v.py`, `v_reference.py`)
masked the badge's dark and cream pixels plus the disc's inset ring into a reference
PNG, and a probe declaration in `.polyweave/fit/` holds the V and the same ring;
`geometry.fit` then searched the arm's parameters against it.

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

### §PW192 Cottony's audio made through polyweave

The block is proven when its first consumer uses it. Cottony's music and effects are
declared in its `polyweave.toml`, made by `music.render` and `sound.synth`, and held to
`*.accept.toml` bounds, and its own audio scripts are removed. Anything Cottony needs
that a second game would not becomes configuration.

### §PW313 A jingle heard as one

Found in starship (RK160), scoring the Viglet Games splash as a cartoon jingle: five
`sound.synth` cues (`splash_gather`, `splash_pop`, `splash_boing`, `splash_crash`,
`splash_fall` in `art/audio/effects.sfx.toml`) that `game/ui/splash.gd` plays on its own
clock: the whistle at 0 s, eight pops at the times a share of the cells lands, each
pitched up the major pentatonic, the boing at 1.2 s, crash and fall together at 1.75 s.

`sound.sitting --members [...] --out art/review/splash-jingle` laid the five out one by
one. A person judging a jingle hears its parts, never the jingle: whether the boing is
too loud over the whistle, or the pops land on the beat, only shows when they are heard
together, and today that means launching the game and watching the splash.

What polyweave should do: a declared arrangement, cues at times with a pitch and a gain
each (`[arrangement.splash]` beside the effects, say), that a sitting can play as one
mixed preview beside its parts, and that the project's code can read so the times it
plays match what the person accepted instead of being repeated in GDScript. A verdict on
the arrangement then covers the mix, and `sound.measure` can report its peak once
summed.

Workaround: none written. The times live only in `splash.gd`, and the owner hears the
whole only in the running game.

### §PW314 A line spoken aloud

Found in starship: the owner asked for the Viglet Games splash to end on a spoken
"Viglet Games", the way EA Sports games open on a voiced tag. polyweave has no operation
that makes speech. `sound.buy` drives ElevenLabs' text-to-sound model
(`eleven_text_to_sound_v2`), which makes effects from a description and does not speak a
given line reliably; `python -m polyweave describe` lists nothing for a voice, a speaker
or text to speech.

What polyweave should do: `voice.buy` (or `sound.speak`) that speaks a declared line
through a text-to-speech service (ElevenLabs' TTS models are one), at a declared cue's
file, against the project's budget and ledger as `sound.buy` is. The declaration names
the words, the voice (a service voice id, or a described voice), and the delivery
(energy, pace, stability), so the same line can be re-made; the record keeps the voice
and model, and the credits list the service. Optionally a local engine (Piper,
espeak-ng) as a free rung for a draft before money is spent. A sitting plays takes side
by side for a person's verdict, and `words.check` can hold the spoken text to the world
like any other line.

Workaround: none; starship's RK161 waits on this rather than recording a voice outside
polyweave. It also needs the owner to set a `[budget.elevenlabs]` in starship's
polyweave.toml.

### §PW320 A price by the character

`[service.<name>] prices` holds one figure per model, and `sound.buy` charges it per
sound. That fits Ideogram, which bills per picture, and ElevenLabs' sound generation,
which bills per request. Text to speech does not: ElevenLabs charges credits per
character of the text sent, at a rate that depends on the model (the Flash and Turbo
models are cheaper per character than Multilingual v2). A studio tag of twelve
characters and a paragraph of briefing are priced the same today, so a ceiling either
blocks the paragraph or lets through far more tag takes than the person expected.

What polyweave should do: a `prices` row may name its unit, e.g. `{ per = "character",
rate = 0.00003 }`, and a job states the count before anything is sent. `purchase.allow`
then asks about the count times the rate, and the refusal quotes both. The service also
publishes `/v1/user/subscription` with `character_count` and `character_limit`, so where
it answers, the spend is the difference between two readings and the entry carries
`measured: true`, as a mesh's does. The quoted rate stays as the fallback and says it
was quoted.

The spec change belongs in `docs/specs/fetching.md` beside the quoted-price exception.
Nothing here decides a line is worth voicing: it only makes the ceiling a person set
mean what they meant.

### §PW321 A character's voice, designed once

PW314 speaks one line in a voice the call names. A game has a cast: Ada's lines must all
sound like Ada, and a second session that picks another voice id for her next line
breaks that without anything noticing.

What polyweave should do: `[entity.<id>.voice]` in the world file, beside `look`,
holding either a service voice id or a `description` ("a dry, tired foreman in their
fifties, northern accent") with a sample line. `voice.design` sends the description to
ElevenLabs' voice design endpoint (`/v1/text-to-voice/design`), which answers several
previews speaking the sample, each priced and ledgered against the service's ceiling. A
sitting plays the previews side by side with the entity's description and the world's
`tone`, and the person's verdict names one; only then is it saved as a voice
(`/v1/text-to-voice`) and its id written back as the entity's voice, with the preview's
record as its provenance.

The speech operation then takes `entity=<id>` and reads the voice from the world,
refusing an entity without one (`voice.none`) instead of guessing. Delivery settings
(stability, similarity, style, speed) belong to the voice and may be overridden per
line. The agent never picks among previews itself: that is the non-goal on accepting its
own look, applied to a sound.

The record carries the entity's voice digest, so changing a voice makes every line
spoken in it outdated.

### §PW322 A catalog voiced as a set

A game's lines already live in locale catalogs, and each row names its speaker (the
`_speaker` column `words.check` reads). Once a speaker has a voice (PW321), the takes a
game ships are a function of those rows: one file per key, speaker and locale.

What polyweave should do: `voice.lines` takes a catalog, and optionally a speaker, a
locale or a list of keys, and answers first without spending: each row it would voice,
the characters and the price (PW320), and each row it would skip because a take already
exists whose text, voice and model digests still match. Only a second call with the same
selection and a `spend` flag sends them, stopping at the ceiling with the rest named as
not voiced. Takes land at a cue path the project declares (`[voice] out =
"audio/voice/{locale}/{key}.ogg"`), transcoded as `sound.buy` does, each with its own
record naming the catalog, the row and the entity.

A row whose words change in the catalog makes its take outdated in the provenance
record's outdated report, so the next call offers it again. A row whose speaker has no
voice is reported (`voice.none`), not voiced in a default. The locale selects a
multilingual model where the voice is in another language, and a sitting groups the new
takes by speaker so a person hears a character's lines together before any is accepted.

Nothing here writes a line: the catalog is the person's, and this only speaks it.

### §PW323 A take that says its line

`sound.measure` reports loudness, peak and length, which is what an effect is held to. A
spoken take has failures of its own that are measurable before anybody listens: leading
and trailing silence the game would play as a pause, a take far longer or shorter than
its words suggest (a skipped phrase, a repeated one), a clipped last syllable, and a
name read wrongly, which is the common failure on invented names like the world's.

What polyweave should do: speech measures in the vocabulary, each with a declared bound
in `[voice]`: `lead_silence` and `tail_silence` in seconds, trimmed to the bound on
capture where the project asks; `rate` in characters per second against a band;
`loudness` aimed at the same integrated target a project's effects use, so dialogue and
effects sit together. And `said`: a local speech-to-text pass (faster-whisper, when
installed) transcribes the take and reports the words that differ from the line, with
the entity names from the world passed as the vocabulary to expect. It runs locally
because paying a service to check a take is spending on the agent's own judgement.

A take that fails a bound is kept and reported, never silently re-bought: whether to
spend on another take is the person's ceiling, and the measures only say which takes are
worth their ear. The sitting shows each take's measures beside it.

### §PW324 A free draft before a paid take

Pictures and meshes climb rungs from cheap to dear, and the dear rung is reached only
when the cheap one has settled what it can. Speech has the same shape: whether a line
fits the moment, whether a tag ends on the beat of a splash, whether a subtitle keeps
up, can all be judged in a plain voice, and only the character of the voice needs the
service.

What polyweave should do: the speech operation takes a `rung`. The draft rung speaks
through a local engine the machine already has (Piper with a downloaded model, or
espeak-ng as the floor), at the same cue path, with a record that says it is a draft and
names the engine; it costs nothing and needs no budget. The paid rung is ElevenLabs as
PW314 describes. A draft never satisfies a line in `voice.lines`: its take is reported
as a draft still to be bought, so a game cannot ship the placeholder by accident, and
the provenance list of generated artefacts shows it apart.

Where no local engine is installed the draft rung is refused with the install command
(`speech.no-engine`), not replaced by the paid one: moving to a rung that costs money is
the person's call. The engine and its model are configuration in the project, not
compiled in, since a project in Portuguese needs a different model than one in English.

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

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

### §PW325 An artefact borrowed from a sibling project

Found in starship (RK170): the splash now turns its voxel V into the studio's real
badge, `viglet_games_badge.png`, which Cottony renders from the publisher's model
(`D:\Git\viglet\cottony\docs\design\art\brand\viglet_games_badge.png`, made by Cottony's
`tools/art/bake_model.py` from `tools/art/3d/viglet-logo.blend`, commit 00a3663). The
badge is shared by every Viglet game and redrawn by none.

polyweave has no operation that brings an artefact another project made into this one:
`normalise.ingest` takes a mesh, `picture.buy`/`picture.collect` a paid picture, and
`purchase.adopt` a ledger. The badge carries no `.prov.json` in Cottony either, so there
is no record to carry.

Expected: an operation (`artefact.borrow`, say) that copies a file from a named sibling
project to a path here, writes a record naming the source project, its path, its commit
and its sha256, and lets `polyweave provenance outdated` say when the source has moved
on, so a change to the studio badge in Cottony shows up as stale in every game that
borrowed it.

Workaround: the PNG is copied by hand to `game/ui/brand/viglet_games_badge.png`, and
`game/ui/splash.gd` names its source in a comment.

## Block U — A window on everything a project governs

### §PW299 One read lists everything a project governs

Today the view of what a project holds is spread over `polyweave.toml` paths,
`.prov.json` sidecars, `*.accept.toml` specs, geometry, music, sfx, vfx and world
declarations, the style families and the line table. `loop.assets` lists the assets with
a spec, and `provenance_verify` lists records, but no single read says "here is
everything, by kind". An agent starting in an unfamiliar project walks the tree by hand,
and a desktop window (the rest of this block) has nothing to draw its tree from without
reimplementing that walk in TypeScript, which would drift from the Python the first time
a kind is added.

`project.inventory` is one bounded read. Each row carries a stable id, a kind (mesh,
picture, sound, music, vfx, clip, line, capture), the declaration path, the artefact
path, whether the provenance record is sound, changed, missing or outdated, whether a
verdict is pending, and a digest. It pages and filters by kind, so a large project fits
a turn. The row format goes in a new `docs/specs/inventory.md`, because the window,
`asset.brief` and the revision record later in this block all depend on it. The
operation writes nothing, and a kind the project does not use is simply absent. It is
never refused.

### §PW300 A brief for every kind, not only a mesh

`asset.brief` (PW131) joins the declaration, the spec's predicates, the artefact's
record, the last verdict, the budget and whether a person is waited on. Its
`_declaration` walks `*.toml` through `is_declaration`, which is the geometry
vocabulary, so a `*.music.toml`, `*.sfx.toml`, `*.vfx.toml`, a style family in
`[style.<family>]` or a line in the words table comes back with `declaration: null` even
where its spec and record exist. A line with no spec at all is refused as unknown.

The window's item view and the per-item Claude Code session both start from this read,
so it has to answer for everything the inventory lists. It takes the inventory's id as
well as a name, reads each kind's declaration back in the words that kind's own describe
uses (the music vocabulary for a cue, the family's palette and floors for a picture, the
world's canon for a line), and keeps the digest so a session can ask whether anything
moved while it worked. It adds `dependents` from `provenance_dependents`, because a
change to one item reaches whatever was made from it, and the person should see that
before asking for the change.

### §PW301 A change a person asks for is a record, not a chat line

The review page already keeps a person's words and a mask tied to a picture's digest
(PW173, PW174), but only as an answer to a sitting the agent laid out. Starting from the
other end is not possible: "this picture needs a warmer rim", said about an item nobody
put up for review, exists only in the conversation that heard it. It is lost when that
session ends, and nothing tells the next one it was asked.

A revision is an append-only line in `.polyweave/revisions.jsonl`, the same shape as
`answers.jsonl`: the inventory id, the digest the person was looking at, an optional
mask or time range (a sound), their words, and when it was asked. `revision.open` hands
the agent the open revisions with the item's brief. `revision.close` ends one with the
run and the sitting that answered it, or with the reason it was withdrawn. It never
closes on a verdict, because the verdict stays the person's (non-goal: an agent
accepting its own look). Writing a revision is the window's second write, and like
`verdict.judge` it is an operation an agent could call on a person's behalf from chat.
Its record goes in `docs/specs/acceptance-spec.md` beside the answer.

### §PW302 The plugin ships without the window

`.claude-plugin/marketplace.json` declares `"source": "./"`, so installing polyweave
copies the whole repository into the adopter's plugin cache: the site, the tests, and
from now on an Electron app with its `node_modules`. Roadkeep hit exactly this when its
GUI moved into its tree (RK1699) and answered by moving the plugin into `plugin/`.

The window belongs in this repository and not a second one. Roadkeep kept its GUI apart
first, and every CLI change then reached the GUI's CI only through a second checkout
(RK1697). A payload change here, to the inventory, the brief or a revision, has to break
the window's tests in the same commit.

So the plugin's manifest, `.mcp.json`, `hooks/` and `skills/` move under a folder the
marketplace names, with the MCP server command still resolving to `src/polyweave`. The
gates add a check that the plugin folder holds no `gui/`, `site/` or `node_modules`. The
move is its own task because it changes what every adopter installs. It is verified by
installing from the marketplace into a scratch project and running `project.check`
there.

### §PW303 A desktop window that opens a polyweave project

The model is roadkeep's own GUI (`D:\Git\alegauss\roadkeep\gui`), whose choices were
paid for once already. It uses npm workspaces with three `tsc` projects. `core` holds
the transport, the payload readers and pure rules, with no Node or DOM. `ui` is React 19
with Tailwind and the viglet design system. `shell` is Electron main with a sandboxed
renderer, a frozen preload bridge and no raw `ipcRenderer`.

Nothing is scanned until a person names a root and a depth. A project is a folder with
`polyweave.toml`.

Opening a project holds one `python -m polyweave serve` process over stdio JSON-RPC.
Every fact on screen is an operation's payload, and the window never parses a TOML, a
sidecar or a JSONL itself, so a kind added in Python appears without a client change.
The engine resolves the project's own polyweave first and PATH last, and is named on
screen. That copy may be pinned, and a server that outlives a change to its code is the
defect in PW294.

Every string comes from the locale catalogs, `en` and `pt-BR`, chosen by `[review]
language`, as the review page does (PW287). The window is local only: no account, no
remote store (non-goal: a hosted service). Its tests run under `python tools/gate.py`
beside pytest, so one gate covers both halves.

### §PW304 Each item seen with what it was held to

This is the browsing half of the window. On the left is the inventory, grouped by kind,
and filterable by what needs a person: a pending verdict, an outdated record, an open
revision. On the right is one item.

Each kind gets the viewer that fits it:
- a picture at its real size, with its gate lanes (PW175);
- a mesh as the turntable the rig already bakes (PW176), never a live 3D editor;
- a sound or music cue with a player, and the loop played looped (PW256);
- a clip as its curves;
- a line with its speaker and the world canon it is held to;
- an effect through `vfx.preview`.

Beside the viewer is `asset.brief` read back in words. It shows each predicate with its
bound and where the bound came from, the last measures, the provenance chain up to its
purchase (`provenance_generated`), and what was made from it (`provenance_dependents`).

Nothing on this view writes. The files it shows come through the operations or the
review server's `/file` route, which already refuses anything outside the project. A
render or preview that does not exist yet is offered as the operation that would make
it, run by the agent session and never by the window. Only then is the view a reader and
not the graphical editor the non-goals rule out.

### §PW305 One verdict path, whichever surface a person uses

`review.py` and `review_page/` already do the hard part of a verdict. They lay a sitting
out old beside new. They lay out kept and refused lanes, a canon board, and a sound
played beside the one it replaces. They take the choices with a consequence per choice,
in the project's language (PW287). They keep masks tied to a digest, and an accept may
carry no comment (PW288). They redraw only what changed (PW289), and they read sittings
from before PW287 through the catalog (PW293). Each of those was a defect found on a
real owner's screen.

A second implementation in React would have to find every one of them again. So the
window does not rebuild the sitting view. It hosts the review page for the open project
in a sandboxed view: the same server, the same `/api/judge` with its `X-Polyweave`
header, the same `answers.jsonl`. The window's own inventory then links an item to the
sitting that holds it.

Where the page needs a change to sit inside the window, such as a route for one sitting,
a link out to an item, or the theme, that change is made in `review_page/`. That keeps
the browser-only path and the window the same code. The review server's lifetime then
follows the window's held server, which also closes PW294's stale-code case for a person
using the window.

### §PW306 A Claude Code session opened on one item

The person looks at an item, marks where it is wrong if it is a picture (the PW174 mask)
or a sound (a time range), and says what should change. The window writes that as a
revision and opens a session on it.

The mechanics are roadkeep's (RG273). The Agent SDK's `query()` runs the person's own
`claude` binary, found on PATH and then at its install locations, and never the SDK's
bundled one. The session uses the `claude_code` preset and the user, project and local
setting sources, so the project's CLAUDE.md, the polyweave skill and its MCP server are
the ones a terminal session would have. The session's first message is built from
`revision.open` and `asset.brief`: the item, the digest the person saw, their words, the
bounds, and what depends on the item. It is not a prompt the window wrote freehand.

The window shows the session as a conversation beside the item. Every raw message stays
readable, and a permission request is answered in the window (`canUseTool`). The person
can keep talking to it to refine, explain or add technical detail, and each turn is kept
on the revision.

One session belongs to one revision. Two revisions on one item are two sessions, and the
second waits while the first holds the item. That gives the isolation asked for: each
improvement is made, seen and judged on its own.

### §PW307 The harness that keeps a revision honest

A session left alone does what a chat does: it changes a file and says it is better. The
harness is what makes a revision a polyweave loop.

1. **Start.** It opens a loop run against the revision (`loop.start`), so the change has a run, a ledger line and a budget.
2. **After every write.** When the session writes the item's artefact or declaration, the window runs the item's own checks, not the agent's choice of them. That means `accept.check` against its spec, or `words.check`, `sound.measure` or `geometry.compare` by kind. It shows the result beside the change, old and new, with each predicate's bound. The session hears the same result as a hook message, so it cannot skip it.
3. **When it thinks it is finished.** It must lay a sitting out (`verdict.sitting`, `sound.sitting` or `words.sheet`). The window shows it through the review page (PW305).
4. **Closing.** The revision closes only when the person answers it. A `look` or `number` answer goes back to the same session as the next turn.

The session's tool list leaves out `verdict.judge` and `verdict.promote`, and the
harness refuses them if called (non-goal: an agent accepting its own look). A question
the agent needs answered, such as "warmer rim or brighter?", reaches the window as an
ask. The harness is a Claude Code hook plus settings the window passes, so a terminal
session on a revision gets the same one.

### §PW308 A revision spends only what a person weighed

"Make this picture different" can be answered by a local re-fit, or by `picture.buy`,
`mesh.buy` or `sound.buy` against a real balance. The purchase ceiling (Block D) bounds
how much an agent may spend. But a session opened from a click can burn through that
ceiling one small buy at a time while the person is looking at something else. That is
the spend-on-its-own-judgement the non-goals rule out.

Every tool that draws on a balance is marked in the operation registry, and the window reads that mark instead of keeping its own list. In a revision session the window answers `canUseTool` for such a tool by stopping and showing:
- the call;
- the service's price for it, from `purchase.find`;
- what `purchase.remaining` leaves under the ceiling;
- the revision it is for.

Only an explicit yes lets it run, and the yes is for that one call. The window never
offers "always allow" for a paid tool, even though Claude Code does for other tools. A
local alternative, a re-fit or a variation from the existing parent (`picture.vary`), is
named beside the price when the item has one, because the cheaper path is often what the
person meant. Each purchase is tied to the revision in the ledger, so the credits a
change cost appear on its closed record.

### §PW309 A revision stays inside the item it was asked about

The point of opening a change from one item is that the change is about that item. What
a change to it may legitimately reach is already known. The provenance graph gives the
item's dependents: a picture's dependents are the meshes modelled from it, a palette's
dependents are every picture of that family. The inventory gives the item's own
declaration, spec and artefact. Everything else is outside the revision.

While the session runs, the window watches the project root recursively, as roadkeep's
session watch does (RG247). A write inside the scope passes. A write outside it, for
example a shared palette in `polyweave.toml`, a second family's canon, or a script in
the game, pauses on a question in the window. The question names the file and why it is
outside ("this is the style family every hull picture is held to"). The person can allow
it once, or tell the session to find another way.

When the revision closes, its record lists every file the session touched. Each
dependent that `provenance_outdated` now marks is either re-checked by the harness or
listed as waiting. So accepting a change to one item never silently leaves ten others
out of date. This is also what makes a later `git` commit of one revision a clean one,
though the window itself runs no git command.

### §PW310 The window follows the project as it changes

A project changes under the window in several ways. A revision session writes, an agent
in a terminal runs a fit, the person edits a declaration in their editor, or `git
checkout` swaps half the tree. A window that shows the state it read at open time
invites a verdict on a picture that is no longer the one on disk. That is the same
failure the digest on an answer exists to catch.

The window watches the directories that hold what the inventory lists, plus
`.polyweave/answers.jsonl`, `revisions.jsonl` and `sittings.json`. It watches
directories, not files, so a file that did not exist yet, or one rewritten by rename, is
still caught, as roadkeep's governed watch learned. A burst of events becomes one
re-read of `project.inventory`.

Rows are keyed by the inventory id and redrawn only where the digest moved. The open
item is redrawn only when its brief's digest changed, and never in the middle of an
answer. The review page learned this the hard way (PW289): redrawing everything every
few seconds lost a click between two. An item whose artefact changed while the person
was looking at it is marked as changed, with old and new offered side by side, instead
of swapped silently.

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
