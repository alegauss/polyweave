# polyweave site

The public site — a self-contained Vite + React 19 + TypeScript + Tailwind v4 workspace,
and this repository's only code. It never writes into `docs/`, which is roadkeep's, and it
reads from there rather than copying it.

## Commands

```
npm install        # once
npm run dev        # dev server at /polyweave/
npm run build      # generate → tsc → client → og image → SSR → prerender
npm test           # the site's own claims, against what the build produced
npm run typecheck  # tsc -b, no emit
npm run preview    # serve the built dist/
```

`npm run build` is the gate, and it is one command on purpose: it regenerates the roadmap
module from `docs/ROADMAP.md`, type-checks, builds the client, rasterises the social card,
builds the SSR bundle and prerenders every route with its Markdown twin, its
`manifest.json`, its `sitemap.xml` and its `robots.txt`. A drifted `<head>` template, a
route with no page, or a feature record naming a block the roadmap has lost all fail it.
`npm test` then asserts the built output, so it runs after the build rather than instead of
it.

GitHub Pages derives the base path from the repository name, so Vite's `base` is
`/polyweave/` and every asset path carries that prefix. It is written twice — in
[vite.config.ts](vite.config.ts) and in [src/routes.tsx](src/routes.tsx) — and nowhere else.

## The one rule this site is held to

**It states where the project stands from the roadmap, and never claims a result no run
has measured.**

A status typed into the copy goes stale: this page said "there is no code yet" a hundred
shipped lines after the code arrived, and its own test defended the sentence. So:

- The landing page carries a status band, second on the page, built from
  `roadmap.generated.ts`: how many blocks have nothing left open, and how many lines do.
  `scripts/prerender.test.mjs` fails the build if the page disagrees with the module.
- Every measurement quoted is Cottony's, named as Cottony's, and describes the cost
  polyweave exists to remove.
- `scripts/lint.test.mjs` refuses copy that claims a result for polyweave ("faster than",
  "we measured", "benchmarked"). The loop ledger that would measure it has only begun.

A site for a tool whose argument is *an unmeasured claim is worthless* does not get to make
one.

## Where things live

| Path | What |
|---|---|
| `src/lib/site-content.ts` | **All copy** — sections only render it, so a claim is one array element a reviewer can check |
| `src/lib/roadmap.generated.ts` | **Generated** from `docs/ROADMAP.md` through roadkeep: the blocks, the lines and the non-goals. Committed, because roadkeep is not |
| `src/lib/roadmap.ts` | The typed read over it, and where every count in the prose comes from |
| `src/lib/features.ts` | One record per roadmap block — route, `<head>` and page, declared together |
| `src/lib/diagrams.ts` | The illustrative SVGs and the session transcript, kept verbatim as figures |
| `src/lib/theme.ts` + `index.html` pre-paint script + `src/index.css` tokens | **The theme follows the OS**, a stored choice overrides it, applied before first paint |
| `src/routes.tsx` | The route table and its metadata, asserted against each other at import time |
| `src/components/sections/` | One component per landing section; the composition lives here |
| `src/pages/Landing.tsx` | The landing page — the section order is the argument |
| `scripts/` | The generator, the prerender, the social card and the tests that read `dist/` |

## The generated module, and why it is committed

`.roadkeep` is in this repository's `.gitignore`, so a clean checkout has the roadmap but
not the tool that reads it. `npm run generate` refreshes `src/lib/roadmap.generated.ts`
where roadkeep is reachable and leaves the committed file alone where it is not, so the
build works either way.

`scripts/roadmap.test.mjs` is what keeps that honest: with roadkeep present it regenerates
into memory and asserts the committed file is byte-identical, so a line added, shipped,
renumbered or reworded without a regenerate fails. Without roadkeep it checks the committed
module against itself — unique ids, every dependency resolving, every block declared.

Set `$ROADKEEP` to a command if yours is not at `.roadkeep/scripts/roadkeep.py` or on PATH.

## Deliberate non-goals here

No third-party fonts fetched at page load (the product claims nothing leaves your machine;
the site adds no fetch of its own), no analytics, no cookie banner. Inter and JetBrains Mono
are named with system fallbacks rather than pulled from a CDN.
