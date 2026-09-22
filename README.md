# polyweave

A Claude Code plugin for making 3D assets — geometry, surface and motion — on top of
Blender, Godot and a generative mesh service.

The premise: generating a mesh is the cheap part. The expensive part is everything between
*having a mesh* and *knowing it is right*, and today that is a person changing one number at
a time and looking at a two-minute render. polyweave aims to close that loop — you state
what the asset has to satisfy, and it searches for the parameters that satisfy it, measuring
against the reference rather than against an opinion.

It is built for an agent to drive. No GUI, no account, no hosted service: it runs on your
machine against files in your own repository.

## Status

Design stage. There is no code yet — `docs/ROADMAP.md` holds the plan, in eight blocks:

| Block | |
|---|---|
| A | What a tool call costs the turn |
| B | Seeing the result cheaply |
| C | The asset compiler |
| D | Fetching from a paid service without surprise |
| E | One world with the engine |
| F | Motion |
| G | Geometry as a declaration |
| H | Proof on a real game |

Every line in that file was drawn from a failure measured in a real project. `docs/ROADMAP.md`
also carries the non-goals, which say what this deliberately will not be.

## Roadmap docs

`docs/ROADMAP.md`, `docs/CHANGELOG.md` and `docs/IMPROVEMENTS.md` are maintained by roadkeep
and are not edited by hand — `python .roadkeep/scripts/roadkeep.py` is the entry point here.

`docs/specs/` is the other half: the contracts that more than one roadmap line depends on — a
file format, a vocabulary, a behaviour every call obeys. Those are ordinary documents, edited
directly, and they are settled enough to build against.

## The site

`site/` is the public page, at `alegauss.github.io/polyweave/` once Pages is pointed at the
`site` workflow. It describes the product the roadmap specifies, in the present tense, and
says on the page — second, above everything but the hero — that none of it is built.

Everything it counts is generated from `docs/ROADMAP.md` through roadkeep rather than typed,
so the page cannot disagree with the file, and `npm test` fails the build if the page stops
saying there is no implementation. See [`site/README.md`](site/README.md).
