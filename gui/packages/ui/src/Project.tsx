// One project (§PW303, §PW304): its inventory on the left, one tab per kind, filterable
// by what needs a person and searchable by path, and one item on the right with what it
// was held to. Nothing here writes: what the window cannot draw itself is offered as the
// operation that would.

import { Button, Input } from '@viglet/viglet-design-system'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { KINDS, type Bridge, type Desk, type Item, type Kind, type Opened } from '@pw/core'

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

/** A tab: one kind, with how many of its rows the list shows. */
export interface Tab {
  kind: Kind
  count: number
}

/**
 * The tabs the inventory draws (§PW684), in the inventory's order. Unnarrowed, each kind
 * the payload counts is a tab with the payload's count, so the tabs sum to the inventory
 * even while its later pages are still being read. Narrowed by a filter or a typed path,
 * a tab counts the rows that are left, and a kind with none is no tab.
 */
export function tabs(
  rows: Item[],
  kinds: Partial<Record<Kind, number>>,
  narrowed: boolean,
): Tab[] {
  return KINDS.map((kind) => ({
    kind,
    count: narrowed ? rows.filter((i) => i.kind === kind).length : (kinds[kind] ?? 0),
  })).filter((tab) => tab.count > 0)
}

/** The rows whose id holds the typed text, case aside. */
export function matching(items: Item[], query: string): Item[] {
  const typed = query.trim().toLowerCase()
  return typed ? items.filter((i) => i.id.toLowerCase().includes(typed)) : items
}

/** The height one row of the list is drawn at, which the window below counts in. */
export const ROW = 36

/**
 * Which rows a list of `count` draws, scrolled `top` pixels into a `height`-pixel view
 * (§PW684): the ones in view and `spare` on either side, so a kind of thousands draws a
 * screenful and not every row. A view not measured yet is taken as one screen.
 */
export function windowed(
  count: number,
  top: number,
  height: number,
  spare = 10,
): { from: number; to: number } {
  const view = height > 0 ? height : 720
  const from = Math.min(count, Math.max(0, Math.floor(top / ROW) - spare))
  const to = Math.min(count, Math.ceil((top + view) / ROW) + spare)
  return { from, to: Math.max(from, to) }
}

/** One kind's rows, drawn a screenful at a time as the list scrolls. */
function Rows({
  rows,
  chosen,
  choose,
}: {
  rows: Item[]
  chosen: Item | null
  choose: (item: Item) => void
}) {
  const { t } = useTranslation()
  const box = useRef<HTMLDivElement>(null)
  const [top, setTop] = useState(0)
  const [height, setHeight] = useState(0)
  useLayoutEffect(() => {
    const element = box.current
    if (!element) return
    setHeight(element.clientHeight)
    const watch = new ResizeObserver(() => setHeight(element.clientHeight))
    watch.observe(element)
    return () => watch.disconnect()
  }, [])
  const { from, to } = windowed(rows.length, top, height)
  return (
    <div
      ref={box}
      data-rows
      onScroll={(e) => setTop(e.currentTarget.scrollTop)}
      className="max-h-[70vh] overflow-y-auto rounded-lg border"
    >
      <ul style={{ height: rows.length * ROW, position: 'relative' }}>
        {rows.slice(from, to).map((item, at) => (
          <li
            key={item.id}
            style={{ position: 'absolute', top: (from + at) * ROW, height: ROW, left: 0, right: 0 }}
            className="border-b"
          >
            <button
              type="button"
              data-item={item.id}
              aria-current={chosen?.id === item.id}
              onClick={() => choose(item)}
              className="flex h-full w-full items-center gap-3 px-2 text-left text-sm hover:bg-muted aria-[current=true]:bg-muted"
            >
              <span className="min-w-0 flex-1 truncate font-mono" title={item.id}>
                {item.id}
              </span>
              {item.pending && (
                <span className="shrink-0 text-xs text-amber-600">{t('project.pending')}</span>
              )}
              <span className="shrink-0 text-xs text-muted-foreground">
                {t(`record.${item.record ?? 'none'}`)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function Project({
  bridge,
  opened,
  items,
  kinds,
  total,
  reading = false,
  moved = [],
  back,
}: {
  bridge: Bridge
  opened: Opened
  /** The rows read so far: the first page at once, the rest as it arrives (§PW684). */
  items: Item[]
  /** The payload's count by kind, for the whole inventory however much is read. */
  kinds: Partial<Record<Kind, number>>
  /** The payload's count of every row. */
  total: number
  /** Whether later pages are still being read. */
  reading?: boolean
  /** Ids whose digest moved since the window drew them (§PW310). */
  moved?: string[]
  back: () => void
}) {
  const { t, i18n } = useTranslation()
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<Kind | null>(null)
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
  const shown = matching(kept(items, filter, revised ?? []), query)
  const narrowed = filter !== 'all' || query.trim() !== ''
  const drawn = tabs(shown, kinds, narrowed)
  // The tab chosen stays chosen while it has rows; a narrowing that empties it moves to
  // the first tab left, so a typed name lands on the kind that holds it.
  const current = drawn.find((one) => one.kind === tab)?.kind ?? drawn[0]?.kind ?? null
  const rows = current ? shown.filter((i) => i.kind === current) : []

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
          {t('project.items', { count: total })}
          {reading && (
            <output className="ml-2 text-muted-foreground">
              {t('project.reading', {
                read: items.length.toLocaleString(i18n.language),
                total: total.toLocaleString(i18n.language),
              })}
            </output>
          )}
        </p>
        <Input
          type="search"
          aria-label={t('project.search')}
          placeholder={t('project.search')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-64"
        />
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
        <div className="flex min-w-0 flex-col gap-2">
          {total === 0 && <p className="text-muted-foreground">{t('project.empty')}</p>}
          {total > 0 && drawn.length === 0 && (
            <p className="text-muted-foreground">{t('project.no_match')}</p>
          )}
          {drawn.length > 0 && (
            <div role="tablist" className="flex flex-wrap gap-1 border-b pb-2">
              {drawn.map((one) => (
                <button
                  key={one.kind}
                  type="button"
                  role="tab"
                  data-kind={one.kind}
                  aria-selected={one.kind === current}
                  onClick={() => setTab(one.kind)}
                  className="rounded-md px-3 py-1 text-sm hover:bg-muted aria-selected:bg-muted aria-selected:font-medium"
                >
                  {t(`kind.${one.kind}`)} <span className="text-muted-foreground">({one.count})</span>
                </button>
              ))}
            </div>
          )}
          {current && (
            <div role="tabpanel" data-kind={current}>
              <Rows key={current} rows={rows} chosen={chosen} choose={setChosen} />
            </div>
          )}
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
