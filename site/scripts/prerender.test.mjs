// The site's own claims, asserted against the built output. These read dist/, so they run
// after `npm run build` (which is what CI does). A claim that has gone false — a route with
// no file, a duplicate title, a twin that leaked the nav or the call to action, a card that
// is not 1200x630, a landing page that no longer says the project is unbuilt — fails here
// rather than being invisible until somebody reads the page against the repository.
import { test, before } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(siteDir, "dist");
const generated = readFileSync(join(siteDir, "src", "lib", "roadmap.generated.ts"), "utf8");

let manifest;
before(() => {
  const mf = join(distDir, "manifest.json");
  assert.ok(existsSync(mf), "dist/manifest.json is missing — run `npm run build` first");
  manifest = JSON.parse(readFileSync(mf, "utf8"));
});

const EXPECTED = [
  "/", "/claude-code", "/specs",
  "/features/tool-surface", "/features/preview", "/features/compiler",
  "/features/fetch", "/features/engine", "/features/motion", "/features/geometry",
];

test("every expected route is in the manifest", () => {
  const paths = manifest.routes.map((r) => r.path);
  for (const p of EXPECTED) assert.ok(paths.includes(p), `route ${p} missing from manifest`);
});

test("each route has its HTML and Markdown file at the stated size", () => {
  for (const r of manifest.routes) {
    const html = join(distDir, r.html);
    const md = join(distDir, r.markdown);
    assert.ok(existsSync(html), `${r.html} missing`);
    assert.ok(existsSync(md), `${r.markdown} missing`);
    assert.equal(statSync(html).size, r.htmlBytes, `${r.html} size drifted from manifest`);
    assert.equal(statSync(md).size, r.markdownBytes, `${r.markdown} size drifted from manifest`);
  }
});

test("each page has a unique title, its canonical, and an og:image", () => {
  const titles = new Set();
  for (const r of manifest.routes) {
    const html = readFileSync(join(distDir, r.html), "utf8");
    const title = html.match(/<title>([\s\S]*?)<\/title>/)?.[1];
    assert.ok(title, `${r.html} has no <title>`);
    assert.ok(!titles.has(title), `duplicate <title>: ${title}`);
    titles.add(title);
    assert.ok(html.includes(`<link rel="canonical" href="${r.url}"`), `${r.html} canonical wrong`);
    assert.ok(html.includes('property="og:image"'), `${r.html} has no og:image`);
  }
});

test("no twin leaks the nav, the footer or the call to action", () => {
  // Each of these appears in exactly one place in the rendered page and nowhere in the
  // prose: the nav/hero button, the hero's own call to action, and the footer disclaimer.
  // Deliberately not a short phrase like "part of" — the copy says "part of the design"
  // about the geometry escape hatch, and a guard that fires on prose is one somebody
  // silences by rewording the prose.
  const banned = ["★ View on GitHub", "Read the plan", "independent open-source project"];
  for (const r of manifest.routes) {
    const md = readFileSync(join(distDir, r.markdown), "utf8");
    assert.ok(md.trim().length > 0, `${r.markdown} is empty`);
    for (const b of banned) {
      assert.ok(!md.includes(b), `${r.markdown} leaked "${b}"`);
    }
  }
});

test("the landing twin carries the session — the product an agent can grep", () => {
  const md = readFileSync(join(distDir, "index.md"), "utf8");
  assert.ok(md.includes("polyweave search mascot"), "landing twin missing the session");
  assert.ok(md.includes("post.render-uniform"), "landing twin missing the typed failure");
});

// --- the honesty gate ---
// The one thing this site must never stop saying. Every page in the manifest describes an
// unbuilt product in the present tense, which is the right way to write about a settled
// design and is only honest while the landing page says, above the fold's worth of
// scrolling, that none of it exists. If this ever fails, the fix is the copy, not the test.

test("the landing page states that there is no implementation", () => {
  const md = readFileSync(join(distDir, "index.md"), "utf8");
  assert.ok(
    md.includes("There is no code yet"),
    "the landing page no longer says the project is unbuilt",
  );
  assert.ok(
    md.includes("none of them shipped"),
    "the landing page no longer says nothing has shipped",
  );
});

