// The specs page's index, read off docs/specs/README.md at build time rather than typed
// here. The page once listed six specs, three of them "to come", while the folder held
// twenty-two, all written: a copy of an index drifts the day a spec is added. The README is
// the index, so the table and the not-yet list are its own rows.
//
// Not in site-content.ts: vite.config.ts loads that module through Vite's config loader,
// which resolves no `?raw` import.
import index from "../../../docs/specs/README.md?raw";
import type { Rich, Run } from "./site-content";

export interface SpecRow {
  name: string;
  fixes: string;
  binds: string;
}

/** Inline Markdown as runs: bold, code, and a link kept as its text. */
function runs(md: string): Rich {
  const out: Run[] = [];
  const pattern = /\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\([^)]+\)/g;
  let at = 0;
  for (const m of md.matchAll(pattern)) {
    if (m.index > at) out.push(md.slice(at, m.index));
    if (m[1] !== undefined) out.push({ b: m[1] });
    else if (m[2] !== undefined) out.push({ code: m[2] });
    else out.push(m[3]);
    at = m.index + m[0].length;
  }
  if (at < md.length) out.push(md.slice(at));
  return out;
}

function section(heading: string): string {
  const parts = index.split(/^## /m);
  const found = parts.find((p) => p.startsWith(heading));
  if (!found) throw new Error(`docs/specs/README.md lost its "## ${heading}" section`);
  return found.slice(heading.length);
}

function tableRows(): SpecRow[] {
  const rows: SpecRow[] = [];
  for (const line of index.split(/\r?\n/)) {
    const m = /^\| \[([^\]]+\.md)\]\([^)]+\) \| (.+?) \| (.+?) \|$/.exec(line);
    if (m) rows.push({ name: m[1], fixes: m[2].replace(/"([^"]+)"/g, "“$1”"), binds: m[3] });
  }
  if (rows.length === 0) throw new Error("docs/specs/README.md has no spec table rows");
  return rows;
}

function bullets(heading: string): Rich[] {
  const items = section(heading)
    .split(/\r?\n(?=- )/)
    .map((b) => b.trim())
    .filter((b) => b.startsWith("- "))
    .map((b) => b.slice(2).replace(/\s*\r?\n\s*/g, " "));
  if (items.length === 0) throw new Error(`docs/specs/README.md: "${heading}" lists nothing`);
  return items.map(runs);
}

export const specRows = tableRows();
export const notSpecced = bullets("Deliberately not specced yet");
