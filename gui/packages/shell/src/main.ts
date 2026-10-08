// The Electron main process (§PW303): the only place a path or a process is touched.
// Every call the renderer can make is one IPC channel `core` names, answered here with
// what a held `polyweave serve` says.

import { writeFile } from 'node:fs/promises'

import { app, BrowserWindow, ipcMain } from 'electron'

import { CHANNELS, find, opening, page, type Kind, type Opened, type Revision, type Smoke } from '@pw/core'

import { agent } from './agent'
import { disk } from './disk'
import { shown } from './files'
import { Held } from './held'
import { Reviews } from './reviews'
import { start, type Session } from './sessions'
import { SMOKE_VAR } from './smoke'
import { createWindow } from './window'

const held = new Held()
const reviews = new Reviews()
/** One session per revision, by the revision's id (§PW306). */
const sessions = new Map<string, Session>()
const smoke: Smoke | null = process.env[SMOKE_VAR]
  ? (JSON.parse(process.env[SMOKE_VAR]) as Smoke)
  : null

ipcMain.handle(CHANNELS.find, (_event, root: string, depth: number) =>
  find(disk, root, depth),
)
ipcMain.handle(CHANNELS.open, async (_event, project: string): Promise<Opened> => {
  const open = await held.opened(project)
  return { project, server: open.server, engine: open.engine }
})
ipcMain.handle(
  CHANNELS.inventory,
  async (_event, project: string, kind?: Kind, offset?: number) =>
    page((await held.opened(project)).client, project, {
      ...(kind ? { kind } : {}),
      ...(offset ? { offset } : {}),
    }),
)
ipcMain.handle(CHANNELS.brief, async (_event, project: string, id: string) =>
  (await held.opened(project)).client.call('asset.brief', { asset: id, root: project }),
)
ipcMain.handle(CHANNELS.lineage, async (_event, project: string, path: string) =>
  (await held.opened(project)).client.call('provenance.generated', {
    paths: [path],
    root: project,
  }),
)
ipcMain.handle(CHANNELS.file, (_event, project: string, path: string) => shown(project, path))
ipcMain.handle(CHANNELS.revisions, async (_event, project: string) => {
  const open = (await (await held.opened(project)).client.call('revision.open', {
    root: project,
  })) as { revisions: { item: string }[] }
  return [...new Set(open.revisions.map((one) => one.item))]
})
ipcMain.handle(CHANNELS.review, async (_event, project: string) =>
  reviews.url(project, (await held.opened(project)).engine),
)
ipcMain.handle(CHANNELS.revise, async (_event, project: string, item: string, words: string) =>
  (await held.opened(project)).client.call('revision.ask', { item, words, root: project }),
)
ipcMain.handle(CHANNELS.sessionStart, async (event, project: string, revision: string) => {
  const client = (await held.opened(project)).client
  const open = (await client.call('revision.open', { root: project })) as {
    revisions: (Revision & { brief: Record<string, unknown> })[]
  }
  const asked = open.revisions.find((one) => one.revision === revision)
  if (!asked) throw new Error(`revision ${revision} is not open in ${project}`)
  const runs = agent(process.env, app.isPackaged)
  if (!runs) throw new Error('there is no claude on this machine: install Claude Code and sign in')
  const first = opening(asked, asked.brief)
  if (!sessions.has(revision)) {
    const window = event.sender
    sessions.set(
      revision,
      start(runs, project, first, (line) => {
        if (!window.isDestroyed()) window.send(CHANNELS.sessionLine, revision, line)
      }),
    )
  }
  return { agent: runs.from, first }
})
ipcMain.handle(CHANNELS.sessionSay, (_event, revision: string, text: string) =>
  sessions.get(revision)?.say(text),
)
ipcMain.handle(CHANNELS.sessionAnswer, (_event, revision: string, requestId: string, allow: boolean) =>
  sessions.get(revision)?.answer(requestId, allow) ?? false,
)
ipcMain.handle(CHANNELS.sessionStop, (_event, revision: string) => {
  sessions.get(revision)?.stop()
  sessions.delete(revision)
})
ipcMain.handle(CHANNELS.smoke, () => smoke)
ipcMain.handle(CHANNELS.rendered, async (event, report: Record<string, unknown>) => {
  if (!smoke) return
  const window = BrowserWindow.fromWebContents(event.sender)
  if (smoke.shot && window) {
    await writeFile(smoke.shot, (await window.webContents.capturePage()).toPNG())
  }
  process.stdout.write(`rendered: ${JSON.stringify(report)}\n`)
  app.quit()
})

app.on('before-quit', () => {
  // The review page's server lives as long as the project's own (§PW305).
  for (const session of sessions.values()) session.stop()
  void reviews.closeAll()
  void held.closeAll()
})
app.on('window-all-closed', () => app.quit())

void app.whenReady().then(() => {
  // A hidden window is not composited, so a smoke run asked for a picture is shown.
  createWindow(!smoke || Boolean(smoke.shot))
})
