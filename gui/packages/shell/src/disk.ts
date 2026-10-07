// The disk, as `core` is handed it: a directory listing and whether a path exists.

import { readdir, stat } from 'node:fs/promises'
import { join } from 'node:path'

import type { Lister, Probe } from '@pw/core'

export const disk: Lister & Probe = {
  async list(path) {
    const entries = await readdir(path, { withFileTypes: true })
    return entries.map((entry) => ({ name: entry.name, directory: entry.isDirectory() }))
  },
  async exists(path) {
    try {
      await stat(path)
      return true
    } catch {
      return false
    }
  },
  join: (...parts) => join(...parts),
}
