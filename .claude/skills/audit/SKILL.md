---
name: audit
description: Full audit of polyweave — runs the gates, scans the tree in parallel with the scanner agent, deduplicates, verifies with the verifier agent, then reconciles the roadkeep backlog against the code, the specs and the confirmed findings. Use when asked to audit, review the whole repository, hunt debt, look for defects outside a specific change, or check whether the roadmap still matches the code.
---

An audit of this repository, from the gates to the backlog. `/code-review` reads a diff;
this reads the project at rest. It fixes no code: the product is a reconciled backlog, not
a patch.

**This project's shape decides how much of the audit is worth running.** polyweave started
as a roadmap and a set of drafted specs, and the code arrives block by block. Where the
tree holds little code, steps 2–4 are small and steps 5–6 are the whole product: the
question worth asking is whether the backlog and the specs still agree with each other and
with what has been built. Do not skip the scan because the tree looks empty — scan what is
there — but do not manufacture eight partitions for four files either.

## 1. The gates first — the baseline

Note `git status --short` and `git rev-parse --short HEAD`: another session may share this
checkout, and its files are not the audit's.

Then **discover the gates rather than assuming them**, because this project's command list
is still growing: read `pyproject.toml`, a `Makefile` or `noxfile.py`, and
`.github/workflows/` for the commands that actually run. Run them in the cheap-to-expensive
order they declare, keeping every output. Two exist regardless:

```
python --version
roadkeep lint        # the three governed docs
```

`python ".claude/hooks/roadkeep-launch.py"` is the entry point where `roadkeep` is on no
PATH; the vendored `.roadkeep/scripts/roadkeep.py` is the same engine.

Then establish what this machine **cannot** answer, once, and hand it down with the
baseline: whether `import bpy` works, whether the engine binary in `[paths] godot` is
reachable, whether the service key variable named by `[service] key_env` is set. Each
missing one makes a whole class of finding unverifiable, and none of them fails with a
message naming the cause.

What already fails is **baseline**, not a finding. Hand it to every agent below so nobody
re-reports it.

## 2. One `scanner` per partition, in parallel

Check coverage first: `Glob` the source tree (`**/*.py`, plus any `*.gd`, `*.toml` and
`*.json` the plugin ships) and make sure every file lands in **exactly one** row. A file no
row names goes to the row of the block whose subject it shares.

**Partition by the roadmap's blocks**, not by directory depth, because that is how this
project's work is organised and how the reconciliation in step 6 will file what you find.
Run `roadkeep block list` for the current set; today it answers:

| Block | Subject                                        |
| ----- | ---------------------------------------------- |
| A     | What a tool call costs the turn                |
| B     | Seeing the result cheaply                      |
| C     | The asset compiler                             |
| D     | Fetching from a paid service without surprise  |
| E     | One world with the engine                      |
| F     | Motion                                         |
| G     | Geometry as a declaration                      |
| H     | Proof on a real game                           |

Collapse blocks whose code is thin into one row, and split a row that has grown past roughly
5k lines. Aim for rows of comparable size; a row of 200 lines and a row of 6k in the same
run is a scan that finished early and a scan that skimmed.

Then one `scanner` call per row, **all in one message**. Each prompt carries its row's name,
its file list, the spec that binds it (`docs/specs/`), and the baseline — nothing about the
other rows.

Two rows exist even with no code at all, and they are worth running on their own:

- **the specs** — `docs/specs/*.md` read against each other: a measure named in
  `acceptance-spec.md` that `measurements.md` does not define, a convention restated in two
  files with two values, a field in the `provenance.md` cache key that `project-config.md`
  cannot supply, a spec binding a task id that no longer exists.
- **the plugin's own wiring** — `.claude/`, `.mcp.json`, `roadkeep.toml`, `.gitignore`,
  `CLAUDE.md`, `README.md`: a hook pointing at a file that is not there, a path that is
  right on one platform only, `.polyweave/` missing from `.gitignore`, a document
  contradicting a spec.

## 3. Deduplicate

The same defect in the same file from two scanners → one entry, both reproductions kept.
The same defect in several files → one entry listing every site: that is one backlog line,
not seven. Most severe first.

## 4. One `verifier` in FINDINGS mode

One call, its prompt starting `MODE: FINDINGS`, with the whole deduplicated list and the
baseline. It needs the full list to close findings in batches by command; one verifier per
row would run the test suite once per row.

