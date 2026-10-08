// The window follows the project as it changes (§PW310): a revision's session writes, a
// terminal runs a fit, the person edits a declaration, or a checkout swaps half the tree.
// The root is watched, not files, so a file that did not exist yet, or one rewritten by a
// rename, is still caught, as roadkeep's governed watch learned. A burst of events is one
// call.

import { watch, type FSWatcher } from 'node:fs'
import { sep } from 'node:path'

/** Folders whose changes are never the project's items. */
const PASSED_OVER = ['node_modules', '.git', '.godot', '.import']

/** The plugin's own files the window does read: answers, revisions, sittings. */
const READ = ['answers.jsonl', 'revisions.jsonl', 'sittings.json', 'gates.jsonl']

/** Whether a changed path, relative to the root, is one the window would show. */
export function heard(path: string): boolean {
  const parts = path.split(/[\\/]/)
  if (parts.some((one) => PASSED_OVER.includes(one))) return false
  if (parts[0] === '.polyweave') return READ.includes(parts[parts.length - 1]!)
  return true
}

export class Watching {
  private readonly watchers = new Map<string, { watcher: FSWatcher; timer: NodeJS.Timeout | null }>()

  /** Call `changed` once per burst of changes under `project`, after `quiet` ms of calm. */
  start(project: string, changed: () => void, quiet = 300): void {
    if (this.watchers.has(project)) return
    const held: { watcher: FSWatcher; timer: NodeJS.Timeout | null } = {
      watcher: watch(project, { recursive: true }, (_event, name) => {
        if (name && !heard(String(name).split(sep).join('/'))) return
        if (held.timer) clearTimeout(held.timer)
        held.timer = setTimeout(() => {
          held.timer = null
          changed()
        }, quiet)
      }),
      timer: null,
    }
    held.watcher.on('error', () => undefined)
    this.watchers.set(project, held)
  }

  stop(project: string): void {
    const held = this.watchers.get(project)
    if (!held) return
    if (held.timer) clearTimeout(held.timer)
    held.watcher.close()
    this.watchers.delete(project)
  }

  stopAll(): void {
    for (const project of [...this.watchers.keys()]) this.stop(project)
  }
}
