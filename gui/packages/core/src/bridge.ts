// The one door between the window and the machine (§PW303). The renderer runs
// sandboxed and holds nothing but this object, which the preload freezes and hands over;
// every path and every process stays on the shell's side of it.

import type { Server } from './client'
import type { AnswerBody, Board, Difference, Mark, Overrule, State, Words } from './desk'
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
  reviewState: 'pw:review-state',
  reviewWords: 'pw:review-words',
  reviewAnswer: 'pw:review-answer',
  reviewCompare: 'pw:review-compare',
  reviewCanon: 'pw:review-canon',
  revise: 'pw:revise',
  sessionStart: 'pw:session-start',
  sessionSay: 'pw:session-say',
  sessionAnswer: 'pw:session-answer',
  sessionStop: 'pw:session-stop',
  sessionLine: 'pw:session-line',
  changed: 'pw:changed',
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
  /** Open the decision screen, on the card of the item named (§PW403). */
  review?: boolean
  /** Open the window's own decision screen, and answer this there when given (§PW400). */
  decide?: boolean | { family: string; choice: string; why: string; marks?: Mark[] }
  /** On the decision screen, load the canon boards, and promote this gate's picture (§PW402). */
  canon?: boolean
  promote?: { picture: string; why: string }
  /** Report only once the chosen item has changed on disk and been redrawn (§PW310). */
  follow?: boolean
  /** Ask for this change on the item and open a session on it (§PW306). */
  ask?: string
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
  /** `review.state`: the sittings, their answers and what waits, as the page reads them. */
  reviewState(project: string): Promise<State>
  /** `review.words`: the review catalog's words in the project's language (§PW400). */
  reviewWords(project: string): Promise<Words>
  /** `review.answer`: a person's verdict on one family, the page's one write. */
  reviewAnswer(project: string, body: AnswerBody | Overrule): Promise<Record<string, unknown>>
  /** `review.compare`: where two pictures differ above the noise floor (§PW401). */
  reviewCompare(project: string, old: string, now: string): Promise<Difference>
  /** `review.canon`: every style family's canon board (§PW402). */
  reviewCanon(project: string): Promise<Board[]>
  /** Keep a person's request to change an item, with `revision.ask` (§PW301). */
  revise(project: string, item: string, words: string): Promise<{ revision: string }>
  /** Open the session on a revision; one revision has one session, kept by its id. */
  startSession(
    project: string,
    revision: string,
  ): Promise<{ agent: string; first: string; waiting: string | null }>
  say(revision: string, text: string): Promise<void>
  answer(revision: string, requestId: string, allow: boolean): Promise<boolean>
  stop(revision: string): Promise<void>
  /** Every line a session writes, as it writes it; the answer stops listening. */
  onSessionLine(listener: (revision: string, line: string) => void): () => void
  /** Called once per burst of changes under an open project (§PW310). */
  onChanged(listener: (project: string) => void): () => void
  smoke(): Promise<Smoke | null>
  rendered(report: Record<string, unknown>): Promise<void>
}
