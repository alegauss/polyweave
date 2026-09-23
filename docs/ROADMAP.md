# Roadmap (active backlog)

## Block A — What a tool call costs the turn

## Block B — Seeing the result cheaply

## Block C — The asset compiler

## Block D — Fetching from a paid service without surprise

## Block E — One world with the engine

## Block F — Motion

## Block G — Geometry as a declaration

- 📋 **PW68** (deps: —) **a built mesh has no texture coordinates, so a drawn panel is the right shape wearing nothing** — A mesh here is vertices and faces, and Cottony's panel route builds a UV layer as it lifts the grid, because the drawing that shaped it is also its face. → §PW68

## Block H — Proof on a real game

- ⏳ **PW54** (deps: PW50 ✅, PW60 ✅, PW67 ✅, PW68) **a Cottony shape is a bmesh program that exists only inside a bake, so nothing can read, diff or search it** — The drawn panels are cloth.cushion, which is a drawing's alpha blurred into a height field on a grid, carrying the UVs that make it its own face. → §PW54
- 📋 **PW57** (deps: PW53 ⏸) **every Cottony look gate restates its own floor, so no asset has a bar a search can aim at** — Five check scripts measure after the render is spent, which is a verdict and never a target, and a threshold moved in one of them is invisible to the rest. → §PW57
- 📋 **PW59** (deps: PW53 ⏸, PW54 ⏳, PW55 ✅, PW56 ⏸, PW57, PW58 ✅) **nothing says how much of Cottony still does its own version of what the plugin does** — Adoption is asserted per asset, so a hand-rolled rig, gate or runner can come back without anything failing, and 100% stays an opinion. → §PW59

## Done when — PW36

- **Every piece of Cottony's pipeline runs on the plugin, with no fork** The
  script-built tray, the fetched prop in drawn cloth, the inflated cushion, the rig, the
  paid service and the four engine captures each pass the check the existing pipeline
  passes, against a before-side baseline recorded before that piece moved. A piece left
  behind is named, with what it needed.

## Done when — PW54

- **Every shape those two scripts build is a declaration that builds here** The tray and
  the star are done: tests/fixtures/cottony/*.toml build through geometry.build, at the
  arithmetic their own constants do. What is left is the panels, which are cloth.cushion
  inflating a drawn PNG rather than composing primitives.
- **A ported model keeps both its materials all the way to a render** The tray is a
  cream rope rim on a cushion face, and the join that makes it one output keeps one
  material or none (§PW67). Checked by reading the two colours off what a build returns,
  rather than off the document that stated them.

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
