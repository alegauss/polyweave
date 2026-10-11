// The window's own decision screen (§PW400): the review page's sittings and cards drawn
// with the window's components, every word from the review catalog (`review.words`) and
// never a copy of it. It reads and writes through a `Desk`, so the same screen can run
// over the page's own routes in a browser; the window's desk is three bridge channels.

import { Button, Textarea } from '@viglet/viglet-design-system'
import { useEffect, useState } from 'react'

import {
  answered,
  choices,
  last,
  ordered,
  progress,
  say,
  status,
  title,
  unready,
  visual,
  type Desk,
  type Laid,
  type Member,
  type Sitting,
  type State,
  type Words,
} from '@pw/core'

/** An answer a smoke run gives on the screen, as a person would. */
export interface Scripted {
  family: string
  choice: string
  why: string
}

const BADGE = {
  wait: 'bg-amber-100 text-amber-900',
  accept: 'bg-emerald-100 text-emerald-900',
  look: 'bg-rose-100 text-rose-900',
  other: 'bg-sky-100 text-sky-900',
} as const

const when = (words: Words, at: string | undefined) => {
  const date = new Date(at ?? '')
  return Number.isNaN(date.getTime())
    ? (at ?? '')
    : date.toLocaleString(words.language, { dateStyle: 'medium', timeStyle: 'short' })
}

/** A project file, carried across the desk and shown as it is. */
function Shown({ desk, path, alt, sound }: { desk: Desk; path: string; alt: string; sound?: boolean }) {
  const [source, setSource] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    void desk.file(path).then(
      (one) => live && setSource(`data:${one.mime};base64,${one.base64}`),
      () => undefined,
    )
    return () => {
      live = false
    }
  }, [desk, path])
  if (!source) return <div className="h-24 w-full animate-pulse rounded bg-muted" />
  if (sound) return <audio controls src={source} className="w-full" />
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
}: {
  desk: Desk
  words: Words
  sitting: Sitting
  name: string
  state: State
  scripted?: Scripted
  onAnswered: () => void
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

  const send = async (choice: string | null, said: string) => {
    const missing = unready(choice, said)
    if (missing) return setMessage({ text: say(words, missing), bad: true })
    setSending(true)
    setMessage({ text: say(words, 'recording'), bad: false })
    try {
      await desk.answer({ sitting: sitting.manifest, family: name, choice: choice!, why: said.trim() })
      setMessage({ text: say(words, 'recorded'), bad: false })
      setAgain(false)
      setPicked(null)
      setWhy('')
      onAnswered()
    } catch (refused) {
      setMessage({ text: (refused as Error).message, bad: true })
    } finally {
      setSending(false)
    }
  }

  // A smoke run answers its family once, the way a person would: a choice, then words.
  useEffect(() => {
    if (scripted?.family === name && !before) void send(scripted.choice, scripted.why)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scripted, name])

  const answeredAs = before ? offered.find(([word]) => word === before.choice)?.[1] : undefined
  const sounds = (laid.members ?? []).filter((one) => one.sound && one.new)
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
        <Shown key={member.new} desk={desk} path={member.new!} alt={member.name} sound />
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
            void send(picked, why)
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
  onDrawn,
}: {
  desk: Desk
  /** An answer a smoke run gives here, once its card is drawn. */
  scripted?: Scripted
  /** Called after each read is drawn, with whether the scripted answer is in. */
  onDrawn?: (state: State) => void
}) {
  const [words, setWords] = useState<Words | null>(null)
  const [state, setState] = useState<State | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const read = () =>
    desk.state().then(setState, (refused: Error) => setFailed(refused.message))
  useEffect(() => {
    void desk.words().then(setWords, (refused: Error) => setFailed(refused.message))
    void read()
    // The files are read again every few seconds, as the page does, so an answer given
    // elsewhere, or the agent's next sitting, shows without asking.
    const every = setInterval(() => void read(), 5000)
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
  const shared = { desk, words, state, scripted, onAnswered: () => void read() }
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
    </div>
  )
}
