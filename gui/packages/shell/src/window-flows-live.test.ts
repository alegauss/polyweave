// The window's screens driven the way a person uses them (§PW581): Playwright launches the
// built shell, finds by role and name what a person reads, and waits on what the page
// draws rather than on a guessed timeout. A screen's picture is the window's own render,
// whatever lies over it on the desk.

import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import electron from 'electron'
import { _electron, type ElectronApplication, type Page } from 'playwright'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { starship } from './window-fixture'

const MAIN = join(import.meta.dirname, '..', 'dist', 'main.js')

/** The window, in the language a person reads it in. */
async function launch(language: string): Promise<{ app: ElectronApplication; page: Page }> {
  const env: Record<string, string> = {}
  for (const [key, value] of Object.entries(process.env)) if (value !== undefined) env[key] = value
  // An editor that runs Electron as Node would start a Node, not a window (§PW438).
  delete env['ELECTRON_RUN_AS_NODE']
  const app = await _electron.launch({
    executablePath: String(electron),
    args: [MAIN, `--lang=${language}`],
    env,
  })
  return { app, page: await app.firstWindow() }
}

/** Find the projects under `root` and open the one called `name`. */
async function open(page: Page, root: string, labels: { root: string; find: string; open: string }) {
  await page.getByLabel(labels.root).fill(root)
  await page.getByRole('button', { name: labels.find }).click()
  await page.getByRole('listitem').filter({ hasText: 'starship' }).getByRole('button', { name: labels.open }).click()
  await page.getByRole('heading', { level: 1, name: 'starship' }).waitFor({ timeout: 30_000 })
}

const EN = { root: 'Folder to look under', find: 'Find projects', open: 'Open' }

describe.skipIf(!existsSync(MAIN))('the window, as a person drives it', () => {
  let root: string
  let app: ElectronApplication | undefined

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'pw-flows-'))
    await starship(root)
  })

  afterEach(async () => {
    await app?.close()
    app = undefined
    await rm(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  })

  it('opens a project found under the root and draws its inventory by kind, in pt-BR', async () => {
    const launched = await launch('pt-BR')
    app = launched.app
    const page = launched.page
    await page.getByRole('heading', { level: 1, name: 'Projetos' }).waitFor()
    await open(page, root, { root: 'Pasta onde procurar', find: 'Procurar projetos', open: 'Abrir' })
    // Nothing is still opening once the project is on screen.
    expect(await page.getByRole('status').count()).toBe(0)
    await page.getByText(join(root, 'starship'), { exact: true }).waitFor()
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
    const launched = await launch('en')
    app = launched.app
    const page = launched.page
    await open(page, root, EN)
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
    const launched = await launch('en')
    app = launched.app
    const page = launched.page
    await open(page, root, EN)
    await page.getByRole('button', { name: /^audio\/calm\.wav/ }).click()
    const audio = page.locator('audio')
    await audio.waitFor()
    // The shell has no DOM types: the element is read for the one property asked.
    expect(await audio.evaluate((element) => (element as unknown as { loop: boolean }).loop)).toBe(true)
  })
})
