// The only code on both sides of the isolation boundary. It hands the renderer one
// frozen object built from `core`'s Bridge and nothing else: no ipcRenderer, no module,
// no path. Bundled to CommonJS, because a sandboxed preload can require Electron alone.

import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'

import { BRIDGE_KEY, CHANNELS, type Bridge } from '@pw/core'

const bridge: Bridge = {
  find: (root, depth) => ipcRenderer.invoke(CHANNELS.find, root, depth),
  open: (project) => ipcRenderer.invoke(CHANNELS.open, project),
  inventory: (project, kind, offset) =>
    ipcRenderer.invoke(CHANNELS.inventory, project, kind, offset),
  brief: (project, id) => ipcRenderer.invoke(CHANNELS.brief, project, id),
  lineage: (project, path) => ipcRenderer.invoke(CHANNELS.lineage, project, path),
  file: (project, path) => ipcRenderer.invoke(CHANNELS.file, project, path),
  revisions: (project) => ipcRenderer.invoke(CHANNELS.revisions, project),
  review: (project) => ipcRenderer.invoke(CHANNELS.review, project),
  revise: (project, item, words) => ipcRenderer.invoke(CHANNELS.revise, project, item, words),
  startSession: (project, revision) => ipcRenderer.invoke(CHANNELS.sessionStart, project, revision),
  say: (revision, text) => ipcRenderer.invoke(CHANNELS.sessionSay, revision, text),
  answer: (revision, requestId, allow) =>
    ipcRenderer.invoke(CHANNELS.sessionAnswer, revision, requestId, allow),
  stop: (revision) => ipcRenderer.invoke(CHANNELS.sessionStop, revision),
  onSessionLine: (listener) => {
    const heard = (_event: IpcRendererEvent, revision: string, line: string) => listener(revision, line)
    ipcRenderer.on(CHANNELS.sessionLine, heard)
    return () => ipcRenderer.removeListener(CHANNELS.sessionLine, heard)
  },
  smoke: () => ipcRenderer.invoke(CHANNELS.smoke),
  rendered: (report) => ipcRenderer.invoke(CHANNELS.rendered, report),
}

contextBridge.exposeInMainWorld(BRIDGE_KEY, Object.freeze(bridge))
