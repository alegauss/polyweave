// What the review page keeps under "Advanced", drawn natively (§PW402): each gate run's
// kept and refused lanes with a door to promote a refused picture or take one into a
// canon, each mesh's turntable against the one before, every canon board with its
// floors and a door to withdraw a picture or admit a candidate, and where every asset
// stands. Every write is `review.answer`'s gate, admit or withdraw body, as the page's.

import { Button, Textarea } from '@viglet/viglet-design-system'
import { useState } from 'react'

import {
  figures,
  lanes,
  narrower,
  say,
  turned,
  type Board,
  type Candidate,
  type Desk,
  type Gate,
  type Overrule,
  type State,
  type Turntable,
  type Words,
} from '@pw/core'

import { Compare, Shown, when } from './Decide'

/** One sentence and one button, as the canon and the gates use. */
function Sentence({
  words,
  placeholder,
  label,
  done,
  send,
}: {
  words: Words
  placeholder: string
  label: string
  done: string
  send: (why: string) => Promise<unknown>
}) {
  const [why, setWhy] = useState('')
  const [said, setSaid] = useState<{ text: string; bad: boolean } | null>(null)
  const [sent, setSent] = useState(false)
  const submit = async (text: string) => {
    if (!text.trim()) return setSaid({ text: say(words, 'write_first'), bad: true })
    setSent(true)
    try {
      await send(text)
      setSaid({ text: done, bad: false })
      setWhy('')
    } catch (refused) {
      setSent(false)
      setSaid({ text: (refused as Error).message, bad: true })
    }
  }
  return (
    <form
      className="flex flex-col gap-1"
      onSubmit={(event) => {
        event.preventDefault()
        void submit(why)
      }}
    >
      <Textarea value={why} placeholder={placeholder} aria-label={placeholder} onChange={(e) => setWhy(e.target.value)} />
      <div className="flex items-center gap-2">
        <Button type="submit" size="sm" disabled={sent}>
          {label}
        </Button>
        {said && (
          <span aria-live="polite" className={`text-xs ${said.bad ? 'text-rose-700' : 'text-muted-foreground'}`}>
            {said.text}
          </span>
        )}
      </div>
    </form>
  )
}

function CandidateView({
  desk,
  words,
  run,
  one,
  onWritten,
}: {
  desk: Desk
  words: Words
  run: Gate
  one: Candidate
  onWritten: () => void
}) {
  const write = (body: Overrule) => desk.answer(body).then(onWritten)
  return (
    <div data-candidate={one.picture} className="flex flex-col gap-2 rounded-md border p-3">
      <Shown desk={desk} path={one.picture} alt={one.picture} />
      <ul className="text-xs">
        {figures(words, one).map((line, at) => (
          <li key={at} className={at > 0 && at <= one.failed.length ? 'text-rose-700' : ''}>
            {line}
          </li>
        ))}
      </ul>
      {one.compare && (
        <Compare
          desk={desk}
          words={words}
          old={one.compare.old}
          now={one.picture}
          start={one.compare.mode}
          mask={one.compare.mask}
        />
      )}
      <Sentence
        words={words}
        placeholder={say(words, 'why_canon')}
        label={say(words, 'add_to_canon')}
        done={say(words, 'added')}
        send={(why) => write({ gate: run.id, picture: one.picture, choice: 'accept', why, canon: run.family || 'default' })}
      />
      {!one.passed && (
        <Sentence
          words={words}
          placeholder={say(words, 'why_promote')}
          label={say(words, 'promote')}
          done={say(words, 'promoted')}
          send={(why) => write({ gate: run.id, picture: one.picture, choice: 'accept', why })}
        />
      )}
    </div>
  )
}

