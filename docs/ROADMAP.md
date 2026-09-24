# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

- 📋 **PW57** (deps: PW53 ⏸) **every Cottony look gate restates its own floor, so no asset has a bar a search can aim at** — Five check scripts measure after the render is spent, which is a verdict and never a target, and a threshold moved in one of them is invisible to the rest. → §PW57
- 📋 **PW59** (deps: PW53 ⏸, PW54 ✅, PW55 ✅, PW56 ⏳, PW57, PW58 ✅) **nothing says how much of Cottony still does its own version of what the plugin does** — Adoption is asserted per asset, so a hand-rolled rig, gate or runner can come back without anything failing, and 100% stays an opinion. → §PW59
- ⏳ **PW56** (deps: PW57) **twelve GDScript runners in Cottony each start Godot their own way, and a settings mismatch is silent** — The seven perf scripts started by hand have no driver, and five of them are gates whose verdict shape is §PW57's question. → §PW56

## Block I — Voxel models from a declaration

- 📋 **PW93** (deps: —) **a declaration can only become a triangle mesh, so a game that draws and breaks cells has nothing to read** — Starship builds its ship and enemies from cubes that fly apart when shot, and a mesh says neither which cells exist nor what each one wears. → §PW93
- 📋 **PW94** (deps: PW93) **a voxel model cannot be seen without starting Blender and paying for a render** — Authoring a shape is dozens of small edits, and each one needs a look that costs milliseconds rather than a render. → §PW94
- 📋 **PW95** (deps: PW93) **a shape placed cell by cell, like layered pixel art, has no op and would take dozens of cube nodes** — Hand-placed details such as a cockpit, an eye or a stripe give voxel art its character, and a primitive per cell is unreadable. → §PW95
- 📋 **PW96** (deps: —) **a symmetric shape must be declared whole, so its two halves can drift apart** — Ships and most enemies are mirror-symmetric, and declaring one half halves the work and makes asymmetry impossible by construction. → §PW96
- 📋 **PW97** (deps: PW93) **a voxel model with floating cells, one-cell threads or too many cells builds without complaint** — Each reads badly on screen or costs a game frames, and all of them are countable from the cells before anything renders. → §PW97
- 📋 **PW98** (deps: PW93, PW94) **fitting a voxel model to a concept drawing or a fetched mesh is guessing numbers by hand** — The search already tunes declared parameters against a measure, and a voxel silhouette is measurable in microseconds without a render. → §PW98
- 📋 **PW99** (deps: PW93) **a game breaking a voxel model must work out its fragments and damage order itself at runtime** — Grouping cells into fragments and ordering them for erosion is geometry the build already holds, and precomputing it keeps the kill frame cheap. → §PW99
- 💭 **PW100** (deps: PW93) **a fetched mesh cannot be the starting block of a voxel model** — A Meshy hull voxelized, then cut and painted by a declaration, would keep what was bought and still get hand-made detail. → §PW100
- 📋 **PW101** (deps: —) **building a declaration takes a Python script of the project's own** — Every consumer writes the same few lines to build, write and preview, and a project written in GDScript has no natural place to keep them. → §PW101
- 📋 **PW102** (deps: PW93) **a Godot project reading a voxel model must write its own loader and MultiMesh setup** — Godot is one of the three tools the plugin serves, and an importer written once saves every Godot consumer the same parser. → §PW102
- 💭 **PW103** (deps: —) **a family of models that differ in a few numbers is one document copied per member** — Enemy tiers and boss phases are one shape at other proportions or colours, and copies drift apart. → §PW103

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
