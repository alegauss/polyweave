// The window's first screen (§PW303): the projects under a folder a person names. Opening
// one hands it to the project screen.

import { Button, Input } from '@viglet/viglet-design-system'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { merged, type Bridge, type Item, type Kind, type Opened } from '@pw/core'

import { Project } from './Project'

interface Shown {
  opened: Opened
  /** The rows read so far (§PW684): the first page, then each later one as it lands. */
  items: Item[]
  /** The payload's counts, which stand for the whole inventory from the first page on. */
  kinds: Partial<Record<Kind, number>>
  total: number
  /** Whether later pages are still being read. */
  reading: boolean
  /** The ids whose digest moved in the last re-read, for the item on screen. */
  moved: string[]
}

/** A project being opened (§PW580): which one, until its first page is on screen. */
interface Opening {
  project: string
}

export function App({ bridge }: { bridge: Bridge }) {
  const { t } = useTranslation()
  const [root, setRoot] = useState('')
  const [depth, setDepth] = useState(2)
  const [found, setFound] = useState<string[] | null>(null)
  const [shown, setShown] = useState<Shown | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [opening, setOpening] = useState<Opening | null>(null)

  const attempt = async <T,>(work: () => Promise<T>): Promise<T | undefined> => {
    setFailed(null)
    try {
      return await work()
    } catch (error) {
      setFailed(error instanceof Error ? error.message : String(error))
      return undefined
    }
  }

  const look = () => attempt(async () => setFound(await bridge.find(root, depth)))

  // Which read of the inventory is the live one: a later open, a re-read or going back
  // makes the pages an earlier read is still fetching land nowhere.
  const live = useRef(0)

  /** The pages after the first, each put on screen as it lands (§PW684). */
  const rest = async (project: string, mine: number, from: number | null) => {
    let offset = from
    try {
      while (offset !== null) {
        const read = await bridge.inventory(project, undefined, offset)
        if (mine !== live.current) return
        offset = read.next
        const done = offset === null
        setShown((now) =>
          now && now.opened.project === project
            ? { ...now, items: [...now.items, ...read.items], reading: !done }
            : now,
        )
      }
    } catch (error) {
      if (mine !== live.current) return
      // What was read stays on screen, and the page that failed is said.
      setShown((now) => (now && now.opened.project === project ? { ...now, reading: false } : now))
      setFailed(error instanceof Error ? error.message : String(error))
    }
  }

  // While one project opens every "Open" is disabled, so a slow open is never a second
  // read. The open waits on the first page alone: the screen shows it, and the pages
  // after it arrive behind it (§PW684).
  const open = (project: string) => {
    if (opening) return
    setOpening({ project })
    return attempt(async () => {
      const opened = await bridge.open(project)
      const mine = ++live.current
      const head = await bridge.inventory(project, undefined, 0)
      if (mine !== live.current) return
      setShown({
        opened,
        items: head.items,
        kinds: head.kinds,
        total: head.total,
        reading: head.next !== null,
        moved: [],
      })
      void rest(project, mine, head.next)
    }).finally(() => setOpening(null))
  }

  /** Every page from offset 0, for a re-read that replaces what is on screen. */
  const everything = async (project: string) => {
    const items: Item[] = []
    let kinds: Shown['kinds'] = {}
    let total = 0
    let offset: number | null = 0
    while (offset !== null) {
      const read = await bridge.inventory(project, undefined, offset)
      if (offset === 0) ({ kinds, total } = read)
      items.push(...read.items)
      offset = read.next
    }
    return { items, kinds, total }
  }

  // A burst of changes is one re-read, folded over what is on screen (§PW310). It takes
  // over from a read still paging, whose rows it holds as well.
  useEffect(
    () =>
      bridge.onChanged((project) => {
        const mine = ++live.current
        void everything(project).then(
          (fresh) => {
            if (mine !== live.current) return
            setShown((now) => {
              if (!now || now.opened.project !== project) return now
              const folded = merged(now.items, fresh.items)
              return {
                ...now,
                items: folded.items,
                kinds: fresh.kinds,
                total: fresh.total,
                reading: false,
                moved: [...now.moved, ...folded.moved],
              }
            })
          },
          () => undefined,
        )
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bridge],
  )

  return (
    // An open project takes the window's whole width (§PW686); the list of projects keeps
    // a reading column.
    <main className={shown ? 'flex flex-col gap-6 p-6' : 'mx-auto flex max-w-5xl flex-col gap-6 p-8'}>
      {failed && (
        <p role="alert" className="text-destructive">
          {t('error.failed', { message: failed })}
        </p>
      )}
      {shown ? (
        <Project
          bridge={bridge}
          opened={shown.opened}
          items={shown.items}
          kinds={shown.kinds}
          total={shown.total}
          reading={shown.reading}
          moved={shown.moved}
          back={() => {
            live.current += 1
            setShown(null)
          }}
        />
      ) : (
        <section className="flex flex-col gap-4">
          <h1 className="text-2xl font-semibold">{t('projects.heading')}</h1>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-80 flex-1 flex-col gap-1 text-sm">
              {t('projects.root')}
              <Input value={root} onChange={(e) => setRoot(e.target.value)} />
            </label>
            <label className="flex w-32 flex-col gap-1 text-sm">
              {t('projects.depth')}
              <Input
                type="number"
                min={0}
                max={8}
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
              />
            </label>
            <Button onClick={() => void look()} disabled={!root}>
              {t('projects.find')}
            </Button>
          </div>
          {found === null ? (
            <p className="text-muted-foreground">{t('projects.nothing_yet')}</p>
          ) : found.length === 0 ? (
            <p className="text-muted-foreground">{t('projects.none')}</p>
          ) : (
            <ul className="flex flex-col divide-y rounded-lg border" aria-busy={opening !== null}>
              {found.map((project) => (
                <li key={project} className="flex items-center justify-between gap-4 p-3">
                  <span className="truncate font-mono text-sm">{project}</span>
                  {opening?.project === project && (
                    <output className="text-sm text-muted-foreground">
                      {t('projects.opening')}
                    </output>
                  )}
                  <Button
                    variant="outline"
                    disabled={opening !== null}
                    onClick={() => void open(project)}
                  >
                    {t('projects.open')}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  )
}