/** The refused beside the kept (§PW175). */
function GateRun(props: { desk: Desk; words: Words; run: Gate; onWritten: () => void }) {
  const { words, run } = props
  const { kept, refused } = lanes(run)
  return (
    <article data-gate={run.id} className="flex flex-col gap-3 rounded-lg border p-4">
      <h3 className="text-lg font-medium">
        {say(words, 'gate_of', { at: when(words, run.at) })}
        {run.family ? ` (${run.family})` : ''}
      </h3>
      <p className="text-sm">{say(words, 'chosen', { chosen: run.chosen || say(words, 'none'), why: run.why ?? '' })}</p>
      <section data-lane="kept" className="flex flex-col gap-2">
        <h4 className="font-medium">{say(words, 'kept', { n: kept.length })}</h4>
        <div className="grid gap-3 md:grid-cols-2">
          {kept.map((one) => (
            <CandidateView key={one.picture} {...props} one={one} />
          ))}
        </div>
      </section>
      <details data-lane="refused">
        <summary className="cursor-pointer font-medium">{say(words, 'refused', { n: refused.length })}</summary>
        <div className="grid gap-3 pt-2 md:grid-cols-2">
          {refused.map((one) => (
            <CandidateView key={one.picture} {...props} one={one} />
          ))}
        </div>
      </details>
    </article>
  )
}

/** A mesh turned at the rig's own camera, never a viewer's (§PW176). */
function Mesh({ desk, words, asset, turns }: { desk: Desk; words: Words; asset: string; turns: Turntable[] }) {
  const newest = turns[turns.length - 1]!
  const before = turns.length > 1 ? turns[turns.length - 2]! : null
  const [at, setAt] = useState(0)
  const frame = newest.frames[at]
  const earlier = before?.frames[at]
  return (
    <article data-turntable={asset} className="flex flex-col gap-2 rounded-lg border p-4">
      <h3 className="text-lg font-medium">{say(words, 'turned', { asset })}</h3>
      <input
        type="range"
        min={0}
        max={Math.max(0, newest.frames.length - 1)}
        value={at}
        aria-label={say(words, 'which_frame')}
        onChange={(event) => setAt(Number(event.target.value))}
      />
      {frame && (
        <p className="text-sm">
          {say(words, 'azimuth', { azimuth: frame.azimuth, elevation: newest.elevation ?? 0 })}
          {before
            ? say(words, 'turned_against', { before: before.at ?? '', newest: newest.at ?? '' })
            : say(words, 'one_turntable')}
        </p>
      )}
      {frame &&
        (earlier ? (
          <Compare key={at} desk={desk} words={words} old={earlier.picture} now={frame.picture} />
        ) : (
          <Shown key={at} desk={desk} path={frame.picture} alt={`${asset} ${frame.azimuth}°`} />
        ))}
      {newest.against && newest.front && (
        <>
          <h4 className="font-medium">{say(words, 'front_against')}</h4>
          <Compare desk={desk} words={words} old={newest.against} now={newest.front} start="onion" />
        </>
      )}
    </article>
  )
}

