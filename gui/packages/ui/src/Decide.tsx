// The window's own decision screen (§PW400): the review page's sittings and cards drawn
// with the window's components, every word from the review catalog (`review.words`) and
// never a copy of it. It reads and writes through a `Desk`, so the same screen can run
// over the page's own routes in a browser; the window's desk is three bridge channels.

import { Button, Textarea } from '@viglet/viglet-design-system'
import { useCallback, useEffect, useRef, useState } from 'react'

import {
  answered,
  choices,
  drawn,
  inPixels,
  last,
  measuredOf,
  ordered,
  progress,
  say,
  spanned,
  status,
  title,
  unready,
  visual,
  type Board,
  type Box,
  type Desk,
  type Difference,
  type Laid,
  type Mark,
  type Member,
  type Sitting,
  type State,
  type Words,
} from '@pw/core'

import { Advanced, type Promoted } from './Advanced'

/** An answer a smoke run gives on the screen, as a person would. */
export interface Scripted {
  family: string
  choice: string
  why: string
  marks?: Mark[]
}

/** Where a file will show once it has come across the desk. */
export const Loading = () => <div data-loading className="h-24 w-48 animate-pulse rounded bg-muted" />

/** A project file as a data URL, read once across the desk. */
export function useShown(desk: Desk, path: string | null): string | null {
  const [source, setSource] = useState<string | null>(null)
  useEffect(() => {
    if (!path) return
    let live = true
    void desk.file(path).then(
      (one) => live && setSource(`data:${one.mime};base64,${one.base64}`),
      () => undefined,
    )
    return () => {
      live = false
    }
  }, [desk, path])
  return source
}

/**
 * Where it is wrong, drawn over the member's own picture (§PW174). A drag draws a box in
 * the picture's own pixels, whatever size it is shown at; `review.answer` turns the boxes
 * into a mask the picture's size and keeps it with the answer.
 */
function Marker({
  desk,
  words,
  member,
  boxes,
  onBoxes,
}: {
  desk: Desk
  words: Words
  member: Member
  boxes: Box[]
  onBoxes: (boxes: Box[]) => void
}) {
  const source = useShown(desk, member.new ?? null)
  const picture = useRef<HTMLImageElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const [start, setStart] = useState<[number, number] | null>(null)
  const [moving, setMoving] = useState<Box | null>(null)
  const at = (event: React.PointerEvent): [number, number] => {
    const frame = canvas.current!.getBoundingClientRect()
    const shown = picture.current!
    return inPixels(event.clientX - frame.left, event.clientY - frame.top, shown.naturalWidth, shown.clientWidth)
  }
  const paint = () => {
    const shown = picture.current
    const pen = canvas.current?.getContext('2d')
    if (!shown || !pen || !canvas.current) return
    canvas.current.width = shown.clientWidth
    canvas.current.height = shown.clientHeight
    const k = shown.naturalWidth / (shown.clientWidth || 1)
    pen.strokeStyle = '#ff3b30'
    pen.lineWidth = 2
    for (const box of moving ? [...boxes, moving] : boxes) {
      pen.strokeRect(box[0] / k, box[1] / k, (box[2] - box[0]) / k, (box[3] - box[1]) / k)
    }
  }
  useEffect(paint)
  const alt = say(words, 'mark_alt', { name: member.name })
  return (
    <div data-marker={member.name} className="flex flex-col gap-2">
      <p className="text-xs text-muted-foreground">{say(words, 'mark_help')}</p>
      <div className="relative inline-block self-start">
        {!source && <Loading />}
        {source && (
          <img
            ref={picture}
            src={source}
            alt={alt}
            onLoad={paint}
            className="block max-h-96 w-auto min-w-48 [image-rendering:pixelated]"
          />
        )}
        <canvas
          ref={canvas}
          aria-label={alt}
          className="absolute inset-0 h-full w-full cursor-crosshair touch-none"
          onPointerDown={(event) => setStart(at(event))}
          onPointerMove={(event) => start && setMoving([...start, ...at(event)] as Box)}
          onPointerUp={(event) => {
            if (!start) return
            const box = spanned(start, at(event))
            if (box) onBoxes([...boxes, box])
            setStart(null)
            setMoving(null)
          }}
        />
      </div>
      <Button type="button" size="sm" variant="outline" className="self-start" onClick={() => onBoxes([])}>
        {say(words, 'clear_marks')}
      </Button>
    </div>
  )
}

