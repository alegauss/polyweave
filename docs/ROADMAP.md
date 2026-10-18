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
- 📋 **PW523** (deps: —) **the saves kit's proof writes to one fixed user:// folder, so two proofs at once empty each other's slots** — The gate went red once on the saves proof and passed when rerun alone, and a flaky gate teaches the next run to rerun rather than read. → §PW523
- 📋 **PW524** (deps: —) **a Blender render test's xdist worker crashes under the full gate and passes when the file runs alone** — Two render workers died with no traceback on an unchanged tree, and a gate that goes red by chance is one the next run reruns instead of reading. → §PW524
- 📋 **PW525** (deps: —) **the crash kit's mid-run kill races the game under load, so the full gate fails it and a lone run passes** — It failed twice today on trees that never touched the kit, and a kill timed by the clock instead of the game's own signal is right only on an idle machine. → §PW525

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

## Block W — A core that grows by layers

- 🛠 **PW516** (deps: PW499 ✅) **Each paid service's HTTP client is written inside the domain that buys from it, so a new service copies a client** — Meshes and pictures go through one buy() now (PW526, PW527); Scenario and ElevenLabs are still bought by their own domain code. → §PW516
- 📋 **PW517** (deps: PW503 ✅, PW508 ✅, PW512 ✅) **A project cannot add a measure of its own, so a look only its game needs is a fork, a side script or a PW line** — A project measure keeps the first-call guarantee only when it is described, bounded and recorded exactly as a built-in one is. → §PW517
- 📋 **PW518** (deps: PW504 ✅, PW517) **A project's own generator can run as a job but is no operation, so no agent finds it, describes it or searches over it** — A target named as a file path has only the worker's signature check, so the project's most-used script is the one call the surface cannot describe. → §PW518
- 📋 **PW519** (deps: PW518) **An extension would hide the gap it fills, so a measure two games both wrote never becomes vocabulary** — Friction filed as PW lines is how this vocabulary grew, and an extension point that silences the friction stops that growth unless it reports what it holds. → §PW519
- 📋 **PW520** (deps: PW512 ✅, PW516 🛠) **A project's polyweave.toml and the Python importing polyweave break on the new layout, with nothing to carry them over** — The block owes callers no compatibility, so one command must carry a project across, or every adopter pays for the break by hand. → §PW520
- 📋 **PW521** (deps: PW520, PW518) **Cottony still runs on the flat package and serves every layer, so the block is unproven on its first consumer** — A layering proven only on fixtures can still be wrong where a real game reaches into it, and Cottony reaches deepest, from Python, a rig and its own scripts. → §PW521
- 📋 **PW522** (deps: PW520) **Spinhold still runs on the flat package, so the 443 records and 30 verdicts most at stake in the break are unchecked** — Spinhold holds the most data a person judged, so it proves whether the break kept the one thing it promised to keep. → §PW522

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

## Done when — PW480

- **A kind's sample is cut and read from a frame by one call** reference.sample(frames,
  at, box, name) writes the crop under the project and answers its colour, so no
  throwaway script picks a kind's colour.
- **Resogun's phase 1 counts its pods, not its city** On Spinhold's resogun_p1 frames
  the count per frame follows the pods by eye on the sheets, with silhouette or warp-in
  where motion alone is not enough.

## Done when — PW516

- **One kernel buy() alone spends, through a Service adapter per provider** mesh_buy,
  sound_buy, picture and scenario buy through buy(service, request), which checks the
  ceiling and ledgers before submitting; a fixture service is quoted, bought, refused
  over its ceiling and reconciled.

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
