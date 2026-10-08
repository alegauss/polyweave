// A project's file, handed to the page as bytes (§PW304). The page never names a path the
// machine resolves: this does, and refuses one that lands outside the open project.

import { readFile, stat } from 'node:fs/promises'
import { extname, relative, resolve, sep } from 'node:path'

import type { Shown } from '@pw/core'

/** What the page can show, by suffix; anything else is not carried across. */
export const SHOWN: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.mp3': 'audio/mpeg',
}

/** The largest file carried across, so one huge texture cannot stall the window. */
export const LARGEST = 32 * 1024 * 1024

export async function shown(project: string, path: string): Promise<Shown> {
  const root = resolve(project)
  const where = resolve(root, path)
  const inside = relative(root, where)
  if (!inside || inside.startsWith('..') || inside.split(sep).includes('..')) {
    throw new Error(`${path} is outside ${project}, so the window does not read it`)
  }
  const mime = SHOWN[extname(where).toLowerCase()]
  if (!mime) throw new Error(`${path} is not a picture or a sound the window shows`)
  const size = (await stat(where)).size
  if (size > LARGEST) throw new Error(`${path} is ${size} bytes, past what the window shows`)
  return { path, mime, base64: (await readFile(where)).toString('base64') }
}
