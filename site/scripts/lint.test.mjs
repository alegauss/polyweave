// Source lints. Three rules, each of which is a claim this site makes about itself and
// would otherwise have nothing behind it.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, extname } from "node:path";
import { fileURLToPath } from "node:url";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === "dist" || name === "dist-server") continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

const sourceFiles = walk(join(siteDir, "src")).filter((f) =>
  [".ts", ".tsx", ".js", ".jsx"].includes(extname(f)),
);

// Only the reader moves the window. A panel that keeps its own content in view scrolls its
// own element, never scrollIntoView, which scrolls every scrollable ancestor including the
// document — and drags a reader somewhere they did not ask to go.
test("no source calls scrollIntoView", () => {
  // the call, not the word — a comment explaining why we avoid it is fine
  const offenders = sourceFiles.filter((f) => readFileSync(f, "utf8").includes("scrollIntoView("));
  assert.deepEqual(
    offenders.map((f) => f.replace(siteDir + "/", "")),
    [],
    "a panel must scroll its own element (scrollTop), never scrollIntoView",
  );
});

// The product's first non-goal is a hosted service and an account; the site adds no
// third-party fetch of its own. Inter and JetBrains Mono are named with system fallbacks
// rather than pulled from a CDN.
test("no source fetches a third-party font at page load", () => {
  const all = [...sourceFiles, join(siteDir, "index.html"), join(siteDir, "src", "index.css")];
  const offenders = all.filter((f) => readFileSync(f, "utf8").includes("fonts.googleapis.com"));
  assert.deepEqual(offenders.map((f) => f.replace(siteDir + "/", "")), []);
});

// The lattice loops by translating one whole repeat of its bands, so a period that does not
// divide that repeat puts a visible seam through the weave once per cycle — every few
// seconds, forever. The arithmetic is the whole of the illusion, so it is asserted rather
// than trusted to whoever next retunes it.
test("every lattice period closes on the repeat the drift translates by", () => {
  const src = readFileSync(join(siteDir, "src", "components", "ui", "Lattice.tsx"), "utf8");
  const span = Number(/const SPAN = (\d+)/.exec(src)?.[1]);
  assert.ok(span > 0, "Lattice.tsx no longer declares SPAN");
  // the drift animation moves by 50% of a band drawn at 200% — one repeat is half the span
  const repeat = span / 2;
  const periods = [...src.matchAll(/period: (\d+)/g)].map((m) => Number(m[1]));
  assert.ok(periods.length >= 3, "expected a period per lattice layer");
  assert.deepEqual(
    periods.filter((p) => repeat % p !== 0),
    [],
    `every period must divide ${repeat}`,
  );
});

// Nothing on this site may claim polyweave has been measured. The words below are the ones
// that would do it, and the rule exists because the product's own argument is that an
// unmeasured claim is worthless — a site for it that made one would be self-refuting.
test("no copy claims a measured result for polyweave", () => {
  const content = readFileSync(join(siteDir, "src", "lib", "site-content.ts"), "utf8");
  const banned = [/\bfaster than\b/i, /\b\d+x faster\b/i, /\bwe measured\b/i, /\bbenchmarked\b/i];
  const hits = banned.filter((re) => re.test(content));
  assert.deepEqual(
    hits.map(String),
    [],
    "the copy states a result polyweave has not produced — there is no implementation",
  );
});
