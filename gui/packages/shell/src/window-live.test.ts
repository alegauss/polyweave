// The window itself, opened by Electron on a project it finds under a named root
// (§PW303). It runs in its smoke mode: the renderer drives the find and the open, and
// main prints what the page drew, read back off the page.

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import electron from 'electron'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { SMOKE_VAR } from './smoke'

const MAIN = join(import.meta.dirname, '..', 'dist', 'main.js')

function opened(root: string, language: string): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const env: Record<string, string | undefined> = {
      ...process.env,
      [SMOKE_VAR]: JSON.stringify({ root, depth: 1, language }),
    }
    delete env['ELECTRON_RUN_AS_NODE']
    const child = spawn(String(electron), [MAIN], { env, windowsHide: true })
    let out = ''
    child.stdout.on('data', (chunk: Buffer) => {
      out += chunk.toString('utf8')
      const said = /^rendered: (.*)$/m.exec(out)
      if (said) resolve(JSON.parse(said[1]!) as Record<string, unknown>)
    })
    child.stderr.on('data', (chunk: Buffer) => (out += chunk.toString('utf8')))
    child.on('exit', (code) => reject(new Error(`electron exited ${code} without drawing:\n${out}`)))
  })
}

describe.skipIf(!existsSync(MAIN))('the window', () => {
  let root: string

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'pw-window-'))
    await mkdir(join(root, 'starship', 'text'), { recursive: true })
    await writeFile(join(root, 'starship', 'polyweave.toml'), '[words]\ntable = "text/strings.csv"\n')
    await writeFile(join(root, 'starship', 'text', 'strings.csv'), 'keys,en\nTITLE,Starship\nSTART,Go\n')
  })

  afterEach(async () => {
    await rm(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  })

  it('opens a project found under the root and draws its inventory by kind', async () => {
    const drew = await opened(root, 'pt-BR')
    expect(drew['project']).toBe(join(root, 'starship'))
    expect(drew['server']).toBe('polyweave')
    expect(drew['engine']).toBe('path')
    expect(drew['groups']).toEqual(['line'])
    expect(drew['rows']).toBe(2)
    // The words are the catalog's, in the language asked.
    expect(drew['count']).toBe('2 itens')
  })
})
