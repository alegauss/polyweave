// The one door between the window and the machine (§PW303). The renderer runs
// sandboxed and holds nothing but this object, which the preload freezes and hands over;
// every path and every process stays on the shell's side of it.

import type { Server } from './client'
import type { Engine } from './engine'
import type { Kind, Page } from './inventory'

/** Where the preload puts the bridge on `window`. */
export const BRIDGE_KEY = 'polyweave'

/** One IPC channel per call, so the shell handles nothing it did not name. */
export const CHANNELS = {
  find: 'pw:find',
  open: 'pw:open',
  inventory: 'pw:inventory',
  smoke: 'pw:smoke',
  rendered: 'pw:rendered',
} as const

/** An open project, as the screen names it: who answered and which engine it is. */
export interface Opened {
  project: string
  server: Server
  engine: Engine
}

/** A run that drives itself and reports what it drew, for the gate's live test. */
export interface Smoke {
  root: string
  depth: number
  language: string
  /** Where to save a picture of the window once it has drawn, when asked. */
  shot?: string
}

export interface Bridge {
  find(root: string, depth: number): Promise<string[]>
  open(project: string): Promise<Opened>
  inventory(project: string, kind?: Kind, offset?: number): Promise<Page>
  smoke(): Promise<Smoke | null>
  rendered(report: Record<string, unknown>): Promise<void>
}
