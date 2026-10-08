import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, describe, expect, it } from 'vitest'

import { heard, Watching } from './watch'

describe('following the project', () => {
  it("hears the project's own files and the plugin's answers, not its caches", () => {
    expect(heard('art/icon.png')).toBe(true)
    expect(heard('.polyweave/answers.jsonl')).toBe(true)
    expect(heard('.polyweave/revisions.jsonl')).toBe(true)
    expect(heard('.polyweave/cache/ab/cd.png')).toBe(false)
    expect(heard('node_modules/x/index.js')).toBe(false)
    expect(heard('.godot/imported/a.ctex')).toBe(false)
  })

  let root = ''
  const watching = new Watching()
  afterEach(async () => {
    watching.stopAll()
    await rm(root, { recursive: true, force: true })
  })

  it('calls once for a burst of writes, a new file and a nested one included', async () => {
    root = await mkdtemp(join(tmpdir(), 'pw-watch-'))
    await mkdir(join(root, 'art'))
    let calls = 0
    watching.start(root, () => calls++, 100)
    await new Promise((resolve) => setTimeout(resolve, 100))
    await writeFile(join(root, 'art', 'icon.png'), 'a')
    await writeFile(join(root, 'art', 'icon.png'), 'b')
    await writeFile(join(root, 'new.toml'), 'c')
    await new Promise((resolve) => setTimeout(resolve, 600))
    expect(calls).toBe(1)
  })
})
