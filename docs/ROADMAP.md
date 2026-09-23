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
- 📋 **PW75** (deps: —) **a project that has made every capture reproducible has no way to keep it that way** — Cottony's four captures now reproduce byte for byte, and `reproduced` is a report no gate reads, so the next change that unpins one writes its bytes and passes. → §PW75

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
