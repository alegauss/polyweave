// One item beside what it was held to (§PW304): its viewer, its bar read back from
// `asset.brief`, the chain back to a purchase, and what was made from it. Read-only: a
// view the window cannot draw is offered as the operation that would, for the session.

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { Bridge, Item, Shown } from '@pw/core'

type Brief = Record<string, any>

/** How each kind is seen; the ones the window draws itself carry the file across. */
export function viewer(item: Item): 'picture' | 'sound' | 'line' | 'operation' {
  if (item.kind === 'line') return 'line'
  if (!item.artefact) return 'operation'
  if (/\.(png|jpe?g|webp|svg)$/i.test(item.artefact)) return 'picture'
  if (/\.(wav|ogg|mp3)$/i.test(item.artefact)) return 'sound'
  return 'operation'
}

/** The call that would draw what the window will not, by kind; the session runs it. */
export function offered(item: Item): string {
  const declared = item.declaration ?? item.id
  switch (item.kind) {
    case 'mesh':
      return item.artefact
        ? `shape.turntable --mesh ${item.artefact} --out review/${item.id}.turntable`
        : `geometry.build --source ${declared}`
    case 'clip':
      return `clip.read --path ${declared}`
    case 'vfx':
      return `vfx.preview --source ${declared} --out review/${item.id}`
    default:
      return `asset.brief --asset ${item.id}`
  }
}

export function ItemView({
  bridge,
  project,
  item,
  onDrawn,
}: {
  bridge: Bridge
  project: string
  item: Item
  onDrawn: () => void
}) {
  const { t } = useTranslation()
  const [brief, setBrief] = useState<Brief | null>(null)
  const [chain, setChain] = useState<string[] | null>(null)
  const [file, setFile] = useState<Shown | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const seen = viewer(item)

  useEffect(() => {
    let live = true
    const loads: Promise<unknown>[] = [
      bridge.brief(project, item.id).then((b) => live && setBrief(b)),
    ]
    if (item.artefact) {
      loads.push(
        bridge.lineage(project, item.artefact).then((found) => {
          const made = (found['generated'] as { chain: string[] }[] | undefined)?.[0]
          if (live) setChain(made ? made.chain : [])
        }),
      )
    }
    if (seen === 'picture' || seen === 'sound') {
      loads.push(bridge.file(project, item.artefact!).then((f) => live && setFile(f)))
    }
    Promise.all(loads)
      .catch((error: unknown) => live && setFailed(error instanceof Error ? error.message : String(error)))
      .finally(() => live && onDrawn())
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id])

  const source = file ? `data:${file.mime};base64,${file.base64}` : null
  const line = brief?.['declaration'] as Brief | undefined
  const spec = brief?.['spec'] as Brief | null | undefined
  const dependents = (brief?.['dependents'] as { artefact: string; kind: string }[]) ?? []

  return (
    <article className="flex flex-col gap-4 rounded-lg border p-4">
      <h2 className="truncate font-mono text-base">{item.id}</h2>
      {failed && <p role="alert" className="text-destructive">{t('error.failed', { message: failed })}</p>}

      <div data-viewer={seen} className="overflow-auto rounded-md bg-muted/40 p-2">
        {seen === 'picture' && source && (
          <img src={source} alt={item.id} className="max-w-none" style={{ imageRendering: 'pixelated' }} />
        )}
        {seen === 'sound' && source && (
          <audio controls loop={brief?.['loop'] === true} src={source} className="w-full" />
        )}
        {seen === 'line' && line && (
          <dl className="flex flex-col gap-1 text-sm">
            {Object.entries((line['text'] as Record<string, string>) ?? {}).map(([locale, text]) => (
              <div key={locale} className="flex gap-2">
                <dt className="w-16 shrink-0 font-mono text-muted-foreground">{locale}</dt>
                <dd data-said>{text}</dd>
              </div>
            ))}
            {line['speaker'] && (
              <p className="text-muted-foreground">{t('item.speaker', { who: line['speaker'] })}</p>
            )}
            <p className="text-muted-foreground">
              {line['verdict']
                ? t(line['verdict']['on_this_text'] ? 'item.judged' : 'item.judged_before', {
                    choice: line['verdict']['choice'],
                  })
                : t('item.not_judged')}
            </p>
          </dl>
        )}
        {seen === 'operation' && (
          <p className="text-sm">
            {t('item.offered')} <code className="font-mono">{offered(item)}</code>
          </p>
        )}
      </div>

      {brief?.['gate'] && (
        <section className="flex flex-col gap-1">
          <h3 className="font-medium">{t('item.gate')}</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div data-lane="kept">
              <p className="text-muted-foreground">{t('item.kept')}</p>
              <ul>
                {(brief['gate']['kept'] as string[]).map((where) => (
                  <li key={where} className={lane(where, item)}>
                    {where}
                  </li>
                ))}
              </ul>
            </div>
            <div data-lane="refused">
              <p className="text-muted-foreground">{t('item.refused')}</p>
              <ul>
                {(brief['gate']['refused'] as { picture: string; failed: string[] }[]).map((one) => (
                  <li key={one.picture} className={lane(one.picture, item)}>
                    {one.picture}
                    <span className="block text-xs text-muted-foreground">{one.failed.join('; ')}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      <section className="flex flex-col gap-1">
        <h3 className="font-medium">{t('item.bar')}</h3>
        {spec ? (
          <ul className="text-sm">
            {(spec['predicates'] as Brief[]).map((p) => (
              <li key={p['id']} data-predicate={p['id']} className="font-mono">
                {p['id']}: {p['measure']}
                {bound(p['min'], '≥')}
                {bound(p['max'], '≤')}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">{t('item.no_bar')}</p>
        )}
      </section>

      {item.artefact && (
        <section className="flex flex-col gap-1">
          <h3 className="font-medium">{t('item.chain')}</h3>
          <p className={chain?.length ? 'font-mono text-sm' : 'text-sm text-muted-foreground'}>
            {chain === null ? '…' : chain.length ? chain.join(' ← ') : t('item.authored')}
          </p>
        </section>
      )}

      <section className="flex flex-col gap-1">
        <h3 className="font-medium">{t('item.dependents')}</h3>
        {dependents.length ? (
          <ul className="text-sm">
            {dependents.map((d) => (
              <li key={d.artefact} data-dependent className="font-mono">
                {d.artefact}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">{t('item.no_dependents')}</p>
        )}
      </section>
    </article>
  )
}

/** A gate lane's entry, marked where it is the item being looked at. */
function lane(where: string, item: Item): string {
  return where === item.artefact ? 'font-mono font-semibold' : 'font-mono'
}

function bound(side: unknown, sign: string): string {
  if (side === undefined || side === null) return ''
  const value = typeof side === 'object' ? (side as Brief)['value'] : side
  const origin = typeof side === 'object' ? ` (${(side as Brief)['origin']})` : ''
  return ` ${sign} ${value}${origin}`
}
