# Roadmap (active backlog)

## Block A — What a tool call costs the turn

- 📋 **PW51** (deps: —) **a record says nothing about the tolerances its measurements were taken against** — Reading the config back gives the project's numbers now, not the artefact's, so two records carrying one measurement can mean different things and nothing says which. → §PW51
- 📋 **PW52** (deps: —) **a render holding two opaque pixels in one corner is empty for every purpose and passes every check** — Coverage clears the alpha floor and the two pixels differ, so neither assertion fires, and the obvious number to compare against would refuse a correctly framed thin asset. → §PW52

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

- 📋 **PW46** (deps: —) **a normalised mesh sits beside the paid one with nothing recording what it derives from** — Ingest writes a second file and returns the transform to its caller, so the mesh the project loads is one `verify` reads as an artefact nothing recorded. → §PW46
- 📋 **PW49** (deps: —) **a fetched mesh arrives with shading painted into its texture, and nothing can take the marks back out** — Those marks are shadows that do not move when the light does, and Cottony had to keep its own scrub pass with three thresholds found by eye, which is the fork adoption tests for. → §PW49

## Block E — One world with the engine

- 📋 **PW47** (deps: PW24 ✅) **a bake renders square at the rung's size, so a declared world rectangle can be refused but never met** — PW24's contract names the size a sprite must be, and nothing renders at it: the size is the rung's, and it is not in the cache key either. → §PW47

## Block F — Motion

## Block G — Geometry as a declaration

- 📋 **PW50** (deps: —) **a fuzzy surface cannot be declared at all, because shell texturing is a technique and no table holds one** — Cottony's plush look is eight constants found by eye, and a table of eight keys would be one project's look compiled in while helping nobody who wanted fur instead. → §PW50

## Block H — Proof on a real game

- 📋 **PW48** (deps: —) **every test input is synthetic, so nothing is ever checked against an artefact somebody made** — The suite has no real mesh, photograph or capture in it, and those are where every symptom in this backlog was measured in the first place. → §PW48

## Done when — PW36

- **Every piece of Cottony's pipeline runs on the plugin, with no fork** The
  script-built tray, the fetched prop in drawn cloth, the inflated cushion, the rig, the
  paid service and the four engine captures each pass the check the existing pipeline
  passes, against a before-side baseline recorded before that piece moved. A piece left
  behind is named, with what it needed.

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
