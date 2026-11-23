# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

- 📋 **PW721** (deps: —) (from: urdido) **capture.web cannot scroll to a sentence the page prints or draw a highlight over it** — A video that quotes a published page films it with a Playwright script of its own, outside the visit's record. → §PW721
- 📋 **PW725** (deps: —) **A review window of a cut decodes and filters every clip before it, so a late window costs nearly a whole render** — Reviewing the end of a long cut is as slow as exporting it, which is the cost PW713 set out to remove. → §PW725
- 📋 **PW726** (deps: —) **stock.find answers a hit a media library already rejected as if it were a new candidate** — A clip a person turned down is fetched and reviewed again before the library's refusal surfaces. → §PW726

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

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

- 📋 **PW327** (deps: PW205 ✅, Spinhold RK313) **A playtest's trace of spawns, kills and hits cannot be measured or laid against the wave it played** — level.trace reads traces already; Spinhold RK313 writes them from real play, then the declared curve and a spec over both follow. → §PW327
- 📋 **PW722** (deps: —) **level.curve refuses a pair whose difference equals its step, by floating-point rounding** — A set sitting exactly on its declared step reads as broken, as Cottony's levels 10 and 11 did at 0.06. → §PW722
- 📋 **PW723** (deps: —) **A level search samples a fraction for an integer key and probes a value it already measured** — Each wasted candidate is 50 games in Godot, and a trace naming 22.5 moves reads as a level that cannot exist. → §PW723
- 📋 **PW724** (deps: —) **level.probe refuses a level that has no file, so a game's fallback curve past its shipped levels cannot be probed** — Cottony's endless tail is the formula alone, and checking it meant writing an empty level file per sampled number. → §PW724

## Block S — Playing the game, not only rendering it

## Block T — Adopting polyweave in a project

## Block U — A window on everything a project governs

## Block V — Parts every game repeats, installed already proved

## Block W — A core that grows by layers

## Block X — The site on the shared design system

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

## Done when — PW327

- **a played phase's trace is read beside its declared curve and held to a spec**
  Spinhold's runs write the event trace, the probe gives the declared pressure per
  second, level.trace lays the two together, and accept.check holds bounds a person set
  (alive never above N, a peak above the phase before), naming the rule broken.

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