const MODES = ['side', 'slider', 'onion', 'difference'] as const
type Mode = (typeof MODES)[number]

/** Two versions in one place (§PW176): side by side, a slider, an onion skin, and a
 * difference map lit only above the noise floor. */
export function Compare({
  desk,
  words,
  old,
  now,
  start = 'slider',
  mask = null,
}: {
  desk: Desk
  words: Words
  old: string
  now: string
  /** The mode that suits what is compared; the person can switch. */
  start?: string
  /** Where an edit was allowed, shown over the slider (§PW174). */
  mask?: string | null
}) {
  const [mode, setMode] = useState<Mode>((MODES as readonly string[]).includes(start) ? (start as Mode) : 'side')
  const masked = useShown(desk, mask)
  const [at, setAt] = useState(50)
  const [difference, setDifference] = useState<Difference | string | null>(null)
  const before = useShown(desk, old)
  const after = useShown(desk, now)
  const map = useShown(desk, typeof difference === 'object' && difference ? difference.map : null)
  useEffect(() => {
    if (mode !== 'difference' || difference) return
    void desk.compare(old, now).then(setDifference, (refused: Error) => setDifference(refused.message))
  }, [desk, mode, old, now, difference])
  // Shown as large as the marker draws it, so a small sprite is still seen pixel by pixel.
  const image = 'block max-h-96 w-auto min-w-48 [image-rendering:pixelated]'
  const layered = (top: React.CSSProperties) => (
    <div className="flex flex-col gap-2 self-start">
      <div className="relative">
        {!(before && after) && <Loading />}
        {before && <img src={before} alt={say(words, 'before')} className={image} />}
        {after && (
          <img
            src={after}
            alt={say(words, 'after')}
            className="absolute inset-0 h-full w-full [image-rendering:pixelated]"
            style={top}
          />
        )}
        {masked && 'clipPath' in top && (
          <img src={masked} alt="" className="absolute inset-0 h-full w-full opacity-40 mix-blend-multiply" />
        )}
      </div>
      <input
        className="w-full"
        type="range"
        min={0}
        max={100}
        value={at}
        aria-label={say(words, `mode_${mode}`)}
        onChange={(event) => setAt(Number(event.target.value))}
      />
    </div>
  )
  return (
    <div data-compare className="flex flex-col gap-2">
      <div role="tablist" className="flex flex-wrap gap-1">
        {MODES.map((one) => (
          <Button
            key={one}
            type="button"
            role="tab"
            size="sm"
            data-mode={one}
            aria-selected={mode === one}
            variant={mode === one ? 'default' : 'outline'}
            onClick={() => setMode(one)}
          >
            {say(words, `mode_${one}`)}
          </Button>
        ))}
      </div>
      {mode === 'side' && (
        <div className="flex flex-wrap gap-3">
          {before && <img src={before} alt={say(words, 'before')} className={image} />}
          {after && <img src={after} alt={say(words, 'after')} className={image} />}
        </div>
      )}
      {mode === 'slider' && layered({ clipPath: `inset(0 ${100 - at}% 0 0)` })}
      {mode === 'onion' && layered({ opacity: at / 100 })}
      {mode === 'difference' &&
        (difference === null ? (
          <p className="text-sm text-muted-foreground">{say(words, 'measuring_difference')}</p>
        ) : typeof difference === 'string' ? (
          <p className="text-sm text-rose-700">{difference || say(words, 'no_map')}</p>
        ) : (
          <div className="flex flex-col gap-1">
            {map && <img src={map} alt={say(words, 'mode_difference')} className={image} />}
            <p className="text-sm">
              {say(words, 'difference_says', {
                changed: difference.changed_patches,
                patches: difference.patches,
                tolerance: difference.tolerance,
                from: difference.tolerance_from ?? '',
              })}
            </p>
          </div>
        ))}
    </div>
  )
}

