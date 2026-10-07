// A real `python -m polyweave serve`, found and opened the way the window will (§PW303).

import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { find, page, Refused } from '@pw/core'

import { disk } from './disk'
import { Held } from './held'

describe('a held server', () => {
  let root: string
  const held = new Held()

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'pw-gui-'))
    await mkdir(join(root, 'starship', 'text'), { recursive: true })
    await writeFile(
      join(root, 'starship', 'polyweave.toml'),
      '[words]\ntable = "text/strings.csv"\n',
    )
    await writeFile(join(root, 'starship', 'text', 'strings.csv'), 'keys,en\nTITLE,Starship\n')
    await mkdir(join(root, 'notes'))
  })

  afterEach(async () => {
    await held.closeAll()
    await rm(root, { recursive: true, force: true })
  })

  it('finds a project, opens it, and reads its inventory', async () => {
    const [project] = await find(disk, root, 1)
    expect(project).toBe(join(root, 'starship'))
    const open = await held.opened(project!)
    expect(open.server.name).toBe('polyweave')
    expect(open.engine.from).toBe('path')
    const read = await page(open.client, project!)
    expect(read.items.map((item) => item.id)).toEqual(['line:TITLE'])
    // Opened again, it is the same server rather than a second one.
    expect(await held.opened(project!)).toBe(open)
  })

  it('carries a refusal back with its code', async () => {
    const open = await held.opened(join(root, 'starship'))
    const refused = open.client.call('project.inventory', { root, kind: 'hologram' })
    await expect(refused).rejects.toBeInstanceOf(Refused)
    await expect(refused).rejects.toMatchObject({ refusal: { code: 'op.bad-choice' } })
  })
})
