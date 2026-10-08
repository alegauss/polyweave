// A Claude Code session on one item, as a conversation beside it (§PW306). Every raw line
// stays readable; a permission the session asks for is answered here; the person can keep
// talking to it, or stop it.

import { Button, Textarea } from '@viglet/viglet-design-system'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { said, type Bridge, type Said } from '@pw/core'

interface Heard {
  line: string
  read: Said
}

export function Conversation({
  bridge,
  revision,
  first,
  onResult,
  onCheck,
}: {
  bridge: Bridge
  revision: string
  first: string
  onResult?: () => void
  /** Called on each check the window ran after a change, to show old beside new. */
  onCheck?: () => void
}) {
  const { t } = useTranslation()
  const [heard, setHeard] = useState<Heard[]>([])
  const [answered, setAnswered] = useState<string[]>([])
  const [more, setMore] = useState('')
  const [raw, setRaw] = useState(false)

  useEffect(
    () =>
      bridge.onSessionLine((which, line) => {
        if (which !== revision) return
        const read = said(line)
        setHeard((before) => [...before, { line, read }])
        // Where the session now waits on the person: a question, or the end of a turn.
        if (read.kind === 'result' || read.kind === 'ask') onResult?.()
        if (read.kind === 'check') onCheck?.()
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bridge, revision],
  )

  const asks = heard.filter((h) => h.read.kind === 'ask') as { read: Extract<Said, { kind: 'ask' }> }[]
  const withdrawn = new Set(
    heard.flatMap((h) => (h.read.kind === 'withdrawn' ? [h.read.requestId] : [])),
  )
  const open = asks.filter((a) => !answered.includes(a.read.requestId) && !withdrawn.has(a.read.requestId))
  // A paid call's price, matched to the question it holds up (§PW308).
  const quotes = new Map(
    heard.flatMap((h) => (h.read.kind === 'quote' ? [[h.read.requestId, h.read] as const] : [])),
  )

  const answer = (requestId: string, allow: boolean) => {
    setAnswered((before) => [...before, requestId])
    void bridge.answer(revision, requestId, allow)
  }

  return (
    <section data-conversation className="flex flex-col gap-2 rounded-md border p-3">
      <div className="flex items-center gap-2">
        <h3 className="flex-1 font-medium">{t('session.heading')}</h3>
        <Button size="sm" variant="ghost" onClick={() => setRaw(!raw)}>
          {t(raw ? 'session.read' : 'session.raw')}
        </Button>
        <Button size="sm" variant="outline" onClick={() => void bridge.stop(revision)}>
          {t('session.stop')}
        </Button>
      </div>
      <details className="text-xs text-muted-foreground">
        <summary>{t('session.first')}</summary>
        <pre className="whitespace-pre-wrap">{first}</pre>
      </details>
      <ol className="flex max-h-96 flex-col gap-1 overflow-auto text-sm">
        {heard.map((h, index) =>
          raw ? (
            <li key={index} className="font-mono text-xs break-all">
              {h.line}
            </li>
          ) : (
            <Turn key={index} read={h.read} />
          ),
        )}
      </ol>
      {open.map(({ read }) => (
        <div key={read.requestId} data-ask={read.tool} className="flex flex-wrap items-center gap-2 rounded bg-muted p-2 text-sm">
          <span className="flex-1">{t('session.asks', { tool: read.tool })}</span>
          {read.why && <p data-why className="w-full text-amber-700">{read.why}</p>}
          {quotes.has(read.requestId) && <Price quote={quotes.get(read.requestId)!} />}
          <Button size="sm" onClick={() => answer(read.requestId, true)}>
            {t('session.allow')}
          </Button>
          <Button size="sm" variant="outline" onClick={() => answer(read.requestId, false)}>
            {t('session.deny')}
          </Button>
        </div>
      ))}
      <div className="flex gap-2">
        <Textarea
          value={more}
          placeholder={t('session.more')}
          onChange={(e) => setMore(e.target.value)}
          className="min-h-10 flex-1"
        />
        <Button
          disabled={!more.trim()}
          onClick={() => {
            void bridge.say(revision, more.trim())
            setMore('')
          }}
        >
          {t('session.send')}
        </Button>
      </div>
    </section>
  )
}

/** What a paid call costs, beside the question; a yes is for this one call. */
function Price({ quote }: { quote: Extract<Said, { kind: 'quote' }> }) {
  const { t } = useTranslation()
  if (quote.failed) {
    return <p data-price="unknown" className="w-full text-destructive">{t('session.unpriced', { why: quote.failed })}</p>
  }
  return (
    <div data-price={quote.price} className="w-full text-xs">
      <p className={quote.affordable ? '' : 'text-destructive'}>
        {t('session.price', { price: quote.price, unit: quote.unit, left: quote.left, after: quote.after })}
      </p>
      {quote.cheaper && <p className="text-muted-foreground">{t('session.cheaper', { how: quote.cheaper })}</p>}
      <p className="text-muted-foreground">{t('session.once')}</p>
    </div>
  )
}

function Turn({ read }: { read: Said }) {
  const { t } = useTranslation()
  switch (read.kind) {
    case 'text':
      return <li data-turn className="whitespace-pre-wrap">{read.text}</li>
    case 'tool':
      return <li className="font-mono text-xs text-muted-foreground">{t('session.used', { tool: read.tool })}</li>
    case 'check':
      return (
        <li
          data-check={read.passed === null ? 'none' : read.passed ? 'passed' : 'failed'}
          className={read.passed === false ? 'text-destructive' : 'text-muted-foreground'}
        >
          {t('session.checked', { said: read.said })}
        </li>
      )
    case 'answered':
      return <li className="whitespace-pre-wrap font-medium">{t('session.answered', { said: read.said })}</li>
    case 'closed':
      return (
        <li data-closed className="flex flex-col gap-1">
          <span className="font-medium">{t('session.closed', { sitting: read.sitting })}</span>
          {read.touched.length > 0 && (
            <span className="text-xs">{t('session.touched', { files: read.touched.join(', ') })}</span>
          )}
          {read.waiting.length > 0 && (
            <span className="text-xs text-amber-700">{t('session.waits', { files: read.waiting.join(', ') })}</span>
          )}
        </li>
      )
    case 'result':
      return (
        <li data-result={read.ok ? 'ok' : 'failed'} className={read.ok ? 'text-muted-foreground' : 'text-destructive'}>
          {t(read.ok ? 'session.done' : 'session.failed', { text: read.text })}
        </li>
      )
    default:
      return null
  }
}
