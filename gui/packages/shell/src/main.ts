// The Electron main process (§PW303): the only place a path or a process is touched.
// Every call the renderer can make is one IPC channel `core` names, answered here with
// what a held `polyweave serve` says.

import { writeFile } from 'node:fs/promises'

import { app, BrowserWindow, ipcMain } from 'electron'

import { CHANNELS, find, page, type Kind, type Opened, type Smoke } from '@pw/core'

import { disk } from './disk'
import { shown } from './files'
import { Held } from './held'
import { SMOKE_VAR } from './smoke'
import { createWindow } from './window'

const held = new Held()
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
  void held.closeAll()
})
app.on('window-all-closed', () => app.quit())

void app.whenReady().then(() => {
  createWindow(!smoke)
})
