# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

- 📋 **PW654** (deps: —) **no operation enlarges a corner of a capture, so a HUD icon a few pixels wide cannot be judged** — Checking small UI parts falls to a hand-run crop script on every retake. → §PW654

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

- 📋 **PW658** (deps: —) **picture.buy writes only PNG, so a web project re-encodes to WebP outside polyweave and ships a file with no provenance** — A site needing WebP under a byte bound converts by hand, and credits name a file the release does not carry. → §PW658
- 📋 **PW659** (deps: —) **picture.buy on Ideogram 4.0 returns another aspect ratio than asked, and the record holds both with no warning** — The caller pays for a 16x9 picture, gets 3x2 unannounced, and crops by hand after the spend. → §PW659
- 📋 **PW660** (deps: —) **provenance.credits lists only owed credits, so a per-asset source and licence manifest is built from .prov.json by hand** — A package that must name every image's source and licence reads polyweave's records with its own script and types the licence. → §PW660

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

- 📋 **PW655** (deps: —) **engine.sweep flies headless, so a capture script saves no picture and every combination ends in a script error** — Measuring variants over seeds falls to a hand-written loop of capture.run calls. → §PW655

## Block I — Voxel models from a declaration

## Block J — A bar a person sets once

- 📋 **PW656** (deps: PW637 ✅) **a first spec's bound on a value near zero is a share of almost nothing, so the same picture redrawn fails it** — Spinhold's dark glass got a max of 0.006 where its own hand-written spec held 0.1049, and calibrate.run cannot widen a picture it did not render. → §PW656

## Block K — Reached without reading the source

## Block L — What a run leaves as evidence

- 📋 **PW653** (deps: —) **a capture hashes a class_name script from a stale copy under .polyweave, so an edited script reads as undeclared** — An edit-and-capture loop reads as nondeterminism, so the honest fix is to switch the record off and lose provenance. → §PW653

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
- 📋 **PW608** (deps: PW203) **a declared level schema gives the engine no typed reader and gives a game's tools no field bounds, units or help** — Each level key is written again in the reader, the editor and the docs, and the three drift apart. → §PW608
- 📋 **PW609** (deps: PW203) **an accepted reference transcription cannot become a draft level, so its rows are retyped into the level file by hand** — Retyping what a person already settled row by row costs a session per stage and brings back the slips the sitting removed. → §PW609

## Block S — Playing the game, not only rendering it

- 📋 **PW651** (deps: —) **the MCP server runs a stale installed copy of polyweave, and no answer says which copy replied** — Every call had to go through the CLI, and the refusal never said two copies of polyweave were in play. → §PW651
- 📋 **PW652** (deps: —) **the remap kit keeps an English-wide label column, so pt-BR labels run into their controls** — A game in Portuguese ships a Controls screen whose words collide, and the host cannot fix the kit's layout. → §PW652
- 📋 **PW657** (deps: PW640 ✅) **nothing reads a game's scripts for play timed by frames, so a drift is found only after a replay parts** — Spinhold's four frame-timed causes were each a pattern a check could name at its line before any run, and game.replay_rates sees only the state kit's names. → §PW657

## Block T — Adopting polyweave in a project

## Block U — A window on everything a project governs

## Block V — Parts every game repeats, installed already proved

## Block W — A core that grows by layers

## Block X — The site on the shared design system

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

## Done when — PW582

- **Cottony keeps no mesh preparation of its own** tools/art/prep.py and export_props,
  export_boosters and export_friends are gone from Cottony, its families name prepare
  steps through fixes, and project.adoption lists none of them as kept.

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
