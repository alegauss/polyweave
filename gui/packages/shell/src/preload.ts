// The only code on both sides of the isolation boundary. It hands the renderer one
// frozen object built from `core`'s Bridge and nothing else: no ipcRenderer, no module,
// no path. Bundled to CommonJS, because a sandboxed preload can require Electron alone.

import { contextBridge, ipcRenderer } from 'electron'

import { BRIDGE_KEY, CHANNELS, type Bridge } from '@pw/core'

const bridge: Bridge = {
  find: (root, depth) => ipcRenderer.invoke(CHANNELS.find, root, depth),
  open: (project) => ipcRenderer.invoke(CHANNELS.open, project),
  inventory: (project, kind, offset) =>
    ipcRenderer.invoke(CHANNELS.inventory, project, kind, offset),
  smoke: () => ipcRenderer.invoke(CHANNELS.smoke),
  rendered: (report) => ipcRenderer.invoke(CHANNELS.rendered, report),
}

contextBridge.exposeInMainWorld(BRIDGE_KEY, Object.freeze(bridge))
