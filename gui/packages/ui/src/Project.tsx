// One project (§PW303, §PW304): its inventory by kind on the left, filterable by what
// needs a person, and one item on the right with what it was held to. Nothing here
// writes: what the window cannot draw itself is offered as the operation that would.

import { Button } from '@viglet/viglet-design-system'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { KINDS, type Bridge, type Item, type Opened, type Smoke } from '@pw/core'

import { ItemView } from './ItemView'

/** What the list can be narrowed to. */
export const FILTERS = ['all', 'pending', 'attention'] as const
type Filter = (typeof FILTERS)[number]

/** Record states that mean the file and what made it no longer agree. */
const ATTENTION = new Set(['changed', 'missing', 'outdated', 'unrecorded'])

export function kept(items: Item[], filter: Filter): Item[] {
  if (filter === 'pending') return items.filter((i) => i.pending)
  if (filter === 'attention') return items.filter((i) => ATTENTION.has(i.record ?? ''))
  return items
}

export function Project({
  bridge,
  opened,
  items,
  smoke,
  back,
}: {
  bridge: Bridge
  opened: Opened
  items: Item[]
  smoke: Smoke | null
  back: () => void
}) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<Filter>('all')
  const [chosen, setChosen] = useState<Item | null>(
    items.find((i) => i.id === smoke?.item) ?? null,
  )
  const [drawn, setDrawn] = useState(false)
  const shown = kept(items, filter)
  const byKind = KINDS.map((kind) => [kind, shown.filter((i) => i.kind === kind)] as const).filter(
    ([, rows]) => rows.length > 0,
  )

  // A smoke run reports once the list, and the item it asked for, are on the page.
  useEffect(() => {
    if (!smoke || (chosen && !drawn)) return
    requestAnimationFrame(() => {
      void bridge.rendered({
        project: opened.project,
        server: opened.server.name,
        engine: opened.engine.from,
        heading: document.querySelector('h1')?.textContent ?? '',
        count: document.querySelector('[data-count]')?.textContent ?? '',
        groups: [...document.querySelectorAll('[data-kind]')].map((g) => g.getAttribute('data-kind')),
        rows: document.querySelectorAll('[data-item]').length,
        viewer: document.querySelector('[data-viewer]')?.getAttribute('data-viewer') ?? null,
        bar: document.querySelectorAll('[data-predicate]').length,
        dependents: document.querySelectorAll('[data-dependent]').length,
        said: document.querySelector('[data-said]')?.textContent ?? null,
      })
    })
  }, [smoke, chosen, drawn, bridge, opened])

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
                      onClick={() => {
                        setDrawn(false)
                        setChosen(item)
                      }}
                      className="flex w-full items-center gap-3 p-2 text-left text-sm hover:bg-muted aria-[current=true]:bg-muted"
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
          {chosen ? (
            <ItemView
              key={chosen.id}
              bridge={bridge}
              project={opened.project}
              item={chosen}
              onDrawn={() => setDrawn(true)}
            />
          ) : (
            <p className="text-muted-foreground">{t('item.choose')}</p>
          )}
        </div>
      </div>
    </section>
  )
}
