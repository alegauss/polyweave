// The window's first screen (§PW303): the projects under a folder a person names. Opening
// one hands it to the project screen.

import { Button, Input } from '@viglet/viglet-design-system'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { merged, type Bridge, type Item, type Opened } from '@pw/core'

import { Project } from './Project'

interface Shown {
  opened: Opened
  items: Item[]
  /** The ids whose digest moved in the last re-read, for the item on screen. */
  moved: string[]
}

/** A project being opened (§PW580): which one, and how far its inventory has been read. */
interface Opening {
  project: string
  read: number
  total: number | null
}

export function App({ bridge }: { bridge: Bridge }) {
  const { t, i18n } = useTranslation()
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

  const everything = async (project: string, page?: (read: number, total: number) => void) => {
    const items: Item[] = []
    let offset: number | null = 0
    while (offset !== null) {
      const read = await bridge.inventory(project, undefined, offset)
      items.push(...read.items)
      page?.(items.length, read.total)
      offset = read.next
    }
    return items
  }

  // While one project opens every "Open" is disabled, so a slow open is never a second read.
  const open = (project: string) => {
    if (opening) return
    setOpening({ project, read: 0, total: null })
    return attempt(async () => {
      const opened = await bridge.open(project)
      const items = await everything(project, (read, total) => setOpening({ project, read, total }))
      setShown({ opened, items, moved: [] })
    }).finally(() => setOpening(null))
  }

  const count = (n: number) => n.toLocaleString(i18n.language)

  // A burst of changes is one re-read, folded over what is on screen (§PW310).
  useEffect(
    () =>
      bridge.onChanged((project) => {
        void everything(project).then(
          (fresh) =>
            setShown((now) => {
              if (!now || now.opened.project !== project) return now
              const folded = merged(now.items, fresh)
              return { ...now, items: folded.items, moved: [...now.moved, ...folded.moved] }
            }),
          () => undefined,
        )
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bridge],
  )

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
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
          moved={shown.moved}
          back={() => setShown(null)}
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
                      {opening.total === null
                        ? t('projects.opening')
                        : t('projects.opening_read', {
                            read: count(opening.read),
                            total: count(opening.total),
                          })}
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
