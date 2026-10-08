// The window's first screen (§PW303): the projects under a folder a person names. Opening
// one hands it to the project screen.

import { Button, Input } from '@viglet/viglet-design-system'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { Bridge, Item, Opened, Smoke } from '@pw/core'

import { Project } from './Project'

interface Shown {
  opened: Opened
  items: Item[]
}

export function App({ bridge, smoke }: { bridge: Bridge; smoke: Smoke | null }) {
  const { t } = useTranslation()
  const [root, setRoot] = useState(smoke?.root ?? '')
  const [depth, setDepth] = useState(smoke?.depth ?? 2)
  const [found, setFound] = useState<string[] | null>(null)
  const [shown, setShown] = useState<Shown | null>(null)
  const [failed, setFailed] = useState<string | null>(null)

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

  const open = (project: string) =>
    attempt(async () => {
      const opened = await bridge.open(project)
      const items: Item[] = []
      let offset: number | null = 0
      while (offset !== null) {
        const read = await bridge.inventory(project, undefined, offset)
        items.push(...read.items)
        offset = read.next
      }
      setShown({ opened, items })
    })

  // A smoke run drives itself: find under the root it was given, and open the first.
  useEffect(() => {
    if (!smoke) return
    void bridge.find(smoke.root, smoke.depth).then((projects) => {
      setFound(projects)
      if (projects[0]) void open(projects[0])
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
          smoke={smoke}
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
            <ul className="flex flex-col divide-y rounded-lg border">
              {found.map((project) => (
                <li key={project} className="flex items-center justify-between gap-4 p-3">
                  <span className="truncate font-mono text-sm">{project}</span>
                  <Button variant="outline" onClick={() => void open(project)}>
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
