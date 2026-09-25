# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

- 📋 **PW141** (deps: —) **a bake does not say whether its silhouette moved or only its look, so two bakes are compared by measuring both again** — An agent asking "did my bevel change the outline" re-runs the measures on both pictures, when one string per question would answer it across sessions. → §PW141
- 📋 **PW145** (deps: —) **a bake after `preview_size` changed is served the old-size picture from the cache, as a hit** — The rung's size is read from the project file and is in no field the cache key covers, so every measure on the hit answers for a size nobody asked for. → §PW145

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

- 📋 **PW146** (deps: —) **a misspelt key in a geometry declaration is accepted silently, at the top level or on a node** — parse checks names, ids and the output and reads nothing else, so a typo builds the shape without that field and says nothing. → §PW146

## Block H — Proof on a real game

- 📋 **PW57** (deps: PW53 ⏸) **every Cottony look gate restates its own floor, so no asset has a bar a search can aim at** — Five check scripts measure after the render is spent, which is a verdict and never a target, and a threshold moved in one of them is invisible to the rest. → §PW57
- 📋 **PW59** (deps: PW53 ⏸, PW54 ✅, PW55 ✅, PW56 ⏳, PW57, PW58 ✅) **nothing says how much of Cottony still does its own version of what the plugin does** — Adoption is asserted per asset, so a hand-rolled rig, gate or runner can come back without anything failing, and 100% stays an opinion. → §PW59
- ⏳ **PW56** (deps: PW57) **twelve GDScript runners in Cottony each start Godot their own way, and a settings mismatch is silent** — The seven perf scripts started by hand have no driver, and five of them are gates whose verdict shape is §PW57's question. → §PW56

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

- 📋 **PW132** (deps: —) **an agent in a consumer is never told the plugin exists, because it ships no manifest, skill or session notice** — Six of Cottony's tools import the plugin and not one of its agent documents names it, so each session rediscovers it from a script's imports. → §PW132
- 📋 **PW133** (deps: PW125 ✅) **an agent may hand-edit a built mesh or voxel file, and nothing notices the output no longer follows its declaration** — The build stamp hashes inputs only and geometry outputs carry no record, so an edited output is reported cached and rebuilt only when an input moves. → §PW133
- 📋 **PW160** (deps: —) **a clip is baked to an animation and a sheet only from Python, since every step takes a mesh and a rig in memory** — The census lists compile, frames, sprites.bake and skeleton.fit as internal, so motion is the one surface a GDScript project still needs a script for. → §PW160

## Block L — What a run leaves as evidence

- 📋 **PW134** (deps: —) **a green suite with Blender and Godot absent reads the same as one that rendered, and leaves no record it ran** — The render, engine and capture tests skip without `bpy` or `$GODOT`, and a backgrounded run is known only by whoever read the tail of its output. → §PW134
- 📋 **PW135** (deps: —) **a test log written at the repository root is staged by the commit tool, because nothing ignores `*.log`** — `run-commit.cmd` stages everything, which is how Shio committed sh545.log with a fix, and a five-minute suite is exactly the run an agent redirects to a file. → §PW135
- 📋 **PW136** (deps: PW134) **no pytest or ruff runs anywhere but a desk, so a consumer pinned to a commit gets one nobody gated** — The workflows run only roadkeep's lint and the site, while Cottony's CI installs this repository at a pinned commit. → §PW136
- 📋 **PW137** (deps: —) **the site's own test requires the page to say there is no implementation, after a hundred lines have shipped** — README and CLAUDE.md still say Block A has started, so the first thing a reader or an agent learns about the plugin is false, and a test defends it. → §PW137
- 📋 **PW138** (deps: —) **the tool-surface spec names twelve error areas and the code declares nineteen, and nothing reads one against the other** — A name a spec spells that the code lacks, or the reverse, is found only by a reader who checks both, which is the drift the specs exist to prevent. → §PW138
- 📋 **PW139** (deps: —) **two jobs started at once can both pass the capacity check, so `[render] max_parallel` is exceeded** — `start` lists the running jobs and then spawns with nothing held between the two, the shape of roadkeep's race that minted one id twice. → §PW139
- 📋 **PW140** (deps: —) **a build is reported cached after the plugin that built it changed, because its stamp hashes the inputs alone** — The stamp leaves out the plugin's version and `--preview`, and geometry writes no provenance record, so two answers to "what made this" already disagree. → §PW140

## Block M — What a game needs beyond the look

