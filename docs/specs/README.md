# Specs

A spec here is a **contract more than one roadmap line depends on** — a file format, a
vocabulary, or a behaviour every tool obeys. It exists because a rationale section in
`docs/IMPROVEMENTS.md` is capped at 250 words and says *why*, and a format needs to say
*what*, at whatever length that takes.

These files are ordinary documents. Nothing governs them, and they are edited directly —
unlike `docs/ROADMAP.md`, `docs/CHANGELOG.md` and `docs/IMPROVEMENTS.md`, which belong to
roadkeep and refuse a hand edit.

**Status: part built.** [tool-surface.md](tool-surface.md), [project-config.md](project-config.md),
[provenance.md](provenance.md), [rungs.md](rungs.md), [fetching.md](fetching.md) and
[engine.md](engine.md) describe code that exists; the rest is still ahead of its code. Each spec is settled enough to build against, and the first
implementation that disagrees with one is evidence about the spec, not only about the code —
which is why §1 now names a heartbeat and a `sweep` that its first implementation needed.

| Spec | What it fixes | Lines it binds |
|---|---|---|
| [tool-surface.md](tool-surface.md) | How every call behaves: handles, post-conditions, errors, self-description, conventions | PW1–PW6 |
| [project-config.md](project-config.md) | What a project declares, and how a value is resolved | PW5 |
| [measurements.md](measurements.md) | The closed vocabulary a comparison may return | PW8–PW11 |
| [rungs.md](rungs.md) | The preview ladder: what each rung is, and which question it carries | PW7, PW13–PW15 |
| [context.md](context.md) | Judging an asset where it will be seen, and what survives at display size | PW10, PW15 |
| [fetching.md](fetching.md) | Buying a mesh: the shape check, the ledger, the schema, the reference | PW16–PW21 |
| [engine.md](engine.md) | Running a scene script, and reading a verdict rather than an exit code | PW22 |
| [acceptance-spec.md](acceptance-spec.md) | What "correct" means, as a file a search can aim at | PW12, PW13, PW15 |
| [geometry.md](geometry.md) | A shape as data rather than as a program | PW30–PW34 |
| [provenance.md](provenance.md) | What is recorded beside an artefact, and the cache key | PW6, PW14, PW17 |

## Two format rules, so nobody has to decide twice

**TOML for documents a person authors or reads** — the project config, an acceptance spec, a
geometry declaration. **JSON for records a machine writes** — provenance sidecars, job state,
ledgers, cache entries. The split is about who edits the file, not about what is in it.

A document may also arrive as JSON where a caller emits it programmatically. A record never
arrives as TOML.

## Deliberately not specced yet

- **The clip and curve format** (PW28). It depends on decisions PW26 makes about skeletons,
  and a format written before them would be guessing. PW28's own section holds the
  requirements until then.
- **The paid-service lock and ledger** (PW17, PW18). One file written by one task, and
  §PW17 already pins its fields. It becomes a spec here if a second consumer appears.
- **The MCP tool list.** Which calls exist is implementation, and it follows from
  [tool-surface.md](tool-surface.md) rather than needing its own document.
