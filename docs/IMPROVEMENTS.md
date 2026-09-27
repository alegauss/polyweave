# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

### §PW264 A purchase picks the service that sells the thing

Found in Starship (2026-09-27, RK97). The project declares two paid services: Meshy,
which sells meshes, and Ideogram, which sells pictures. `mesh.buy` without `--service`
refused with `fetch.service-unnamed`, although only one of the two can sell a mesh. A
service's schema already says what it sells. `mesh.buy` should pick the one service that
sells meshes, and `picture.buy` the one that sells pictures, and ask only when two
could.

Done when `mesh.buy --picture_path ...` in Starship picks Meshy on its own.

## Block E — One world with the engine

### §PW245 The engine takes the declared size

Found in Starship's RK68 (the codex), 2026-09-27. `capture.run` with the default
`[capture] resolution = [1920, 1080]` ran `.polyweave/drivers/codex_pages.gd`, which
sets `root.size` from the `resolution=1920x1080` argument, and the answer said `applied:
1280x720`. Starship's `project.godot` sets `window/size/window_width_override=1280` and
`window_height_override=720`, and the window override wins over `root.size`, so every
picture came back at 1280x720. `dev/shot.gd`, the project's older capture script,
applies neither setting at all.

PW25 made the environment declared and checked, but applying it is still each scene
script's own code, and each script has to know how its project's window settings
interact. polyweave knows the resolution before the engine starts: it should put it on
the engine's own command line (`--resolution WxH`, and the window size overrides as
project settings where the engine needs them), so the picture is taken at the declared
size whatever the script does, and a script only has to report what applied.

A data point from the same task: a script that also calls DisplayServer.window_set_size
before setting root.size got 1920x1080 applied and the environment held, so the
engine-side fix is that call or the flag.

Worse (RK131): dev/site_shots.gd sets root.size and prints it, so capture.run answered
holds true at 1920x1080 for a picture that is 1280x720. The environment check believes
the script's own line; it should read the size of the picture it names.

Done when a capture of a project with a smaller window override comes back at the
declared resolution, with no change to the scene script.

### §PW249 A capture that keeps every frame of a shot

Found in Starship's RK81 (2026-09-27): the trailer and short clips need frame-perfect
footage of the game, every frame between two ticks of a deterministic run (a replay, or
a seed and a scripted pilot), at 4K and 60 a second, with the HUD on or off, a camera
path, slow motion still recorded at full rate, and the music track started on the shot's
first frame so the edit can lay it back.

`capture.run` takes one still: it runs a scene script, reads one `expect` line and
checks the environment. Nothing takes a sequence. So the project writes
`dev/capture.gd`, which saves a PNG from the viewport on every rendered frame between
`from` and `to`, and names its shots in `dev/trailer_shots.json`. It has to keep the
frame count, the tick each frame is at, the resolution (PW245 again) and the record of
what was flown, all by hand.

