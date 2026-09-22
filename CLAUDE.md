# polyweave

A Claude Code plugin for making 3D assets — geometry, surface and motion — by **declaring
what an asset should be** and letting a machine search for the parameters that satisfy it,
on top of Blender, Godot and a generative mesh service.

There is no code yet. `docs/ROADMAP.md` is the whole project.

## The one thing to keep in mind

**The caller is an agent in a terminal, not a person at a screen.** Every design decision
here is judged by whether an agent gets it right on the first call, without reading the
implementation. That is what the first block is about, and it is why a feature that needs a
GUI, a second round trip or a source read to use is a feature that has not landed.

## Where the evidence comes from

Nearly every symptom in the backlog was measured in **Cottony** (`D:\Git\viglet\cottony`),
which is the first consumer and the thing Block H adopts the plugin onto. Two files there
are worth reading before designing anything:

- `tools/art/bake_model.py` — the fourteen-parameter render rig, every constant of which was
  found by hand at two minutes a sample. This is the cost the plugin exists to remove.
- `.claude/skills/cottony-art-pipeline/SKILL.md` — which pipeline an asset belongs in, why a
  look is measured at a percentile and never a mean, and the two silent failures that each
  cost a render.

Also `tools/art/solid.py` (the geometry vocabulary Block G is read off), `tools/art/meshy.py`
(the paid-service client Block D generalises) and `tools/capture_screens.py` (the Godot
runner Block E replaces).

## The specs are where a format lives

`docs/specs/` holds the contracts more than one roadmap line depends on — the tool surface,
the project config, the measurement vocabulary, the acceptance spec, the geometry declaration
and the provenance record. Read the one that covers what you are about to build, because a
rationale section in `docs/IMPROVEMENTS.md` is capped at 250 words and says *why*, while the
spec says *what*. `docs/specs/README.md` indexes them and says what is deliberately not
specced yet.

Those files are ordinary documents and are edited directly. The three below are not.

## The docs are governed

`docs/ROADMAP.md`, `docs/CHANGELOG.md` and `docs/IMPROVEMENTS.md` belong to roadkeep. A hand
edit is refused — call the CLI, which is wired at `.roadkeep/scripts/roadkeep.py`. The skill
at `.claude/skills/roadkeep/` is the reference; `roadkeep brief` starts a task and
`roadkeep lint` is the gate.

Read `roadkeep non-goal list` before proposing anything. Five constraints bind this project,
and the sharpest is that **nothing here spends money on an agent's own judgement**.

## One task, one commit

Each finished roadmap task ends in one local commit — the code and the doc sync together,
staged by path, never pushed. Use `run-commit.cmd -m "<conventional-commits title>"`.
