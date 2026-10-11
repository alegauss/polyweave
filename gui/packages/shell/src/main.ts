// The Electron main process (§PW303): the only place a path or a process is touched.
// Every call the renderer can make is one IPC channel `core` names, answered here with
// what a held `polyweave serve` says.

import { writeFile } from 'node:fs/promises'

import { app, BrowserWindow, ipcMain } from 'electron'

import { CHANNELS, find, opening, page, said, type Kind, type Opened, type Revision, type Smoke } from '@pw/core'

import { agent } from './agent'
import { Answers } from './answers'
import { disk } from './disk'
import { shown } from './files'
import { Held } from './held'
import { Holding } from './holding'
import { Strays, type Stray } from './outside'
import { Reviews } from './reviews'
import { start, type Session } from './sessions'
import { SMOKE_VAR } from './smoke'
import { Watching } from './watch'
import { createWindow } from './window'

const held = new Held()
const reviews = new Reviews()
const watching = new Watching()
/** One session per revision, by the revision's id (§PW306). */
const sessions = new Map<string, Session>()
/** The project each revision's session works in, for keeping its turns. */
const worked = new Map<string, string>()
const holding = new Holding()
const answers = new Answers()
// The person answers on the review page, so the window reads the answers every few
// seconds, as the page itself does (§PW307).
setInterval(() => void answers.look(), 5000)

/** Turns still being written, which quitting waits for so none is lost. */
const writing = new Set<Promise<unknown>>()

/** One turn kept on its revision (§PW306); a turn that cannot be kept is not fatal. */
function kept(revision: string, text: string, by: 'person' | 'session'): void {
  const project = worked.get(revision)
  if (!project || !text.trim()) return
  const write = held
    .opened(project)
    .then((open) => open.client.call('revision.turn', { revision, text, by, root: project }))
    .catch(() => undefined)
  writing.add(write)
  void write.finally(() => writing.delete(write))
}
const smoke: Smoke | null = process.env[SMOKE_VAR]
  ? (JSON.parse(process.env[SMOKE_VAR]) as Smoke)
  : null

ipcMain.handle(CHANNELS.find, (_event, root: string, depth: number) =>
  find(disk, root, depth),
)
ipcMain.handle(CHANNELS.open, async (event, project: string): Promise<Opened> => {
  const open = await held.opened(project)
  // The window follows the project as it changes (§PW310).
  const window = event.sender
  watching.start(project, () => {
    if (!window.isDestroyed()) window.send(CHANNELS.changed, project)
  })
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
  let waiting: string | null = null
  if (!sessions.has(revision) && !worked.has(revision)) {
    const window = event.sender
    worked.set(revision, project)
    // One session holds an item: a second revision on it starts once the first ends.
    const harness = (await client.call('revision.settings', { revision, root: project })) as {
      permissions: { deny: string[]; ask: string[] }
      env: Record<string, string>
    }
    const send = (line: string) => {
      if (!window.isDestroyed()) window.send(CHANNELS.sessionLine, revision, line)
    }
    // The change has a run, a ledger line and a budget, as any polyweave change does.
    const name = asked.item.split('/').pop()!.replace(/\.[^.]+$/, '')
    const run = (await client
      .call('loop.start', { asset: name, way: 'after', brief: asked.words, root: project })
      .catch(() => null)) as Record<string, unknown> | null
    answers.watch(revision, {
      project,
      call: (operation, args) => client.call(operation, args),
      run,
      say: (text) => {
        sessions.get(revision)?.say(text)
        kept(revision, text, 'person')
        send(JSON.stringify({ type: 'polyweave_answer', said: text }))
      },
      closed: (sitting, reached) => {
        send(JSON.stringify({ type: 'polyweave_closed', sitting, ...reached }))
        sessions.get(revision)?.stop()
        sessions.delete(revision)
      },
    })
    // What a shell command wrote outside the item, shown after it ran (§PW378).
    const strays = new Strays(() =>
      client
        .call('revision.outside', { revision, root: project })
        .then((found) => (found as { outside: Stray[] }).outside),
    )
    waiting = holding.take(asked.item, revision, () => {
      const session = start(
        runs,
        project,
        first,
        (line) => {
          const read = said(line)
          if (read.kind === 'text') kept(revision, read.text, 'session')
          // A paid call stops with its price and what the ceiling leaves (§PW308): the
          // question is held until its quote is beside it, so it is never asked bare.
          if (read.kind === 'ask' && harness.permissions.ask.includes(read.tool)) {
            void client
              .call('purchase.quote', { operation: read.tool, arguments: read.input, root: project })
              .then(
                (quoted) => ({ ...(quoted as object) }),
                (failed: Error) => ({ failed: failed.message }),
              )
              .then((quoted) => {
                send(JSON.stringify({ type: 'polyweave_quote', request_id: read.requestId, ...quoted }))
                send(line)
              })
          } else {
            send(line)
          }
          void strays.after(line).then((lines) => lines.forEach(send))
          // After a tool that may have changed the item, the window runs its checks too,
          // and shows them beside the conversation (§PW307).
          if (read.kind === 'tool' && /^(Write|Edit|MultiEdit|mcp__polyweave__)/.test(read.tool)) {
            void client
              .call('revision.check', { revision, root: project })
              .then((found) => send(JSON.stringify({ type: 'polyweave_check', ...(found as object) })))
              .catch(() => undefined)
          }
        },
        { ...process.env, ...harness.env },
        { settings: harness, disallowed: harness.permissions.deny },
      )
      sessions.set(revision, session)
      return session.finished
    })
  }
  return { agent: runs.from, first, waiting }
})
ipcMain.handle(CHANNELS.sessionSay, (_event, revision: string, text: string) => {
  sessions.get(revision)?.say(text)
  kept(revision, text, 'person')
})
ipcMain.handle(CHANNELS.sessionAnswer, (_event, revision: string, requestId: string, allow: boolean) =>
  sessions.get(revision)?.answer(requestId, allow) ?? false,
)
ipcMain.handle(CHANNELS.sessionStop, (_event, revision: string) => {
  answers.forget(revision)
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
  // A turn still being written is kept before the run ends.
  await Promise.all(writing)
  process.stdout.write(`rendered: ${JSON.stringify(report)}\n`)
  app.quit()
})

app.on('before-quit', () => {
  // The review page's server lives as long as the project's own (§PW305).
  watching.stopAll()
  for (const session of sessions.values()) session.stop()
  void reviews.closeAll()
  void held.closeAll()
})
app.on('window-all-closed', () => app.quit())

void app.whenReady().then(() => {
  // A hidden window is not composited, so a smoke run asked for a picture is shown.
  createWindow(!smoke || Boolean(smoke.shot))
})
