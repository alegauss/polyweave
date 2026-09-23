# Roadmap (active backlog)

## Block A — What a tool call costs the turn

- 📋 **PW51** (deps: —) **a record says nothing about the tolerances its measurements were taken against** — Reading the config back gives the project's numbers now, not the artefact's, so two records carrying one measurement can mean different things and nothing says which. → §PW51
- 📋 **PW52** (deps: —) **a render holding two opaque pixels in one corner is empty for every purpose and passes every check** — Coverage clears the alpha floor and the two pixels differ, so neither assertion fires, and the obvious number to compare against would refuse a correctly framed thin asset. → §PW52

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

- 📋 **PW50** (deps: —) **a fuzzy surface cannot be declared at all, because shell texturing is a technique and no table holds one** — Cottony's plush look is eight constants found by eye, and a table of eight keys would be one project's look compiled in while helping nobody who wanted fur instead. → §PW50

## Block H — Proof on a real game

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
