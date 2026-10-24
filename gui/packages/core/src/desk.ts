// The decision screen's facts (§PW400): what it decides about a sitting (which are open,
// what a card shows, what a choice says, how far along a person is) is here as plain
// functions, so the screen in the window and in the browser draws the same (§PW403).

import type { Shown } from './bridge'

/** A choice as a sitting says it: what it is, what it means, what follows. */
export interface Choice {
  label: string
  means: string
  then: string
  /** What the choice is called on a card that failed a bound, where it is the person's
   * acceptance of the look (§PW486). */
  failing_label?: string
  failing_means?: string
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
  /** Where the look is motion, a short muted loop (.mp4 or .webm) played in place. */
  motion?: string
  /** A model's .glb, seen in 3D beside its still (§PW601). */
  model?: string
  /** A sound's numbers by version, or a line's measure as words. */
  measured?: { old?: Record<string, unknown>; new?: Record<string, unknown> } | string
  /** A loop, played looped so its seam is heard. */
  loop?: boolean
}

/** A box drawn on a picture, in the picture's own pixels: left, top, right, bottom. */
export type Box = [number, number, number, number]

/** Where a person marked one member wrong; `review.answer` turns it into a mask. */
export interface Mark {
  member: string
  shapes: { box: Box }[]
}

/** Where two pictures differ above the noise floor, as `review.compare` answers. */
export interface Difference {
  map: string
  changed_patches: number
  patches: number
  tolerance: number
  tolerance_from?: string | null
}

/** One member as the tool held it: passed, failed, or not held at all. */
export interface Held {
  name: string
  passed: boolean | null
  failed?: string[]
  /** Each predicate's value today and its bounds, which a target is set beside (§PW620). */
  predicates?: Measured[]
}

/** One predicate of a held member, as the sheet measured it. */
export interface Measured {
  id: string
  value: number | null
  min: number | null
  max: number | null
}

/**
 * The targets a person typed, as `review.answer` takes them (§PW620): each predicate's id to
 * a number, a blank or unreadable field left out. Null where nothing was typed.
 */
export function aims(typed: Record<string, string>): Record<string, number> | null {
  const found = Object.entries(typed)
    .map(([id, text]) => [id, Number(text.trim().replace(',', '.'))] as const)
    .filter(([id, value]) => typed[id]!.trim() !== '' && Number.isFinite(value))
  return found.length ? Object.fromEntries(found) : null
}

export interface Laid {
  members?: Member[]
  sheet: string
  said?: Held[]
  about?: string
  /** Its members are alternatives for one slot: an accept names the one picked (§PW547). */
  pick?: 'one'
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
  /** The member picked of a family of alternatives (§PW547). */
  chosen?: string
}

/** One picture a gate weighed, with the numbers it was judged on (§PW175). */
export interface Candidate {
  picture: string
  passed: boolean
  failed: string[]
  silhouette_iou?: number
  drift?: Record<string, { value: number; canon: number; floor: number; which_way?: string }>
  unchecked?: string[]
  bought?: { credits: number; service: string } | null
  ceiling?: { left: number; unit: string } | null
  /** What it is best compared with: the parent it was varied from, or the canon. */
  compare?: { old: string; mode: string; mask: string | null } | null
}

export interface Gate {
  id: string
  at?: string
  family?: string | null
  chosen?: string | null
  why?: string
  candidates: Candidate[]
}

/** A mesh turned at the rig's own camera (§PW176). */
export interface Turntable {
  asset: string
  at?: string
  elevation?: number
  frames: { azimuth: number; picture: string }[]
  against?: string | null
  front?: string | null
}

/** One style family's canon on a board (§PW177), as `review.canon` answers. */
export interface Board {
  family: string
  palette: string[]
  skeleton?: unknown
  floors: Record<string, number | null>
  pictures: { picture: string; path: string; verdict: { choice: string; when: string; why: string } }[]
  without: Record<string, Record<string, number | null>>
  says?: string
  candidates?: { path: string }[]
}