/** One family's canon on a board (§PW177). */
function CanonBoard({ desk, words, board, onWritten }: { desk: Desk; words: Words; board: Board; onWritten: () => void }) {
  const write = (body: Overrule) => desk.answer(body).then(onWritten)
  const floors = Object.entries(board.floors)
    .map(([measure, value]) => `${measure} ${value === null ? say(words, 'floor_none') : value}`)
    .join(', ')
  return (
    <article data-board={board.family} className="flex flex-col gap-3 rounded-lg border p-4">
      <h3 className="text-lg font-medium">{say(words, 'canon_of', { family: board.family })}</h3>
      <div className="flex flex-wrap gap-2">
        {board.palette.map((colour) => (
          <span key={colour} title={colour} className="flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-xs">
            <span className="inline-block h-3 w-3 rounded-sm border" style={{ background: colour }} />
            {colour}
          </span>
        ))}
      </div>
      <p className="text-sm">{say(words, 'floors', { floors })}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {board.pictures.map((one) => {
          const narrows = narrower(board, one.picture)
          return (
            <div key={one.picture} data-canon-picture={one.picture} className="flex flex-col gap-2 rounded-md border p-3">
              <Shown desk={desk} path={one.path} alt={one.picture} />
              <ul className="text-xs">
                <li>
                  {one.picture}: {one.verdict.choice}, {one.verdict.when}, “{one.verdict.why}”
                </li>
                <li>{narrows.length ? say(words, 'narrow', { which: narrows.join(', ') }) : say(words, 'no_narrow')}</li>
              </ul>
              <Sentence
                words={words}
                placeholder={say(words, 'why_withdraw')}
                label={say(words, 'withdraw')}
                done={say(words, 'withdrawn')}
                send={(why) => write({ canon: board.family, withdraw: one.picture, why })}
              />
            </div>
          )
        })}
      </div>
      {board.says && <p className="text-sm text-muted-foreground">{board.says}</p>}
      {(board.candidates ?? []).length > 0 && (
        <>
          <h4 className="font-medium">{say(words, 'candidates')}</h4>
          <div className="grid gap-3 md:grid-cols-2">
            {board.candidates!.map((offer) => (
              <div key={offer.path} className="flex flex-col gap-2 rounded-md border p-3">
                <Shown desk={desk} path={offer.path} alt={offer.path} />
                <p className="font-mono text-xs">{offer.path}</p>
                <Sentence
                  words={words}
                  placeholder={say(words, 'why_canon')}
                  label={say(words, 'add_to_canon')}
                  done={say(words, 'added')}
                  send={(why) => write({ canon: board.family, admit: offer.path, why })}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </article>
  )
}

export function Advanced({
  desk,
  words,
  state,
  onWritten,
}: {
  desk: Desk
  words: Words
  state: State
  onWritten: () => void
}) {
  // The canon is loaded only when asked: it measures every picture on every board.
  const [boards, setBoards] = useState<Board[] | string | null>(null)
  const [loading, setLoading] = useState(false)
  const load = () => {
    setLoading(true)
    void desk.canon().then(setBoards, (refused: Error) => setBoards(refused.message))
  }
  const gates = (state.gates ?? []).slice().reverse()
  const meshes = turned(state.turntables ?? [])
  return (
    <details data-advanced className="flex flex-col gap-4">
      <summary className="cursor-pointer text-sm font-medium">{say(words, 'advanced')}</summary>
      <div className="flex flex-col gap-4 pt-2">
        {state.codes?.page && (
          <p data-code className="text-sm text-muted-foreground">
            {say(words, 'lanes_code', { code: state.codes.page })}
          </p>
        )}
        {gates.map((run) => (
          <GateRun key={run.id} desk={desk} words={words} run={run} onWritten={onWritten} />
        ))}
        {meshes.map(([asset, turns]) => (
          <Mesh key={asset} desk={desk} words={words} asset={asset} turns={turns} />
        ))}
        <h3 className="text-lg font-medium">{say(words, 'canons_title')}</h3>
        {boards === null ? (
          <Button type="button" size="sm" variant="outline" className="self-start" disabled={loading} onClick={load}>
            {loading ? say(words, 'measuring_canons') : say(words, 'show_canons')}
          </Button>
        ) : typeof boards === 'string' ? (
          <p className="text-sm text-rose-700">{boards}</p>
        ) : (
          boards.map((board) => (
            <CanonBoard key={board.family} desk={desk} words={words} board={board} onWritten={onWritten} />
          ))
        )}
        <h3 className="text-lg font-medium">{say(words, 'pending_title')}</h3>
        <table data-pending className="w-full text-left text-sm">
          <thead>
            <tr>
              <th>{say(words, 'th_asset')}</th>
              <th>{say(words, 'th_waiting')}</th>
              <th>{say(words, 'th_candidate')}</th>
              <th>{say(words, 'th_judged')}</th>
            </tr>
          </thead>
          <tbody>
            {state.pending.assets.map((asset) => (
              <tr key={asset.asset} className="border-t">
                <td className="font-mono">{asset.asset}</td>
                <td>{say(words, asset.waiting ? 'yes' : 'no')}</td>
                <td>{asset.candidate ?? ''}</td>
                <td>{asset.judged ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