polyweave should own `capture.movie`: run a scene script under the engine's fixed frame
rate (Godot's Movie Maker, `--write-movie`, or its own frame grab), keep the frames
between two marks the script prints, and write one record for the sequence with the
environment, frame rate, count, each frame's tick and the inputs. It should say when a
frame was dropped or the run ended early. Re-taking a shot after an art change is then
one call, and `provenance_outdated` names the shots a changed model made stale.

Done when Starship's shots are taken by `capture.movie` and `dev/capture.gd` only flies
the run and prints the marks.

### §PW251 A frame budget the caller sets

Found in Starship's RK81 (2026-09-27). `capture.run` starts the engine with
`--quit-after 6000` and answers `frame_budget: 6000, bounded: false`, and no parameter
of the operation (`describe` lists script, expect, root, environment, record, strict,
args, until_visible, tries) moves it. A scene script that has to fly a run to a late
moment before its picture (Starship's Mason breaking at tick 6713, the Kiln at 15236) is
killed at frame 6000, before it prints its `expect` line, and the answer would blame the
script.

The budget should be a parameter with a stated range, sized by the caller (a shot's last
tick plus a margin), and `bounded` should say whether the run ended by the budget rather
than by itself, with a `why` naming the budget when it did. `describe` then lists it
beside the rest.

Done when a capture past frame 6000 runs to its own end with the budget passed, and one
cut by the budget says so in `why`.

### §PW260 capture.run records the picture its line names

Found in Starship (2026-09-27, RK132). `capture.run` writes a picture's `.prov.json`
only for the paths `engine.run` lists in `artefacts`, and `engine.run` fills that list
only from the named groups its `produces` argument names. `offscreen.capture` passes the
caller's `how` straight through. But neither the MCP tool `capture_run` nor the CLI
`capture.run` takes a `produces`, so every capture a project runs through the tool comes
back with `artefacts: []` and `records: []`. That happens even when its `expect` names
the picture in an `artefact` group.

This happened with the pattern `captured: (?P<artefact>\S+) (?P<width>\d+) x
(?P<height>\d+)`, the one `offscreen.CAPTURED` uses. The run was ok, and `found` held
`artefact: art/renders/citadel.png`. Nothing was recorded, and the review picture has no
provenance.

`capture.run` should read an `artefact` group in `expect` as the picture, as
`offscreen`'s own probe does, without being asked. It could also take a `produces` list
for scripts that name several pictures. Where `expect` has no such group, the answer
should say that nothing will be recorded rather than answer an empty `records`.

Done when Starship's citadel capture, with that pattern, writes
`art/renders/citadel.png.prov.json` in the same call.

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

### §PW252 A paint that paints nothing is a finding

Found in Starship's RK86 (2026-09-27), declaring the Viglet V
(`art/voxels/viglet_v.toml`) at cell 0.05. Two `paint` nodes, `face: eyed painted blush
where blush_marks` and the smile half of `eyed: arm painted eye where eye_marks and
smile_marks`, took no cell: their marks were cubes 0.05 high, one cell, placed between
cell centres, so no centre fell inside them. The build said `status: built`, `findings:
[]`, and `says` counted "7 materials" where the document declares 8. The only trace was
that count; the face came out with eyes and no smile or blush, found by looking at the
preview.

A `paint` whose `where` covers none of `on`'s cells, or only part of what it lists (one
member of a list covering nothing), is a mistake every time. The build should report it
as a finding naming the node and the member, with the nearest cells of `on` and how far
the mark sits from them. The same holds for a declared material no cell wears, which
should be named rather than left to a count.

Done when the first viglet_v draft reports `blush_marks` and `smile_marks` as painting
nothing, and `blush` as a material no cell wears.

### §PW253 A front view that is the camera's

Found in Starship's RK86 (2026-09-27), building `art/voxels/viglet_v.toml`, an
asymmetric badge whose warm side was declared at +x. The build's preview
(`viglet_v.voxels.png`), view "front, from -z", drew that side on the right. In the game
the model is turned to face its camera, which is the same as a camera standing at -z
looking toward +z, and there +x is on the left, which is where the capture showed it. So
the preview's front view is the model mirrored left to right against a real camera at
-z.

The cost: a symmetric actor never shows it, so the first asymmetric declaration (a
badge, a lettered sign, a face with one scar) is fixed by hand in the wrong direction or
flipped after a capture. Here the declaration's warm side had to move to -x after the
capture disagreed with the preview.

Either draw the front view as a camera at -z sees it, or label it with what it is (e.g.
"front, from -z, mirrored"), and say in the spec which way +x reads in each view. A test
builds a model with one marked cell at +x and checks which side of each view it lands
on.

Done when the viglet_v preview and a Godot capture of it facing its camera agree on
which side the warm side is.

### §PW262 A thin region that straddles a cell boundary is a finding

Found in Starship (2026-09-27, RK132 and RK133), three times in one day. A thin shape
used as a `paint` or `where` region, one cell wide, centred on a point the grid puts on
a boundary between two cells, takes both cells. On an even-count axis the grid's cell
centres sit at odd multiples of half a cell, so a mullion declared at x = 0 with width =
cell covers two columns. A row of them spaced one cell apart covers every column. The
build reports no finding, and the fix is found by counting cells in the preview.

- The citadel's mullions at ±1.5 and ±3 swallowed the low and high tiers' faces whole.
- The skybridge, 10 cells long with posts every 0.8, came out all trim.
- The ribbed shaft's 8-cell ledge shifted the grid under 7-cell walls, and its ribs covered
  the slots.

A shape whose extent on an axis is one cell or less, but covers two cells there, should
get a finding naming the node and the axis ("`mullions_x` is 0.4 wide on x and covers 2
cells: its faces fall on cell boundaries; move it by 0.2 or make the model odd-sized on
x"). The answer could also carry each axis's cell centres, so a declaration can be
written against them rather than inferred from a preview.

Done when rebuilding the citadel with its first mullion positions reports that finding.

### §PW263 A fit that knows the box from the shape

Found in Starship (2026-09-27, RK97). The Mote's voxel declaration was fitted to the
mesh Meshy made from its drawing. The mesh, normalised to height 1, is 1.97 wide. The
game holds the Mote to a 1.5 x 1.05 hitbox, so the declaration's ranges keep it inside
that box. `geometry.fit` scores silhouettes at the reference's own aspect. The only way
it can raise the overlap is to make every part smaller, so the best values landed on the
edge of every range (core, spike, outer_h and inner_w at their minimum). The fitted
model was worse: its seams slid onto the orb's caps and its shields thinned to lines.
The answer gave no hint that the aspect was the cause, only a score of 0.65.

When the reference's aspect in a view differs from what the ranges can reach, the answer
should say so ("the reference is 1.97:1 in front and the declaration can reach 1.43:1 at
most"). It should offer to score after normalising each view's box, so the fit compares
shape and proportion inside the box rather than the box itself. A best value on the edge
of its range should be named as bound by the range, not reported as the fit.

Done when the Mote's fit reports the aspect gap and, scored inside the box, moves its
parameters off their range edges.

## Block J — A bar a person sets once

## Block K — Reached without reading the source

### §PW246 One field says why a capture failed

Found in Starship's RK68 (the codex), 2026-09-27, over the MCP tool `capture_run`. A run
that took all five pictures and exited 0 answered `"ok": false`, `"verdict": "ok"`,
`"why": ""`, `"found": {}` and `"artefacts": []`. The reason, that the resolution was
applied at 1280x720 and not the 1920x1080 asked, was only in `environment.why`, and it
took reading `capture.py` (the `against["holds"]` branch) to learn that this alone had
turned `ok` false.

An answer should read in one field: where `ok` is false, the top-level `why` says why
(copying `environment.why` when the environment is the cause), and `verdict` names the
cause (e.g. `environment-differs`) rather than `ok`. The pictures the script did write
should be listed under `artefacts` either way, found from the `expect` lines, so the
caller does not go back to the log for the paths it printed.

Done when the same run answers with a non-empty `why`, a verdict that is not `ok`, and
the five paths.

### §PW247 A list the shell cannot mangle

Found in Starship's RK68, 2026-09-27. From PowerShell, `python -m polyweave capture.run
--script dev/shot.gd --expect SHOT --args '["--scene=...", "--frames=45"]'` was refused
with `op.bad-type: --args is a list, and '[--scene=..., --frames=45]' does not read as
one`: Windows PowerShell 5.1 strips the inner double quotes when it hands a
single-quoted argument to a native program, so the JSON never arrives. The remedy, "pass
it as JSON", is the thing that failed. The MCP tool took the same list at once, but
AGENTS.md names the CLI as the second way in, and a shell is where a session often is.

The CLI should take a list in a form no shell mangles: the flag repeated (`--args
--scene=... --args --frames=45`), or a file (`--args @path.json`), with the refusal
naming both. `describe` should state the forms a list accepts.

Done when that call works from PowerShell 5.1 and from bash with no JSON quoting.

## Block L — What a run leaves as evidence

### §PW248 What a build ships that a generator made

Found in Starship's RK78 (2026-09-27), the task that takes the generated art out of the
shipped game. Steam's content survey asks whether a game ships generated content, and
the honest answer needs to know, for every file the build ships, whether a generator
made it (Meshy, Ideogram, any `mesh.buy`, `picture.buy` or `sound.buy`), directly or
through its inputs. polyweave has every piece: each artefact's `.prov.json` names its
inputs, and the purchase ledger names what was bought. It has no read that joins them.
`provenance_credits` answers for sounds' licences only, and `provenance_dependents` goes
from an input forward, one file at a time.

So the project walked it by hand: it read the records to see that
`assets/voxels/drone.voxels.json` has one input, `art/voxels/drone.toml`, while
`assets/models/drone.glb` descends from `tools/art/meshy/drone.stripped.glb`, and it
wrote its own check (`check_authored_art` in `dev/check.gd`) that walks Godot's
dependencies and refuses a path under `assets/models/`, `tools/` or `art/`. That check
knows directories and not lineage.

polyweave should answer a new `provenance_generated` operation: given the paths a build
ships (or a project's export filter), the ones whose lineage reaches a purchase or a
generator, each with the chain and the service, and the ones with no record at all. With
it, the survey's answer and the project's gate are one call.

Done when Starship's check asks polyweave instead of listing directories, and a planted
Meshy mesh is named with its chain.

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
build it into what the engine plays (for Godot, a GPUParticles3D or a ribbon mesh and
its material, with a record), render it over a few frames on a neutral background as a
look a person can judge, and hold it to an acceptance spec (how long it lives, how far
it reaches, its brightness, its particle count against a budget).

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

### §PW256 A sitting for sounds

Found in Starship's RK115 (2026-09-27). Its design says a person listens before the old
sounds go, a verdict per effect, since a synth swap changes how every hit feels. Twelve
effects and three phase tracks were remade through `sound.synth` and `music.render`, and
the old ones kept aside in `.polyweave/audio_before/`. Nothing in polyweave can put them
in front of a person: `verdict.sheet` and `verdict.sitting` lay out pictures, `review`
serves them, and `verdict.judge` carries words about a look. So the verdicts are asked
for in a chat message listing file paths, and whatever the person answers is not
recorded beside the sounds.

A sitting should take sounds as members: each with its new file, the old one it
replaces, and what `sound.measure` says of both (loudness, peak, length, the seam for a
loop), played side by side on the review page with the same keep, change or reject
answer a picture gets, and `verdict.judge` recording it against the sound's record. A
loop plays looped, so its seam is heard.

Done when Starship's fifteen sounds are one sitting and a person's answers land in their
records.

### §PW261 A malformed member is refused, never raised

Found in Starship (2026-09-27, RK132). `verdict.sitting` was given a family as a list of
picture paths, which is what "each family's name to its members, as for a sheet" reads
as to a caller that has not read `MEMBERS`. `_checked` calls `member.get("spec")` on a
string and raises AttributeError. Through the CLI that is a traceback. Through the MCP
server the whole server went down ("Connection closed"), and every other polyweave tool
was lost for the rest of the turn.

Each member should be validated before any picture is opened. A member that is not a
table, or lacks `name` or `new`, should be refused with a code (`verdict.bad-member`), a
remedy quoting `MEMBERS`, and the index of the member at fault. A bare path could also
be read as `{"name": <stem>, "new": <path>}`, a picture shown without a spec, since that
is the commonest first guess. Separately, an exception inside any operation should come
back to an MCP caller as a refusal and not end the server.

Done when the call above answers a refusal naming member 0, and the server still answers
the next call.

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

### §PW254 An effect made to a loudness

Found in Starship's RK115 (2026-09-27), moving eight effects from a project script to
`sound.synth`. The game's mix is a table of weights that assumes each effect's loudness,
so a replacement has to land where the old one was. `sound.synth` normalises an effect
to `peak` and nothing else, and sfxr's explosions are dense: at the old peaks the new
kill measured -5.6 dBFS RMS against the old -18.6, the death -5.3 against -16.3, the
evolution -8.0 against -20.0. A swap like that jumps every hit in the mix.

The workaround was arithmetic by hand, per effect: measure the old sound with
`sound.measure`, synthesise, measure the new one, and move `peak` down by the
difference, then synthesise again, since loudness scales with the gain.

An effect should be able to say `loudness = -18.6` (RMS dBFS, as `sound.measure` reports
it), or `match = "<path of the sound it replaces>"`, and be normalised to it, with
`peak` then a ceiling that is reported when it binds. The answer states both the
loudness aimed at and the loudness reached.

Done when Starship's effects declare their loudness instead of a hand-worked peak, and a
re-synthesis lands each within 0.5 dB of it.

### §PW255 A render in the format the game loads

Found in Starship's RK115 (2026-09-27), rendering the phase music into
`game/audio/music/phase_<n>`. `music.render` writes both `.wav` and `.ogg`, each with a
`.prov.json`, and takes no parameter to choose. Starship loads the WAV (its import loops
it and compresses it for export); an OGG beside it is a second copy Godot imports and
the build ships unless someone deletes it, and deleting it by hand leaves the render's
pair of records half gone, which `provenance_verify` then has to be told about.

`[sound.music]`, or the render call, should say which formats the game loads (`format =
"wav"`, as `[sound.effects]` already does for effects), and the render writes those
alone, with a record for each. The answer names what it wrote.

Done when Starship's three phases render to WAV alone and `provenance_verify` is clean.

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

### §PW257 A name's plural is the name

Found in Starship's RK122 (2026-09-27). A wave announcement in the world's words,
`WAVE_GLEANERS,GLEANERS INCOMING - FREE THE HOLDERS`, drew `WAVE_GLEANERS (en) names
'GLEANERS', which is no name the world shows`, though `docs/design/starship.world.toml`
declares `[entity.gleaner] name = "Gleaner"`. The check matches a capitalised word to a
declared name exactly, so the plural of a name the world declares reads as a new name.
Every entity is spoken of in the plural somewhere (Motes, Lancers, Holders, Foremen), so
a project either writes its interface in the singular, lists each plural as `ordinary`
(which then hides a real misspelling of it), or lives with a standing finding.

The check should take a declared name's English plural as the name (Gleaner, Gleaners;
Foreman, Foremen), with an entity able to state an irregular one (`plural = "Foremen"`),
and a finding for a word that is only near a name ("Gleeners") should say which name it
is near.

Starship's RK130 then moved its goals into the table and drew eight more such findings
in one go: Motes, Lancers, Divers, Gleaners, Sowers, Spurs and Foremen (twice).

Done when Starship's string table passes with GLEANERS in it and no `ordinary` entry for
it.

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

### §PW250 A sweep of a script over arguments

Found in Starship's RK81 (2026-09-27), choosing trailer shots. A shot needs a run where
the moment happens: a pulse across a full wave, an evolution taken, a Foreman breaking.
Which seed and pilot policy give one is found only by flying the game. The project's
scene script prints `EVENT tick=N <what>` lines in a scan mode, and the agent ran it by
hand, seed after seed and policy after policy (seven headless runs of about a minute
each), reading each log for the event. Two runs with the evolution recipe dealt showed
it was never taken, because the pilot's pick list did not name it; the next change to
the list changed the whole run.

This is a sweep: a scene script, a grid of arguments (seeds, policies), and a pattern
the log must show. `search.sweep` searches a rig's values against a spec, and
`capture.run` runs one script once, so neither fits.

polyweave should run a scene script over an argument grid, in parallel where the machine
allows (`search.worth_parallel` already says when), collect every line matching a
pattern with the arguments that produced it, and stop at the first `n` hits if asked.
The answer lists, for each hit, the arguments and the lines (`EVENT tick=7469 evolution
Ring Gunner` under seed SWEEPING, policy list:...), and records the sweep so it is not
flown again for the same build.

Done when finding Starship's evolution shot is one call over a seed list, and it returns
SWEEPING with its tick.

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