export interface Waiting {
  asset: string
  waiting?: boolean
  candidate?: string
  judged?: string
}

export interface State {
  language: string
  project?: string | null
  pending: { assets: Waiting[] }
  sittings: Sitting[]
  answers: Recorded[]
  /** The codes a person says to accept from a conversation, by sitting manifest and
   * `page` for the gate and canon lanes (§PW443). Only the page's server sends them. */
  codes?: Record<string, string>
  gates?: Gate[]
  turntables?: Turntable[]
  /** The page's server, older than the package it runs, cannot record an answer (§PW294). */
  stale?: { code: string; message: string; remedy?: string } | null
}

/** The card a file is judged on, as `sitting#family`, or null where none holds it (§PW305). */
export function holding(state: State, member: string): string | null {
  for (const sitting of state.sittings) {
    for (const [name, laid] of Object.entries(sitting.families)) {
      if ((laid.members ?? []).some((one) => one.new === member || one.old === member)) {
        return `${sitting.manifest}#${name}`
      }
    }
  }
  return null
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
  marks?: Mark[]
  /** Moments of a loop marked wrong, each a member and seconds into its loop (§PW600). */
  moments?: { member: string; at: number }[]
  /** Views of a model marked wrong: where the camera stood and what it looked at (§PW601). */
  views?: { member: string; camera: [number, number, number]; target: [number, number, number] }[]
  /** The alternative picked, for an accept of a family whose `pick` is one (§PW547). */
  member?: string
  /** With a redo: each predicate's id to the bar the person says it must reach (§PW620). */
  targets?: Record<string, number>
}

/** The page's other writes: a gate's picture promoted or taken into a canon, a candidate
 * admitted to a canon, a canon picture withdrawn. Each is still `verdict.judge`'s. */
export type Overrule =
  | { gate: string; picture: string; choice: 'accept'; why: string; canon?: string }
  | { canon: string; admit: string; why: string }
  | { canon: string; withdraw: string; why: string }

/** What a decision screen reads and writes through, wherever it runs. */
export interface Desk {
  state(): Promise<State>
  words(): Promise<Words>
  answer(body: AnswerBody | Overrule): Promise<Record<string, unknown>>
  file(path: string): Promise<Shown>
  /** Where a browser can load a file itself, so it never crosses the desk as text. */
  href?(path: string): string
  compare(old: string, now: string): Promise<Difference>
  /** Every style family's canon board, read only when asked: it measures every picture. */
  canon(): Promise<Board[]>
}

/** A gate run's candidates in two lanes, the kept and the refused beside them. */
export function lanes(run: Gate): { kept: Candidate[]; refused: Candidate[] } {
  return {
    kept: run.candidates.filter((one) => one.passed),
    refused: run.candidates.filter((one) => !one.passed),
  }
}

/** A candidate's numbers as lines: the silhouette, what failed, each drift, what went unchecked. */
export function figures(words: Words, one: Candidate): string[] {
  const lines = [`${one.picture}: silhouette IoU ${one.silhouette_iou ?? '?'}`, ...one.failed]
  for (const [measure, number] of Object.entries(one.drift ?? {})) {
    lines.push(
      `${measure} ${number.value} / ${number.canon} ± ${number.floor}` +
        (number.which_way ? `, ${number.which_way}` : ''),
    )
  }
  for (const gap of one.unchecked ?? []) lines.push(say(words, 'unchecked', { gap }))
  if (one.bought) {
    const left = one.ceiling ? say(words, 'left', { left: one.ceiling.left, unit: one.ceiling.unit }) : ''
    lines.push(say(words, 'cost', { credits: one.bought.credits, service: one.bought.service }) + left)
  }
  return lines
}

