# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

- 📋 **PW625** (deps: —) **purchase.remaining refuses a ceiling with no expiry and says, as its reason, that it never lapses** — Cottony's 90 credits read left 0 and not spendable, with a why that argued the opposite and named no door. → §PW625
- 📋 **PW626** (deps: —) **reference.prepare cuts every pixel near the edge colour, so a subject sharing a hue with its ground loses parts** — Cottony's rainbow ball lost its blue and green bands and the star most of its tail to the well's blue. → §PW626
- 📋 **PW627** (deps: —) **mesh.buy cannot buy a textured mesh, so a toy whose colours make it must go through a project client** — Cottony's booster toys are fetched textured and had to bypass the ceiling and ledger through meshy.py. → §PW627
- 📋 **PW628** (deps: —) **port.run bakes nothing when one member fails and takes no member list, so passing members wait on an unrelated one** — Cottony's two re-bought toys passed but could not bake beside an unchanged ball failing its spec. → §PW628
- 📋 **PW629** (deps: —) **a recorded flow replays in whatever locale the machine has, so a flow recorded in pt-BR fails on an English CI runner** — Every flow that reads a translated label breaks on a machine in another language, and the failure reads as a changed screen. → §PW629
- 📋 **PW630** (deps: —) **a carve's cut faces wear the plate's material, so no render can tell a pocket from the plate it is pressed into** — Composing an engraved pocket means recomputing its outline by hand from the declaration, tuned by eye to the camera. → §PW630
- 📋 **PW631** (deps: —) **inflate stripes a star outline and rings a drawn one with contour steps, so a glossy inflated shape is unusable** — Candy is glossy by rule, so inflate cannot make any candy panel or puffy shape the style guide asks for. → §PW631
- 📋 **PW632** (deps: —) **crowned over a concave outline rises in straight ridges to its centroid, so a star comes out a pyramid, never a pillow** — A puffy star or any concave plaque has to be faked from blended primitives, which loses the drawn outline. → §PW632
- 📋 **PW633** (deps: —) **a capture at a window resolution sizes the viewport to its pixels and ignores the project's stretch** — A game laid out by canvas_items and expand is captured at a layout no player gets, unless the project does the stretch arithmetic itself. → §PW633
- 📋 **PW634** (deps: —) **a bought mesh cannot be brought down to a game's triangle and texture budget; no operation decimates or downsizes** — Cottony's booster toys are 104k triangles on a 4096 texture each, so loading them live would take most of a 24 MB build. → §PW634
- 📋 **PW636** (deps: —) **vfx.preview films only in 3D, so an effect drawn on a 2D canvas has no sitting of its own** — A drift between panels is judged only inside the whole screen, where a change to it cannot be laid beside the drift as it was. → §PW636

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
- 📋 **PW608** (deps: PW203) **a declared level schema gives the engine no typed reader and gives a game's tools no field bounds, units or help** — Each level key is written again in the reader, the editor and the docs, and the three drift apart. → §PW608
- 📋 **PW609** (deps: PW203) **an accepted reference transcription cannot become a draft level, so its rows are retyped into the level file by hand** — Retyping what a person already settled row by row costs a session per stage and brings back the slips the sitting removed. → §PW609

## Block S — Playing the game, not only rendering it

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