/** A sound beside the one it replaces (§PW256), each on its own player, a loop looped so
 * its seam is heard, with what was measured of it. */
function Listen({ desk, words, member }: { desk: Desk; words: Words; member: Member }) {
  const old = useShown(desk, member.old ?? null)
  const now = useShown(desk, member.new ?? null)
  return (
    <div data-listen={member.name} className="grid gap-3 sm:grid-cols-2">
      {(['old', 'new'] as const)
        .filter((version) => member[version])
        .map((version) => (
          <div key={version} className="flex flex-col gap-1">
            <strong className="text-sm">{say(words, version === 'old' ? 'before' : 'after')}</strong>
            {(version === 'old' ? old : now) && (
              <audio
                controls
                preload="auto"
                loop={Boolean(member.loop)}
                src={(version === 'old' ? old : now)!}
                aria-label={say(words, version === 'old' ? 'before' : 'after')}
                className="w-full"
              />
            )}
            <p className="text-xs text-muted-foreground">{measuredOf(member, version)}</p>
          </div>
        ))}
    </div>
  )
}

const BADGE = {
  wait: 'bg-amber-100 text-amber-900',
  accept: 'bg-emerald-100 text-emerald-900',
  look: 'bg-rose-100 text-rose-900',
  other: 'bg-sky-100 text-sky-900',
} as const

export const when = (words: Words, at: string | undefined) => {
  const date = new Date(at ?? '')
  return Number.isNaN(date.getTime())
    ? (at ?? '')
    : date.toLocaleString(words.language, { dateStyle: 'medium', timeStyle: 'short' })
}

/** A project file, carried across the desk and shown as it is. */
export function Shown({ desk, path, alt }: { desk: Desk; path: string; alt: string }) {
  const source = useShown(desk, path)
  if (!source) return <Loading />
  return <img src={source} alt={alt} className="max-h-80 w-auto rounded border object-contain [image-rendering:pixelated]" />
}

function Visual({ desk, words, name, laid }: { desk: Desk; words: Words; name: string; laid: Laid }) {
  const shown = visual(laid)
  const sheet = (label: string, path: string) => (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">{label}</summary>
      <Shown desk={desk} path={path} alt={name} />
    </details>
  )
  if (shown.kind === 'line') {
    return (
      <>
        {shown.lines.map((member: Member) => (
          <div key={member.name} className="flex flex-col gap-1">
            <p className="text-sm text-muted-foreground">
              {say(words, 'says', { who: member.who ?? member.speaker ?? '' })}
            </p>
            {Object.entries(member.text ?? {}).map(([locale, text]) => (
              <blockquote key={locale} lang={locale} className="border-l-4 pl-3 text-xl">
                {text}
              </blockquote>
            ))}
            <p className="font-mono text-xs text-muted-foreground">{member.line}</p>
          </div>
        ))}
      </>
    )
  }
  if (shown.kind === 'films') {
    return (
      <>
        <div className="flex flex-wrap gap-3">
          {shown.films.map((film) => (
            <figure key={film.path} className="flex flex-col gap-1">
              <figcaption className="text-xs text-muted-foreground">{film.label}</figcaption>
              <Shown desk={desk} path={film.path} alt={film.label} />
            </figure>
          ))}
        </div>
        {sheet(say(words, 'frames'), shown.sheet)}
      </>
    )
  }
  if (shown.kind === 'pictures') {
    return (
      <>
        <div className="flex flex-wrap gap-3">
          {shown.members.flatMap((member) =>
            (member.old
              ? [
                  [say(words, 'before'), member.old],
                  [say(words, 'after'), member.new!],
                ]
              : [[member.name, member.new!]]
            ).map(([label, path]) => (
              <figure key={`${member.name}:${path}`} className="flex flex-col gap-1">
                <figcaption className="text-xs text-muted-foreground">{label}</figcaption>
                <Shown desk={desk} path={path!} alt={label!} />
              </figure>
            )),
          )}
        </div>
        {sheet(say(words, 'sheet'), shown.sheet)}
      </>
    )
  }
  return <Shown desk={desk} path={shown.sheet} alt={name} />
}

