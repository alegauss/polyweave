# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

- 🛠 **PW372** (deps: Spinhold RK215) **a camera move cannot be declared as a clip or played by the game, so a cutscene's shots are numbers in the project** — No shot is yet captured onto a sitting for a person to accept, and Starship's opening still reads its own JSON. → §PW372
- 🛠 **PW36** (deps: PW5 ✅, PW82 ⏸) **a real project cannot adopt the plugin without carrying its own paths and palette into it** — Every family has its before side recorded and the stars have moved; the rest move one family at a time, each on a person's look, down to PW82. → §PW36
- 📋 **PW466** (deps: —) **Cottony's tests, boot check and export check still start Godot through subprocess, each with its own lookup** — They never read [paths] godot and bound each run their own way, which is the procedure PW56 took out of the twelve GDScript runners. → §PW466
- 📋 **PW467** (deps: —) **a game's engine scripts and the line each prints are a table in a Python driver the game writes itself** — Cottony keeps three drivers that only map scripts to patterns around engine.run and capture.run, and a second game would write the same three. → §PW467

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

## Block M — What a game needs beyond the look

## Block N — Pictures held to a canon

## Block O — A person sees and answers

## Block P — Music and sound a game can ship

## Block Q — Words held to the world

## Block R — Levels measured before a person plays them

- 📋 **PW202** (deps: PW201 ⏸) **A game's own headless play of a level has no way to report what it measured** — Only the game can play its own rules, so polyweave needs a contract for what the game's probe prints, not a simulator of its own. → §PW202
- 📋 **PW203** (deps: PW201 ⏸) **A level declared as data cannot reach the engine without each game's own converter** — Cottony writes JSON from a curve and Starship hand-edits .tres waves, so neither level is validated, linked to the world or recorded before it lands. → §PW203
- 📋 **PW204** (deps: PW202, PW203) **A level's difficulty has no bar a search can aim at, and a level set has no curve to hold** — Cottony's curve constants were set by feel and never measured, so a level can be unwinnable or trivial and nothing fails. → §PW204
- 📋 **PW205** (deps: PW202, PW203) **A shooter's waves have no measure of threat, so the level contract is proven on one genre only** — A contract only Cottony's match-3 has exercised may still assume a board, and Starship's check_phase_waves counts enemies without asking how many arrive at once. → §PW205
- 📋 **PW206** (deps: PW204, PW205) **Cottony's levels are still tuned by a curve nobody measured** — The block is proven only when its first consumer's shipped levels are declared, compiled, probed and accepted here, and make_levels.py has nothing left to do. → §PW206
- 📋 **PW327** (deps: PW205) **A playtest's trace of spawns, kills and hits cannot be measured or laid against the wave it played** — A declared wave says what it asks of a player; only a trace says where players struggle, and Starship's balance needs both. → §PW327

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

## Block U — A window on everything a project governs

## Block V — Parts every game repeats, installed already proved

- 🛠 **PW370** (deps: PW345 ✅, PW357 ✅, PW394 ✅, PW395 ✅, PW396 ✅, PW397 ✅, Spinhold RK216) **Starship keeps its own bindings and co-op code after the input kits were extracted from it** — A kit proved only in a fixture has not met a game, and the game it came from is the cheapest first consumer. → §PW370
- 🛠 **PW371** (deps: PW347 ✅, PW348 ✅, PW398 ✅, Cottony RK151) **Cottony keeps its own settings and save code where the kits provide them** — The second game is what shows a kit is not one project's code moved into a folder. → §PW371

## Done when — PW36

- **Every piece of Cottony's pipeline runs on the plugin, with no fork** The
  script-built tray, the fetched prop in drawn cloth, the inflated cushion, the rig, the
  paid service and the four engine captures each pass the check the existing pipeline
  passes, against a before-side baseline recorded before that piece moved. A piece left
  behind is named, with what it needed.

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

## Done when — PW368

- **A declared skeleton read off two games' state code** Once Cottony as well as
  Starship carries a hand-written state machine, the declaration and its generated
  skeleton take the shape both share, checked by engine.states as it stands.

## Done when — PW372

- **Each shot of a built camera clip is captured onto a sitting** One operation captures
  the game at every shot of a clip.camera scene and lays the frames on a sitting, so a
  person accepts or refuses the framing on the review page.
- **Starship's opening plays a clip.camera scene, not its own JSON**
  game/ui/opening_shots.json is replaced by a *.camera.toml built with clip.camera, and
  opening.gd seeks the built scene, mapping places on the ring through its place
  Callable.

## Done when — PW450

- **One family's canon trains a real Scenario model within the ceiling** With the
  owner's Scenario key and a [budget.scenario] ceiling, style.train trains on a canon of
  five or more, and a picture bought from the model passes or fails the family's gate
  with its record naming the model and its members.

## Done when — PW57

- **check_pieces.py's three rules are specs, or a person keeps them as a test** Each of
  ink on the faced kinds, no pale ring of marks round a rim, and the kinds' silhouettes
  kept apart is either a predicate in a Cottony acceptance spec over the committed piece
  sheet, or recorded as a test a person chose to keep.

## Done when — PW466

- **Every script that starts Godot in Cottony does it one way, and says what applied**
  No tool under Cottony's tools/ calls subprocess on Godot: tests, boot and export each
  go through a polyweave operation, and CI's verdicts are the same before and after on
  one tree.

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