/** Each asset's turntables, oldest first, so the newest is turned against the one before. */
export function turned(turntables: Turntable[]): [string, Turntable[]][] {
  const by = new Map<string, Turntable[]>()
  for (const one of turntables) by.set(one.asset, [...(by.get(one.asset) ?? []), one])
  return [...by]
}

/** The floors a canon picture holds open: each measure its absence would narrow. */
export function narrower(board: Board, picture: string): string[] {
  return Object.entries(board.without[picture] ?? {})
    .filter(([measure, value]) => {
      const floor = board.floors[measure]
      return value !== null && floor !== null && floor !== undefined && value < floor
    })
    .map(([measure, value]) => `${measure} ${board.floors[measure]} → ${value}`)
}

/** The box two points span, rounded to whole pixels; null where it is too thin to mean one. */
export function spanned(start: [number, number], end: [number, number]): Box | null {
  const box = [
    Math.min(start[0], end[0]),
    Math.min(start[1], end[1]),
    Math.max(start[0], end[0]),
    Math.max(start[1], end[1]),
  ].map(Math.round) as Box
  return box[2] - box[0] > 1 && box[3] - box[1] > 1 ? box : null
}

/** A point on a picture shown `shown` wide, in the pixels of the picture `natural` wide. */
export function inPixels(x: number, y: number, natural: number, shown: number): [number, number] {
  const k = shown ? natural / shown : 1
  return [x * k, y * k]
}

/** The marks worth sending: a member with no box says nothing. */
export function drawn(marks: Mark[]): Mark[] {
  return marks.filter((one) => one.shapes.length > 0)
}

