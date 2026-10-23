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
    // The window's own quiet, not a third of it: on Linux the recursive watch is built on
    // inotify, and on a loaded runner one write's events came more than 100 ms apart and
    // were counted as two bursts (gates run 39963801275, 2026-10-23).
    const quiet = 300
    watching.start(root, () => calls++, quiet)
    // Settled first, so an event the watch raises setting itself up is not counted.
    await new Promise((resolve) => setTimeout(resolve, 2 * quiet))
    calls = 0
    await writeFile(join(root, 'art', 'icon.png'), 'a')
    await writeFile(join(root, 'art', 'icon.png'), 'b')
    await writeFile(join(root, 'new.toml'), 'c')
    await new Promise((resolve) => setTimeout(resolve, 4 * quiet))
    expect(calls).toBe(1)
  })
})
