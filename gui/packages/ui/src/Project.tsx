// One project (§PW303, §PW304): its inventory by kind on the left, filterable by what
// needs a person, and one item on the right with what it was held to. Nothing here
// writes: what the window cannot draw itself is offered as the operation that would.

import { Button } from '@viglet/viglet-design-system'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { KINDS, type Bridge, type Desk, type Item, type Opened } from '@pw/core'

import { Decide } from './Decide'
import { ItemView } from './ItemView'

/** What the list can be narrowed to. */
export const FILTERS = ['all', 'pending', 'attention', 'revision'] as const
type Filter = (typeof FILTERS)[number]

/** Record states that mean the file and what made it no longer agree. */
const ATTENTION = new Set(['changed', 'missing', 'outdated', 'unrecorded'])

export function kept(items: Item[], filter: Filter, revised: string[] = []): Item[] {
  if (filter === 'revision') return items.filter((i) => revised.includes(i.id))
  if (filter === 'pending') return items.filter((i) => i.pending)
  if (filter === 'attention') return items.filter((i) => ATTENTION.has(i.record ?? ''))
  return items
}

export function Project({
  bridge,
  opened,
  items,
  moved = [],
  back,
}: {
  bridge: Bridge
  opened: Opened
  items: Item[]
  /** Ids whose digest moved since the window drew them (§PW310). */
  moved?: string[]
  back: () => void
}) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<Filter>('all')
  const [chosen, setChosen] = useState<Item | null>(null)
  // The digest of the item as the person was last shown it: a change to it is marked,
  // never swapped in silently, and the new one is shown when they ask (§PW310).
  const chosenDigest = chosen ? (items.find((i) => i.id === chosen.id)?.digest ?? null) : null
  const [seenAt, setSeenAt] = useState<string | null>(null)
  const [revised, setRevised] = useState<string[] | null>(null)
  useEffect(() => {
    void bridge.revisions(opened.project).then(setRevised, () => setRevised([]))
  }, [bridge, opened.project])
  // The project's verdicts are the decision screen, the same one the review page serves
  // in a browser (§PW403); "where it is judged" opens it on the item's card.
  const [deciding, setDeciding] = useState(false)
  const [member, setMember] = useState<string | null>(null)
  const judge = (on?: string | null) => {
    setMember(on ?? null)
    setDeciding(true)
  }
  const desk = useMemo<Desk>(
    () => ({
      state: () => bridge.reviewState(opened.project),
      words: () => bridge.reviewWords(opened.project),
      answer: (body) => bridge.reviewAnswer(opened.project, body),
      file: (path) => bridge.file(opened.project, path),
      compare: (old, now) => bridge.reviewCompare(opened.project, old, now),
      canon: () => bridge.reviewCanon(opened.project),
    }),
    [bridge, opened.project],
  )
  const shown = kept(items, filter, revised ?? [])
  const byKind = KINDS.map((kind) => [kind, shown.filter((i) => i.kind === kind)] as const).filter(
    ([, rows]) => rows.length > 0,
  )

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" onClick={back}>
          {t('project.back')}
        </Button>
        <h1 className="truncate text-2xl font-semibold">
          {opened.project.split(/[\\/]/).filter(Boolean).pop()}
        </h1>
      </div>
      <p className="truncate font-mono text-xs text-muted-foreground">{opened.project}</p>
      <p className="text-sm text-muted-foreground">
        {t('project.engine', {
          name: opened.server.name,
          version: opened.server.version,
          command:
            opened.engine.from === 'project' ? t('project.from_project') : t('project.from_path'),
        })}
      </p>
      <div className="flex gap-2">
        <Button size="sm" variant={deciding ? 'outline' : 'default'} onClick={() => setDeciding(false)}>
          {t('project.inventory')}
        </Button>
        <Button size="sm" variant={deciding ? 'default' : 'outline'} onClick={() => judge()}>
          {t('project.decide')}
        </Button>
      </div>
      {deciding ? (
        <Decide
          desk={desk}
          member={member}
        />
      ) : (
        <>
      <div className="flex flex-wrap items-center gap-2">
        <p data-count className="mr-auto text-sm">
          {t('project.items', { count: items.length })}
        </p>
        {FILTERS.map((one) => (
          <Button
            key={one}
            size="sm"
            variant={one === filter ? 'default' : 'outline'}
            onClick={() => setFilter(one)}
          >
            {t(`filter.${one}`)}
          </Button>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div className="flex flex-col gap-4">
          {byKind.length === 0 && <p className="text-muted-foreground">{t('project.empty')}</p>}
          {byKind.map(([kind, rows]) => (
            <section key={kind} data-kind={kind} className="flex flex-col gap-2">
              <h2 className="text-lg font-medium">
                {t(`kind.${kind}`)} <span className="text-muted-foreground">({rows.length})</span>
              </h2>
              <ul className="flex flex-col divide-y rounded-lg border">
                {rows.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      data-item={item.id}
                      aria-current={chosen?.id === item.id}
                      onClick={() => setChosen(item)}
                      className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 p-2 text-left text-sm hover:bg-muted aria-[current=true]:bg-muted"
                    >
                      <span className="min-w-32 flex-1 truncate font-mono">{item.id}</span>
                      {item.pending && (
                        <span className="shrink-0 text-xs text-amber-600">
                          {t('project.pending')}
                        </span>
                      )}
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {t(`record.${item.record ?? 'none'}`)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        <div>
          {chosen && moved.includes(chosen.id) && seenAt !== chosenDigest && (
            <div data-changed className="mb-2 flex items-center gap-2 rounded-md bg-amber-50 p-2 text-sm">
              <span className="flex-1">{t('item.changed')}</span>
              <Button size="sm" onClick={() => setSeenAt(chosenDigest)}>
                {t('item.see_new')}
              </Button>
            </div>
          )}
          {chosen ? (
            <ItemView
              key={`${chosen.id}@${seenAt ?? ''}`}
              bridge={bridge}
              project={opened.project}
              item={chosen}
              onJudge={() => judge(chosen.artefact)}
            />
          ) : (
            <p className="text-muted-foreground">{t('item.choose')}</p>
          )}
        </div>
      </div>
        </>
      )}
    </section>
  )
}
