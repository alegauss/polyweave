---
name: polyweave
description: Drive the polyweave plugin to make or change a 3D asset - build a geometry declaration, check a render or sprite against its acceptance spec, search a rig for values that pass, and record the verdict. Use when a project has *.accept.toml specs or geometry declarations, when asked to bake, render, port or check an asset, or when a script imports polyweave.
---

# Driving polyweave

polyweave makes an asset by **declaring what it must satisfy** and letting a search find
the numbers. You do not tune by eye: you state the bar, and the tool reports how close
each render came.

Every operation is an MCP tool (`polyweave` server) and a subcommand
(`python -m polyweave <operation> --<param> <value>`). Their names and parameters come
from one registry, so `describe` is always current.

## The loop: four calls

1. **Brief.** `asset.brief --asset <name>` says where the asset stands in one read: its
   declaration, each predicate and where its bound came from, whether the artefact still
   matches its record, and the last verdict. Start here, not by opening files.
2. **Build.** `geometry.build --source <declaration>` builds a shape; `--given` sets its
   params as one JSON table, and `--preview true` writes a cheap look.
3. **Search.** `search.sweep --spec <spec> --out <picture>` turns only the parameters the
   spec permits under `[search]`, and spends a stated number of renders. Add `--job` to
   get a handle; `job result <handle>` collects it.
4. **Check.** `accept.check --spec <spec> --subject <picture>` returns every predicate's
   value, verdict, margin and headroom. `accept.verify` checks every committed artefact.

## Rules that save a call

- **A look is a person's to accept.** You never decide a render is right. Put the review
  sheet in front of a person (`verdict.sheet`) and carry their words with
  `verdict.judge`. Never call `calibrate.apply` to loosen a bound a person set.
- **Nothing here spends money on your judgement.** A paid fetch needs a budget a person
  set; `purchase.remaining` says what is left.
- **A refusal is the answer.** It carries `code`, `remedy`, and where a name was wrong,
  `allowed` and `did_you_mean`. Use them; do not guess again.
- **Ask the cheapest rung.** `render.plan --asking '["saturation_p99"]'` says which rung
  can answer before a render is spent.

## Look up only when needed

- [references/operations.md](references/operations.md): the operations by task.
- [references/specs.md](references/specs.md): the acceptance spec's shape and where a
  bound's number comes from.