/** One family as a card: what it is, what to look at, and the decision. */
function Card({
  desk,
  words,
  sitting,
  name,
  state,
  scripted,
  onAnswered,
  onHold,
}: {
  desk: Desk
  words: Words
  sitting: Sitting
  name: string
  state: State
  scripted?: Scripted
  onAnswered: () => void
  /** Says whether a decision is being made here, which no redraw may run over. */
  onHold: (card: string, held: boolean) => void
}) {
  const laid = sitting.families[name]!
  const before = last(sitting, name, state.answers)
  const badge = status(before)
  const offered = choices(words, sitting, laid)
  const [picked, setPicked] = useState<string | null>(null)
  const [why, setWhy] = useState('')
  const [again, setAgain] = useState(false)
  const [message, setMessage] = useState<{ text: string; bad: boolean } | null>(null)
  const [sending, setSending] = useState(false)
  // Boxes drawn on each member's picture, sent with the answer as its marks (§PW174).
  const [boxes, setBoxes] = useState<Record<string, Box[]>>({})
  const marked = Object.values(boxes).some((one) => one.length > 0)
  const card = `${sitting.manifest}#${name}`
  useEffect(() => {
    onHold(card, Boolean(picked || why.trim() || marked))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [card, picked, why, marked])
  useEffect(() => () => onHold(card, false), [card, onHold])

  const send = async (choice: string | null, said: string, marks: Mark[]) => {
    const missing = unready(choice, said)
    if (missing) return setMessage({ text: say(words, missing), bad: true })
    setSending(true)
    setMessage({ text: say(words, 'recording'), bad: false })
    try {
      await desk.answer({
        sitting: sitting.manifest,
        family: name,
        choice: choice!,
        why: said.trim(),
        marks: drawn(marks),
      })
      setMessage({ text: say(words, 'recorded'), bad: false })
      setAgain(false)
      setPicked(null)
      setWhy('')
      setBoxes({})
      onAnswered()
    } catch (refused) {
      setMessage({ text: (refused as Error).message, bad: true })
    } finally {
      setSending(false)
    }
  }

  // A smoke run answers its family once, the way a person would: a choice, then words.
  useEffect(() => {
    if (scripted?.family === name && !before) void send(scripted.choice, scripted.why, scripted.marks ?? [])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scripted, name])

  const answeredAs = before ? offered.find(([word]) => word === before.choice)?.[1] : undefined
  const sounds = (laid.members ?? []).filter((one) => one.sound && one.new)
  // Marks are drawn on a picture, so a sound or a line has none to draw on.
  const drawable = (laid.members ?? []).filter((one) => one.new && !one.sound && !one.text)
  const marks = (): Mark[] =>
    Object.entries(boxes).map(([member, shapes]) => ({ member, shapes: shapes.map((box) => ({ box })) }))
  return (
    <article data-card={`${sitting.manifest}#${name}`} className="flex flex-col gap-3 rounded-lg border p-4">
      <header className="flex items-center gap-3">
        <h3 className="flex-1 truncate text-lg font-medium">{title(name, laid)}</h3>
        <span data-badge={badge} className={`rounded-full px-2 py-0.5 text-xs ${BADGE[badge]}`}>
          {say(words, `status_${badge}`)}
        </span>
      </header>
      {laid.about && <p className="text-sm">{laid.about}</p>}
      <Visual desk={desk} words={words} name={name} laid={laid} />
      {sounds.map((member) => (
        <Listen key={member.name} desk={desk} words={words} member={member} />
      ))}
      {before && (
        <div data-answered className="flex flex-col gap-1 rounded-md bg-muted p-3 text-sm">
          <p>{say(words, 'answered', { choice: answeredAs?.label ?? before.choice, at: when(words, before.at) })}</p>
          <q>{before.why || say(words, 'no_comment')}</q>
          {!again && (
            <Button size="sm" variant="link" className="self-start px-0" onClick={() => setAgain(true)}>
              {say(words, 'answer_again')}
            </Button>
          )}
        </div>
      )}
      {(!before || again) && (
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            void send(picked, why, marks())
          }}
        >
          <p className="text-sm font-medium">{say(words, 'question')}</p>
          <div role="group" aria-label={say(words, 'question')} className="grid gap-2 sm:grid-cols-2">
            {offered.map(([word, choice]) => (
              <Button
                key={word}
                type="button"
                data-choice={word}
                variant={picked === word ? 'default' : 'outline'}
                aria-pressed={picked === word}
                onClick={() => setPicked(word)}
                className="h-auto flex-col items-start gap-0.5 whitespace-normal py-2 text-left"
              >
                <b>{choice.label}</b>
                <small>{choice.means}</small>
                {choice.then && <small>→ {choice.then}</small>}
              </Button>
            ))}
          </div>
          {picked && (
            <label className="flex flex-col gap-1 text-sm">
              {say(words, picked === 'accept' ? 'note_accept' : 'note_look')}
              <Textarea
                value={why}
                onChange={(event) => setWhy(event.target.value)}
                placeholder={say(
                  words,
                  picked === 'accept' ? 'placeholder_accept' : picked === 'look' ? 'placeholder_look' : 'placeholder_other',
                )}
              />
            </label>
          )}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={sending}>
              {say(words, 'record')}
            </Button>
            {message && (
              <span aria-live="polite" className={`text-sm ${message.bad ? 'text-rose-700' : 'text-muted-foreground'}`}>
                {message.text}
              </span>
            )}
          </div>
        </form>
      )}
      {drawable.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">{say(words, 'mark')}</summary>
          <div className="flex flex-col gap-4 pt-2">
            {drawable.map((member) => (
              <div key={member.name} className="flex flex-col gap-3">
                {member.old && <Compare desk={desk} words={words} old={member.old} now={member.new!} />}
                <Marker
                  desk={desk}
                  words={words}
                  member={member}
                  boxes={boxes[member.name] ?? []}
                  onBoxes={(next) => setBoxes((all) => ({ ...all, [member.name]: next }))}
                />
              </div>
            ))}
          </div>
        </details>
      )}
      {(laid.said ?? []).length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">{say(words, 'details')}</summary>
          {laid.said!.map((held) => (
            <p key={held.name}>
              <strong>{held.name}: </strong>
              {held.passed === null || held.passed === undefined
                ? say(words, 'unheld')
                : say(words, held.passed ? 'passes' : 'fails')}
              {(held.failed ?? []).map((failed) => (
                <span key={failed} className="block">
                  {failed}
                </span>
              ))}
            </p>
          ))}
        </details>
      )}
    </article>
  )
}