test("the landing page states the roadmap's own counts", () => {
  const md = readFileSync(join(distDir, "index.md"), "utf8");
  const lines = [...generated.matchAll(/^    id: "([^"]+)",$/gm)].length;
  const blocks = [...generated.matchAll(/\{ block: "([^"]+)", title:/g)].length;
  assert.ok(
    md.includes(`${lines} lines across`),
    `the landing page does not state ${lines} lines`,
  );
  assert.ok(lines > 0 && blocks > 0, "the generated module is empty");
});

test("every non-goal in the roadmap reaches the landing page", () => {
  const md = readFileSync(join(distDir, "index.md"), "utf8");
  const leads = [...generated.matchAll(/^    lead: "([^"]+)",$/gm)].map((m) => m[1]);
  assert.ok(leads.length > 0, "the generated module declares no non-goals");
  for (const lead of leads) {
    assert.ok(md.includes(lead), `the landing page does not carry the non-goal "${lead}"`);
  }
});

// --- discovery ---

test("the sitemap lists every route exactly once, and nothing else", () => {
  const xml = readFileSync(join(distDir, "sitemap.xml"), "utf8");
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);

  // Exactly once and in both directions: a route missing from the sitemap is one a crawler
  // finds only if something links inward, and a URL with no route is an address that 404s.
  assert.equal(locs.length, manifest.routes.length, "sitemap URL count differs from the routes");
  assert.equal(new Set(locs).size, locs.length, "the sitemap lists a URL twice");
  for (const r of manifest.routes) {
    assert.ok(locs.includes(r.url), `sitemap missing ${r.url}`);
  }
});

test("every sitemap URL carries the base prefix", () => {
  const xml = readFileSync(join(distDir, "sitemap.xml"), "utf8");
  for (const [, loc] of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) {
    assert.ok(
      loc.startsWith(`https://alegauss.github.io${manifest.base}`),
      `${loc} does not carry ${manifest.base}`,
    );
  }
});

test("the sitemap states no lastmod it cannot derive, and never the build clock", () => {
  const xml = readFileSync(join(distDir, "sitemap.xml"), "utf8");
  const stamps = [...xml.matchAll(/<lastmod>([^<]+)<\/lastmod>/g)].map((m) => m[1]);
  for (const s of stamps) {
    assert.match(s, /^\d{4}-\d{2}-\d{2}$/, `lastmod ${s} is not a plain date`);
  }

  // Either every URL carries one or none does — a sitemap where some routes look fresher
  // for want of a source, rather than for having changed, is the misleading half.
  assert.ok(
    stamps.length === 0 || stamps.length === manifest.routes.length,
    "lastmod is on some routes and not others",
  );
});

test("robots allows everything and names a sitemap that was written", () => {
  const robots = readFileSync(join(distDir, "robots.txt"), "utf8");
  assert.match(robots, /^User-agent: \*$/m);
  assert.match(robots, /^Allow: \/$/m);

  const named = robots.match(/^Sitemap: (\S+)$/m);
  assert.ok(named, "robots.txt names no sitemap");

  // Absolute, and the file it names is the one beside it — a Sitemap: line pointing at
  // nothing is worse than no line, because it is a claim a crawler acts on.
  const url = named[1];
  assert.ok(url.startsWith("https://"), "the Sitemap: line is not absolute");
  assert.equal(url, `https://alegauss.github.io${manifest.base}sitemap.xml`);
  assert.ok(existsSync(join(distDir, "sitemap.xml")), "robots names a sitemap that is not there");
});

test("the social card is a 1200x630 PNG", () => {
  const png = join(distDir, "og.png");
  assert.ok(existsSync(png), "dist/og.png missing");
  const buf = readFileSync(png);
  assert.equal(buf.toString("ascii", 1, 4), "PNG", "og.png is not a PNG");
  assert.equal(buf.readUInt32BE(16), 1200, "og.png width");
  assert.equal(buf.readUInt32BE(20), 630, "og.png height");
});
