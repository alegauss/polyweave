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

## Block J — A bar a person sets once

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

- 📋 **PW207** (deps: —) **Every public description still calls polyweave a tool for 3D assets** — Blocks P, Q and R make sound, words and levels, so an agent choosing a plugin from its description never reaches for this one outside a mesh. → §PW207

## Block N — Pictures held to a canon

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

- 📋 **PW184** (deps: —) **Nobody knows if agent-composed, headlessly rendered music sounds good enough to ship in a game** — Every later line in this block spends effort on that premise, so a person's listening verdict decides whether the block proceeds or is retired. → §PW184
- 📋 **PW185** (deps: PW184) **No declaration says which music and sound effects a game needs or where they land** — Cottony keeps that list in its own scripts, so polyweave cannot say which audio is missing or out of bounds. → §PW185
- 📋 **PW186** (deps: PW184) **An agent cannot write multi-track music as data that polyweave validates** — An agent composes well only when a validator answers its output, and no format here has tracks, drums or loop points. → §PW186
- 📋 **PW187** (deps: PW185, PW186) **A composed score cannot become a WAV or OGG file without a DAW open** — Nothing renders music headlessly, so the only route to game audio is a person in a DAW or a paid generator. → §PW187
- 📋 **PW188** (deps: PW187) **One theme cannot play at several intensities that stay in step** — Game music changes with play, and layers rendered separately drift unless they share one length and grid. → §PW188
- 📋 **PW189** (deps: PW185) **Retro sound effects are synthesised by each consumer's own script** — A second project would have to copy Cottony's generator, which the non-goal on one project's paths forbids. → §PW189
- 📋 **PW190** (deps: PW185) **Realistic sound effects have no bounded way to be bought from a service** — A synthesiser does footsteps and glass badly, and a paid fetch without a ceiling is the surprise Block D exists to prevent. → §PW190
- 📋 **PW191** (deps: PW187, PW189) **Rendered audio does not record which instruments made it or what their licences owe** — Sample libraries carry licences from CC0 to credit-required, and a game cannot ship credits nobody recorded. → §PW191
- 📋 **PW192** (deps: PW188, PW189, PW190, PW191) **Cottony still makes its audio outside polyweave** — The block is proven only when its first consumer's music and effects are declared, made and accepted here. → §PW192

## Block Q — Words held to the world

- 📋 **PW196** (deps: —) **No declaration says which names, factions and characters a game's world holds** — Starship's bible is prose, so no tool can tell a name on screen from one the world never had. → §PW196
- 📋 **PW197** (deps: PW196) **Text a player reads is never checked against the world's names and rules** — Starship shows KEEPERS where its bible says Lattice, and a line over 60 characters or a code name on screen fails nothing. → §PW197
- 📋 **PW198** (deps: PW196) **A character's picture or mesh is bought from a description retyped by hand** — The world already says who the Mason is and whose palette it wears, so a prompt written again per call is where an asset leaves the canon. → §PW198
- 📋 **PW199** (deps: PW197) **Whether a line keeps the world's tone has nowhere to be answered but a chat** — Warm, short and never heroic is a judgement no rule measures, so it needs a person's recorded verdict and a canon of lines they approved. → §PW199
- 📋 **PW200** (deps: PW197, PW198, PW199, Starship RK88) **Starship's screen still shows names its world bible replaced** — The block is proven only when its first consumer's text, lines and character assets are held to a declared world through polyweave. → §PW200

## Block R — Levels measured before a person plays them

- 📋 **PW201** (deps: —) **Nobody knows if a scripted bot's win rate tracks how hard a level feels to a person** — Every later line in this block tunes levels against a simulated player, so a person's verdict on that proxy decides whether the block proceeds or is retired. → §PW201
- 📋 **PW202** (deps: PW201) **A game's own headless play of a level has no way to report what it measured** — Only the game can play its own rules, so polyweave needs a contract for what the game's probe prints, not a simulator of its own. → §PW202
- 📋 **PW203** (deps: PW201) **A level declared as data cannot reach the engine without each game's own converter** — Cottony writes JSON from a curve and Starship hand-edits .tres waves, so neither level is validated, linked to the world or recorded before it lands. → §PW203
- 📋 **PW204** (deps: PW202, PW203) **A level's difficulty has no bar a search can aim at, and a level set has no curve to hold** — Cottony's curve constants were set by feel and never measured, so a level can be unwinnable or trivial and nothing fails. → §PW204
- 📋 **PW205** (deps: PW202, PW203) **A shooter's waves have no measure of threat, so the level contract is proven on one genre only** — A contract only Cottony's match-3 has exercised may still assume a board, and Starship's check_phase_waves counts enemies without asking how many arrive at once. → §PW205
- 📋 **PW206** (deps: PW204, PW205) **Cottony's levels are still tuned by a curve nobody measured** — The block is proven only when its first consumer's shipped levels are declared, compiled, probed and accepted here, and make_levels.py has nothing left to do. → §PW206

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

## Done when — Block N

- **Two games keep two canons with no style compiled in** Cottony and Spinhole each
  declare `[style]` in their own polyweave.toml and generate against it, and a grep of
  src/polyweave finds neither project's palette, skeleton or path.
- **A mesh bought from a picture had its silhouette passed on the picture** For a real
  Cottony asset, the ledger holds the picture's entry and its shape check before the
  mesh's entry, and the mesh's provenance names that picture as its reference by digest.

## Done when — Block O

- **A real sitting is answered on the page and resumed without a chat message** For a
  Cottony family, a person answers on the review page, the ledger holds that verdict
  through judge alone, and the agent's next candidate follows from verdict.answers with
  no chat message in between.

## Non-goals

- **A graphical editor** The caller here is an agent in a terminal, so a surface only a
  person can operate is one the agent cannot use. A local page where a person looks and
  answers is not an editor: it edits nothing, and its one write is the verdict call an
  agent would make.
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
- **An agent accepting or rejecting its own look** A look, a sound, a line a character
  says and how hard a level feels are each what a person agreed to, so an agent that can
  write the verdict on its own run turns the one check the loop cannot automate into one
  more number it tunes.
- **One genre's level format built in** A match-3 level is three numbers and a shooter's
  is a spawn timeline, so polyweave checks, compiles and measures a level through what
  the project declares, and a schema that assumes a genre fails the next game; PW205
  exists to catch that.
- **Writing a game's story for it** A world is a person's authorship, so polyweave holds
  what the game shows to the world a person declared and routes a line's tone to their
  verdict, and never invents the canon it then checks against.
