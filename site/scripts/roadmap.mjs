// The generator. Every roadmap line this site quotes — the eight blocks, the thirty-six
// symptoms, the five non-goals — is read out of `docs/ROADMAP.md` through roadkeep's own
// CLI and written to `src/lib/roadmap.generated.ts`, so the page and the governed file
// cannot disagree. The alternative is a second copy of the backlog typed into the site,
// which is the one list nobody keeps current: this project's whole argument is that a
// claim nobody can check is a claim nobody should make, and the site is not exempt.
//
// roadkeep is not committed here (`.gitignore` holds `.roadkeep`), so the generated module
// IS committed and this script refreshes it. Where the tool cannot be found — a clean CI
// checkout — the committed module stands and the build carries on; `roadmap.test.mjs` is
// what then checks it, against roadkeep where there is one and against itself where there
// is not.
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
export const siteDir = join(here, "..");
export const repoDir = join(siteDir, "..");
export const generatedPath = join(siteDir, "src", "lib", "roadmap.generated.ts");

/** The ways roadkeep is reachable, in the order they are tried. */
function candidates() {
  const vendored = join(repoDir, ".roadkeep", "scripts", "roadkeep.py");
  const list = [];
  if (process.env.ROADKEEP) {
    list.push({ cmd: process.env.ROADKEEP, pre: [], why: "$ROADKEEP" });
  }
  if (existsSync(vendored)) {
    for (const py of ["python", "python3"]) {
      list.push({ cmd: py, pre: [vendored], why: `${py} .roadkeep/scripts/roadkeep.py` });
    }
  }
  list.push({ cmd: "roadkeep", pre: [], why: "roadkeep on PATH" });
  return list;
}

/**
 * Ask roadkeep for the four listings, as parsed JSON, or null where it cannot be run.
 *
 * Deliberately one probe and then four calls with the same resolved command: a tool that
 * answered `block list` and then vanished for `list` would produce a module that is half
 * one revision and half another, which is worse than no module at all.
 */
export function readRoadkeep() {
  for (const candidate of candidates()) {
    const run = (args) =>
      execFileSync(candidate.cmd, [...candidate.pre, ...args, "--json"], {
        cwd: repoDir,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      });
    try {
      const blocks = JSON.parse(run(["block", "list"]));
      const tasks = JSON.parse(run(["list"]));
      const nonGoals = JSON.parse(run(["non-goal", "list"]));
      // The backlog is not only the roadmap. A line that was set aside keeps its id and
      // every line that waited on it still does, annotated `PW53 ⏸` — so without this
      // read a deferred dep is indistinguishable from an id nothing declares.
      const paused = JSON.parse(run(["list", "--role", "deferred"]));
      // roadkeep accepts three spellings for a dep — an id, a `Block X` label and a
      // range — and only it can expand the last two. Asking beats re-deriving: this
      // generator's own attempt turned `Block G` into a dangling `Block` (§PW61). One
      // call per line that has any deps at all, which is a handful, and no call decides
      // whether a token is an id.
      const resolved = {};
      for (const task of tasks.tasks ?? []) {
        if ((task.deps ?? []).length) {
          resolved[task.id] = JSON.parse(run(["deps", task.id]));
        }
      }
      return { via: candidate.why, blocks, tasks, nonGoals, paused, resolved };
    } catch {
      // the next candidate, or none
    }
  }
  return null;
}

const q = (s) => JSON.stringify(s);

/**
 * Which resolutions are still a wait. Everything else has settled one way or another.
 *
 * `shipped` has landed and `unresolvable` never will — a retired task, an external dep,
 * a label with nothing under it — so neither is something the page can say this line is
 * waiting for. `unknown` stays in deliberately: a dep naming nothing is a defect, and
 * dropping it here would hide it from the gate whose whole job is to catch one.
 */
const WAITED = new Set(["open", "deferred", "unknown"]);

/**
 * The ids a line still waits on, as roadkeep resolved them.
 *
 * **Asked for, not re-derived** (§PW61). A dep is an id, a `Block X` label or a range,
 * and this generator used to keep the first whitespace token of whichever it was — right
 * for `PW5` and for `PW5 ✅`, where the mark is what says the wait is over, and wrong the
 * moment the first token is not an id. `Block G` became a dangling `Block`, and the gate
 * reported a missing task rather than a grammar nothing here implements.
 *
 * roadkeep hands back each dep whole, with the grammar it is written in and how it
 * resolved, so `Block G` stays `Block G` and the page says what the line says. Its
 * members are deliberately not substituted: a line that waits on a block waits on the
 * block, and printing the three ids it happens to hold today would be a different claim
 * that goes stale on the next `add`.
 */
