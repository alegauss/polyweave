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
  more: Record<string, unknown> = {},
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
        ...more,
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

  it("opens the decision screen on the card an item is judged on, in no frame", async () => {
    const game = join(root, 'starship')
    const laid = spawnSync('python', [
      '-m', 'polyweave', 'verdict.sitting',
      '--families', JSON.stringify({ icon: [{ name: 'icon', new: 'docs/renders/icon.png' }] }),
      '--out', 'review/first', '--root', game,
    ])
    expect(laid.status, laid.stderr?.toString()).toBe(0)
    const drew = await opened(root, 'en', 'docs/renders/icon.png', true)
    // The window's own screen, the one the review page serves in a browser (§PW403).
    expect(drew['framed']).toBe(false)
    expect(drew['focused']).toBe('review/first/sitting.json#icon')
  })

  it('draws a sitting on its own decision screen in pt-BR, and keeps an answer given there', async () => {
    const game = join(root, 'starship')
    const config = join(game, 'polyweave.toml')
    await writeFile(config, readFileSync(config, 'utf8') + '\n[review]\nlanguage = "pt-BR"\n')
    const laid = spawnSync('python', [
      '-m', 'polyweave', 'verdict.sitting',
      '--families', JSON.stringify({ icon: [{ name: 'icon', new: 'docs/renders/icon.png' }] }),
      '--out', 'review/first', '--root', game,
    ])
    expect(laid.status, laid.stderr?.toString()).toBe(0)
    const drew = await opened(root, 'pt-BR', undefined, false, undefined, {
      decide: { family: 'icon', choice: 'look', why: 'mais quente na borda' },
    })
    // Drawn natively, in the review catalog's words for the project's language.
    expect(drew['decide']).toBe('pt-BR')
    expect(drew['cards']).toEqual(['review/first/sitting.json#icon'])
    expect(drew['how']).toEqual(['Aceitar:', 'Refazer:'])
    expect(drew['badges']).toEqual(['Pedido para refazer'])
    // The answer is the page's write: in answers.jsonl, as the page would keep it.
    const kept = readFileSync(join(game, '.polyweave', 'answers.jsonl'), 'utf8').trim().split('\n')
    const answer = JSON.parse(kept.at(-1)!) as Record<string, unknown>
    expect(answer).toMatchObject({ sitting: 'review/first/sitting.json', family: 'icon', choice: 'look', why: 'mais quente na borda' })
  })

  it('compares a picture with the one it replaces, and keeps a mark drawn on it as a mask', async () => {
    const game = join(root, 'starship')
    await writeFile(join(game, 'docs', 'renders', 'icon_old.png'), Buffer.from(PNG, 'base64'))
    const laid = spawnSync('python', [
      '-m', 'polyweave', 'verdict.sitting',
      '--families', JSON.stringify({ icon: [{ name: 'icon', old: 'docs/renders/icon_old.png', new: 'docs/renders/icon.png' }] }),
      '--out', 'review/again', '--root', game,
    ])
    expect(laid.status, laid.stderr?.toString()).toBe(0)
    const drew = await opened(root, 'en', undefined, false, undefined, {
      decide: {
        family: 'icon',
        choice: 'look',
        why: 'the corner is wrong',
        marks: [{ member: 'icon', shapes: [{ box: [0, 0, 1, 1] }] }],
      },
    })
    // The four ways to compare two versions, on the card with an old picture.
    expect(drew['modes']).toEqual(['side by side', 'slider', 'onion skin', 'difference'])
    expect(drew['markers']).toBe(1)
    // The mark is the page's: a mask the picture's size, tied to its digest.
    const kept = readFileSync(join(game, '.polyweave', 'answers.jsonl'), 'utf8').trim().split('\n')
    const answer = JSON.parse(kept.at(-1)!) as { marks: { member: string; mask: string; sha256: string }[] }
    expect(answer.marks).toHaveLength(1)
    expect(answer.marks[0]).toMatchObject({ member: 'icon' })
    expect(existsSync(join(game, answer.marks[0]!.mask))).toBe(true)
  })

  it('draws the gate lanes, a turntable and the canon, and promotes a refused picture', async () => {
    const game = join(root, 'starship')
    const config = join(game, 'polyweave.toml')
    await writeFile(config, readFileSync(config, 'utf8') + '\n[style]\ncanon = "canon"\npalette = ["#f2c14e"]\n')
    // A real gate run against a one-picture canon, and a mesh turned by a stand-in bake.
    const made = spawnSync('python', [
      '-c',
      [
        'import json, sys',
        'from pathlib import Path',
        'from PIL import Image, ImageDraw',
        'from polyweave import picture, shape',
        'g = Path(sys.argv[1])',
        'def drawn(path, box):',
        '    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))',
        '    ImageDraw.Draw(image).ellipse(box, fill=(242, 193, 78, 255))',
        '    image.save(g / path)',
        '(g / "canon").mkdir()',
        'drawn("canon/c0.png", (14, 44, 114, 84))',
        '(g / "canon" / "canon.json").write_text(json.dumps([{"picture": "c0.png", "sha256": "0",',
        '    "verdict": {"choice": "accept", "why": "yes", "when": "2026-09-25"}}]))',
        'drawn("outline.png", (14, 44, 114, 84))',
        'drawn("wide.png", (15, 44, 115, 84))',
        'drawn("dome.png", (44, 8, 84, 120))',
        'picture.gate(["wide.png", "dome.png"], "outline.png", root=g)',
        'def bake(report, *, out, model, rung, root, inline, azimuth, elevation):',
        '    Image.new("RGBA", (16, 16), (100, 100, 100, 255)).save(out)',
        '    return {"artefact": out}',
        '(g / "m.glb").write_bytes(b"glTF")',
        'shape.turntable("m.glb", out="turns/m", root=g, frames=4, bake=bake)',
      ].join('\n'),
      game,
    ])
    expect(made.status, made.stderr?.toString()).toBe(0)
    const drew = await opened(root, 'en', undefined, false, undefined, {
      decide: true,
      canon: true,
      promote: { picture: 'dome.png', why: 'the dome is what I wanted' },
    })
    // The refused beside the kept, for this run and the fixture's own, the mesh turned,
    // and the canon on its board.
    expect(drew['gates']).toBe(2)
    expect(drew['kept']).toBe(2)
    expect(drew['refused']).toBe(2)
    expect(drew['turntables']).toEqual(['m'])
    expect(drew['boards']).toEqual(['default'])
    // The promotion is the page's write: an overruling of the gate, kept as an answer.
    const kept = readFileSync(join(game, '.polyweave', 'answers.jsonl'), 'utf8').trim().split('\n')
    const answer = JSON.parse(kept.at(-1)!) as { sitting: string; family: string; why: string }
    expect(answer.sitting).toMatch(/^gate:/)
    expect(answer).toMatchObject({ family: 'dome', why: 'the dome is what I wanted' })
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

  it('follows the project: an item changed on disk is marked, not swapped silently', async () => {
    const icon = join(root, 'starship', 'docs', 'renders', 'icon.png')
    let flip = 0
    // Rewritten until the window says it saw the change, as a session or terminal would.
    const writing = setInterval(() => {
      flip += 1
      void writeFile(icon, Buffer.concat([Buffer.from(PNG, 'base64'), Buffer.from([flip])]))
    }, 700)
    try {
      const drew = await opened(root, 'en', 'docs/renders/icon.png', false, undefined, { follow: true })
      expect(drew['changed']).toBe(true)
    } finally {
      clearInterval(writing)
    }
  })

  it('opens through npm start even where the editor runs Electron as Node', async () => {
    // §PW438: VS Code exports ELECTRON_RUN_AS_NODE=1, and the window failed to start.
    const launch = join(import.meta.dirname, '..', 'launch.mjs')
    const drew = await new Promise<Record<string, unknown>>((resolve, reject) => {
      const env = {
        ...process.env,
        ELECTRON_RUN_AS_NODE: '1',
        [SMOKE_VAR]: JSON.stringify({ root, depth: 1, language: 'en' }),
      }
      const child = spawn(process.execPath, [launch, MAIN], { env, windowsHide: true })
      let out = ''
      child.stdout.on('data', (chunk: Buffer) => {
        out += chunk.toString('utf8')
        const said = /^rendered: (.*)$/m.exec(out)
        if (said) resolve(JSON.parse(said[1]!) as Record<string, unknown>)
      })
      child.stderr.on('data', (chunk: Buffer) => (out += chunk.toString('utf8')))
      child.on('exit', (code) => reject(new Error(`launch exited ${code} without drawing:\n${out}`)))
    })
    expect(drew['project']).toBe(join(root, 'starship'))
  })

  it('plays a loop looped', async () => {
    const sound = await opened(root, 'en', 'audio/calm.wav')
    expect(sound['viewer']).toBe('sound')
    expect(sound['looped']).toBe(true)
  })
})
