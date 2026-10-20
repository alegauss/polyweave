// The prerender and the social card, both through the design system's build helpers (PW572).
//
// prerenderSite renders every route into the client build's index.html, patching the <head>
// by replace-or-throw so a drifted template fails the build rather than shipping a page under
// another route's title, and writes the Markdown twin beside each page, manifest.json,
// sitemap.xml (lastmod from git, never the build clock) and robots.txt — all from the route
// table routes.tsx has already asserted against the component map.
//
// renderOgCard rasterises the card to dist/og.png at 1200x630. An og:image pointing at an SVG
// is an empty rectangle on every platform that renders a card. The card is a template, not a
// finished drawing: its mark is spliced in from public/logo.svg, because a card carrying its
// own copy of the artwork goes stale the next time the artwork changes, and its status pill
// is measured, not typed. The card asks for DejaVu and takes whatever the build machine has,
// so a pill hand-fitted to one font overflows on another; resvg measures the text here and
// the pill is drawn round the answer.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";
import { prerenderSite, renderOgCard } from "@viglet/viglet-design-system/vite";

import {
  render,
  renderStatic,
  ROUTE_META,
  canonicalUrl,
  outputDir,
  OG_IMAGE,
} from "../dist-server/entry-server.js";
import { htmlToMarkdown } from "./markdown.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const siteDir = join(here, "..");
const distDir = join(siteDir, "dist");

// Where the mark sits on the card, and how big. Height only: the artwork is taller than it
// is wide and carries its own silhouette, so it is sized by height and left to find its
// width. A width here would squash it.
const MARK = { left: 90, top: 96, height: 156 };

// The pill's left edge, and the space left after the text ends. The dot sits 28px inside
// the left edge and the text 46px, so 26 on the right reads as the same inset once the
// corner radius is allowed for. GUTTER is the card's right margin, which the pill may not
// cross.
const CHIP = { left: 90, padding: 26 };
const GUTTER = 1110;
const FONT = "DejaVu Sans";

function cardSvg() {
  const card = readFileSync(join(here, "og-card.svg"), "utf8");
  const logo = readFileSync(join(siteDir, "public", "logo.svg"), "utf8");

  const viewBox = logo.match(/\bviewBox="([\d.\-\s]+)"/);
  if (!viewBox) throw new Error("og-card: public/logo.svg has no viewBox");
  const [minX, minY, , boxHeight] = viewBox[1].trim().split(/\s+/).map(Number);
  // The logo's own root <svg> cannot come along: a nested svg brings its own viewport and
  // re-fits the artwork to a box this did not choose. Its children can, <defs> included.
  const artwork = logo.replace(/^[\s\S]*?<svg\b[^>]*>/, "").replace(/<\/svg>\s*$/, "").trim();
  const scale = MARK.height / boxHeight;
  const mark =
    `<g transform="translate(${MARK.left - minX * scale},${MARK.top - minY * scale})` +
    ` scale(${scale.toFixed(6)})">\n${artwork}\n  </g>`;

  // Where the chip's text lands once this font has had its say, rendered alone on a
  // card-sized canvas so the box comes back in the card's coordinates.
  const chipText = card.match(/<text\b[^>]*\bid="chip"[\s\S]*?<\/text>/);
  if (!chipText) throw new Error('og-card: og-card.svg has no <text id="chip">');
  const canvas = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">${chipText[0]}</svg>`;
  const box = new Resvg(canvas, { font: { loadSystemFonts: true, defaultFontFamily: FONT } }).getBBox();
  if (!box) throw new Error("og-card: the chip's text measured as nothing");
  const chipWidth = Math.ceil(box.x + box.width + CHIP.padding - CHIP.left);
  if (CHIP.left + chipWidth > GUTTER) {
    throw new Error(`og-card: the status pill needs ${chipWidth}px and runs past x=${GUTTER}`);
  }

  // A slot that is not there is a card drawn without the thing it was supposed to carry, and
  // String.replace says nothing about a pattern it never found.
  let svg = card;
  for (const [slot, value] of Object.entries({ "{{mark}}": mark, "{{chip-width}}": String(chipWidth) })) {
    if (!svg.includes(slot)) throw new Error(`og-card: og-card.svg has no ${slot} slot`);
    svg = svg.replace(slot, () => value);
  }
  return svg;
}

const card = await renderOgCard({ svg: cardSvg(), out: join(distDir, "og.png"), fontFamily: FONT });
console.log(`og-image: dist/og.png  ${card.width}x${card.height}  (${(card.bytes / 1024).toFixed(0)} kB)`);

const written = prerenderSite({
  distDir,
  routes: ROUTE_META,
  render,
  canonicalUrl,
  outputDir,
  ogImage: OG_IMAGE,
  // The Markdown twin, converted from the same component tree as clean static HTML.
  twin: (path) => htmlToMarkdown(renderStatic(path)),
  manifest: { name: "polyweave", base: "/polyweave/", llms: "llms.txt" },
  git: { cwd: siteDir },
  log: console.log,
});

console.log(`prerender: ${written.length} route(s) + twins, manifest.json, sitemap.xml and robots.txt written to dist/`);