With no findings at all, say so and go straight to step 5. The backlog reconciliation is not
conditional on the scan.

## 5. One `verifier` in ROADMAP mode

Read the open backlog through roadkeep, never by opening `docs/ROADMAP.md`:

```
roadkeep list        # every open line, verbatim
roadkeep unclosed    # open lines whose work the history already names
```

One call, its prompt starting `MODE: ROADMAP`, with both outputs and the CONFIRMED findings,
so it can spot overlaps. It returns one line per task —
`task-id | status | evidence | text` — and a `COVERED` line for each finding an open task
already holds.

## 6. Reconcile, through roadkeep only

The three governed files are written by the tool, and a hook refuses a hand-edit. The
`mcp__roadkeep__*` tool of the same name is the first choice; the CLI is the same engine, and
`python .claude/hooks/roadkeep-launch.py` is the fallback. Run `roadkeep show <id>` before
touching a line. The `roadkeep` skill has the flags.

| Verifier said   | Command                                                                                                                                  |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| ALREADY DONE    | `roadkeep ship <id> --why "<outcome>"`.                                                                                                  |
| OUTDATED        | `roadkeep retire <id> --reason "<reason>"`, adding `--superseded-by <id>` or `--folds-into <id>` when another line takes the work.        |
| NEEDS REWORDING | `roadkeep restate <id> --symptom "…"` for the claim, `roadkeep amend <id> --why "…"` for the why. A line too broad is restated narrower and the rest filed as a new line. |
| STILL VALID     | Nothing.                                                                                                                                 |

This project declares no decisions file (`roadkeep.toml` governs the roadmap, the changelog
and the improvements, and nothing else), so a rule that must outlive the line it was found in
belongs in the ship's `--why` or, where it is a contract, in the spec that owns it. A spec
edit is an ordinary edit — `docs/specs/` is not governed — and it is a change to a draft, so
say in the report that you made one.

Then file each CONFIRMED finding no `COVERED` line claims — one line per finding, or per
pattern:

1. `roadkeep delivered <block> --near "<symptom>" --open` — the duplicate check, before an id
   is spent. An open line that says the same thing takes the finding into its design
   (`roadkeep section amend`), not a new line; a shipped one means a regression — file it and
   name the shipped id in the why.
2. Pick the block by subject from `roadkeep block list` — the table in step 2.
3. Read `roadkeep non-goal list` before writing the line. Five constraints bind this project,
   and the sharpest is that **nothing here spends money on an agent's own judgement**; a
   finding whose fix crosses one of them is not a backlog line, it is a note in the report.
4. Write the design to a scratchpad file, then:
   `roadkeep add --block <X> --symptom "<what does not work>" --why "<one sentence.>" --status 📋 --section "<title>" --section-body-file <path>`.
   The symptom says what does not work, never the fix. 📋 when the section names the
   mechanism; 💭 only when a question no code can answer blocks the start — 💭 is `undesigned`
   here and hides the line from `pick --designed`.

Close with `roadkeep lint`; each finding it reports names its own door, and `roadkeep repair`
applies the one-command ones. Then
`Select-String docs\*.md -Pattern '</section_body>|</invoke>'` must count 0: an inline MCP
body can leak its closing markup, and lint stays green over it.

FALSE POSITIVE and UNVERIFIABLE findings are not filed. If roadkeep is unreachable — no MCP,
no CLI, no launcher — stop here and write the same reconciliation to `docs/AUDIT.md` as a
dated section instead.

Do not commit. An audit is not a task: the reconciliation stays in the tree for the user to
read in `git diff docs/`, and another session's files may share the tree. Offer a commit of
`docs/` alone — `run-commit.cmd -m "docs: reconcile the backlog with the <date> audit"` — and
never push.

## 7. Report counts only

```
findings: raw N · after dedupe N · CONFIRMED N · FALSE POSITIVE N · UNVERIFIABLE N
tasks: kept N · closed N · removed N · rewritten N · added N
baseline: <gates already red, or "clean"> · unavailable: <blender/engine/key, or "none">
specs touched: <files, or "none"> · uncommitted: git diff docs/
```

Do not repeat the findings; they are in the backlog now. If a CONFIRMED finding is small and
obvious, offer to fix it as the next task. Do not fix it inside the audit.
