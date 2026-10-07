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

### §PW316 A UI panel built from a declaration

Met in starship (RK151): the menus need holo-glass panels, a bevelled edge, corner
brackets, scan lines and an accent tick, each with focus, pressed and disabled states.
`describe` had nothing for it, so starship hand-wrote `game/ui/kit/holo_panel.gdshader`
and held it only by a verdict on screenshots. RK156 did the same for a screen wipe, a
bowed sweep and an iris timed by a progress uniform, in `game/ui/kit/wipe.gdshader`.

Landed (docs/specs/panel.md): a `*.panel.toml` declares a frame's fill, cut, edge,
brackets, scan lines and states, and `panel.build` draws each state to nine-patch PNGs
with records, plus a `StyleBoxTexture` with the margins. A corner reaching past the
margin is refused.

Left: build the same declaration to a Godot canvas shader with its uniforms, which is
where an accent mark mid-edge belongs, since a nine-patch would stretch it. Then declare
a screen wipe, build it to a shader, and capture it at each progress step so a spec can
hold the steps. Starship's two hand-written shaders are then replaced by built ones.

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

### §PW331 A declared icon set, built and accepted

Met in starship (RK147): every prompt names its button in words (A, RB, CROSS, OPTIONS,
LS DOWN, SPACE), and the owner wants the button drawn as the player sees it on the pad.
`describe` lists no operation that makes a set of small 2D icons, and the project may
not draw them by hand. Nothing was built; RK147 waits on this line.

What the game needs, per layout (Xbox, PlayStation, a generic pad, and keycaps for the
keyboard): the face buttons in their own colours (green A, red B, blue X, yellow Y; the
cross, circle, square and triangle), shoulders and triggers as their shapes, the two
menu buttons, the sticks and their clicks, and the D-pad directions. The premise asks
for detail: a lit rim, shading, the symbol in its colour and a dark outline that reads
over a bright scene, never a flat disc with a letter.

What polyweave should do: build a declared icon set (each icon a base shape, its fill,
rim, symbol and outline, from a small set of primitives) into PNGs at stated sizes, or
one atlas with a map of names, each recorded with the declaration as input. An
acceptance spec per set holds legibility at the smallest size (contrast against light
and dark backgrounds, the symbol's share of the face), and a sitting puts each set in
front of a person.

Done when starship's three pad sets and its keycaps build from a declaration, pass their
specs and wait in a sitting.

### §PW336 Text that fits, read off a held screen

Met in starship (RK166). The design asks that every screen, captured in pt-BR, be held
with `accept.check_screen` so no text leaves its box or overlaps another. That operation
holds an asset's spec to where the asset stands in a capture, and has no predicate for
text. Nothing in `describe` reads a running screen's labels and says whether each fits.

The worker drove each screen through `game.open`/`game.call`/`game.shot` and looked at
the pictures. Three faults were found by eye: the options' sixteenth row sat on the
panel's bevel, the title's help line read through the options' help line, and a crew
card wrapped "MARA ·" / "ENFERMEIRA" with the dot left at a line's end. Each was fixed
in layout, but only a person's eye found them, and the next string change can bring them
back unseen.

What polyweave should do: a `game.text_fit` (or a predicate on a held session) that
walks every visible Label and Button in the tree and answers, per node, its text, its
drawn size against its rect and its container's, how many lines it took against how many
it was laid out for, and any other text whose rect it overlaps on screen. It runs per
locale, so a project sweeps each screen in each language and a finding names the key.

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
ring), with cuts and holds. Plus an export the engine plays (a Godot Animation resource
on a Camera3D, with its record), and a capture per shot so a person accepts the framing
on the review page.

### §PW373 A shot that says when it was not written

