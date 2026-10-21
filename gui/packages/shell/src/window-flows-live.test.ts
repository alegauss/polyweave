// The window's screens driven the way a person uses them (§PW581): Playwright launches the
// built shell, finds by role and name what a person reads, and waits on what the page
// draws rather than on a guessed timeout. A screen's picture is the window's own render,
// whatever lies over it on the desk.

import { spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import electron from 'electron'
import { _electron, chromium, type Browser, type ElectronApplication, type Page } from 'playwright'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { AGENT_VAR } from './agent'
import { fakeClaude, type FakeClaude } from './fake-claude'
import { PNG, starship } from './window-fixture'

const MAIN = join(import.meta.dirname, '..', 'dist', 'main.js')
const LAUNCH = join(import.meta.dirname, '..', 'launch.mjs')

/** This process's environment as a child is handed it, with `more` over it. */
function environment(more: Record<string, string> = {}): Record<string, string> {
  const env: Record<string, string> = {}
  for (const [key, value] of Object.entries(process.env)) if (value !== undefined) env[key] = value
  // An editor that runs Electron as Node would start a Node, not a window (§PW438).
  delete env['ELECTRON_RUN_AS_NODE']
  return { ...env, ...more }
}

const EN = { root: 'Folder to look under', find: 'Find projects', open: 'Open' }
const PT = { root: 'Pasta onde procurar', find: 'Procurar projetos', open: 'Abrir' }

/** Find the projects under `root` and open the one called starship. */
async function open(page: Page, root: string, labels: { root: string; find: string; open: string } = EN) {
  await page.getByLabel(labels.root).fill(root)
  await page.getByRole('button', { name: labels.find }).click()
  await page.getByRole('listitem').filter({ hasText: 'starship' }).getByRole('button', { name: labels.open }).click()
  await page.getByRole('heading', { level: 1, name: 'starship' }).waitFor({ timeout: 30_000 })
}

/** Lay out a sitting of one picture family, as an agent would after a change. */
function sitting(game: string, out: string, members: Record<string, string>[]) {
  const laid = spawnSync('python', [
    '-m', 'polyweave', 'verdict.sitting',
    '--families', JSON.stringify({ icon: members }),
    '--out', out, '--root', game,
  ])
  expect(laid.status, laid.stderr?.toString()).toBe(0)
}

/** The answer the page wrote last, as `answers.jsonl` keeps it. */
function lastAnswer(game: string): Record<string, unknown> {
  const kept = readFileSync(join(game, '.polyweave', 'answers.jsonl'), 'utf8').trim().split('\n')
  return JSON.parse(kept.at(-1)!) as Record<string, unknown>
}

describe.skipIf(!existsSync(MAIN))('the window, as a person drives it', () => {
  let root: string
  let game: string
  let app: ElectronApplication | undefined
  let fake: FakeClaude | undefined

  /** The window, in the language a person reads it in. */
  const launch = async (language: string, more: Record<string, string> = {}): Promise<Page> => {
    app = await _electron.launch({
      executablePath: String(electron),
      args: [MAIN, `--lang=${language}`],
      env: environment(more),
    })
    return app.firstWindow()
  }

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'pw-flows-'))
    game = await starship(root)
  })

  afterEach(async () => {
    await app?.close()
    app = undefined
    fake?.dispose()
    fake = undefined
    await rm(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  })

  it('opens a project found under the root and draws its inventory by kind, in pt-BR', async () => {
    const page = await launch('pt-BR')
    await page.getByRole('heading', { level: 1, name: 'Projetos' }).waitFor()
    await open(page, root, PT)
    // Nothing is still opening once the project is on screen.
    expect(await page.getByRole('status').count()).toBe(0)
    await page.getByText(game, { exact: true }).waitFor()
    await page.getByText(/^Servido por polyweave .*, encontrado no PATH$/).waitFor()
    // The kinds in the inventory's order, each with how many it holds, in the catalog's words.
    await expect.poll(() => page.getByRole('heading', { level: 2 }).allTextContents()).toEqual(['Imagens (1)', 'Sons (1)', 'Falas (2)'])
    await page.getByText('4 itens', { exact: true }).waitFor()
    // The open revision is what the list can be narrowed to.
    await page.getByRole('button', { name: 'Com revisão aberta' }).click()
    await expect.poll(() => page.getByRole('heading', { level: 2 }).allTextContents()).toEqual(['Falas (1)'])
    const shot = await page.screenshot()
    expect(shot.byteLength).toBeGreaterThan(1000)
  })

  it('shows a line beside what it was held to, and a picture beside its gate', async () => {
    const page = await launch('en')
    await open(page, root)
    await page.getByRole('button', { name: /^line:TITLE/ }).click()
    await page.getByRole('heading', { level: 2, name: 'line:TITLE' }).waitFor()
    await expect.poll(() => page.getByRole('definition').allTextContents()).toEqual(['Starship'])
    await page.getByText('No person has judged this line yet.').waitFor()

    await page.getByRole('button', { name: /^docs\/renders\/icon\.png/ }).click()
    await page.getByRole('img', { name: 'docs/renders/icon.png' }).waitFor()
    // Both lanes: the kept icon and the refused one beside it, with why it was refused.
    await page.getByRole('heading', { level: 3, name: 'Its last gate' }).waitFor()
    const refused = page.getByRole('listitem').filter({ hasText: 'docs/renders/other.png' })
    await refused.waitFor()
    expect(await refused.textContent()).toContain('edge drifted')
  })

  it('plays a loop looped', async () => {
    const page = await launch('en')
    await open(page, root)
    await page.getByRole('button', { name: /^audio\/calm\.wav/ }).click()
    const audio = page.locator('audio')
    await audio.waitFor()
    // The shell has no DOM types: the element is read for the one property asked.
    expect(await audio.evaluate((element) => (element as unknown as { loop: boolean }).loop)).toBe(true)
  })

  it('opens the decision screen on the card an item is judged on, in no frame', async () => {
    sitting(game, 'review/first', [{ name: 'icon', new: 'docs/renders/icon.png' }])
    const page = await launch('en')
    await open(page, root)
    await page.getByRole('button', { name: /^docs\/renders\/icon\.png/ }).click()
    await page.getByRole('button', { name: 'Where it is judged' }).click()
    // The window's own screen, the one the review page serves in a browser (§PW403).
    const focused = page.locator('article[data-focused]')
    await focused.waitFor()
    expect(await focused.getAttribute('data-card')).toBe('review/first/sitting.json#icon')
    expect(await page.locator('iframe').count()).toBe(0)
  })

  it('draws a sitting on its own decision screen in pt-BR, and keeps an answer given there', async () => {
    const config = join(game, 'polyweave.toml')
    await writeFile(config, readFileSync(config, 'utf8') + '\n[review]\nlanguage = "pt-BR"\n')
    sitting(game, 'review/first', [{ name: 'icon', new: 'docs/renders/icon.png' }])
    const page = await launch('pt-BR')
    await open(page, root, PT)
    await page.getByRole('button', { name: 'Decidir' }).click()
    await page.getByRole('listitem').filter({ hasText: 'review/first' }).getByRole('button').click()
    // Drawn natively, in the review catalog's words for the project's language.
    await page.getByText('Como decidir', { exact: true }).waitFor()
    expect(await page.locator('[lang="pt-BR"][data-decide]').count()).toBe(1)
    await page.getByRole('button', { name: /^Refazer/ }).click()
    await page.getByLabel('O que está diferente? (obrigatório)').fill('mais quente na borda')
    await page.getByRole('button', { name: 'Registrar minha decisão' }).click()
    await page.getByText('Pedido para refazer', { exact: true }).waitFor()
    // The answer is the page's write: in answers.jsonl, as the page would keep it.
    expect(lastAnswer(game)).toMatchObject({
      sitting: 'review/first/sitting.json',
      family: 'icon',
      choice: 'look',
      why: 'mais quente na borda',
    })
  })

  it('compares a picture with the one it replaces, and keeps a mark drawn on it as a mask', async () => {
    await writeFile(join(game, 'docs', 'renders', 'icon_old.png'), Buffer.from(PNG, 'base64'))
    sitting(game, 'review/again', [{ name: 'icon', old: 'docs/renders/icon_old.png', new: 'docs/renders/icon.png' }])
    const page = await launch('en')
    await open(page, root)
    await page.getByRole('button', { name: 'Decide' }).click()
    await page.getByRole('listitem').filter({ hasText: 'review/again' }).getByRole('button').click()
    await page.getByText('Mark where it is wrong (optional)').click()
    // The four ways to compare two versions, on the card with an old picture.
    await expect.poll(() => page.getByRole('tab').allTextContents()).toEqual(['side by side', 'slider', 'onion skin', 'difference'])
    // A box dragged across the picture, as a person marks where it is wrong. It is measured
    // once both versions above it have drawn, which would otherwise move it down.
    await page.getByRole('img', { name: 'after' }).first().waitFor()
    await page.getByRole('img', { name: 'icon, to mark where it is wrong' }).waitFor()
    const canvas = page.locator('canvas[aria-label="icon, to mark where it is wrong"]')
    await canvas.scrollIntoViewIfNeeded()
    const frame = (await canvas.boundingBox())!
    await page.mouse.move(frame.x + 1, frame.y + 1)
    await page.mouse.down()
    await page.mouse.move(frame.x + frame.width - 1, frame.y + frame.height - 1, { steps: 5 })
    await page.mouse.up()
    await page.getByRole('button', { name: /^Redo/ }).click()
    await page.getByLabel('What is different? (required)').fill('the corner is wrong')
    await page.getByRole('button', { name: 'Record my decision' }).click()
    await page.getByText('Redo asked', { exact: true }).waitFor()
    // The mark is the page's: a mask the picture's size, tied to its digest.
    const answer = lastAnswer(game) as { marks: { member: string; mask: string }[] }
    expect(answer.marks).toHaveLength(1)
    expect(answer.marks[0]).toMatchObject({ member: 'icon' })
    expect(existsSync(join(game, answer.marks[0]!.mask))).toBe(true)
  })

  it('draws the gate lanes, a turntable and the canon, and promotes a refused picture', async () => {
    const config = join(game, 'polyweave.toml')
    await writeFile(config, readFileSync(config, 'utf8') + '\n[style]\ncanon = "canon"\npalette = ["#f2c14e"]\n')
    // A real gate run against a one-picture canon, and a mesh turned by a stand-in bake.
    const made = spawnSync('python', [
      '-c',
      [
        'import json, sys',
        'from pathlib import Path',
        'from PIL import Image, ImageDraw',
        'from polyweave.layers.geometry import shape',
        'from polyweave.layers.picture import picture',
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
    const page = await launch('en')
    await open(page, root)
    await page.getByRole('button', { name: 'Decide' }).click()
    await page.getByText('Advanced: gates, turntables, canons and every asset').click()
    // The refused beside the kept, for this run and the fixture's own, and the mesh turned.
    // The fixture's gate carries no date, so its heading is "Gate of" and nothing after.
    await expect.poll(() => page.getByRole('heading', { name: /^Gate of/ }).count()).toBe(2)
    expect(await page.locator('[data-lane="kept"] [data-candidate]').count()).toBe(2)
    expect(await page.locator('[data-lane="refused"] [data-candidate]').count()).toBe(2)
    await page.getByRole('heading', { name: 'm, turned' }).waitFor()
    // The canon on its board, measured only when asked.
    await page.getByRole('button', { name: "Show every family's canon" }).click()
    await page.getByRole('heading', { name: 'default canon' }).waitFor({ timeout: 30_000 })
    // The promotion is the page's write: an overruling of the gate, kept as an answer.
    const dome = page.locator('[data-candidate="dome.png"]')
    await dome.locator('xpath=ancestor::details[1]/summary').click()
    await dome.getByLabel('Why this one is right after all.').fill('the dome is what I wanted')
    await dome.getByRole('button', { name: 'Promote: the bar was wrong for this one' }).click()
    await dome.getByText('Recorded: promoted.').waitFor()
    const answer = lastAnswer(game) as { sitting: string; family: string; why: string }
    expect(answer.sitting).toMatch(/^gate:/)
    expect(answer).toMatchObject({ family: 'dome', why: 'the dome is what I wanted' })
  })

  it('asks for a change and opens a session on it, beside the item', async () => {
    fake = fakeClaude()
    const page = await launch('en', { [AGENT_VAR]: JSON.stringify(fake.argv) })
    await open(page, root)
    await page.getByRole('button', { name: /^line:TITLE/ }).click()
    await page.getByPlaceholder('What should change, in your words').fill('shorter, in capitals')
    await page.getByRole('button', { name: 'Ask, and open a Claude Code session on it' }).click()
    // The fake says its first message back: built from the revision and the brief.
    const turn = page.getByRole('listitem').filter({ hasText: 'Item: line:TITLE' })
    await turn.waitFor({ timeout: 30_000 })
    expect(await turn.textContent()).toContain('What they said: shorter, in capitals')
    // Its question is the window's to answer.
    await page.getByText('It asks to use Write', { exact: true }).waitFor()
    // What the session said is kept on the revision it works through.
    const turns = () => {
      const listed = spawnSync('python', ['-m', 'polyweave', 'revision.open', '--item', 'line:TITLE', '--root', game, '--json'])
      const found = JSON.parse(listed.stdout.toString()) as { revisions: { words: string; turns: { by: string }[] }[] }
      return found.revisions.find((one) => one.words === 'shorter, in capitals')?.turns.map((one) => one.by) ?? []
    }
    await expect.poll(turns, { timeout: 20_000 }).toContain('session')
  })

  it('stops a paid call with its price, for one yes', async () => {
    const config = join(game, 'polyweave.toml')
    await writeFile(
      config,
      [
        readFileSync(config, 'utf8'),
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
    fake = fakeClaude()
    const page = await launch('en', {
      [AGENT_VAR]: JSON.stringify(fake.argv),
      PW_FAKE_ASK: 'mcp__polyweave__picture_buy',
    })
    await open(page, root)
    await page.getByRole('button', { name: /^docs\/renders\/icon\.png/ }).click()
    await page.getByPlaceholder('What should change, in your words').fill('a warmer rim')
    await page.getByRole('button', { name: 'Ask, and open a Claude Code session on it' }).click()
    await page.getByText('It asks to use mcp__polyweave__picture_buy', { exact: true }).waitFor({ timeout: 30_000 })
    await page.getByText(/^This costs 0\.08 USD\./).waitFor()
    await page.getByText('A yes allows this one call, never the next.').waitFor()
  })

  it('follows the project: an item changed on disk is marked, not swapped silently', async () => {
    const page = await launch('en')
    await open(page, root)
    await page.getByRole('button', { name: /^docs\/renders\/icon\.png/ }).click()
    await page.getByRole('img', { name: 'docs/renders/icon.png' }).waitFor()
    // Rewritten as a session or terminal would, once the person is looking at it.
    await writeFile(
      join(game, 'docs', 'renders', 'icon.png'),
      Buffer.concat([Buffer.from(PNG, 'base64'), Buffer.from([1])]),
    )
    await page.getByText('This item changed on disk while you looked at it.').waitFor({ timeout: 30_000 })
    await page.getByRole('button', { name: 'See the new one' }).waitFor()
  })
})

describe.skipIf(!existsSync(MAIN))('npm start', () => {
  let child: ChildProcess | undefined
  let browser: Browser | undefined

  afterEach(async () => {
    await browser?.close().catch(() => undefined)
    child?.kill()
  })

  it('opens the window even where the editor runs Electron as Node', async () => {
    // §PW438: VS Code exports ELECTRON_RUN_AS_NODE=1, and the window failed to start.
    const port = await new Promise<number>((resolve) => {
      const probe = createServer().listen(0, '127.0.0.1', () => {
        const { port } = probe.address() as { port: number }
        probe.close(() => resolve(port))
      })
    })
    child = spawn(process.execPath, [LAUNCH, MAIN, `--remote-debugging-port=${port}`, '--lang=en'], {
      env: { ...environment(), ELECTRON_RUN_AS_NODE: '1' },
      windowsHide: true,
    })
    const exited = new Promise<never>((_resolve, reject) =>
      child!.on('exit', (code) => reject(new Error(`launch exited ${code} without a window`))),
    )
    const connect = async (): Promise<Browser> => {
      for (;;) {
        try {
          return await chromium.connectOverCDP(`http://127.0.0.1:${port}`)
        } catch {
          await new Promise((resolve) => setTimeout(resolve, 250))
        }
      }
    }
    browser = await Promise.race([connect(), exited])
    const pages = () => browser!.contexts().flatMap((context) => context.pages())
    await expect.poll(() => pages().length, { timeout: 30_000 }).toBeGreaterThan(0)
    await pages()[0]!.getByRole('heading', { level: 1, name: 'Projects' }).waitFor()
  })
})
