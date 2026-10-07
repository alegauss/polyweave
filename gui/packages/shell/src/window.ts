// The window, and the posture its renderer runs under (§PW303).

import path from 'node:path'
import { pathToFileURL } from 'node:url'

import { BrowserWindow, shell } from 'electron'

/** The renderer is a web page and nothing more: no Node, isolated, sandboxed. */
export const POSTURE = {
  sandbox: true,
  contextIsolation: true,
  nodeIntegration: false,
  webSecurity: true,
} as const

/** The built renderer, relative to this file once bundled into `shell/dist`. */
const RENDERER = path.join(import.meta.dirname, '..', '..', 'ui', 'dist', 'index.html')

/** The preload, bundled to CommonJS: a sandboxed preload has Electron's `require` only. */
const PRELOAD = path.join(import.meta.dirname, 'preload.cjs')

export function createWindow(show: boolean): BrowserWindow {
  const window = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 560,
    show: false,
    title: 'polyweave',
    webPreferences: { ...POSTURE, preload: PRELOAD },
  })
  const home = pathToFileURL(RENDERER).href
  // The app never navigates away from itself; a link out opens in the person's browser.
  window.webContents.on('will-navigate', (event, url) => {
    if (url !== home) event.preventDefault()
  })
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) void shell.openExternal(url)
    return { action: 'deny' }
  })
  if (show) window.once('ready-to-show', () => window.show())
  void window.loadURL(home)
  return window
}