export function waitsOn(answer) {
  return (answer?.deps ?? [])
    .filter((one) => WAITED.has(one.status))
    .map((one) => one.dep);
}

/** The generated module's text, from one roadkeep read. Deterministic: same in, same out. */
export function renderModule(read) {
  const blocks = read.blocks.blocks.map((b) => ({
    block: b.block,
    title: b.title,
    open: b.open,
  }));
  const tasks = read.tasks.tasks.map((t) => ({
    id: t.id,
    block: t.block,
    symptom: t.symptom,
    why: t.why,
    deps: waitsOn(read.resolved?.[t.id]),
  }));
  const nonGoals = read.nonGoals.non_goals.map((lead) => ({
    lead,
    why: read.nonGoals.non_goals_why[lead] ?? "",
  }));
  const paused = (read.paused?.tasks ?? []).map((t) => t.id);

  const lines = [
    "// GENERATED by scripts/roadmap.mjs from docs/ROADMAP.md, through roadkeep. Do not edit.",
    "// `npm run generate` rewrites this file; `npm test` fails if it drifted from the roadmap.",
    "",
    "export interface GeneratedBlock {",
    "  /** the single letter the roadmap files it under */",
    "  block: string;",
    "  title: string;",
    "  /** lines still open in that block */",
    "  open: number;",
    "}",
    "",
    "export interface GeneratedTask {",
    "  id: string;",
    "  block: string;",
    "  /** the failure the line exists to remove, in the roadmap's own words */",
    "  symptom: string;",
    "  /** the measurement or the argument behind it */",
    "  why: string;",
    "  deps: string[];",
    "}",
    "",
    "export interface GeneratedNonGoal {",
    "  lead: string;",
    "  why: string;",
    "}",
    "",
    "export const generatedBlocks: GeneratedBlock[] = [",
    ...blocks.map(
      (b) => `  { block: ${q(b.block)}, title: ${q(b.title)}, open: ${b.open} },`,
    ),
    "];",
    "",
    "export const generatedTasks: GeneratedTask[] = [",
    ...tasks.flatMap((t) => [
      "  {",
      `    id: ${q(t.id)},`,
      `    block: ${q(t.block)},`,
      `    symptom: ${q(t.symptom)},`,
      `    why: ${q(t.why)},`,
      `    deps: [${t.deps.map(q).join(", ")}],`,
      "  },",
    ]),
    "];",
    "",
    "export const generatedNonGoals: GeneratedNonGoal[] = [",
    ...nonGoals.flatMap((n) => [
      "  {",
      `    lead: ${q(n.lead)},`,
      `    why: ${q(n.why)},`,
      "  },",
    ]),
    "];",
    "",
    "/** Lines set aside rather than shipped. They keep their ids, and are still waited on. */",
    `export const generatedPaused: string[] = [${paused.map(q).join(", ")}];`,
    "",
  ];
  return lines.join("\n");
}

function main() {
  const read = readRoadkeep();

  if (!read) {
    if (!existsSync(generatedPath)) {
      throw new Error(
        "roadmap: roadkeep is not reachable and src/lib/roadmap.generated.ts does not exist."
          + " Install roadkeep (or set $ROADKEEP) and run `npm run generate`.",
      );
    }
    console.log(
      "roadmap: roadkeep not reachable — keeping the committed src/lib/roadmap.generated.ts",
    );
    return;
  }

  const text = renderModule(read);
  const before = existsSync(generatedPath) ? readFileSync(generatedPath, "utf8") : null;
  if (before === text) {
    console.log(`roadmap: up to date (${read.via})`);
    return;
  }
  writeFileSync(generatedPath, text);
  console.log(
    `roadmap: wrote src/lib/roadmap.generated.ts`
      + ` — ${read.blocks.blocks.length} blocks, ${read.tasks.tasks.length} lines,`
      + ` ${read.nonGoals.non_goals.length} non-goals (${read.via})`,
  );
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main();
}