/** What was measured of one version of a sound, as "name value" pairs. */
export function measuredOf(member: Member, version: 'old' | 'new'): string {
  const numbers = typeof member.measured === 'object' ? (member.measured[version] ?? {}) : {}
  return Object.entries(numbers)
    .filter(([, value]) => typeof value === 'number')
    .map(([name, value]) => `${name} ${String(value)}`)
    .join(', ')
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

/** Whether a family's card may be accepted as it stands: nothing failed, or the kind has
 * no "number" to say the bound is wrong with (§PW460); and it is not alternatives for one
 * slot, which only a person's pick answers (§PW547). */
export function acceptable(sitting: Sitting, family: string): boolean {
  const laid = sitting.families[family]
  if (laid?.pick === 'one') return false
  return !laid || !failing(laid) || !('number' in (sitting.choices ?? {}))
}

/** The choices a card offers: "number" only where something failed, and "accept" only
 * where nothing did (§PW460). Accept means the spec agrees, so on a failing card the
 * person's yes is "number", which moves the failed bound to what was measured, as theirs;
 * an accept there left the bound standing and the bake refusing what they accepted. The
 * sitting's own "how to decide" lists every choice its cards offer. */
export function choices(words: Words, sitting: Sitting, laid?: Laid): [string, Choice][] {
  const failed = laid ? failing(laid) : Object.values(sitting.families).some(failing)
  const numbered = 'number' in (sitting.choices ?? {})
  return Object.entries(sitting.choices ?? {})
    .filter(([word]) => word !== 'number' || failed)
    .filter(([word]) => !(laid && failed && numbered && word === 'accept'))
    .map(([word, raw]): [string, Choice] => {
      const choice = choiceOf(words, word, raw, sitting.kind)
      // On a failing card "number" is how a person accepts the look, and it says so:
      // Cottony's owner looked for an accept and found "Adjust the bound" (§PW486).
      if (laid && failed && word === 'number' && choice.failing_label) {
        return [word, { ...choice, label: choice.failing_label,
                        means: choice.failing_means ?? choice.means }]
      }
      return [word, choice]
    })
}

/** Whether a card's accept is held back because a member failed a bound, so the card
 * says why and that "number" is its acceptance (§PW486). */
export function acceptWithheld(sitting: Sitting, laid: Laid): boolean {
  return failing(laid) && 'number' in (sitting.choices ?? {}) && 'accept' in (sitting.choices ?? {})
}

/** Whether an answer was given to the sitting as it is laid out now (§PW615): a sitting
 * laid again in its folder keeps its manifest, and the answers to the members it held
 * before read as answers to the new ones, so a sitting nobody looked at read finished.
 * An answer with no time, from before answers kept one, still counts. */
export function since(sitting: Sitting, answer: Recorded): boolean {
  const laid = Date.parse(sitting.at)
  const given = answer.at ? Date.parse(answer.at) : NaN
  return Number.isNaN(laid) || Number.isNaN(given) || given >= laid
}

/** The last answer a family was given since its sitting was laid out, if any. */
export function last(sitting: Sitting, family: string, answers: Recorded[]): Recorded | undefined {
  return answers
    .filter((one) => one.sitting === sitting.manifest && one.family === family && since(sitting, one))
    .at(-1)
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

/** A sitting as the index lists it (§PW415): where it lives, what it is called, how much of
 * it is answered, and when it was laid out. */
export interface Listed {
  manifest: string
  /** The folder it was laid out in, which tells two sittings of one kind apart. */
  folder: string
  title?: string
  kind?: string
  at: string
  done: number
  total: number
}

const listing = (state: State) => (sitting: Sitting): Listed => ({
  manifest: sitting.manifest,
  folder: sitting.manifest.replaceAll('\\', '/').split('/').slice(0, -1).join('/') || sitting.manifest,
  title: sitting.title,
  kind: sitting.kind,
  at: sitting.at,
  done: answered(sitting, state.answers),
  total: Object.keys(sitting.families).length,
})

/** The index of sittings, each one page of its own, newest first: those with something
 * to answer, then those finished. A person opens one at a time instead of every card of
 * every sitting stacked on one page (§PW415). */
export function listed(state: State): { open: Listed[]; done: Listed[] } {
  const { open, done } = ordered(state)
  return { open: open.map(listing(state)), done: done.map(listing(state)) }
}

/** The families of a sitting no answer has reached yet, in the order it laid them out:
 * what "accept the rest" would answer, never one a person already answered (§PW415). */
export function unanswered(sitting: Sitting, answers: Recorded[]): string[] {
  return Object.keys(sitting.families).filter((name) => !last(sitting, name, answers))
}

/** The sitting a manifest names, or undefined where it is gone. */
export function sittingOf(state: State, manifest: string): Sitting | undefined {
  return state.sittings.find((one) => one.manifest === manifest)
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
  // A member's own loop first, then any films it carries (§PW600).
  const films = members.flatMap((one) => [
    ...(one.motion ? [{ label: one.name, path: one.motion }] : []),
    ...(one.films ?? []),
  ])
  if (films.length) return { kind: 'films', films, sheet: laid.sheet }
  const pictures = members.filter((one) => one.new && !one.sound)
  if (pictures.length) return { kind: 'pictures', members: pictures, sheet: laid.sheet }
  return { kind: 'sheet', sheet: laid.sheet }
}

/** Whether a path is a loop to play rather than a picture to show (§PW600). */
export function moving(path: string): boolean {
  return /\.(mp4|webm)$/i.test(path)
}

/** A card's title: who says a line, else the family's name. */
export function title(name: string, laid: Laid): string {
  const speaking = (laid.members ?? []).find((one) => one.text)
  return speaking ? (speaking.who ?? speaking.speaker ?? name) : name
}

/** Why an answer cannot be sent yet, as a catalog key, or null when it can. An accept of
 * alternatives for one slot (`pick`) needs the one picked (§PW547). */
export function unready(choice: string | null, why: string, pick?: string | null): string | null {
  if (!choice) return 'need_choice'
  if (choice === 'accept' && pick === null) return 'need_pick'
  // A redo needs to say what is wrong; an accept may say nothing more.
  if (choice !== 'accept' && !why.trim()) return 'need_note'
  return null
}
