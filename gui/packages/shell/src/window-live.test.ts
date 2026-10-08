// The window itself, opened by Electron on a project it finds under a named root
// (§PW303). It runs in its smoke mode: the renderer drives the find and the open, and
// main prints what the page drew, read back off the page.

import { spawn, spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import electron from 'electron'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { AGENT_VAR } from './agent'
import { fakeClaude } from './fake-claude'
import { SMOKE_VAR } from './smoke'

const MAIN = join(import.meta.dirname, '..', 'dist', 'main.js')

/** A 2x2 picture, the smallest the window has to carry across and draw. */
const PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFklEQVR4nGP4z8DwnwEJMGHjEcEFABQ7Av8bS6RhAAAAAElFTkSuQmCC'

function opened(
  root: string,
  language: string,
  item?: string,
  review?: boolean,
  ask?: { words: string; agent: string[]; env?: Record<string, string> },
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const env: Record<string, string | undefined> = {
      ...process.env,
      [SMOKE_VAR]: JSON.stringify({
        root,
        depth: 1,
        language,
        ...(item ? { item } : {}),
        ...(review ? { review } : {}),
        ...(ask ? { ask: ask.words } : {}),
      }),
      ...(ask ? { [AGENT_VAR]: JSON.stringify(ask.agent), ...ask.env } : {}),
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
    const game = join(root, 'starship')
    await writeFile(
      join(game, 'polyweave.toml'),
      '[words]\ntable = "text/strings.csv"\n\n[paths]\naudio = "audio"\n\n' +
        '[sound.music]\nkind = "loop"\nformat = "wav"\ncues = ["calm"]\n',
    )
    await writeFile(join(game, 'text', 'strings.csv'), 'keys,en\nTITLE,Starship\nSTART,Go\n')
    // A picture where the project keeps its renders, with no record: listed, and shown.
    await mkdir(join(game, 'docs', 'renders'), { recursive: true })
    await writeFile(join(game, 'docs', 'renders', 'icon.png'), Buffer.from(PNG, 'base64'))
    // The last gate that weighed it, the icon kept and another refused.
    await mkdir(join(game, '.polyweave'), { recursive: true })
    await writeFile(
      join(game, '.polyweave', 'gates.jsonl'),
      JSON.stringify({
        id: 'g1',
        candidates: [
          { picture: 'docs/renders/icon.png', passed: true, failed: [] },
          { picture: 'docs/renders/other.png', passed: false, failed: ['edge drifted'] },
        ],
      }) + '\n',
    )
    // A loop, made the real way: an effect named as a cue a loop family declares.
    await mkdir(join(game, 'audio'), { recursive: true })
    await writeFile(join(game, 'audio', 'fx.sfx.toml'), '[effect.calm]\ngenerator = "pickup"\n')
    const made = spawnSync('python', ['-m', 'polyweave', 'sound.synth', '--source', 'audio/fx.sfx.toml', '--root', game])
    expect(made.status, made.stderr?.toString()).toBe(0)
    // A change a person asked for, still open.
    const asked = spawnSync('python', ['-m', 'polyweave', 'revision.ask', '--item', 'line:TITLE', '--words', 'shorter', '--root', game])
    expect(asked.status, asked.stderr?.toString()).toBe(0)
  })

  afterEach(async () => {
    await rm(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  })

  it('opens a project found under the root and draws its inventory by kind', async () => {
    const drew = await opened(root, 'pt-BR')
    expect(drew['project']).toBe(join(root, 'starship'))
    expect(drew['server']).toBe('polyweave')
    expect(drew['engine']).toBe('path')
    expect(drew['groups']).toEqual(['picture', 'sound', 'line'])
    expect(drew['rows']).toBe(4)
    // The words are the catalog's, in the language asked.
    expect(drew['count']).toBe('4 itens')
    // The open revision is what the list can be narrowed to.
    expect(drew['revised']).toBe(1)
  })

  it('shows a line beside what it was held to, and a picture beside its gate', async () => {
    const line = await opened(root, 'en', 'line:TITLE')
    expect(line['viewer']).toBe('line')
    expect(line['said']).toBe('Starship')
    const picture = await opened(root, 'en', 'docs/renders/icon.png')
    expect(picture['viewer']).toBe('picture')
    // Both lanes: the kept icon and the refused one beside it.
    expect(picture['lanes']).toBe(2)
  })

  it("hosts the project's review page for its verdicts, on an item's sitting", async () => {
    const drew = await opened(root, 'en', 'docs/renders/icon.png', true)
    expect(drew['framed']).toBe(true)
    expect(drew['hosted']).toBe(true)
    const url = String(drew['review'])
    expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+\/\?member=docs%2Frenders%2Ficon\.png$/)
  })

  it('asks for a change and opens a session on it, beside the item', async () => {
    const fake = fakeClaude()
    try {
      const drew = await opened(root, 'en', 'line:TITLE', false, { words: 'shorter, in capitals', agent: fake.argv })
      // The fake says its first message back: built from the revision and the brief.
      const turns = drew['turns'] as string[]
      expect(turns[0]).toContain('Item: line:TITLE')
      expect(turns[0]).toContain('What they said: shorter, in capitals')
      // Its question is the window's to answer.
      expect(drew['asked']).toEqual(['Write'])
      // What the session said is kept on the revision it works through.
      const listed = spawnSync('python', ['-m', 'polyweave', 'revision.open', '--item', 'line:TITLE', '--root', join(root, 'starship'), '--json'])
      const open = JSON.parse(listed.stdout.toString()) as { revisions: { words: string; turns: { by: string }[] }[] }
      const mine = open.revisions.find((one) => one.words === 'shorter, in capitals')!
      expect(mine.turns.map((one) => one.by)).toContain('session')
    } finally {
      fake.dispose()
    }
  })

  it('stops a paid call with its price, for one yes', async () => {
    const game = join(root, 'starship')
    const config = join(game, 'polyweave.toml')
    const declared = readFileSync(config, 'utf8')
    await writeFile(
      config,
      [
        declared,
        '[service.ideogram]',
        'base = "https://api.ideogram.ai"',
        'key_env = "PW_TEST_KEY"',
        'prices = { "4.0" = 0.08 }',
        '',
        '[budget.ideogram]',
        'amount = 1.0',
        'unit = "USD"',
        'expires = "2099-12-31"',
        '',
      ].join('\n'),
    )
    const fake = fakeClaude()
    try {
      const drew = await opened(root, 'en', 'docs/renders/icon.png', false, {
        words: 'a warmer rim',
        agent: fake.argv,
        env: { PW_FAKE_ASK: 'mcp__polyweave__picture_buy' },
      })
      expect(drew['asked']).toEqual(['mcp__polyweave__picture_buy'])
      expect(drew['price']).toBe('0.08')
    } finally {
      fake.dispose()
    }
  })

  it('plays a loop looped', async () => {
    const sound = await opened(root, 'en', 'audio/calm.wav')
    expect(sound['viewer']).toBe('sound')
    expect(sound['looped']).toBe(true)
  })
})
