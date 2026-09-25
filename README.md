# polyweave

A Claude Code plugin for making a game's parts by declaring what each has to satisfy:
3D assets (geometry, surface and motion) and the pictures they start from, sound loops
held to a seam, and the names and lines of the game's world. It works on top of Blender,
Godot and paid generators. Levels are next, on the roadmap.

The premise: generating a mesh is the cheap part. The expensive part is everything between
*having a mesh* and *knowing it is right*, and today that is a person changing one number at
a time and looking at a two-minute render. polyweave aims to close that loop — you state
what the asset has to satisfy, and it searches for the parameters that satisfy it, measuring
against the reference rather than against an opinion.

It is built for an agent to drive. No GUI, no account, no hosted service: it runs on your
machine against files in your own repository.

## Status

The status is not typed here, because a typed status goes stale: this file said "Block A
has started" a hundred shipped lines after most blocks were built. `docs/ROADMAP.md` holds
what is still open, block by block, and `docs/CHANGELOG.md` what has shipped; the site's
landing page states the count, derived from the roadmap. Every line in that file was drawn
from a failure measured in a real project, and it also carries the non-goals, which say
what this deliberately will not be.

No number anywhere is yet a measurement of polyweave: that is Block H, where a real game
adopts the plugin and the loop ledger records what an asset cost to make each way.

## The plugin

Python, under `src/polyweave`, against Python 3.11 — which is the interpreter Blender 4.2
ships, and code here may have to run inside it. It depends on numpy and Pillow, and on
nothing else. Blender is optional: `pip install -e ".[blender]"` brings `bpy` in for the
render path, and without it `capabilities()` says so and a render refuses rather than
importing a renderer nobody asked for.

It is served as a Claude Code plugin from this repository: `.claude-plugin/` holds the
manifest, `skills/polyweave/` the skill that drives it, and `python -m polyweave serve`
the MCP server every operation is exposed through.

```
python tools/gate.py     # the suite, in tests/, under a lock, stamped
python -m ruff check .   # the linter
python -m ruff format .  # the formatter
```

## Roadmap docs

`docs/ROADMAP.md`, `docs/CHANGELOG.md` and `docs/IMPROVEMENTS.md` are maintained by roadkeep
and are not edited by hand — `python .roadkeep/scripts/roadkeep.py` is the entry point here.

`docs/specs/` is the other half: the contracts that more than one roadmap line depends on — a
file format, a vocabulary, a behaviour every call obeys. Those are ordinary documents, edited
directly, and they are settled enough to build against.

## The site

`site/` is the public page, at `alegauss.github.io/polyweave/` once Pages is pointed at the
`site` workflow. It says on the page — second, above everything but the hero — how many
blocks are built and how many lines are still open.

Everything it counts is generated from `docs/ROADMAP.md` through roadkeep rather than typed,
so the page cannot disagree with the file, and `npm test` fails the build if the stated
status differs from the roadmap's. See [`site/README.md`](site/README.md).