- 💭 **PW142** (deps: —) **a voxel model is drawn with every filled cell, including the ones buried where no face of them can be seen** — `multimesh()` instances every centre while the same file records each cell's depth, so a solid model pays for its whole volume and not its skin. → §PW142
- 💭 **PW143** (deps: —) **an acceptance spec bounds how an asset looks and never what it costs the game to draw** — A search that passes every look predicate may triple the triangles, materials or texture memory, and nothing in the spec would refuse the rig that did it. → §PW143
- 💭 **PW144** (deps: —) **the rig a search found is kept nowhere, so each run searches it again and no other game can start from it** — `search_stars.py` spends up to sixty renders finding the stars' rig again, and the half it holds fixed is constants in the script, where no other family can reuse it. → §PW144

## Done when — PW36

- **Every piece of Cottony's pipeline runs on the plugin, with no fork** The
  script-built tray, the fetched prop in drawn cloth, the inflated cushion, the rig, the
  paid service and the four engine captures each pass the check the existing pipeline
  passes, against a before-side baseline recorded before that piece moved. A piece left
  behind is named, with what it needed.

## Done when — PW56

- **Every script that starts Godot here does it one way, and says what applied** Five of
  twelve are done: the four captures and cascade.gd go through engine and capture, and a
  mismatch fails the run. Left are the seven under tools/perf/ that have no driver, and
  run_tests.py, which is a third copy of the lookup and is PW70.

## Done when — PW77

- **Each of the five props has an acceptance spec a person agreed to**
  docs/design/accept/scenery_<name>.accept.toml exists for bush, tree, flower and yarn
  as it does for the mushroom, and the shipped sprite passes each.
- **One searched rig passes all five props and they bake through it** bake_model.py no
  longer renders the five, and polyweave.loop.json holds an after run for map_props with
  a person's verdict.
- **The props' before side is recorded ahead of the port** Cottony's polyweave.loop.json
  holds a before run for map_props at 2153a09, from a re-bake that reproduces the
  committed sprites.

## Done when — PW78

- **Both trays land where the game puts them, from the game's numbers** Cottony's
  tools/art/frame_trays.py exits 0: the board's silhouette matches the shipped sprite to
  the pixel and the booster tray stands within 1 px of its drawing's body.
- **The trays bake through the plugin with a look a person accepted** bake_model.py no
  longer renders board_tray or booster_tray, and polyweave.loop.json holds a before and
  an after run for the trays with a person's verdict.

## Done when — PW79

- **Each mark has a spec that says what its type must read as** docs/design/accept/
  holds a spec for viglet_games_badge, cottony_wordmark and cottony_logo that a person
  agreed to, and the shipped sprites pass it.
- **The marks bake through the plugin and a person judged them** bake_model.py no longer
  renders the three marks, and polyweave.loop.json holds an after run for brand_marks
  beside the before run at 53a9610.

## Done when — PW80

- **The fetched boosters come in from their drawings, textured** Ingested against
  booster_hammer.drawn.png and booster_wand.drawn.png, both keep their texture and the
  hammer's lean is found within a degree of the 22 found by hand.
- **The boosters bake through the plugin and a person judged them** bake_model.py no
  longer renders the three boosters, and polyweave.loop.json holds an after run for
  boosters beside the before run at ef16b28.

## Done when — PW81

- **The five earlier families have baked through the plugin first** PW76 to PW80 are
  shipped whole, each with a person's verdict on its after side, so this family starts
  from a rig and a search that have held elsewhere.
- **The five bake through the plugin or stay hand-tuned by decision** Either
  bake_model.py no longer renders the friends and the mascot and a person judged them,
  or a person decided they stay, and polyweave.loop.json says which.

## Done when — PW113

- **The owner has said whether sound belongs in the acceptance spec** Either a non-goal
  forbidding measures of audio is on the list, or a line exists that adds the first
  audio measure; both are checkable in `non-goal list` and the roadmap.

## Non-goals

- **A graphical editor** The caller here is an agent in a terminal, so a surface that
  needs a person at a screen to operate is one the agent cannot use at all.
- **Replacing Blender, Godot or the generative service** Those three already do the
  work; what is missing is the loop around them, so this orchestrates and measures and
  never re-implements a renderer, an engine or a mesh generator.
- **Spending money on the agent's own judgement** A fetch draws on a real balance, so
  the ceiling is a person's to set and the plugin's job is to make a spend bounded and
  visible, never to decide one is worth it.
- **One project's palette, rig or paths compiled in** Cottony is the first consumer and
  not the specification, so anything it needs that a second project would not is
  configuration, and a default that cannot be overridden is a defect.
- **A hosted service or an account to sign into** Everything runs on the developer's
  machine against files in their own repository, because a plugin that needs an account
  is one that fails on the day the account does.
- **An agent accepting or rejecting its own look** A look is what a person agreed to, so
  an agent that can write the verdict on its own run turns the one check the loop cannot
  automate into one more number it tunes.
