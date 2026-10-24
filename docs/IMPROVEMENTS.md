# Improvements

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

### §PW582 A mesh prepared by declared steps

Found closing PW82 in Cottony on 2026-10-20. `tools/art/bake_model.py` is gone, but its
preparation half survives as `tools/art/prep.py`, driven by three exporters
(`export_props.py`, `export_boosters.py`, `export_friends.py`) before `port.run`.

Landed: `render.bake` takes `prepare`, a list of steps run on the mesh after it loads
and before it is decimated or placed. `dedust { below }` drops every piece under that
share of the largest's vertices, where a piece shares an edge or a position (a glTF
splits vertices at seams). `settle { squash }` keeps volume about the base. `custom { fn
= "file.py:fn", ...args }` calls a project function with the object. Each step is in the
key and the record, a custom one with its source's digest, and the answer says what each
did. A family sets them through `fixes`, which already reaches `render.bake`. Joining
needs no step: `load_mesh` joins every part a file holds.

Left, in Cottony: each exporter's work as prepare steps, then the exporters and
`prep.py` deleted. Two pieces need care. `cloth.dress` projects drawn cloth from the
orthographic camera `prep.frame` builds, so it becomes a custom step that builds its own
camera from the object's bounds. The exporters also scale each mesh to a fill of its
frame (`FILLS`), which the bake's `margin` or `covers` should express; compare a render
before and after for each family, as PW76 to PW81 did, before deleting anything.

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

Site copies, left by PW585 on 2026-10-21: `picture.copies` cuts a `*.copies.toml`, and a
trial on Cottony's hero and favicon came out pixel for pixel equal to `site/assets/`.
Cottony moves IMAGES into `site/assets.copies.toml` (`into`, `quality = 88`, and
`quality = 86` on `og.jpg`), runs it once, deletes `tools/site_assets.py`, and lets CI's
`provenance.outdated` replace `--check`.

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

### §PW621 A sweep over a project's own generator, judged downstream

