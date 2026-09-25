# Specs

A spec here is a **contract more than one roadmap line depends on** — a file format, a
vocabulary, or a behaviour every tool obeys. It exists because a rationale section in
`docs/IMPROVEMENTS.md` is capped at 250 words and says *why*, and a format needs to say
*what*, at whatever length that takes.

These files are ordinary documents. Nothing governs them, and they are edited directly —
unlike `docs/ROADMAP.md`, `docs/CHANGELOG.md` and `docs/IMPROVEMENTS.md`, which belong to
roadkeep and refuse a hand edit.

**Every spec here describes code that exists**, and is the contract that code is held to.
Which of its lines are still open is `docs/ROADMAP.md`'s to say, not this index's. An
implementation that disagrees with a spec is evidence about the spec, not only about the
code — which is why §1 names a heartbeat and a `sweep` that its first implementation
needed.

| Spec | What it fixes | Lines it binds |
|---|---|---|
| [tool-surface.md](tool-surface.md) | How every call behaves: handles, post-conditions, errors, self-description, conventions | PW1–PW6 |
| [project-config.md](project-config.md) | What a project declares, and how a value is resolved | PW5 |
| [measurements.md](measurements.md) | The closed vocabulary a comparison may return | PW8–PW11 |
| [rungs.md](rungs.md) | The preview ladder: what each rung is, and which question it carries | PW7, PW13–PW15 |
| [context.md](context.md) | Judging an asset where it will be seen, and what survives at display size | PW10, PW15 |
| [fetching.md](fetching.md) | Buying a mesh: the shape check, the ledger, the schema, the reference | PW16–PW21 |
| [engine.md](engine.md) | Driving the engine: the verdict, real pixels offscreen, units, environment | PW22–PW25 |
| [motion.md](motion.md) | A skeleton fitted to a mesh, and a clip and its curves authored once as TOML | PW26–PW29 |
| [acceptance-spec.md](acceptance-spec.md) | What "correct" means, as a file a search can aim at | PW12, PW13, PW15 |
| [geometry.md](geometry.md) | A shape as data rather than as a program | PW30–PW34 |
| [provenance.md](provenance.md) | What is recorded beside an artefact, and the cache key | PW6, PW14, PW17 |
| [world.md](world.md) | A game's names, factions and characters declared beside its prose, and the text a player reads held to them | PW196–PW200 |
| [adoption.md](adoption.md) | What one asset cost to make each way, so the claim can be falsified | PW35 |

## Two format rules, so nobody has to decide twice

**TOML for documents a person authors or reads** — the project config, an acceptance spec, a
geometry declaration, an animation clip. **JSON for records a machine writes** — provenance sidecars, job state,
ledgers, cache entries. The split is about who edits the file, not about what is in it.

A document may also arrive as JSON where a caller emits it programmatically. A record never
arrives as TOML.

## Deliberately not specced yet

- **The paid-service lock and ledger** (PW17, PW18). One file written by one task, and
  §PW17 already pins its fields. It becomes a spec here if a second consumer appears.
- **The MCP tool list.** It is served, and derived from the operation registry, so a
  document listing it would be a copy that drifts: `python -m polyweave serve` answers
  `tools/list`, and [tool-surface.md](tool-surface.md) says how each call behaves.
