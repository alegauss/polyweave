// Where the polyweave projects on a machine are (§PW303). Nothing is scanned until a
// person names a root and a depth: walking a whole disk unasked is slow and is not this
// window's to decide. A project is a folder holding `polyweave.toml`.

/** One entry of a directory, as the shell's filesystem reports it. */
export interface Entry {
  name: string
  directory: boolean
}

/** What the shell hands `core` to read a directory with; `core` has no filesystem. */
export interface Lister {
  list(path: string): Promise<Entry[]>
  join(...parts: string[]): string
}

export const MARKER = 'polyweave.toml'

/** Folders that are never a project and never hold one worth finding. */
const PASSED_OVER = new Set(['node_modules', '__pycache__', 'dist', 'build'])

/**
 * Every project under `root`, at most `depth` folders below it, sorted by path.
 *
 * A project's own subfolders are not searched: one project inside another is the
 * inner one's business, and a folder full of games is found one level at a time. A
 * folder that cannot be read is passed over, since one locked directory should not
 * hide the rest of the disk.
 */
export async function find(lister: Lister, root: string, depth: number): Promise<string[]> {
  const found: string[] = []
  const walk = async (path: string, left: number): Promise<void> => {
    let entries: Entry[]
    try {
      entries = await lister.list(path)
    } catch {
      return
    }
    if (entries.some((e) => !e.directory && e.name === MARKER)) {
      found.push(path)
      return
    }
    if (left <= 0) {
      return
    }
    for (const entry of entries) {
      if (entry.directory && !entry.name.startsWith('.') && !PASSED_OVER.has(entry.name)) {
        await walk(lister.join(path, entry.name), left - 1)
      }
    }
  }
  await walk(root, Math.max(0, Math.floor(depth)))
  return found.sort()
}
