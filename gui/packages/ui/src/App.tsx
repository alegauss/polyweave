// The window's two screens (§PW303): the projects under a folder a person names, and one
// project's inventory, by kind, with the engine that answered named at the top.

import { Button, Input } from '@viglet/viglet-design-system'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { KINDS, type Bridge, type Item, type Kind, type Opened, type Smoke } from '@pw/core'

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

  useEffect(() => {
    if (!smoke || !shown) return
    // What was drawn, read back off the page, so the test asserts the screen and not the data.
    requestAnimationFrame(() => {
      void bridge.rendered({
        project: shown.opened.project,
        server: shown.opened.server.name,
        engine: shown.opened.engine.from,
        heading: document.querySelector('h1')?.textContent ?? '',
        count: document.querySelector('[data-count]')?.textContent ?? '',
        groups: [...document.querySelectorAll('[data-kind]')].map((g) => g.getAttribute('data-kind')),
        rows: document.querySelectorAll('[data-item]').length,
      })
    })
  }, [smoke, shown, bridge])

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
      {failed && (
        <p role="alert" className="text-destructive">
          {t('error.failed', { message: failed })}
        </p>
      )}
      {shown ? (
        <Project shown={shown} back={() => setShown(null)} />
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

function Project({ shown, back }: { shown: Shown; back: () => void }) {
  const { t } = useTranslation()
  const { opened, items } = shown
  const byKind = KINDS.map((kind) => [kind, items.filter((i) => i.kind === kind)] as const).filter(
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
      <p data-count className="text-sm">
        {t('project.items', { count: items.length })}
      </p>
      {byKind.length === 0 && <p className="text-muted-foreground">{t('project.empty')}</p>}
      {byKind.map(([kind, rows]) => (
        <Group key={kind} kind={kind} rows={rows} />
      ))}
    </section>
  )
}

function Group({ kind, rows }: { kind: Kind; rows: Item[] }) {
  const { t } = useTranslation()
  return (
    <section data-kind={kind} className="flex flex-col gap-2">
      <h2 className="text-lg font-medium">
        {t(`kind.${kind}`)} <span className="text-muted-foreground">({rows.length})</span>
      </h2>
      <ul className="flex flex-col divide-y rounded-lg border">
        {rows.map((item) => (
          <li data-item={item.id} key={item.id} className="flex items-center gap-3 p-2 text-sm">
            <span className="flex-1 truncate font-mono">{item.id}</span>
            {item.pending && <span className="text-amber-600">{t('project.pending')}</span>}
            <span className="text-muted-foreground">{t(`record.${item.record ?? 'none'}`)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
