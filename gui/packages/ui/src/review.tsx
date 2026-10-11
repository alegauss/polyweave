// The review page in a browser (§PW403): the same decision screen the window draws, over
// the page's own routes, so there is one screen and not two. Built by
// `npm run build:review` into src/polyweave/review_page/screen, which
// `python -m polyweave review` serves; its stamp says which sources it was built from.

import './review.css'

import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

import { say, type Desk, type Words } from '@pw/core'

import { Decide } from './Decide'

/** A route's JSON, or its refusal thrown as the code, the message and the remedy. */
async function asked<T>(path: string, init?: RequestInit): Promise<T> {
  const answer = await fetch(path, { cache: 'no-store', ...init })
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
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-4 p-4 sm:p-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{words ? say(words, 'heading') : ''}</h1>
        {project && <p className="text-sm text-muted-foreground">{project}</p>}
      </header>
      <Decide desk={desk} member={member} />
    </main>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Page />
  </StrictMode>,
)
