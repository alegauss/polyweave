// The decision screen's facts, read the way the review page reads them (§PW400). The
// page is src/polyweave/review_page/page.js; what it decides about a sitting (which are
// open, what a card shows, what a choice says, how far along a person is) is here as
// plain functions, so the window's screen and, later, the browser's draw the same.

import type { Shown } from './bridge'

/** A choice as a sitting says it: what it is, what it means, what follows. */
export interface Choice {
  label: string
  means: string
  then: string
}

export interface Member {
  name: string
  new?: string
  old?: string
  sound?: boolean
  /** A spoken line's words by locale, with who says it and its key. */
  text?: Record<string, string>
  who?: string
  speaker?: string
  line?: string
  examples?: string[]
  films?: { label: string; path: string }[]
  measured?: unknown
}

/** One member as the tool held it: passed, failed, or not held at all. */
export interface Held {
  name: string
  passed: boolean | null
  failed?: string[]
}

export interface Laid {
  members?: Member[]
  sheet: string
  said?: Held[]
  about?: string
}

export interface Sitting {
  manifest: string
  at: string
  kind?: string
  title?: string
  about?: string
  /** A sitting from before choices said what they lead to keeps English strings. */
  choices?: Record<string, Choice | string>
  families: Record<string, Laid>
  tone?: string[]
  legend?: Record<string, string>
}

/** One answer kept in answers.jsonl. */
export interface Recorded {
  sitting: string
  family: string
  choice: string
  why?: string
  at?: string
}

export interface State {
  language: string
  project?: string | null
  pending: { assets: { asset: string; waiting?: boolean; candidate?: string; judged?: string }[] }
  sittings: Sitting[]
  answers: Recorded[]
}

/** The review catalog in one language: the page's words and each kind of sitting's. */
export interface Words {
  language: string
  page: Record<string, string>
  kinds: Record<string, { title?: string; about?: string; choices?: Record<string, Choice> }>
}

/** What the screen sends to `review.answer` for one family. */
export interface AnswerBody {
  sitting: string
  family: string
  choice: string
  why: string
}

/** What a decision screen reads and writes through, wherever it runs. */
export interface Desk {
  state(): Promise<State>
  words(): Promise<Words>
  answer(body: AnswerBody): Promise<Record<string, unknown>>
  file(path: string): Promise<Shown>
}

/** A word of the catalog with its `{fields}` filled, or the key where it has none. */
export function say(words: Words, key: string, fields: Record<string, string | number> = {}): string {
  return (words.page[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) =>
    name in fields ? String(fields[name]) : '',
  )
}

/** A choice as words, an older sitting's English string read by its key. */
export function choiceOf(words: Words, word: string, raw: Choice | string, kind = 'look'): Choice {
  if (typeof raw !== 'string') return raw
  return words.kinds[kind]?.choices?.[word] ?? { label: word, means: raw, then: '' }
}

/** Whether any member of a family failed what it was held to. */
const failing = (laid: Laid) => (laid.said ?? []).some((one) => (one.failed ?? []).length > 0)

/** The choices a card offers: "number" only where something failed. */
export function choices(words: Words, sitting: Sitting, laid?: Laid): [string, Choice][] {
  const failed = laid ? failing(laid) : Object.values(sitting.families).some(failing)
  return Object.entries(sitting.choices ?? {})
    .filter(([word]) => word !== 'number' || failed)
    .map(([word, raw]) => [word, choiceOf(words, word, raw, sitting.kind)])
}

/** The last answer a family was given, if any. */
export function last(sitting: Sitting, family: string, answers: Recorded[]): Recorded | undefined {
  return answers.filter((one) => one.sitting === sitting.manifest && one.family === family).at(-1)
}

/** A card's badge: waiting, accepted, sent back, or answered otherwise. */
export function status(answer: Recorded | undefined): 'wait' | 'accept' | 'look' | 'other' {
  if (!answer) return 'wait'
  return answer.choice === 'accept' || answer.choice === 'look' ? answer.choice : 'other'
}

/** How many of a sitting's families have an answer. */
export function answered(sitting: Sitting, answers: Recorded[]): number {
  return Object.keys(sitting.families).filter((name) => last(sitting, name, answers)).length
}

const finished = (sitting: Sitting, answers: Recorded[]) =>
  answered(sitting, answers) >= Object.keys(sitting.families).length

/** The sittings newest first: those with something to answer, and those finished. */
export function ordered(state: State): { open: Sitting[]; done: Sitting[] } {
  const newest = state.sittings.slice().reverse()
  return {
    open: newest.filter((one) => !finished(one, state.answers)),
    done: newest.filter((one) => finished(one, state.answers)),
  }
}

/** Progress over every open sitting, so two read as one amount of work; null when none. */
export function progress(state: State): { done: number; total: number } | null {
  const { open } = ordered(state)
  if (!open.length) return null
  return {
    done: open.reduce((sum, one) => sum + answered(one, state.answers), 0),
    total: open.reduce((sum, one) => sum + Object.keys(one.families).length, 0),
  }
}

/** What a card shows, the first a family has: a line, films, the pictures, the sheet. */
export type Visual =
  | { kind: 'line'; lines: Member[] }
  | { kind: 'films'; films: { label: string; path: string }[]; sheet: string }
  | { kind: 'pictures'; members: Member[]; sheet: string }
  | { kind: 'sheet'; sheet: string }

export function visual(laid: Laid): Visual {
  const members = laid.members ?? []
  const lines = members.filter((one) => one.text)
  if (lines.length) return { kind: 'line', lines }
  const films = members.flatMap((one) => one.films ?? [])
  if (films.length) return { kind: 'films', films, sheet: laid.sheet }
  const pictures = members.filter((one) => one.new && !one.sound)
  if (pictures.length) return { kind: 'pictures', members: pictures, sheet: laid.sheet }
  return { kind: 'sheet', sheet: laid.sheet }
}

/** A card's title: who says a line, else the family's name. */
export function title(name: string, laid: Laid): string {
  const speaking = (laid.members ?? []).find((one) => one.text)
  return speaking ? (speaking.who ?? speaking.speaker ?? name) : name
}

/** Why an answer cannot be sent yet, as a catalog key, or null when it can. */
export function unready(choice: string | null, why: string): string | null {
  if (!choice) return 'need_choice'
  // A redo needs to say what is wrong; an accept may say nothing more.
  if (choice !== 'accept' && !why.trim()) return 'need_note'
  return null
}