Met in starship (RK190), shooting a cutscene's frames through a held game: `game.batch`
with `{"cmd": "shot", "out": ".polyweave/shots/opening/0.png"}`, where the folder
`opening/` did not exist yet. Every shot answered `{"out":
".polyweave/shots/opening/0.png", "size": [1280, 720]}` with `"errors": []`, and no file
was written. Only the session's log said so: `ERROR: Can't save PNG at path:
'.polyweave/shots/opening/0.png'` from the driver's `_shot`. The worker learned it when
`compose.sheet` refused the first tile as missing, then made the folder by hand and
drove the whole sequence again.

What polyweave should do: `game.shot` makes the folder `out` names (as every other
operation that writes does), checks that the file exists after the save, and where it
does not, answers a refusal (`driver.shot-not-written`) carrying the engine's error,
never an `out` for a file that is not there. A test shoots into a folder that does not
exist yet and expects the file.

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

### §PW334 An @file read past its byte order mark

Met in starship (RK157), laying out a sound sitting from Windows PowerShell 5.1. A list
parameter cannot be passed inline there (the shell eats the JSON's quotes, which the
refusal says), so the remedy offered is a JSON file: `--members @members.json`. The file
was written with `Set-Content -Encoding utf8`, which in Windows PowerShell 5.1 always
writes a UTF-8 byte order mark, and the call came back:

`op.bad-type: --members names ...members.json, which is no JSON file: Unexpected UTF-8
BOM (decode using utf-8-sig)`

The file was valid JSON in every other respect, and the error itself names the fix. The
worker rewrote the file through another tool to drop the mark.

What polyweave should do: read an `@file` argument (and any JSON or TOML a declaration
names) as `utf-8-sig`, so a leading mark is skipped, since on Windows the shell's own
way to write UTF-8 is the one that adds it. A test writes the file with a BOM and
expects the list back.

### §PW337 An @file for every structured parameter

Met in starship (RK166), laying out a sitting from Windows PowerShell. `verdict.sitting`
takes `--families`, a dict. Inline JSON loses its quotes in that shell (PW247's case),
and the remedy PW247 gave lists, `@file.json`, is refused for a dict:

`op.bad-type: --families is a dict, and '@C:\...\ptbr_families.json' does not read as
one` `do: pass it as JSON, such as {"a": 1}`

The file held valid JSON. The worker went round it through the MCP tool, which takes the
object as it is. A CLI-only worker in PowerShell has no way to pass a dict at all.

What polyweave should do: read `@path` for every structured parameter (dict as well as
list), with the same refusal text naming the file when it is not JSON, and say in the
`do:` of a dict's refusal that `@file.json` works.

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

### §PW332 A verdict that lands from the CLI

Met in starship (RK143, RK144), carrying the owner's acceptance of three voxel enemies
given in chat.

What happened, through the CLI:

- `verdict.judge --run '<json from loop.start>'` answered "recorded in the open run",
  but the run is a dict in that process: the verdict was appended to a copy that died
  with the call.
- `loop.finish --run '<the same json>' --accepted true` then appended a run with no
  verdict, said `accepted: true`, and `loop.pending` still showed the asset with
  `judged: null`, waiting.
- `verdict.judge` with no run answers "not recorded: no run was open", which is honest
  but leaves the person's words nowhere.

The workaround was a Python snippet calling `loop.start`, `verdict.judge` and
`loop.finish` in one process.

What polyweave should do: keep an open run on disk (under `.polyweave/`), addressed by
its id, so `verdict.judge --run <id>` and `loop.finish --run <id>` work across calls;
and let `verdict.judge` open and close a run itself when none is named, so a verdict
given in a conversation lands in the ledger in one call. `loop.finish` with `accepted`
and no verdict should be refused, or record the acceptance where `loop.pending` reads
it.

Done when one CLI call carries a person's accept into the ledger and `loop.pending`
shows the asset judged.

### §PW338 A member nothing holds says so

Met in starship (RK166). A sitting of plain screen captures was laid out with
`verdict.sitting`, its members given a `name` and `new` and no `spec`, since no spec
holds a screen's text yet. The answer marked every member `"passed": true, "failed": []`
and offered the choice "the look is right and the spec agrees with it".

No spec was checked, so "passed" claims a measurement that never happened. A person
reading the sheet, or an agent reading the answer, takes the screens to be held by
something.

What polyweave should do: a member without a spec answers `"passed": null` (or
`"checked": false`) with a line saying nothing holds it, the sheet draws it as unheld
rather than green, and the choices drop the spec's wording ("the look is right") for
such a member.

## Block P — Music and sound a game can ship

### §PW192 Cottony's audio made through polyweave

The block is proven when its first consumer uses it. Cottony's music and effects are
declared in its `polyweave.toml`, made by `music.render` and `sound.synth`, and held to
`*.accept.toml` bounds, and its own audio scripts are removed. Anything Cottony needs
that a second game would not becomes configuration.

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

### §PW333 An effect declared at a note

Met in starship (RK157): the menu's interface sounds (move, confirm, back, refused, tab,
open, close) are to be "tuned to the theme's key", A minor, so a confirm lands on a note
of the title music under it. An effect in `*.sfx.toml` takes sfxr's own parameters:
`base_freq` is a number from 0 to 1, `freq_ramp` a slide per sample, `arp_mod` a period
multiplier. Nothing in `describe` or in `sound.synth`'s answer says which pitch they
make.

To place a sound on a note the worker read `src/polyweave/sfxr.py` and worked out that
the pitch is 3528 x (base_freq^2 + 0.001) Hz at 44.1 kHz with 8x supersampling, then
converted each note by hand (A5 is 0.4984, E5 0.4311), the arpeggio's jump from
`arp_mod` (a fourth up is 0.528, a fourth down -0.183), its timing from `arp_speed`, and
a slide of one octave over a duration from `freq_ramp`. The numbers sit in starship's
art/audio/interface.sfx.toml with the notes in comments, and nothing checks them.

What polyweave should do: let an effect declare its pitch as a note or Hz (`note =
"A5"`), its arpeggio as an interval and a time (`arp = { to = "E5", at = 0.05 }`), and a
slide as a target and a duration, compiling them to sfxr's parameters; and have
`sound.measure` answer an effect's fundamental, so a spec can bound a sound to a key's
notes.

## Block Q — Words held to the world

### §PW335 Glyphs a string table needs and its fonts lack

Met in starship (RK166), holding every screen of the game to its Brazilian Portuguese.
The design asks that every character of every pt-BR cell exist in the font its Label
draws with, and says to file a PW line where polyweave cannot answer it. `describe` has
no such operation: `words.check` holds the table to the world's names, `picture.letters`
reads lettering off a picture, and neither opens a font.

The worker read both of the game's fonts once with fontTools from a throwaway command
(Nunito lacks "▶"; Orbitron lacks "·" and "▶"), and the game's own check now asks
Godot's `Font.has_char` for every character of the table, upper case included, against
every font the game ships. That is a font analysed inside the project, which is the
workaround to retire.

What polyweave should do: `words.glyphs` (or a predicate of `words.check`) that reads
the `[words] table` and the fonts the project declares (a `[words] fonts` list, each
with the keys or text styles it draws), and answers, per font and locale, every
character a line needs and the font lacks, with the keys that use it. Upper case counts,
since a game may upper-case a line at draw time. A missing character is a finding, so
the gate goes red before a player sees a box or a borrowed system glyph.

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

### §PW328 Frames and contact sheets from a reference video

Found in starship (RK178): the owner wants Resogun's first phase rebuilt from a gameplay
video as a proof of concept, so the gaps in starship's wave format and enemy behaviour
show up against a known-good level.

`describe` has nothing that takes a video in. The workaround is ffmpeg called directly
(`ffmpeg -i <video> -vf fps=2 <dir>/%05d.png`), then an agent reads the frames. That is
analysis of an artefact done outside polyweave.

What polyweave should do:

- **`reference.frames`**: from a video path, sample frames at a rate, or denser inside named time ranges, into the work area, each frame named by its timestamp, with a `.prov.json` that records the source video's hash, the rate and the ranges. The video is never copied into the project.
- **Cheap reading.** A contact sheet per stretch (say a 4x4 grid of 16 frames with timestamps burnt in), so an agent reads 16 seconds of play as one image instead of 32 reads. A crop option (the radar strip at the top of a Resogun frame, say) gives a second sheet of just that region.
- **Change detection**: optionally keep only frames that differ from the one before by more than a bound, so a quiet stretch costs nothing.

The transcription itself (what spawned, where, on what path) stays the agent's and the
owner's work. polyweave only makes the frames cheap and recorded.

### §PW330 Pressure per second from weighted events

Met in starship (RK176): the owner finds the waves unbalanced, and nothing says how hard
a second of a phase is. §PW205 covers enemies alive at once and a weighted total for a
compiled `.tres`, but starship's waves are now authored `.waves.toml` files with
`times`, drawn shapes and rails, and it needs a curve, not a total.

What polyweave should take: a list of weighted events on a timeline, each `{second,
kind, weight, until}`, where `until` is the end of the wave it belongs to (the game
writes these; it alone knows its own format). What it should answer, per second:

- the threat that enters;
- the threat alive in the two bounding cases, every enemy killed the moment it lands
  (after a declared warp-in) and nothing killed until its wave's end;
- the longest gap with nothing to shoot, against a declared window (starship's
  multiplier window is 2.5 s), and every gap past it.

Two versions of one timeline should lay side by side, so a change is compared with the
one before it, and the result should be a record with provenance like any other.

Starship's thin workaround until this lands: `WaveFile.events` writes the events, and
`dev/pressure.gd` computes the curves and the gaps from them, with weights from
`game/waves/threat.toml`.

Done when starship's `dev/pressure.gd` is deleted and its check calls the operation.

## Block S — Playing the game, not only rendering it

### §PW339 A held game in the declared environment

Met in starship (RK166). The project's `[capture]` declares `resolution = [1920, 1080]`
and `locale = "en"`. Screens were driven with `game.open` (display true), `game.call`
and `game.shot`, and every shot came back `"size": [1280, 720]`: the window override in
project.godot, not the declared resolution. The locale was the machine's (pt_BR), not
`[capture]`'s either. Nothing in the answers said the environment differed from the one
the project declares, so a picture for a fit check was at the wrong size without notice.

`capture.run` states and checks that environment, but it runs a script to its end and
cannot hold a game between calls.

What polyweave should do: `game.open` takes `[capture]` as its default environment
(resolution and locale, overridable per call), applies it the way `capture.run` does,
and `game.shot` answers the environment it was taken in beside its size, so a shot at
the wrong one is visible in the answer.

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

The same gap holds inside one project: starship keeps Godot out of art/ and the export,
so its accepted store logo and icon (RK150, RK188) are copied by hand into
game/ui/brand/ with no record; the operation should take a source path in this project
too.

Workaround: the PNG is copied by hand to `game/ui/brand/viglet_games_badge.png`, and
`game/ui/splash.gd` names its source in a comment.

## Block U — A window on everything a project governs

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

Landed: `core`, and `shell`'s held servers, run by the gate. Left: Electron and `ui`.

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

## Block V — Parts every game repeats, installed already proved

### §PW340 The kit contract

Met across Starship and Cottony: both games wrote their own controls, settings and save
code. Starship's game/core/bindings.gd names pad buttons in text for Xbox, PlayStation
and a generic pad, with no Switch layout and no icons; Cottony has its own
scripts/settings.gd and scripts/save_file.gd. An agent starting a third game writes them
a third time, and what costs it is not the typing but the details only a run reveals (an
orphaned focus neighbour, the Switch's swapped face buttons, a filter that leaves a
resource out of the export), which nobody but a person at the screen can confirm today.

What polyweave should do: a spec, docs/specs/kit.md, for a kit as a unit that lives in
this repository under kits/<name>/ and carries a kit.toml (what it declares, installs
and depends on, and its version), a core copied into the project's
res://addons/polyweave/<name>/ and never edited there, a scene the project owns once
installed, and the acceptance spec that proves it in the game it lands in.

The contract every kit keeps is five steps: read the project, propose the declaration,
install, prove, answer ready to decide. An agent's whole share is one call and one
reading of the answer; a question left over is a person's decision, never an analysis
for the agent. A kit carries no palette or theme of its own and assumes no genre.

### §PW341 Installing a kit in one call

The format of §PW340 says what a kit is; this is the operation that lands one.
`kit.install <name>` reads the project (project.godot's renderer and main scene, the
InputMap, export_presets.cfg, which kits are already in), writes the declaration it
proposes into the project config only where the project has none, copies the core into
res://addons/polyweave/<name>/ and the scene where the declaration says, and records the
kit and its version in the provenance record, so provenance.read answers what the
project carries and from where. It installs first whatever kit.toml names as a
dependency.

Then it runs the kit's own acceptance spec through accept.verify in the real game, and
answers in the shape the tool surface spec asks of every operation: ok or the first
finding with its remedy, the points of the scene meant to be changed, and any question
that is a person's to answer (a verdict, a budget), never a file for the agent to read.
A dry run (`write=false`, as project.init has) answers the same without writing
anything.

An installed kit is then part of the project's own gate, so a later change in the game
that breaks it fails there and not in front of a player.

### §PW342 Every kit proved in polyweave's own gate

A kit is worth more than a snippet only while its proof holds, and a proof that runs
only after install finds a broken kit in the consumer's tree. Each kit under kits/
should carry a fixture, a minimal Godot project shaped to exercise it, and tools/gate.py
should install every kit into its fixture and run the kit's acceptance spec headless
against the Godot that godot.install fetches, saying per kit which held, which failed
and which skipped for want of an engine, as the gate already says for the engine tests.

A Godot upgrade in polyweave then re-proves every kit at once, which is what keeps a kit
from rotting the way a copied snippet does. The fixture is also where a kit's
dependencies are exercised together, the settings kit with the input and audio kits
beside it, so a kit that only works alone is found here and not in a game.

### §PW343 An installed kit that has fallen behind

The provenance record of §PW341 names the kit and the version a project carries.
provenance.outdated should name a kit whose version in polyweave is newer, with the
changelog lines between the two.

`kit.update <name>` replaces the core, which the project never edits: a core whose hash
differs from the version recorded is a finding naming the files, never an overwrite. It
leaves the scene alone, since the project owns it, and lists what the new version
changed in its own copy of the scene for the agent to carry over. Then it re-runs the
acceptance spec, so an upgrade lands proved or not at all.

A project whose own fix belongs in the kit files it through the polyweave-friction
skill, which is how a kit gets better from use: the fix ships as a new version here, and
every other game that carries the kit hears of it from provenance.outdated rather than
by luck.

### §PW344 Button prompts for the pad in the player's hands

Met in Starship: game/core/bindings.gd holds a GLYPHS table for xbox, playstation and
generic, each button a text label ("CROSS", "LB") picked from the pad's name. There is
no Switch layout, whose face buttons sit swapped, and no image.

The kit reads the project's InputMap, declares the families the game supports (xbox,
playstation, switch, keyboard and mouse), and installs a prompt service that knows the
family in use from Input.get_joy_name and the last event, switches live when the player
picks up another device, and draws an action's binding as an icon: a node for menus and
a RichTextLabel tag ([action=jump]) for tutorial text.

The icons are a declared set. A CC0 set ships with the kit (Kenney's input prompts), and
the declaration can point at another, since console certification asks for the platform
holder's own glyphs, which this repository must never carry.

Proof: every action has an icon in every declared family; a game.input from another
family changes what is drawn; an icon's legibility over its backdrop is held by
measure.contrast.

### §PW345 Rebinding the controls

Starship's game/core/bindings.gd is the source. An action's binding is stored as codes a
settings file can hold (key:<physical keycode>, button:<n>, axis:<n>:<-1 or 1>); keys
and pad are two halves replaced independently; a code another action already holds is
swapped, never shared; a reset goes back to the declared defaults; and the stick's
deadzone and inverted vertical sit beside them. What is Starship's own, its actions and
its twin-stick fire, becomes the declaration.

The kit installs the binding store and a remap screen built on the prompt service of
§PW344, so every binding is shown in the icons of the device in use.

Proof, driven through the game: open the screen with the pad alone, rebind an action,
press the new button and query the InputMap; rebind onto a code another action holds and
see the swap; restart the game and find the binding kept; reset and find the defaults.

### §PW346 Menus a pad can drive

A main menu, a pause menu and a yes-or-no confirm are in every game, and the failure
that costs is silent: a control no focus neighbour reaches, a back button that follows
one platform's convention on all of them, a pause that leaves the game ticking
underneath. The kit installs those three screens on the prompt service of §PW344, with
back and confirm bound to the convention of the family in use, and pauses through the
scene tree's pause and each node's process mode.

Proof: a walk of every focusable control by pad events alone reaches each one and comes
back; back from every screen lands where the declaration says; the game's own time does
not advance while it is paused.

The look is the project's Theme, never the kit's. A panel, a frame or a stylebox the
menus draw is §PW316's to declare and build, so this kit owns the behaviour and nothing
of how it looks.

### §PW347 An options screen assembled from the kits

Cottony's scripts/settings.gd and Starship's SettingsStore, fed by the options() rows in
bindings.gd, are two versions of one thing. The kit installs a settings store in
user://, versioned so that a key renamed in a later build migrates, and an options
screen whose tabs are contributed by the kits present: controls from the remap kit of
§PW345, and audio, language, accessibility and graphics from their own kits in this
block, plus any rows the project declares for itself. A kit that contributes a tab
declares it in its kit.toml, so this screen names no kit it does not find installed.

Proof: every row changes what it says it changes, read back in the running game after
the change (a bus volume, a window mode, a locale); every value survives a restart; an
unknown or renamed key in an older file is kept or migrated, never a crash and never a
silent reset of the player's choices.

The screen is navigable by pad through the menus kit of §PW346, so it inherits that
kit's focus walk as part of its own proof.

### §PW348 Saves that survive a crash and an update

Cottony has scripts/save_file.gd and tests/save_test.gd, its own answer to a question
every game asks. The kit installs a save service with slots; it writes through a
temporary file and a rename, so a crash mid-write leaves the last good save in place; it
carries a schema version with migration functions the project declares; and it falls
back to the previous save when the current one fails to parse.

What is saved is the project's: the kit takes a dictionary from the game and never names
a field, so it fits a puzzle game and a shooter alike.

Proof, all automatic: stop the game between the write and the rename and load the old
save; corrupt the file and open the game; load a version-1 file into version 2 through
the declared migration; fill every slot and read each back. None of it needs a person,
which makes this one of the cheapest kits to keep proved.

### §PW349 From launch to the first menu

Cottony has scripts/splash.gd, and every game has some version of it. The kit installs a
declared splash sequence (logos and their durations), skippable by any button of any
family, followed by a threaded load (ResourceLoader.load_threaded_request) into the main
scene, and a scene transition service with a loading screen that every later change of
scene goes through.

Proof: the time from launch to the main menu is measured and held to a declared budget;
a skip from each declared family ends the splash; no frame during a transition exceeds
the frame budget, read from frame times at a percentile and never at a mean, so one long
hitch is not averaged away by a hundred short frames.

The logos are the project's and so is the look of the loading screen; the kit owns the
order, the timing and the threading.

### §PW350 A credits screen from the provenance record

provenance.credits already answers, from the record, who made what and under which
licence. The kit installs a credits scene that reads a file generated from that answer
at build time, beside the people and roles the project declares, so the screen lists
exactly what the game ships and nothing it no longer does.

Proof: every record whose licence requires attribution appears on the screen; nothing is
listed that the record does not hold; the scene scrolls at a declared rate and is
skippable by any family. A generated file older than the record is a finding, so an
asset added after the last build cannot ship uncredited.

It is the cheapest kit in the block, since the answer it draws exists already, and the
one whose failure is a legal one rather than a bug.

### §PW351 The audio runtime a game needs

Cottony has scripts/music.gd and scripts/sound.gd, its own version of what every game
with sound writes. The kit installs a declared bus layout (Master, Music, SFX, UI and
Voice by default), a music player that crossfades between tracks and ducks under voice,
a pooled sound player with pitch variation so a repeated sound does not machine-gun, and
UI sounds wired to the menus kit's focus and confirm.

Proof: each bus exists and routes as declared; a crossfade leaves no gap and no
clipping; sound.measure holds each bus's loudness to its declared target in a captured
scene, the same measure Block P holds a track to, so a track mastered right cannot be
made wrong by the bus it plays through.

The bus volumes are what the settings kit of §PW347 shows as an audio tab, which is why
the layout is declared once here and read there.

### §PW352 The string table on screen in every language

Block Q checks a string table against the world the person declared, and §PW335 finds
the characters its fonts lack. Neither puts the table on screen. This kit is that
runtime half: it loads the [words] table into Godot's TranslationServer, installs a
language selector for the settings kit of §PW347, sets fallback fonts per script (CJK,
Cyrillic, Arabic) as the project declares them, and picks the system locale on first
launch when the game supports it.

Proof: switching to each locale changes every visible label of a captured screen; no key
ever shows its raw name; with §PW335, no character falls to a box or a borrowed system
glyph; a line that grows in translation still fits its control, measured on the capture
rather than assumed.

The words themselves stay the project's and the person's, held by Block Q; the kit only
carries them to the screen.

### §PW353 A dialogue box

Cottony has scripts/dialog.gd. The kit installs a dialogue box that types a line at a
declared rate, completes it on the first press and advances on the next, by the confirm
button of the family in use (§PW344), with an optional portrait and speaker name,
reading each line by its key from the string table so that a translation needs no change
here.

Proof: every line of a declared sequence is reachable by pad alone; a skip completes a
line without dropping any of it; the text fits its box in every locale, measured on a
capture, which is where a longer translation overflows without anyone noticing.

The kit carries no line of its own and orders none: the sequence and the words are the
project's, so it never comes near "Writing a game's story for it".

### §PW354 Flashes counted in a capture

Guidance on photosensitive seizures (WCAG 2.3.1, and the Harding test broadcasters use)
limits a sequence to three general or red flashes in any one second, a flash being a
pair of opposing luminance changes beyond a threshold over a large enough area of the
screen. capture.movie already records a run of the game; nothing reads that recording
for this.

What polyweave should do: measure.flashes over a capture, answering the worst second,
the count of flashes in it, the share of the screen involved and the frame where it
starts, with the threshold and the area taken from the guidance by default and
overridable in the project config.

It is a measure, so an acceptance spec and the accessibility kit can both hold a game to
it. It certifies nothing beyond the run it measured, and its answer says so: a flash in
a scene nobody captured is not found.

### §PW355 Accessibility options with their effect measured

The kit adds an accessibility tab to the settings kit of §PW347: a text scale applied
through the project's Theme; colourblind filters as a full-screen shader (protanopia,
deuteranopia and tritanopia, as simulation and as correction); subtitles for the lines
the voice bus plays; a switch for screen shake and for flashes, which the game's own
effects consult through the kit; and hold-or-toggle for held actions.

Proof: at the largest text scale no label overflows on a captured screen; the colour
pairs the project declares must stay apart stay apart under each filter, by
measure.contrast; with flashes switched off, measure.flashes (§PW354) finds none over a
declared run; with shake off, the camera's offset stays at zero through a declared run.

A filter or a scale is measured, never judged by the agent; whether the result still
looks like the game is a person's verdict, as every look is here.

### §PW356 A pad that leaves, a window that loses focus

When a joypad disconnects mid-game (Input.joy_connection_changed), the kit pauses the
game and says whose pad left, in the prompts of that pad's family (§PW344); it resumes
when the pad reconnects or another pad confirms. When the game's window loses focus it
pauses too, unless the project declares otherwise, as a game meant to run in the
background would.

Proof, driven: a simulated disconnect pauses the game and shows the prompt in the family
of the pad that left; a reconnect resumes it; a focus-out pauses it and a focus-in
leaves it paused until the player says so. Starship's local co-op is where two pads make
the first of these matter most, since the wrong player's pad leaving is the case a
single-player test never meets.

### §PW357 A second player on the same machine

Starship's game/core/coop.gd and the coop_device kept in bindings.gd hold a second
player's pad apart from the first one's, and a rebind there keeps the two pads apart.
The kit installs a join flow (press to join on any unassigned pad), a device-to-player
map the input layer filters every event by, and per-player bindings through the remap
kit of §PW345.

Proof, driven with two simulated pads: both join as two players; an event from one never
moves the other; a rebind on one leaves the other's bindings alone; a leave frees the
pad for the next to join; with the pad lifecycle kit present, the pad that disconnects
is named as that player's.

How many players a game takes, and what a player is in it, are the project's
declaration; the kit assumes neither a genre nor a split screen.

### §PW358 A project that imports and parses clean

Godot 4 refers to resources by UID, and since 4.4 a script carries a .uid file beside
it. Moving a file without its .uid, or editing a .tscn as text, leaves a reference that
resolves to nothing until that scene is loaded; a script with a parse error waits the
same way. An agent moves and writes files without the editor open, so it meets both, and
today learns of them from a person or from a crash.

What polyweave should do: a check, part of project.check or an operation of its own,
that imports the project headless, parses every script (--check-only), and reports each
UID or path reference that resolves to nothing, each .uid left without its file, each
.import out of date with its source, and each resource nothing references, every one
with its file and line and the call that fixes it where one exists.

It belongs in the project's gate, and it is the cheapest item in this block for the most
turns saved, since nothing about it needs a person or a GPU.

### §PW359 A game's state declared for reading

game.query reads whatever the driver can reach, but which values matter (the player's
health, the current scene, the enemy count, the seed) lives only in the agent's head for
one session. So it adds a print, runs the game, reads the output and removes the print,
and the next session does it again.

The kit lets the project declare named paths into its state, each a node path and a
property or a method that returns a dictionary, installs an autoload that exposes them
to the driver, and gives game.query those names, so `game.query health` answers without
the agent knowing where health lives.

Proof: every declared name answers in the running game with its declared type, and a
name whose node is gone is a finding naming it. The same surface is what a crash dump
writes and what a determinism check compares between two runs, so it is declared once
and read three ways.

### §PW360 The same run twice

The kit installs a central random service seeded from the declaration or the command
line, which the project's code draws from instead of the global randf, and a record of
input events stamped with their physics frame. A run is then reproducible from its seed
and its record.

Proof: two runs with the same seed and the same input end in the same observable state
(§PW359), compared name by name; a run that diverges is answered with the first frame
and the first name that differ, which usually points at the one call to the global
random someone forgot.

A divergence, or any bug seen once, is then saved with its seed and recording as a
game.keep flow, so game.replay runs it in the gate from then on. That is the step that
turns a report of "it happened once" into a test that fails until it is fixed, without
the agent guessing at the cause first.

### §PW361 What a crash leaves behind

The kit installs structured logging (level, time, physics frame, current scene) to a
rotating file in user://. On an error it writes the last lines beside a dump of the
observable state of §PW359 and, when the determinism kit is present, the seed and the
input record so far. A crash that kills the process leaves the log up to its last flush,
and the next launch notices the unclean exit and packs what is there.

An operation reads such a capture back, from the user:// of this machine or a file a
person sends, and answers the first error, the script and line that raised it, and the
state at the time, so the agent starts from facts rather than from a retelling.

Proof: an error forced in the fixture leaves the capture, and reading it back names the
forced error with its script and line; a process killed mid-run is reported as an
unclean exit on the next launch.

### §PW362 One way to run a game's tests

Starship runs dev/check.gd; Cottony keeps tests/*.gd with its own runner. Each is fine
alone, and each is a thing a new session must discover before it can tell whether its
change broke anything.

The kit installs a headless test runner that finds the project's tests by a declared
convention, adopts the tests that already exist without rewriting them, and answers in
one shape: the counts first, then each failure with its file, line and message, the same
shape polyweave's other answers take. It wires itself into the project's tools/gate, so
running the gate runs the game's tests too.

Proof: the fixture's passing and failing tests are reported as such; a parse error in a
test file is a failure with its line, never a silent skip; a test that hangs is stopped
at a declared timeout and named.

### §PW363 The exported build, launched

game.release_check reads the export presets and a .pck to make sure the driver does not
ship. What it cannot see is a build that fails at run time: a resource an export filter
excluded, an autoload whose script was stripped, a feature the target renderer lacks.
The editor runs from the project folder, so every one of these works there and fails
only in the exported binary.

What polyweave should do: an operation that exports each declared preset for the host
platform, launches the binary, runs a short kept flow (game.keep) through to the main
menu and back out, and answers per preset whether it held, with the log of any that did
not.

The driver must never ship in a release, which is what game.release_check exists to
hold, so the smoke run uses a debug export of the same preset or a driver loaded from
outside the pack, and the answer says which of the two it ran against, since a pass on
the debug build proves less than a pass on the release.

### §PW364 Data tables with a schema

Games keep their tuning in tables: enemies, items, waves, prices. Read as loose JSON or
CSV, a "10" typed as a string or a field misspelled reaches the game and shows as a
wrong number in play, found by whoever happens to notice.

The kit lets a project declare a table, a CSV or JSON file and the schema of one row,
which is the project's own and assumes no genre, so it stays clear of the non-goal on
one genre's level format. It validates every row with schema.validate in the gate, and
generates a typed Resource per table that the game loads, with a reload in a debug build
so a tuned value shows without a restart.

Proof: a row with a wrong type or a missing required field is a finding naming the file,
the row and the column; the game reads a value back through the generated Resource
exactly as declared; a table edited while the debug build runs is picked up by the
reload.

### §PW365 A performance budget the gate holds

Cottony keeps tools/perf/ (board3d_beside.gd, cascade.gd and others), started by hand,
which PW56 names too. Each measures, prints, and leaves the comparison with last week to
whoever remembers last week's number.

What polyweave should do: let a project declare budgets per scene (frame time at p95 and
p99, never a mean, which is the doctrine of Cottony's art pipeline; load time; peak
memory; node count), and an operation that drives each scene through a declared run,
measures, writes a baseline the first time, and answers each budget held or exceeded and
how far each moved from the baseline.

A measure holds only on the machine that took it, and the answer names that machine's
GPU and driver. On it the gate catches a regression; it never certifies a player's
hardware, and a machine with no GPU skips with that reason rather than passing. The
graphics kit's preset search reads its frame times from here.

### §PW366 Graphics presets and a renderer fallback

The kit reads the project's renderer, whether its scenes are 3D or 2D, and which costly
features its environments use (SDFGI, SSAO, volumetric fog, shadows), and installs
presets that touch only what the game uses. For 3D: render scale with Godot's built-in
upscalers (FSR 1 and FSR 2), anti-aliasing (MSAA, TAA, FXAA), shadow and effect quality,
and a frame cap. For 2D: the stretch mode and integer scaling. It picks a first preset
from RenderingServer's adapter vendor and name, adds a graphics tab to the settings kit
of §PW347, and falls back to the Compatibility renderer when Vulkan fails to start.

Vendor SDKs (DLSS, Reflex, XeSS) stay out: their licences keep them from shipping here
and Godot builds in none of them, so a kit per GPU maker would be the wrong unit.

Proof: every preset applies what it declares, read back from the running game; a launch
with a driver forced to fail reaches the menu on the fallback.

### §PW367 Presets found by search

Cottony's render rig shows the cost: every constant of it was found by hand at two
minutes a sample. A graphics preset is the same problem in another place, a handful of
settings tuned until it looks right and runs fast enough on one machine.

With the frame budget of §PW365 and the settings space of §PW366, engine.sweep can
search, for each preset, the combination that fits its declared budget at p95 and loses
least against the native full-quality frame, scored by measure.same on a captured scene.
The answer per preset is its settings, its frame time, its visual loss, and the feature
that costs most on that scene, so a sentence such as "SDFGI costs 5.9 ms here" arrives
without anyone profiling by hand.

How much visual loss is acceptable is taste, so a preset that trades quality for its
budget goes to the verdict page and the agent never accepts it. The search holds for the
machine it ran on, as §PW365 says of every measure.

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

### §PW369 A game born adopted

project.init adopts a tree that already exists, which is the right door for Starship and
Cottony and the wrong one for the next game, which would be created bare and adopted
afterwards with its first weeks of hand-rolled code to undo.

A new game should start from one call that creates the Godot project; the repository's
.gitignore and .gitattributes, with Git LFS for binaries; the project config with
project.init already run; a gate holding the test runner of §PW362 and the hygiene check
of §PW358; and whichever base kits its declaration asks for, typically input, menus,
settings and save, each installed by kit.install with its proof.

Proof: the new project's gate passes on its first commit, project.check reports it
clean, and provenance.read lists every kit it carries with its version. From then on the
game never has a version of these parts of its own to migrate away from.

### §PW370 Starship onto the input kits

The prompt, remap and co-op kits (§PW344, §PW345, §PW357) are extracted from Starship's
game/core/bindings.gd, controls.gd and coop.gd. Starship then adopts them, which is the
decision that every project adapts to polyweave rather than the other way round: its
actions and options become the kit's declaration, its own input code is removed, its
Controls tab becomes the kit's screen under Starship's Theme, and the checks in
dev/check.gd that cover the same ground give way to the kits' acceptance specs.

Whatever Starship needs that the kits lack is filed here as friction and fixed in the
kit, never patched in the game, so the extraction ends with one copy of the code and not
two.

Done when Starship carries no input code the kits provide, its gate passes on the kits'
proof, and provenance.read names each kit with its version.

### §PW371 Cottony onto the settings and save kits

Cottony's scripts/settings.gd, and scripts/save_file.gd with tests/save_test.gd, are a
second instance of what §PW347 and §PW348 provide, written without either kit in mind.
Moving Cottony onto them proves the kits against a game they were not extracted from,
which is the non-goal on one project's palette, rig or paths compiled in, checked in
practice rather than asserted.

Players' existing save files must load through the kit's declared migration, so no one
loses progress on the update that swaps the code; that is part of the proof, not a
follow-up.

What Cottony needs that the kits lack is filed as friction and fixed in the kits. Done
when Cottony carries neither file, its own save test is replaced by the kit's
acceptance, a save written by the current release loads after the swap, and its gate
passes.
