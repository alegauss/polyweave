// The typed read over the generated module. The site never imports
// `roadmap.generated.ts` directly: this file is where a block letter becomes a pillar on
// the site, and where the counts the copy states are derived rather than typed.
//
// The rule the whole site is held to: a number in the prose comes from here, and a
// sentence is a sentence. Five of the counts below appear in the copy, and none of them
// can go stale without `npm run generate` noticing.
import {
  generatedBlocks,
  generatedNonGoals,
  generatedTasks,
  type GeneratedBlock,
  type GeneratedNonGoal,
  type GeneratedTask,
} from "./roadmap.generated";

export type { GeneratedBlock, GeneratedNonGoal, GeneratedTask };

export const blocks = generatedBlocks;
export const tasks = generatedTasks;
export const nonGoals = generatedNonGoals;

/** Every line still open on the roadmap, across every block. */
export function taskCount(): number {
  return tasks.length;
}

export function blockCount(): number {
  return blocks.length;
}

/** Lines still open, as each block counts them. */
export function openCount(): number {
  return blocks.reduce((n, b) => n + b.open, 0);
}

/**
 * Blocks with nothing left open: the status the page states, derived rather than
 * typed (§PW137). A typed status is what said "there is no code yet" a hundred shipped
 * lines after it stopped being true.
 */
export function finishedCount(): number {
  return blocks.filter((b) => b.open === 0).length;
}

export function tasksIn(block: string): GeneratedTask[] {
  return tasks.filter((t) => t.block === block);
}

export function blockTitle(block: string): string {
  const found = blocks.find((b) => b.block === block);
  if (!found) throw new Error(`roadmap: no block ${block} — regenerate from the roadmap`);
  return found.title;
}

export function task(id: string): GeneratedTask {
  const found = tasks.find((t) => t.id === id);
  if (!found) throw new Error(`roadmap: no line ${id} — it shipped, or it was renumbered`);
  return found;
}

/** Several lines in one read, in the order asked for, each refused if it is gone. */
export function someTasks(ids: readonly string[]): GeneratedTask[] {
  return ids.map(task);
}

const SPELLED = [
  "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
  "ten", "eleven", "twelve",
];

/** A small number as a word, because prose counts up to twelve in words. */
export function spelled(n: number): string {
  return SPELLED[n] ?? String(n);
}

export function Spelled(n: number): string {
  const word = spelled(n);
  return word.charAt(0).toUpperCase() + word.slice(1);
}
