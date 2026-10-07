// The typed read over the generated module. The site never imports
// `roadmap.generated.ts` directly: this file is where a block letter becomes a depth page's
// title, and where the non-goals the landing page carries are read from.
//
// The landing page states no status (what is still open lives in docs/ROADMAP.md), so the
// counts this module used to derive for the prose are gone with the prose that used them.
import {
  generatedBlocks,
  generatedNonGoals,
  type GeneratedBlock,
  type GeneratedNonGoal,
  type GeneratedTask,
} from "./roadmap.generated";

export type { GeneratedBlock, GeneratedNonGoal, GeneratedTask };

export const blocks = generatedBlocks;
export const nonGoals = generatedNonGoals;

export function blockTitle(block: string): string {
  const found = blocks.find((b) => b.block === block);
  if (!found) throw new Error(`roadmap: no block ${block} — regenerate from the roadmap`);
  return found.title;
}
