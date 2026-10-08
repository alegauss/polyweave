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
}: {
  bridge: Bridge
  revision: string
  first: string
  onResult?: () => void
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
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bridge, revision],
  )

  const asks = heard.filter((h) => h.read.kind === 'ask') as { read: Extract<Said, { kind: 'ask' }> }[]
  const withdrawn = new Set(
    heard.flatMap((h) => (h.read.kind === 'withdrawn' ? [h.read.requestId] : [])),
  )
  const open = asks.filter((a) => !answered.includes(a.read.requestId) && !withdrawn.has(a.read.requestId))

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
        <div key={read.requestId} data-ask={read.tool} className="flex items-center gap-2 rounded bg-muted p-2 text-sm">
          <span className="flex-1">{t('session.asks', { tool: read.tool })}</span>
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

function Turn({ read }: { read: Said }) {
  const { t } = useTranslation()
  switch (read.kind) {
    case 'text':
      return <li data-turn className="whitespace-pre-wrap">{read.text}</li>
    case 'tool':
      return <li className="font-mono text-xs text-muted-foreground">{t('session.used', { tool: read.tool })}</li>
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
