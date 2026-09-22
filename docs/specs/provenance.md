# Provenance and the cache key

Binds **PW6, PW14**, and is what §PW17's records are built on.

A path-traced bake is not byte-reproducible. Two runs of one unchanged Cottony scene differed
in 29,696 pixels, none by more than 1/255. So when a render changes, nothing in the file says
whether the scene moved, a library moved, or the sampler simply landed elsewhere. The record
below is what makes that answerable.

## The sidecar

JSON, written beside every artefact this plugin produces, named `<artefact>.prov.json`.

```json
{
  "artefact": { "path": "docs/design/art/ui/mascot.png", "sha256": "9f2c…", "bytes": 148213 },
  "kind": "render",
  "produced_at": "2026-09-22T14:08:31Z",
  "elapsed_s": 121.4,
  "producer": { "tool": "polyweave", "version": "0.3.1" },
  "engine": { "name": "cycles", "version": "4.2.1", "bindings": "bpy 4.2.0" },
  "rung": "final",
  "seed": 20260922,
  "samples": 512,
  "inputs": [
    { "role": "mesh",  "path": "tools/art/3d/mascot.glb",      "sha256": "41ab…" },
    { "role": "cloth", "path": "docs/design/art/ui/cloth.png", "sha256": "c7de…" }
  ],
  "params": { "light": 2.7, "form": 2.5, "ambient": 0.4, "fill": 0.92 },
  "measurements": { "saturation_p99": 0.87, "alpha_coverage": 0.41 }
}
```

`kind` is `render`, `mesh`, `capture` or `fetch`. A `fetch` carries the service fields §PW17
requires — task id, prompt or reference hash, credits consumed — in the same record rather
than a second one.

It costs nothing to write and it is the only thing that makes a difference explicable weeks
later. It is also what lets a regression be bisected: a render that got worse is compared
against the record of the last one that was right, and the fields that differ are the suspect
list.

## The cache key

The key is a sha256 over a canonical form of a **defined subset** of the record. Stating the
subset exactly is what makes returning a hit safe rather than merely likely to be right.

**In the key:** `kind`, `producer.version`, `engine.name`, `engine.version`,
`engine.bindings`, `rung`, `seed`, `samples`, every `inputs[].sha256` with its `role`, and
every entry of `params`. For a geometry build, the declaration's own sha256 and the sha256 of
any `custom` node's source file.

**Not in the key:** `produced_at`, `elapsed_s`, `artefact`, `measurements`, and every input's
`path`. A file that moved is the same input; a file that changed is not.

### Canonicalisation

Three rules, each of which exists because its absence splits the cache:

1. **Keys sorted**, arrays in declaration order, no insignificant whitespace.
2. **Floats rounded to 6 decimal places** before serialising. Without this, `0.1` and
   `0.10000000000000001` are different keys for the same render.
3. **Paths relative to the project root, forward slashes.** A key computed on Windows and one
   computed elsewhere must agree.

The subset is serialised as a **flat object**, so that naming the fields is enough to
reproduce the key:

```json
{"engine_bindings":"bpy 4.2.0","engine_name":"cycles","engine_version":"4.2.1",
 "inputs":[{"role":"mesh","sha256":"41ab…"}],"kind":"render",
 "params":{"form":2.5,"light":2.7},"producer_version":"0.3.1","rung":"final",
 "samples":512,"seed":20260922}
```

An input each carries only `role` and `sha256`, in the order the operation declared them.
An absent field is `null` rather than omitted, so adding a field later changes every key
exactly once rather than only for the records that happened to carry it.

## Layout

```
.polyweave/
  cache/<key[:2]>/<key>.png      the artefact
  cache/<key[:2]>/<key>.json     its record
  jobs/<job>.json                handle state (tool-surface.md §1)
```

`.polyweave/` is gitignored. Artefacts that belong to the project — the sprite the game
loads, the mesh that was paid for — live in the project's own tree with their `.prov.json`
beside them, and those **are** committed. A paid mesh and its record are one artefact and are
committed together; §PW17 is thirty credits of evidence for that rule.

Eviction is least-recently-used against `[cache] max_bytes`. A record whose artefact is
missing is dropped rather than repaired.

## Two behaviours, not just a format

- **A hit is reported as a hit.** A caller timing a sweep needs to know what it actually
  measured, and a cache that silently answers in 4 ms makes a benchmark meaningless.
- **Preview rungs are cached too.** Those are the renders a search asks for thousands of
  times; the final ones are asked for once. A cache that only stores the expensive results
  has optimised the rare case.

## Verification

`verify` walks every `.prov.json` in the project and answers one question: is every artefact
the records claim to hold actually present, and does it still hash to what was written down.
Today nothing can answer that at all, which is how a paid mesh came to be recorded and lost.

It **reports rather than refuses**, because the answer to "what is missing" is a list and one
broken record must not hide the next. Four outcomes per record: sound, the artefact is
**missing**, the artefact **changed** — with both digests, so the difference is attributable
— or the record itself is **unreadable**.

An input that lives outside the project tree is recorded by its absolute path rather than
refused. Paths are not in the key, so a shared library outside the tree still yields the same
key on another machine; what it costs is that the record alone does not say where to find
that file on a machine that has it elsewhere.
