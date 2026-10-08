import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { shown } from './files'

describe('a file handed to the page', () => {
  let root: string
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'pw-files-'))
    await writeFile(join(root, 'hit.wav'), 'RIFF')
    await writeFile(join(root, 'notes.txt'), 'x')
  })
  afterEach(() => rm(root, { recursive: true, force: true }))

  it('carries a sound under the project with its type', async () => {
    const got = await shown(root, 'hit.wav')
    expect(got.mime).toBe('audio/wav')
    expect(Buffer.from(got.base64, 'base64').toString()).toBe('RIFF')
  })

  it('refuses a path that resolves outside the project', async () => {
    await expect(shown(root, '../secret.png')).rejects.toThrow(/outside/)
    await expect(shown(root, join(tmpdir(), 'x.png'))).rejects.toThrow(/outside/)
  })

  it('refuses a file the window does not show', async () => {
    await expect(shown(root, 'notes.txt')).rejects.toThrow(/not a picture or a sound/)
  })
})