/** A sitting: its title and what it is for, how to decide, then a card per family. */
function SittingView(props: {
  desk: Desk
  words: Words
  sitting: Sitting
  state: State
  scripted?: Scripted
  onAnswered: () => void
  onHold: (card: string, held: boolean) => void
}) {
  const { words, sitting, state } = props
  const kind = words.kinds[sitting.kind ?? 'look'] ?? {}
  const total = Object.keys(sitting.families).length
  return (
    <section data-sitting={sitting.manifest} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold">{sitting.title ?? kind.title ?? say(words, 'heading')}</h2>
        <p className="text-sm text-muted-foreground">
          {say(words, total === 1 ? 'sitting_count_one' : 'sitting_count', {
            total,
            done: answered(sitting, state.answers),
          })}
          {' · '}
          {say(words, 'laid_out', { at: when(words, sitting.at) })}
        </p>
        {(sitting.about ?? kind.about) && <p className="text-sm">{sitting.about ?? kind.about}</p>}
        <p className="text-sm font-medium">{say(words, 'how')}</p>
        <ul data-how className="list-disc pl-5 text-sm">
          {choices(words, sitting).map(([word, choice]) => (
            <li key={word}>
              <strong>{choice.label}: </strong>
              {choice.means}
              {choice.then ? ` ${choice.then}` : ''}
            </li>
          ))}
        </ul>
        {(sitting.tone ?? []).length > 0 && (
          <details open className="text-sm">
            <summary className="cursor-pointer">{say(words, 'tone')}</summary>
            <ul className="list-disc pl-5">
              {sitting.tone!.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
      {Object.keys(sitting.families).map((name) => (
        <Card key={name} {...props} name={name} />
      ))}
    </section>
  )
}

export function Decide({
  desk,
  scripted,
  promote,
  canon,
  onDrawn,
  onBoards,
}: {
  desk: Desk
  /** An answer a smoke run gives here, once its card is drawn. */
  scripted?: Scripted
  /** A gate's refused picture a smoke run promotes (§PW402). */
  promote?: Promoted
  /** Load the canon boards at once, as a smoke run asks. */
  canon?: boolean
  /** Called after each read is drawn, with whether the scripted answer is in. */
  onDrawn?: (state: State) => void
  onBoards?: (boards: Board[]) => void
}) {
  const [words, setWords] = useState<Words | null>(null)
  const [state, setState] = useState<State | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const read = () =>
    desk.state().then(setState, (refused: Error) => setFailed(refused.message))
  // The cards where a decision is being made: a choice picked, a word typed, a box drawn.
  const holding = useRef(new Set<string>())
  const onHold = useCallback((card: string, held: boolean) => {
    if (held) holding.current.add(card)
    else holding.current.delete(card)
  }, [])
  useEffect(() => {
    void desk.words().then(setWords, (refused: Error) => setFailed(refused.message))
    void read()
    // The files are read again every few seconds, as the page does, so an answer given
    // elsewhere, or the agent's next sitting, shows without asking; never over a
    // decision being made.
    const every = setInterval(() => {
      if (holding.current.size === 0) void read()
    }, 5000)
    return () => clearInterval(every)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desk])
  useEffect(() => {
    if (state && words) onDrawn?.(state)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, words])

  if (failed) return <p className="text-rose-700">{failed}</p>
  if (!words || !state) return <div className="h-40 w-full animate-pulse rounded bg-muted" />
  const { open, done } = ordered(state)
  const along = progress(state)
  const shared = { desk, words, state, scripted, onAnswered: () => void read(), onHold }
  return (
    <div data-decide lang={words.language} className="flex flex-col gap-6">
      {along && (
        <div className="flex flex-col gap-1">
          <div className="h-2 w-full overflow-hidden rounded bg-muted">
            <div className="h-full bg-primary" style={{ width: `${(100 * along.done) / (along.total || 1)}%` }} />
          </div>
          <p data-progress className="text-sm text-muted-foreground">
            {say(words, 'progress', along)}
          </p>
        </div>
      )}
      {open.length === 0 && <p className="text-muted-foreground">{say(words, 'empty')}</p>}
      {open.map((sitting) => (
        <SittingView key={sitting.manifest} {...shared} sitting={sitting} />
      ))}
      {done.length > 0 && (
        <details className="flex flex-col gap-4">
          <summary className="cursor-pointer text-sm">{say(words, 'older', { n: done.length })}</summary>
          {done.map((sitting) => (
            <SittingView key={sitting.manifest} {...shared} sitting={sitting} />
          ))}
        </details>
      )}
      <Advanced
        desk={desk}
        words={words}
        state={state}
        promote={promote}
        canon={canon}
        onWritten={() => void read()}
        onBoards={onBoards}
      />
    </div>
  )
}
