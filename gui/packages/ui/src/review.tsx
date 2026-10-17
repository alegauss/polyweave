// The review page in a browser (§PW403): the same decision screen the window draws, over
// the page's own routes, so there is one screen and not two. Built by
// `npm run build:review` into src/polyweave/loop/review_page/screen, which
// `python -m polyweave review` serves; its stamp says which sources it was built from.

import './review.css'

import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

import { say, type Desk, type Words } from '@pw/core'

import { Decide } from './Decide'

/** Told while the server hands over to a fresh one on new code (§PW463). */
let restarting: (on: boolean) => void = () => {}

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/** A fetch, sent again while the server says it is starting again on new code: the
 * person's answer then lands on the fresh server instead of being refused (§PW463). */
async function reached(path: string, init?: RequestInit): Promise<Response> {
  let handed = false
  for (let tries = 0; ; tries += 1) {
    let answer: Response | null = null
    try {
      answer = await fetch(path, { cache: 'no-store', ...init })
    } catch (lost) {
      // Between the old server closing and the new one listening nothing answers, and
      // that is waited out only once the old one said it was handing over.
      if (!handed || tries >= 30) throw lost
    }
    if (answer?.status === 503) {
      const said = (await answer.clone().json().catch(() => ({}))) as { code?: string }
      handed = said.code === 'review.restarting'
    }
    if (answer && !(answer.status === 503 && handed)) {
      restarting(false)
      return answer
    }
    if (tries >= 30) return answer!
    restarting(true)
    await pause(1000)
  }
}

/** A route's JSON, or its refusal thrown as the code, the message and the remedy. */
async function asked<T>(path: string, init?: RequestInit): Promise<T> {
  const answer = await reached(path, init)
  const body = (await answer.json()) as T & { code?: string; message?: string; remedy?: string }
  if (!answer.ok) {
    throw new Error(`${body.code ?? answer.status}: ${body.message ?? ''}${body.remedy ? `\n${body.remedy}` : ''}`)
  }
  return body
}

const file = (path: string) => `/file?path=${encodeURIComponent(path)}`

const desk: Desk = {
  state: () => asked('/api/state'),
  words: async () => {
    // The page's words follow the project's language (§PW287).
    const { language } = await asked<{ language: string }>('/api/state')
    const catalog = await asked<{ page: Words['page']; kinds?: Words['kinds'] }>(
      `/locales/${encodeURIComponent(language)}.json`,
    )
    return { language, page: catalog.page, kinds: catalog.kinds ?? {} }
  },
  // The header is one a browser will not send across origins without asking first, so
  // another site open in the same browser cannot post a verdict here.
  answer: (body) =>
    asked('/api/judge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Polyweave': '1' },
      body: JSON.stringify(body),
    }),
  file: async (path) => {
    const answer = await fetch(file(path))
    const bytes = new Uint8Array(await answer.arrayBuffer())
    let text = ''
    for (const byte of bytes) text += String.fromCharCode(byte)
    return { path, mime: answer.headers.get('Content-Type') ?? '', base64: btoa(text) }
  },
  href: file,
  compare: (old, now) => asked(`/api/compare?old=${encodeURIComponent(old)}&new=${encodeURIComponent(now)}`),
  canon: () => asked('/api/canon'),
}

function Page() {
  const [words, setWords] = useState<Words | null>(null)
  const [project, setProject] = useState('')
  const [reloading, setReloading] = useState(false)
  useEffect(() => {
    restarting = setReloading
  }, [])
  useEffect(() => {
    void desk.words().then((found) => {
      setWords(found)
      document.documentElement.lang = found.language
      document.title = `${say(found, 'heading')} · polyweave`
    })
    void desk.state().then((found) => setProject(found.project ?? ''))
  }, [])
  // `?member=<path>` opens on the card a file is judged in (§PW305), as the window does.
  const member = new URLSearchParams(location.search).get('member')
  // `?sitting=<manifest>` is one sitting's own page, and no `sitting` the index of them
  // (§PW415), so a link to a sitting opens it alone and the back button leaves it.
  const [sitting, setSitting] = useState(() => new URLSearchParams(location.search).get('sitting'))
  useEffect(() => {
    const back = () => setSitting(new URLSearchParams(location.search).get('sitting'))
    addEventListener('popstate', back)
    return () => removeEventListener('popstate', back)
  }, [])
  const opened = (manifest: string | null) => {
    setSitting(manifest)
    const query = manifest ? `?sitting=${encodeURIComponent(manifest)}` : location.pathname
    history.pushState(null, '', query)
  }
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-4 p-4 sm:p-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{words ? say(words, 'heading') : ''}</h1>
        {project && <p className="text-sm text-muted-foreground">{project}</p>}
        {reloading && words && (
          <p data-restarting className="text-sm text-amber-700">{say(words, 'restarting')}</p>
        )}
      </header>
      <Decide desk={desk} member={member} sitting={sitting} onSitting={opened} />
    </main>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Page />
  </StrictMode>,
)
