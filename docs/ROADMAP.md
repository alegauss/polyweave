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
- ⏳ **PW76** (deps: —) **Cottony's four progress stars are lit by three constants found by hand, and no search sees them** — One rig has to hold on all four, and the dim still misses its facet ceiling at both sizes, before the stars bake through it and a person judges them. → §PW76
- 📋 **PW77** (deps: PW76 ⏳) **the map's five candy props match a drawn sprite that exists only as medians in a comment** — The bar was measured and written in prose, so nothing can read it, and the sixth prop is fetched where four are built. → §PW77
- 📋 **PW78** (deps: PW77) **the two trays are framed by a world rectangle written out per asset so the game's grid lands on it** — One unit has to be one pixel because board.gd addresses a cell at CELL := 112, and a render fitted to its own bounds misses that grid. → §PW78
- 📋 **PW79** (deps: PW78) **the three brand marks are exposed by a hand-found light and nothing states what the type should read as** — Two blends and one constant each is the least machinery of any family, and the acceptance is the hardest to put a number on. → §PW79
- 📋 **PW80** (deps: PW79) **the three booster objects each needed a scrub, a roll and a fill found by hand after the service returned them** — A fetched mesh faces wherever it was left and keeps the marks the service painted, and rule 2 forbids those on candy. → §PW80
- 📋 **PW81** (deps: PW80) **the two friends, their lean frames and the mascot take eleven constants apiece and nothing declares one** — Cloth, face placement, unsculpt and dust were each solved by hand on the assets a player looks at most, so they move last. → §PW81
- 📋 **PW82** (deps: PW81) **nothing takes bake_model.py out once its assets have moved, so the rig outlives its own replacement** — Each family porting leaves the file smaller and still running, and two live paths to one sprite is the state this whole sequence exists to end. → §PW82
- 📋 **PW85** (deps: —) **a bake that declares the rectangle it covers answers with the rung's size, not the picture's** — The answer is built from the plan's number before the declaration resized the frame, so a 96 px star is reported as 1024. → §PW85

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

## Done when — PW76

- **One searched rig passes all four star specs unchanged** tools/art/search_stars.py in
  Cottony exits 0: fitted on the 96 px gold, the same values pass star_dim,
  star_gold_big and star_dim_big without being searched on them.
- **The four sprites bake through the plugin and a person judged them** bake_model.py no
  longer renders the stars, and polyweave.loop.json holds an after run for stars with a
  person's verdict, so loop.compare has both sides.
- **A before side recorded ahead of the port** Cottony's polyweave.loop.json holds a
  before run for stars at f90de32, taken from a re-bake that is pixel-identical to the
  committed sprites.

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
