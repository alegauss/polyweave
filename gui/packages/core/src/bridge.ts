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
  brief: 'pw:brief',
  lineage: 'pw:lineage',
  file: 'pw:file',
  revisions: 'pw:revisions',
  review: 'pw:review',
  smoke: 'pw:smoke',
  rendered: 'pw:rendered',
} as const

/** A file of the project, carried across as bytes the page can show (§PW304). */
export interface Shown {
  path: string
  mime: string
  base64: string
}

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
  /** The item to open once the project is drawn, by its inventory id. */
  item?: string
  /** Where to save a picture of the window once it has drawn, when asked. */
  shot?: string
  /** Open the project's verdicts, on the item's sitting where an item is named. */
  review?: boolean
}

export interface Bridge {
  find(root: string, depth: number): Promise<string[]>
  open(project: string): Promise<Opened>
  inventory(project: string, kind?: Kind, offset?: number): Promise<Page>
  /** `asset.brief` on one item, as polyweave answers it. */
  brief(project: string, id: string): Promise<Record<string, unknown>>
  /** `provenance.generated` on one file: its chain back to a purchase, if it has one. */
  lineage(project: string, path: string): Promise<Record<string, unknown>>
  /** One file under the project, refused for any path that resolves outside it. */
  file(project: string, path: string): Promise<Shown>
  /** The items a person has an open revision on, from `revision.open` (§PW301). */
  revisions(project: string): Promise<string[]>
  /** The review page's address for the project, its server started on the first call. */
  review(project: string): Promise<string>
  smoke(): Promise<Smoke | null>
  rendered(report: Record<string, unknown>): Promise<void>
}