Found in Cottony's RK158 (the board screen's sky). The sky is a panel the project draws
in Python (`tools/art/make_assets.py`, `_sky_panel(width, height, seed)`) from clouds
polyweave renders, and it is held through the board capture to
`docs/design/accept/board_concept.accept.toml` (PW477's concept predicates). Which
layout passes is a seed, and choosing it meant a loop of four steps per candidate,
written as a throwaway script:

1. call the project's drawing function at a seed and save `sky.png`;
2. `$GODOT --headless --editor --quit` so the engine imports it;
3. `engine.run_declared --runs ["board"]` to re-take the capture;
4. `accept.check` on the capture, reading `failed`.

Twenty seeds, about 35 seconds each, by hand. `search.sweep` and `port.run` search a
render rig against a spec, but neither can turn a parameter of a project's own generator
and judge the declared run's capture downstream of it.

Expected: a sweep whose candidate is "run this project function with these arguments,
then these declared runs, then this spec", answering each candidate's failed predicates
and margins and the best one, with the import step done for it. The generator could be
named in polyweave.toml the way `[extend.measures]` names a function.

Also met in the same loop: on Windows PowerShell 5.1, `--runs '["board"]'` reaches
polyweave without its inner quotes and is read as something else, silently: the run did
not happen and the answer still said passed. It needed `'[\"board\"]'`. A list argument
that does not parse as JSON should be refused, not run as nothing.

### §PW622 A capture's record names the classes its scene resolves

Found in Cottony's RK159 on 2026-10-23. The task changed `scripts/tray_mesh.gd` (the
board tray's geometry, `class_name TrayMesh`, built by `Board3D`), then re-took the
strike screen:

```
python tools/capture_screens.py tools/capture/strike.gd
SAME SETTINGS, DIFFERENT PICTURE: screenshot-strike.png: the same declared settings produced
different bytes ... locale, resolution and seed were pinned, so something this picture
depends on is not declared
```

The picture changed because the tray did, which is the point of the task. PW488 taught
the record to name the sprites a scene draws, so a changed sprite reads as different
work and not as noise; the board capture's own record lists `shaders/tray.gdshader` and
`scripts/level_set.gd` among what moved. But a script the scene reaches by its
`class_name` (`TrayMesh.build()` from `board3d.gd`), never by a `preload` or `load`
path, is not in the record, so its change reads as an undeclared setting.

Expected: the record's inputs include every script the scene's scripts resolve by
`class_name`, read from `.godot/global_script_class_cache.cfg` or the scripts' own
`class_name` lines, so a changed class reads `different-work` naming it.

Workaround: none; the warning was read and the capture kept, since the change was
intended.

### §PW623 Effects declared for a 2D canvas

Found in Cottony's RK162 on 2026-10-23: candy stars drifting slowly in the gaps between
the board screen's panels, as `screen1.png` floats them. Cottony's board screen is 2D
(`Node2D` panels, a `SubViewport` only for the board's own 3D layer), and its effects
are `CPUParticles2D` in `scripts/fx.gd`.

`vfx.build` was the place to declare it: its `shape = "star"` is the very picture
wanted, and `size_over_life`, `colour_over_life`, `angular_velocity` and an emission box
are every knob the drift needed. But every effect it builds is a 3D scene in metres
(`GPUParticles3D`, quads, meshes), with no way to ask for a `CPUParticles2D` or
`GPUParticles2D` in pixels for a canvas. So the drift was written by hand as
`scripts/drift.gd`: four emitter rectangles, a seed, a preprocess, two sizes for depth,
a colour ramp and a fade, which is exactly a declaration's worth of numbers.

Expected: `[effect.<name>] dimension = "2d"` (or a `canvas = true`) that builds the same
declaration into a 2D particle scene, extents and sizes in pixels, with `seed` and
`preprocess` as keys so a capture of it is reproducible, and `emission` taking a list of
rectangles for an effect that lives in several gaps at once.

Workaround: `scripts/drift.gd` in Cottony, which names this line in its header.

### §PW624 A recorded flow that survives an unrelated node

Found in Cottony's RK162 on 2026-10-23. The task added one `Node2D` with eight unnamed
`CPUParticles2D` children to the board screen. `python tools/check_export.py` then
failed a recorded flow it replays:

```
FAIL  flow lose_later_level.flow.json broke at step 2, frame 127: driver.no-node: nothing on
screen answers path /root/Main/@Node2D@155/@TextureButton@163
```

The flow addressed the button by the name Godot generated for it, `@TextureButton@163`,
and those numbers come from one counter every unnamed node in the process draws from.
Eight new unnamed nodes, anywhere and unrelated to that button, moved every number after
them, so the recording broke on a change that has nothing to do with what it plays. The
workaround was to name the new nodes so they draw no numbers; any later unnamed node
breaks it again.

Expected: `game.record_flow` never writes a path with an `@...@N` segment. It records
what stays put: the node's own name where it has one, else a locator such as the class
with the nearest named ancestor and the node's index among siblings of its class, or the
text a button carries. A replay that meets a recorded `@..@N` path could say so as its
own code (`driver.fragile-path`) naming the step to re-record, rather than
`driver.no-node`.

Workaround: `scripts/drift.gd` and `scripts/game.gd` in Cottony name the new nodes.

### §PW625 A ceiling with no date says so

Found in Cottony's RK163 on 2026-10-23. The owner set a ceiling for three booster toys,
and `[budget]` in polyweave.toml was written `credits = 90`, `expires = ""`. Then:

```
python -m polyweave purchase.remaining
declared: 90.0   spent: 0.0   left: 0.0   expires: null   spendable: false
why: the budget has no expiry, and one without a date never lapses
```

The answer refuses to spend and gives as its reason a sentence that argues the opposite:
a budget that never lapses should be spendable. `left: 0.0` beside `declared: 90.0` with
nothing spent says nothing about why. Setting `expires = "2026-11-30"` made it
spendable, so the real rule is that a ceiling needs a date - which is a sound rule, and
a refusal should say it.

Expected: `why` states the rule and the door: "a ceiling with no expiry is not
spendable: give [budget] expires a date", as a `budget.no-expiry` code `explain` knows,
and `left` reports the declared amount with `spendable: false` rather than 0.0, so the
two fields do not contradict.

Workaround: none needed; the date is set in Cottony's polyweave.toml.

### §PW626 Background is what reaches the edge

Found in Cottony's RK163 on 2026-10-23, cutting the three booster toys out of the
concept painting (each standing in a powder-blue well) to send to the mesh service.

```
python -m polyweave reference.prepare --photo .polyweave/toys/shuffle.crop.png \
    --out tools/art/3d/booster_shuffle.painted.png --longest 512 --tolerance 48
```

The hammer came out clean. The ball lost its blue and green bands and the shooting star
lost most of its blue rainbow tail: `prepare` takes every pixel near the edge's colour
wherever it is in the picture, so a subject that shares a hue with its background is cut
into pieces. A lower tolerance kept the well's shading instead.

Expected: background is what is connected to the edge. Flood from the border (and, for a
subject on a vignetted or gradient ground, from many points round it, each compared with
its own neighbourhood), then keep the largest remaining piece so isolated sparkles go
too. A `mode = "colour"` could keep today's behaviour for a ground that shows through
holes.

Workaround: Cottony's `tools/art/booster_toys.py` floods from the corners and 64 points
round each well's rim and keeps the largest piece, and names this line.

### §PW627 A textured mesh bought through the plugin

Found in Cottony's RK163 on 2026-10-23. The booster toys - a pink mallet with a yellow
heart, a rainbow shooting star - are what they are by their colours, and Cottony's
committed toys were fetched textured (`should_texture` true, a `texture_prompt`) by its
own `meshy.py`, from before `mesh.buy`. Re-buying them from the painting through the
plugin was the plan, and `mesh.buy` cannot: it always sends `should_texture` off and
takes no texture prompt, so the mallet would come back one colour. The purchase had to
go back through `tools/art/meshy.py`, which `[adoption.own]` keeps only as "the Meshy
client the committed meshes were fetched with".

Expected: `mesh.buy` takes `texture = true` with a `texture_prompt` (and the service's
texture resolution), books the textured price row, and records the prompt and resolution
on the ledger, so a project's textured fetch goes through the ceiling and the ledger
like every other purchase.

Also met: a 402 from Meshy can mean the plan, not the balance (`NoMorePendingTasks`,
"task creation on the free plan is no longer supported", with 300 credits left).
`fetch.over-budget` would misname it; a `fetch.plan` code with the service's message
would not.

Workaround: Cottony's `tools/art/meshy.py`, which still textures.

### §PW628 A family ported member by member

Found in Cottony's RK163 on 2026-10-23. `tools/art/boosters.family.toml` holds three
members - hammer, wand and shuffle ball. Two were bought again and passed their specs;
the third, which nobody had changed, failed its own, because its project-built mesh no
longer renders the ball that was committed. `port.run` bakes only when every member
passes, so the two accepted renders could not be baked:

```
python -m polyweave port.run --family tools/art/boosters.family.toml
members.booster_hammer.failed: []
members.booster_wand.failed: []
members.booster_shuffle.failed: ["band-reads-mint", "median-tone"]
says: not every member passed, so nothing was baked
```

and the operation takes no member to limit itself to (its parameters are `family`,
`root`, `run`, `fresh`). The workaround was a copy of the family file under
`.polyweave/families/` holding only the two members, ported on its own.

Expected: `port.run --members ["booster_hammer","booster_wand"]` ports and bakes those
alone, recorded as a partial run of the family; and a family whose failing member is
unchanged since its last bake could say so ("booster_shuffle failed and its inputs did
not change: its bake stands") rather than holding the others back.

Workaround: a throwaway family file in Cottony's work area; nothing committed.

### §PW629 Flows pin the locale they were recorded in

Where it happened: Cottony's CI, job `godot`, step `python3 tools/check_export.py
"Windows Desktop"`, which replays the recorded flows under `tests/flows/` (run
40027450789 on viglet-games/cottony). The flows were recorded on a pt-BR Windows desk,
and their expectations read the screen's own words: `LIGADO`, `ACABARAM OS MOVIMENTOS`,
`NÍVEL CONCLUÍDO`. The Ubuntu runner leaves `LANG` unset, Godot reads that as English,
and every flow that reads a label fails with `ON`, `OUT OF MOVES`, `LEVEL COMPLETE`. The
answer says only that the text differed, not that the game ran in another language than
the one the flow was recorded in.

Workaround: `env: LANG: pt_BR.UTF-8` on that step in `.github/workflows/checks.yml`
(RK174). It works only because Godot's Linux build reads `LANG`; on Windows the locale
comes from the system and cannot be set per run, so a flow recorded on an English desk
would fail on this one.

What polyweave should do: a recorded flow carries the locale it was recorded in
(`TranslationServer.get_locale()` at record time), and the replay sets it before the
first step, through `--language` or a `TranslationServer.set_locale` in the driver, on
every platform. A flow may also declare `locale = "any"` when it reads nothing
translated. Where an expectation fails on text and the replay's locale differs from the
recorded one, the answer names both locales.

### §PW630 a carve's cut wears the cutter's material, and a bake can mask by material

Where it happened: Cottony RK168. An unearned star is a star-shaped pocket pressed into
the bar. `tools/art/score_star_hole.toml` carves the puffy star (a `blend`) out of a
cube plate. The sprite has to be cut to the pocket's mouth, because the plate around it
belongs to the bar and not to the sprite.

What came back: every face of the carve wears the plate's material. A test giving the
plate a key green and the cutter brown rendered all green, the pocket included. So no
render can say where the pocket ends and the plate begins. The render has no mask pass,
and the bake answers with no coverage of the cut.

Workaround: `tools/art/make_assets.py` `_star_mouth` recomputes the mouth by hand. It
reads the declaration's `[params]` with tomllib, rebuilds the 2D field (a core circle
and five ellipses through polyweave's own `blend.round_union`), foreshortens it by the
camera's 18 degree elevation, and nudges it 2.5 px down. That number was found by laying
the outline over a render by eye. It breaks whenever the declaration, the camera or the
frame's centring moves.

What polyweave should do: give the faces a carve makes the cutter's material, or the
cutter's own `material` when the node names one, so the cut reads as its own surface.
Then let a bake write a per-material mask (an ID pass or `masks = ["hole"]`) beside the
picture. A pocket, a groove or an engraving could then be composed by its own coverage.

### §PW631 inflate's height field is float end to end

Where it happened: Cottony RK168, trying a puffy star by `inflate` before settling on a
`blend`. There were two declarations.

With a star outline (`outline = { shape = "star", ... }`), the inflated surface came
back striped, with bands running across the arms.

With `drawing = "<a rounded star PNG>"`, `soften` 0.5 to 3 and `floor = 0.5`, the face
came back with concentric contour rings under the specular. They are the stair steps of
an 8-bit height field, which a glossy coat raises to a high power, the same failure
cottony-art-pipeline records for `blur`. Neither result was usable on candy, which is
glossy by rule.

Workaround: none inside inflate. The star became a `blend` of ellipsoids
(`tools/art/score_star.toml`), which gives up the drawn outline.

What polyweave should do: build inflate's height field in float32 end to end: the
distance transform, the soften, and any resample. Then a glossy coat shows no steps.
Find and fix whatever stripes an outline-shaped inflate along its arms. A regression
check would inflate a five-point star with a coat and measure the luma's second
derivative along an arm.

### §PW632 crowned domes a concave outline by distance to its edge

Where it happened: Cottony RK168. The score bar's stars needed to look like puffy
moulded plastic, like screen1.png's. The first try was a `crowned` node over a rounded
five-point outline (plush.shape_star, points passed as `outline = [[x, y], ...]`), with
`crown` at 0.16 of the canvas and `steps = 20`.

What came back: a pyramid. `solid.crowned` shrinks a concave ring toward its centroid
(PW66, as its docstring says), so every arm rises along a straight ridge to the middle,
and each ring between two points folds into a crease. More steps only add more rings to
the same ridges. The docstring promises "a domed face", and it is one only on a convex
outline.

Workaround: `tools/art/score_star.toml` builds the star as a `blend` of a core sphere
and five ellipsoid arms instead, repeated with `rotate = [0, 0, "i * 72"]`. That works,
but the outline is no longer the drawn one. It is whatever five ellipsoids fillet into.

What polyweave should do: give `crowned` a dome that follows distance from the edge, not
the centroid: lift = f(distance to the outline), the way `inflate` does it, but on a
float field (see the inflate line on contour rings) so it stays smooth. A concave
outline would then dome like a pillow, with rounded valleys between the points. Or say
on the node that a concave outline gets ridges, so nobody expects a pillow from it.

### §PW633 Captures render the viewport the stretch gives a window

Where it happened: Cottony RK175 laid the board screen out for a 16:9 PC window. The
project runs `window/stretch/mode = canvas_items` with `aspect = expand` on a 1080 by
1920 design. A real 1920 by 1080 window is therefore laid out as 3413 by 1920 units and
scaled down.

A declared capture asks for `resolution = "1920x1080"` (`capture.wanted(...,
resolution=...)`), and the project's `tools/capture/environment.gd` sizes its
SubViewport to it. That SubViewport has no stretch, so the game sees a 1920 by 1080
viewport in units. Every unit-sized margin, pad and card comes out proportionally larger
than the player's window shows, and the picture is of a layout no player gets.

Workaround: `tools/capture/board_wide.gd` computes the stretch by hand. It renders at
`(DESIGN.y * w / h, DESIGN.y)`, then `Image.resize`s to the window. Before that, a
throwaway `.polyweave/wide.gd` did the same to preview layouts. Every capture of a wide
screen needs it; Cottony RK178 title_wide.gd copied it again.

What polyweave should do: read the project's `[display] window/stretch/*` and
`window/size/viewport_*` from project.godot. A capture at a stated window resolution
then renders the viewport the engine would give that window (the expanded or kept size
in units) and scales the picture to the window's pixels. The environment line would
report both: the window resolution and the viewport it was laid out in. A capture of a
narrow phone and a wide PC screen would then each be the screen the player sees, with no
project arithmetic.

### §PW634 A mesh brought to a budget

Where it happened: Cottony RK172 moves the booster toys from baked PNGs to live meshes
in the board's 3D layer. The two toys bought from Meshy are the meshes to load:
`tools/art/3d/booster_hammer.glb` (8.5 MB) and `booster_wand.glb` (9.1 MB).

`python -m polyweave cost.read --of tools/art/3d/booster_hammer.glb` answers 104,450
triangles and 67,108,864 texture bytes: a 4096 texture, for a toy the wide card draws
about 150 px tall. Cottony's export ceiling is 24 MB (`tools/check_export.py`), so the
two toys alone would be most of the build, and three of them on screen with the board is
a frame cost nobody measured.

Nothing in polyweave brings a mesh to a budget. `normalise.ingest` orients, centres and
sizes. `render.bake --prepare` offers dedust and settle. `cost.read` measures but
changes nothing. The only route is a Blender script in the project (decimate modifier,
texture resize, glTF export) written outside the record, the shape PW582 removed for
prep.py.

What polyweave should do: an operation, say `mesh.budget`, taking a .glb and a target (a
triangle count or ratio, and a texture edge in pixels, or a screen height the mesh is
drawn at from which both are derived). It writes a slimmed .glb with a record naming the
source and the numbers, and reads `cost.read` before and after so the answer says what
was saved. A silhouette check against a render of the source would say whether the
decimation cost the shape.

Until then Cottony's RK172 waits on this line rather than growing a project exporter.

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

### §PW620 A person sets the bar a look must reach

Found in Cottony's RK156, which holds the board screen to its concept painting in 17
regions through PW477's concept predicates
(`docs/design/accept/board_concept.accept.toml`).

Its design asks for each region's bar to be set from a sheet the owner looked at: the
target the rest of the block climbs towards. Today every bound is `origin = "measured"`,
today's value rounded outward, which only stops the screen walking away from the
painting.

`verdict.judge` cannot write that. `accept` takes the look as it is; `look` sends the
renders back and keeps the bounds; `number` rewrites a *failed* bound to the measured
value and is refused where the family passes (`loop.no-failed-bound`), which a measured
bound always does on the day it is written. So a person looking at a region's sheet has
no way to say "this region must reach a palette distance of 4", and the agent would type
a person's number into the spec by hand, which PW109 exists to stop.

Expected: a verdict that sets a bound tighter than the measured value, for a named
predicate or for every predicate of a member, written as `origin = "person"` with the
date and the sentence, offered on the page beside a concept sheet. It could take the
number, or a fraction of the way to the painting, which a concept ratio already makes
meaningful (1.0 is the painting).

Workaround in Cottony: none. RK156 ships the measurement with measured bounds and waits
on the owner for the targets.

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

## Block W — A core that grows by layers

## Block X — The site on the shared design system
